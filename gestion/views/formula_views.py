import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from gestion.permissions import IsSystemAdmin, IsTintoreroOrAdmin
from gestion.models import (
    ProcessStep, FormulaColor, DetalleFormula, FaseReceta, ProcesoTintoreria, VersionFormula,
)
from gestion.serializers import (
    ProcessStepSerializer, ProcesoTintoreriaSerializer,
    FormulaColorSerializer, FormulaColorWriteSerializer, DetalleFormulaSerializer,
    DosificacionSerializer, VersionFormulaResumenSerializer, VersionFormulaSerializer,
    AprobarFormulaSerializer, CrearVarianteSerializer,
)
from gestion.services.versionado_formula import VersionadoFormulaService
from ._common import SedeAutoAssignMixin, AuditedDestroyMixin

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]


def _filtrar_por_sede_usuario(qs, request):
    """Multi-tenancy: superusers, admin_sistemas y ejecutivos ven todas las sedes."""
    user = request.user
    if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
        qs = qs.filter(sede=user.sede)
    sede_id = request.query_params.get('sede_id', request.query_params.get('sede', None))
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return qs


class ProcesoTintoreriaViewSet(SedeAutoAssignMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                               mixins.CreateModelMixin, viewsets.GenericViewSet):
    """GET/POST /procesos-tintoreria/ — catálogo de procesos por sede (spec 2026-09-24 §7).
    Sin update/delete: un proceso en uso por recetas está protegido (FaseReceta.proceso PROTECT)."""
    serializer_class = ProcesoTintoreriaSerializer
    permission_classes = [IsAuthenticated, IsTintoreroOrAdmin]

    def get_queryset(self):
        qs = _filtrar_por_sede_usuario(ProcesoTintoreria.objects.all(), self.request)
        activo = self.request.query_params.get('activo')
        if activo is not None:
            qs = qs.filter(activo=activo.lower() in ('1', 'true'))
        return qs


class FormulaColorViewSet(SedeAutoAssignMixin, AuditedDestroyMixin, viewsets.ModelViewSet):
    queryset = FormulaColor.objects.prefetch_related('fases__proceso', 'fases__detalles__producto').all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return FormulaColorWriteSerializer
        return FormulaColorSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'calcular_dosificacion',
                           'versiones', 'version_detalle', 'version_diff']:
            return [IsAuthenticated()]
        if self.action == 'destroy':
            # Solo admin puede eliminar formulas; tintorero no tiene delete
            return [IsAuthenticated(), IsSystemAdmin()]
        # create, update, partial_update, duplicar, aprobar: tintorero o admin (regla 9)
        return [IsAuthenticated(), IsTintoreroOrAdmin()]

    def get_perform_create_extra_kwargs(self, serializer):
        return {'creado_por': self.request.user}

    def get_queryset(self):
        oficial = VersionFormula.objects.filter(formula=OuterRef('pk'), es_oficial=True).values('numero')[:1]
        qs = _filtrar_por_sede_usuario(
            FormulaColor.objects.prefetch_related('fases__proceso', 'fases__detalles__producto')
            .annotate(numero_version_oficial=Subquery(oficial)),
            self.request)
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
        Crea una VARIANTE: una fórmula nueva, en pruebas y sin versiones, que copia la
        receta de la original. No es una versión (esas se crean al aprobar o al editar
        una fórmula aprobada, ver acción `aprobar`).

        POST /api/formula-colors/{id}/duplicar/
        Body: { "codigo": "...", "nombre_color": "..." }
        """
        formula_original = self.get_object()
        entrada = CrearVarianteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)

        with transaction.atomic():
            try:
                nueva_formula = FormulaColor.objects.create(
                    codigo=entrada.validated_data['codigo'],
                    nombre_color=entrada.validated_data['nombre_color'],
                    description=formula_original.description,
                    tipo_sustrato=formula_original.tipo_sustrato,
                    observaciones=formula_original.observaciones,
                    estado='en_pruebas',
                    sede=formula_original.sede,
                    creado_por=request.user,
                )
            except DjangoValidationError as e:
                raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

            for fase_original in formula_original.fases.select_related('proceso').prefetch_related('detalles'):
                fase_nueva = FaseReceta.objects.create(
                    formula=nueva_formula,
                    proceso=fase_original.proceso,
                    ciclo=fase_original.ciclo,
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

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        """POST /formula-colors/{id}/aprobar/ — body {motivo}. Crea la versión oficial (regla 2)."""
        formula = self.get_object()
        entrada = AprobarFormulaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        try:
            version = VersionadoFormulaService.aprobar(formula, entrada.validated_data['motivo'], request.user)
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
        return Response(VersionFormulaSerializer(version).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='versiones')
    def versiones(self, request, pk=None):
        """GET /formula-colors/{id}/versiones/ — historial, de la más reciente a la más antigua."""
        formula = self.get_object()
        versiones = formula.versiones.select_related('creada_por').order_by('-numero')
        return Response(VersionFormulaResumenSerializer(versiones, many=True).data)

    @action(detail=True, methods=['get'], url_path=r'versiones/(?P<numero>\d+)', url_name='version-detalle')
    def version_detalle(self, request, pk=None, numero=None):
        """GET /formula-colors/{id}/versiones/{n}/ — una versión con su snapshot. Sin update/delete."""
        version = get_object_or_404(
            VersionFormula.objects.select_related('creada_por'), formula=self.get_object(), numero=numero)
        return Response(VersionFormulaSerializer(version).data)

    @action(detail=True, methods=['get'], url_path=r'versiones/(?P<numero_a>\d+)/diff/(?P<numero_b>\d+)',
            url_name='version-diff')
    def version_diff(self, request, pk=None, numero_a=None, numero_b=None):
        """GET /formula-colors/{id}/versiones/{a}/diff/{b}/ — cambios de la versión A a la B."""
        formula = self.get_object()
        version_a = get_object_or_404(VersionFormula, formula=formula, numero=numero_a)
        version_b = get_object_or_404(VersionFormula, formula=formula, numero=numero_b)
        return Response({
            'formula_id': formula.id,
            'a': version_a.numero,
            'b': version_b.numero,
            'cambios': VersionadoFormulaService.diff(version_a.snapshot, version_b.snapshot),
        })

    @action(detail=True, methods=['get'], url_path='exportar-dosificador')
    def exportar_dosificador(self, request, pk=None):
        """
        Genera el archivo o estructura de datos para enviarse a la cocina de colores
        (Infotint, Lawer, Datatex) organizados por Fase de proceso.
        """
        formula = self.get_object()
        fases = formula.fases.select_related('proceso').prefetch_related('detalles__producto').order_by('orden')

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
                "phase_name": fase.proceso.nombre,
                "order": fase.orden,
                "cycle": fase.ciclo,
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
        # DetalleFormula se relaciona con la fórmula vía fase.formula (no hay FK
        # directo 'formula_color'); usar la relación real evita un FieldError.
        qs = DetalleFormula.objects.select_related('producto', 'fase__formula').all()
        formula_color_id = self.request.query_params.get('formula_color')
        if formula_color_id:
            qs = qs.filter(fase__formula_id=formula_color_id)
        return qs
