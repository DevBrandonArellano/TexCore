from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
import logging
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, IsAdminUser, AllowAny
from gestion.permissions import IsSystemAdmin, IsTintoreroOrAdmin, IsAdminSistemasOrSede, IsJefeAreaOrAdmin
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.pago_reversion import PagoReversionService
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db.models import Count
from gestion.models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente, PagoCliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Maquina,
    Proveedor, FaseReceta
)
from gestion.utils import PrintingService, PaymentReconciler
from gestion.serializers import (
    GroupSerializer, SedeSerializer, AreaSerializer, CustomUserSerializer, ProductoSerializer,
    BatchSerializer, BodegaSerializer, ProcessStepSerializer,
    FormulaColorSerializer, FormulaColorWriteSerializer,
    DetalleFormulaSerializer, DosificacionSerializer,
    ClienteSerializer, ClienteListSerializer, OrdenProduccionSerializer, OrdenProduccionEstadoSerializer,
    LoteProduccionSerializer, PedidoVentaSerializer, DetallePedidoSerializer,
    MaquinaSerializer, RegistrarLoteProduccionSerializer, PagoClienteSerializer,
    ProveedorSerializer, AnulacionPedidoSerializer, ModificacionPedidoSerializer,
)
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db.models import Sum, F, Avg, DurationField, ExpressionWrapper, Q
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


from django.db.models import OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]


class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]


class FormulaColorViewSet(viewsets.ModelViewSet):
    queryset = FormulaColor.objects.prefetch_related('fases__detalles__producto').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return FormulaColorWriteSerializer
        return FormulaColorSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'calcular_dosificacion']:
            return [IsAuthenticated()]
        if self.action == 'destroy':
            # Solo admin puede eliminar formulas; tintorero no tiene delete
            return [IsAuthenticated(), IsSystemAdmin()]
        # create, update, partial_update, duplicar: tintorero o admin
        return [IsAuthenticated(), IsTintoreroOrAdmin()]

    def perform_destroy(self, instance):
        from gestion.middleware import set_cascade_justification, clear_cascade_justification
        # Extraer justificacion de query params, headers o body
        justificacion = self.request.query_params.get('_justificacion_auditoria') or \
                        self.request.headers.get('X-Justificacion-Auditoria')
        if not justificacion:
            justificacion = self.request.data.get('_justificacion_auditoria')
        # Fallback: admin ya paso el permiso IsSystemAdmin; auditoria con motivo generico
        if not justificacion:
            justificacion = "Eliminación desde panel de administración"
        instance._justificacion_auditoria = justificacion
        set_cascade_justification(justificacion)  # Para DetalleFormula eliminados en cascada
        try:
            instance.delete()
        finally:
            clear_cascade_justification()

    def perform_create(self, serializer):
        save_kwargs = {'creado_por': self.request.user}
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
             save_kwargs['sede'] = user.sede
        serializer.save(**save_kwargs)

    def get_queryset(self):
        user = self.request.user
        qs = FormulaColor.objects.prefetch_related('fases__detalles__producto').all()
        # Multi-tenancy: Superusers, admin_sistemas y ejecutivos pueden ver todas las sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            qs = qs.filter(sede=user.sede)
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)
        tipo_sustrato = self.request.query_params.get('tipo_sustrato')
        if tipo_sustrato:
            qs = qs.filter(tipo_sustrato=tipo_sustrato)
        return qs

    @action(detail=True, methods=['post'], url_path='calcular-dosificacion')
    def calcular_dosificacion(self, request, pk=None):
        """
        Calcula la dosificacion de cada insumo quimico de la formula dado un peso
        de tela y una relacion de bano.

        POST /api/formula-colors/{id}/calcular-dosificacion/
        Body: { "kg_tela": 100, "relacion_bano": 10 }
        """
        from gestion.services_formula import DosificacionCalculator
        formula = self.get_object()

        serializer = DosificacionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        calculator = DosificacionCalculator(formula)
        resultado = calculator.calcular(
            kg_tela=serializer.validated_data['kg_tela'],
            relacion_bano=serializer.validated_data['relacion_bano'],
        )

        insumos_data = [
            {
                'producto_id': r.producto_id,
                'producto_descripcion': r.producto_descripcion,
                'tipo_calculo': r.tipo_calculo,
                'cantidad_kg': str(r.cantidad_kg),
                'cantidad_gr': str(r.cantidad_gr),
                'concentracion_gr_l': str(r.concentracion_gr_l) if r.concentracion_gr_l is not None else None,
                'porcentaje': str(r.porcentaje) if r.porcentaje is not None else None,
                'orden_adicion': r.orden_adicion,
                'notas': r.notas,
            }
            for r in resultado.insumos
        ]

        return Response({
            'formula_id': formula.id,
            'formula_nombre': formula.nombre_color,
            'formula_version': formula.version,
            'kg_tela': str(resultado.kg_tela),
            'relacion_bano': str(resultado.relacion_bano),
            'volumen_bano_litros': str(resultado.volumen_bano_litros),
            'insumos': insumos_data,
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='duplicar')
    def duplicar(self, request, pk=None):
        """
        Crea una nueva version de la formula copiando todos sus detalles.
        La version original permanece intacta.
        La nueva copia queda en estado 'en_pruebas' con version incrementada.

        POST /api/formula-colors/{id}/duplicar/
        """
        formula_original = self.get_object()

        # Calcular el numero de version mas alto para este codigo de color base
        max_version = FormulaColor.objects.filter(
            codigo__startswith=formula_original.codigo.split('-v')[0]
        ).order_by('-version').values_list('version', flat=True).first() or formula_original.version

        nueva_version = max_version + 1
        codigo_base = formula_original.codigo.split('-v')[0]

        nueva_formula = FormulaColor.objects.create(
            codigo=f"{codigo_base}-v{nueva_version}",
            nombre_color=f"{formula_original.nombre_color} (v{nueva_version})",
            description=formula_original.description,
            tipo_sustrato=formula_original.tipo_sustrato,
            version=nueva_version,
            estado='en_pruebas',
            creado_por=request.user,
        )

        # Recorrer fases y sus detalles para copiar
        for fase_original in formula_original.fases.all():
            fase_nueva = FaseReceta.objects.create(
                formula=nueva_formula,
                nombre=fase_original.nombre,
                orden=fase_original.orden,
                temperatura=fase_original.temperatura,
                tiempo=fase_original.tiempo,
                observaciones=fase_original.observaciones
            )
            for detalle in fase_original.detalles.all():
                DetalleFormula.objects.create(
                    fase=fase_nueva,
                    producto=detalle.producto,
                    gramos_por_kilo=detalle.gramos_por_kilo,
                    tipo_calculo=detalle.tipo_calculo,
                    concentracion_gr_l=detalle.concentracion_gr_l,
                    porcentaje=detalle.porcentaje,
                    orden_adicion=detalle.orden_adicion,
                    notas=detalle.notas,
                )

        return Response(
            FormulaColorSerializer(nueva_formula, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='exportar-dosificador')
    def exportar_dosificador(self, request, pk=None):
        """
        Genera el archivo o estructura de datos para enviarse a la cocina de colores
        (Infotint, Lawer, Datatex) organizados por Fase de proceso.
        """
        formula = self.get_object()
        fases = formula.fases.prefetch_related('detalles__producto').order_by('orden')

        # Simularemos un formato estandar de integracion de receta:
        ticket = {
            "recipe_code": formula.codigo,
            "recipe_name": formula.nombre_color,
            "version": formula.version,
            "substrate": formula.tipo_sustrato,
            "phases": []
        }

        for fase in fases:
            fase_data = {
                "phase_name": fase.get_nombre_display(),
                "order": fase.orden,
                "temperature": fase.temperatura,
                "time": fase.tiempo,
                "chemicals": []
            }
            for det in fase.detalles.all():
                fase_data["chemicals"].append({
                    "product_code": det.producto.codigo,
                    "product_name": det.producto.descripcion,
                    "calculation_type": det.tipo_calculo,
                    "concentration_g_l": float(det.concentracion_gr_l) if det.concentracion_gr_l else None,
                    "percentage": float(det.porcentaje) if det.porcentaje else None,
                    "sequence": det.orden_adicion
                })
            ticket["phases"].append(fase_data)

        # En un sistema real esto generaria un archivo .xml o .csv
        # Aqui, devolvemos un payload JSON que el frontend puede descargar
        return Response(ticket, status=status.HTTP_200_OK)



class DetalleFormulaViewSet(viewsets.ModelViewSet):
    serializer_class = DetalleFormulaSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        if self.action == 'destroy':
            return [IsAuthenticated(), IsSystemAdmin()]
        return [IsAuthenticated(), IsTintoreroOrAdmin()]

    def get_queryset(self):
        qs = DetalleFormula.objects.select_related('producto', 'formula_color').all()
        formula_color_id = self.request.query_params.get('formula_color')
        if formula_color_id:
            qs = qs.filter(formula_color_id=formula_color_id)
        return qs


