from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, IsAdminUser, AllowAny
from .permissions import IsSystemAdmin, IsTintoreroOrAdmin, IsAdminSistemasOrSede, IsJefeAreaOrAdmin
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db.models import Count
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente, PagoCliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Maquina,
    Proveedor, FaseReceta
)
from .utils import PrintingService, PaymentReconciler
from .serializers import (
    GroupSerializer, SedeSerializer, AreaSerializer, CustomUserSerializer, ProductoSerializer,
    BatchSerializer, BodegaSerializer, ProcessStepSerializer,
    FormulaColorSerializer, FormulaColorWriteSerializer,
    DetalleFormulaSerializer, DosificacionSerializer,
    ClienteSerializer, ClienteListSerializer, OrdenProduccionSerializer, OrdenProduccionEstadoSerializer,
    LoteProduccionSerializer, PedidoVentaSerializer, DetallePedidoSerializer,
    MaquinaSerializer, RegistrarLoteProduccionSerializer, PagoClienteSerializer,
    ProveedorSerializer
)
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db.models import Sum, F, Avg, DurationField, ExpressionWrapper
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

# Vistas refactorizadas usando Django ORM y ModelViewSet

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

from django.db.models import OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce

class SedeViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # Optimización: usando Subqueries en lugar de Count con JOINs (más eficiente para grandes volúmenes)
        return Sede.objects.annotate(
            num_areas=Coalesce(
                Subquery(Area.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_users=Coalesce(
                Subquery(CustomUser.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_bodegas=Coalesce(
                Subquery(Bodega.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_ordenes=Coalesce(
                Subquery(OrdenProduccion.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_pedidos=Coalesce(
                Subquery(PedidoVenta.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            )
        ).all()



    serializer_class = SedeSerializer

    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

class AreaViewSet(viewsets.ModelViewSet):
    serializer_class = AreaSerializer
    
    def get_queryset(self):
        queryset = Area.objects.all()
        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'reporte_eficiencia']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

    @action(detail=True, methods=['get'], url_path='reporte-eficiencia')
    def reporte_eficiencia(self, request, pk=None):
        from django.db.models import Sum, Count, Min, Max, FloatField
        from django.db.models.functions import Cast
        from datetime import date
        area = self.get_object()
        hoy = date.today()

        # 1. Métricas de Máquinas — una sola query con anotaciones (resuelve N+1)
        maquinas = area.maquina_set.annotate(
            produccion_hoy=Sum(
                'loteproduccion__peso_neto_producido',
                filter=models.Q(loteproduccion__hora_final__date=hoy),
            )
        ).values('id', 'nombre', 'capacidad_maxima', 'produccion_hoy')

        maquinas_data = []
        for m in maquinas:
            produccion = m['produccion_hoy'] or 0
            cap = m['capacidad_maxima'] or 0
            eficiencia = (Decimal(str(produccion)) / cap * 100) if cap > 0 else 0
            maquinas_data.append({
                "maquina_id": m['id'],
                "maquina_nombre": m['nombre'],
                "capacidad_maxima": cap,
                "produccion_total": produccion,
                "eficiencia": round(eficiencia, 2),
            })

        # 2. Métricas de Operarios — una sola query con anotaciones (resuelve N+1)
        operarios = CustomUser.objects.filter(
            area=area, groups__name='operario'
        ).annotate(
            total_lotes=Count(
                'loteproduccion',
                filter=models.Q(loteproduccion__hora_final__date=hoy),
                distinct=True,
            ),
            produccion_total_kg=Sum(
                'loteproduccion__peso_neto_producido',
                filter=models.Q(loteproduccion__hora_final__date=hoy),
            ),
            hora_inicio_min=Min(
                'loteproduccion__hora_inicio',
                filter=models.Q(loteproduccion__hora_final__date=hoy),
            ),
            hora_final_max=Max(
                'loteproduccion__hora_final',
                filter=models.Q(loteproduccion__hora_final__date=hoy),
            ),
        ).values('id', 'username', 'total_lotes', 'produccion_total_kg', 'hora_inicio_min', 'hora_final_max')

        operarios_data = []
        for op in operarios:
            total_kg = op['produccion_total_kg'] or 0
            count = op['total_lotes'] or 0
            horas = 0
            if op['hora_final_max'] and op['hora_inicio_min']:
                duration = op['hora_final_max'] - op['hora_inicio_min']
                horas = duration.total_seconds() / 3600
            operarios_data.append({
                "operario_id": op['id'],
                "username": op['username'],
                "total_lotes": count,
                "produccion_total_kg": total_kg,
                "promedio_kg_por_lote": round(total_kg / count, 2) if count > 0 else 0,
                "horas_trabajadas_aprox": round(horas, 2),
                "productividad_kg_hora": round(float(total_kg) / horas, 2) if horas > 0 else 0,
            })

        total_area = sum(m['produccion_total'] for m in maquinas_data)
        ef_promedio = sum(m['eficiencia'] for m in maquinas_data) / len(maquinas_data) if maquinas_data else 0

        return Response({
            "area_id": area.id,
            "area_nombre": area.nombre,
            "fecha_reporte": hoy,
            "maquinas": maquinas_data,
            "operarios": operarios_data,
            "produccion_total_area": total_area,
            "eficiencia_promedio_area": round(ef_promedio, 2),
        })

class MaquinaViewSet(viewsets.ModelViewSet):
    queryset = Maquina.objects.all()
    serializer_class = MaquinaSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        if self.request.user.groups.filter(name__in=['jefe_area', 'jefe_planta', 'admin_sistemas']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        queryset = Maquina.objects.select_related('area').all()
        
        # Security: Jefe de Área only sees their area machines
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)
        
        area_id = self.request.query_params.get('area', None)
        if area_id:
            queryset = queryset.filter(area_id=area_id)
            
        return queryset

    @action(detail=True, methods=['get'], url_path='eficiencia')
    def eficiencia(self, request, pk=None):
        maquina = self.get_object()
        from django.db.models import Sum
        from datetime import date
        
        produccion = LoteProduccion.objects.filter(
            maquina=maquina, 
            hora_final__date=date.today()
        ).aggregate(total=Sum('peso_neto_producido'))['total'] or 0
        
        eficiencia = (Decimal(str(produccion)) / maquina.capacidad_maxima * 100) if maquina.capacidad_maxima > 0 else 0
        
        return Response({
            "maquina": maquina.nombre,
            "capacidad_maxima": maquina.capacidad_maxima,
            "produccion_hoy": produccion,
            "eficiencia_porcentaje": round(eficiencia, 2)
        })

class CustomUserViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'desempeno', 'vendedores']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.select_related('sede', 'area').prefetch_related('groups').all()
        
        # Security: Jefe de Área only sees their area members by default
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)

        # Multi-tenancy: Superusers, admin_sistemas y ejecutivos pueden ver todas las sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(sede=user.sede)

        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id is not None:
            queryset = queryset.filter(sede_id=sede_id)
        
        area_id = self.request.query_params.get('area', None)
        if area_id is not None:
            queryset = queryset.filter(area_id=area_id)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='vendedores')
    def vendedores(self, request):
        """
        Lista vendedores para filtros en dashboards (ejecutivo/admin).
        """
        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()):
            return Response({"detail": "No autorizado."}, status=status.HTTP_403_FORBIDDEN)

        qs = CustomUser.objects.filter(groups__name='vendedor').distinct()

        # Para roles gerenciales, permitir ver vendedores de todas las sedes.
        # Para otros roles, mantener el ámbito por sede.
        if not (user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()):
            qs = qs.filter(sede=user.sede)

        data = list(
            qs.order_by('username').values('id', 'username', 'first_name', 'last_name')
        )
        return Response(data)

    @action(detail=True, methods=['get'], url_path='desempeno')
    def desempeno(self, request, pk=None):
        operario = self.get_object()
        from django.db.models import Sum, Count
        from datetime import date
        
        lotes = LoteProduccion.objects.filter(operario=operario).order_by('-hora_final')[:50]
        summary = LoteProduccion.objects.filter(operario=operario, hora_final__date=date.today()).aggregate(
            total_kg=Sum('peso_neto_producido'),
            count=Count('id')
        )
        
        return Response({
            "operario": operario.username,
            "produccion_hoy_kg": summary['total_kg'] or 0,
            "lotes_hoy": summary['count'] or 0,
            "ultimos_lotes": LoteProduccionSerializer(lotes, many=True).data
        })

class ChemicalViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        queryset = Producto.objects.filter(tipo__in=['quimico', 'insumo'])
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        # create/update/delete: admin_sistemas y admin_sede (consistente con setup_permissions)
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        user = self.request.user
        queryset = Producto.objects.all()
        
        # Multi-tenancy: Solo restringir si el usuario no es admin global
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            from django.db.models import Q
            queryset = queryset.filter(Q(sede=user.sede) | Q(sede__isnull=True))

        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

        # Security Filter: Salesmen strictly cannot see chemicals or inputs
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(tipo__in=['hilo', 'tela', 'subproducto'])

        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            tipos = [t.strip() for t in tipo.split(',')]
            queryset = queryset.filter(tipo__in=tipos)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = Proveedor.objects.all()
        # Multi-tenancy: Superusers, admin_sistemas y ejecutivos pueden ver todas las sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            from django.db.models import Q
            qs = qs.filter(Q(sede=user.sede) | Q(sede__isnull=True))
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]

class BodegaViewSet(viewsets.ModelViewSet):
    serializer_class = BodegaSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        user = self.request.user
        base = Bodega.objects.prefetch_related('usuarios_asignados')
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists():
            if sede_id:
                return base.filter(sede_id=sede_id)
            return base
        # Bodegueros y otros: solo bodegas asignadas
        qs = base.filter(id__in=user.bodegas_asignadas.values_list('id', flat=True))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        
        # Opcional: Asegurar que si es una bodega global asignada también se vea (ya cubierto por id__in)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

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
        from .middleware import set_cascade_justification, clear_cascade_justification
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
        from .services_formula import DosificacionCalculator
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


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ClienteListSerializer
        return ClienteSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Cliente.objects.all()
        
        # Solo prefecheamos si es detalle o si realmente necesitamos ver pedidos anidados
        if self.action != 'list':
            queryset = queryset.prefetch_related(
                'pedidoventa_set',
                'pedidoventa_set__detalles',
                'pedidoventa_set__detalles__producto'
            )

        # Filtro opcional por vendedor (solo para roles con visión gerencial/sistemas)
        vendedor_id = self.request.query_params.get('vendedor_id')
        vendedor_username = self.request.query_params.get('vendedor_username')
        if (vendedor_id or vendedor_username) and (
            user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()
        ):
            if vendedor_id:
                try:
                    queryset = queryset.filter(vendedor_asignado_id=int(vendedor_id))
                except (TypeError, ValueError):
                    pass
            elif vendedor_username:
                queryset = queryset.filter(vendedor_asignado__username=vendedor_username)
        
        # Multi-tenancy: Superusers, system admins and executives can see all sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(sede=user.sede)

        # If user is a salesman, only show their assigned clients
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(vendedor_asignado=user)
        
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
            
        return queryset.all()

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}
        
        # Auto-asignar vendedor si el usuario pertenece al grupo 'vendedor'
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
             save_kwargs['vendedor_asignado'] = user
        
        # Auto-asignar sede del usuario si no se proporcionó una explícitamente
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            save_kwargs['sede'] = user.sede
            
        serializer.save(**save_kwargs)

    def perform_destroy(self, instance):
        from .middleware import set_cascade_justification, clear_cascade_justification
        justificacion = self.request.query_params.get('_justificacion_auditoria') or \
                        self.request.headers.get('X-Justificacion-Auditoria') or \
                        self.request.data.get('_justificacion_auditoria')
        if not justificacion:
            justificacion = "Eliminación desde panel de administración"
        instance._justificacion_auditoria = justificacion
        set_cascade_justification(justificacion)
        try:
            instance.delete()
        finally:
            clear_cascade_justification()

class OrdenProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = OrdenProduccionSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        if self.request.user.groups.filter(name__in=['jefe_area', 'jefe_planta', 'admin_sistemas', 'admin_sede']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        user = self.request.user
        queryset = OrdenProduccion.objects.select_related(
            'producto', 'formula_color', 'sede', 'area', 'maquina_asignada', 'operario_asignado', 'bodega'
        ).prefetch_related('lotes').all()
        
        # Filter by area if user is a Jefe de Área
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)
        
        # Filter for operators: only show assigned orders
        if user.groups.filter(name='operario').exists() and not user.is_superuser:
            queryset = queryset.filter(operario_asignado=user)

        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
                 
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

    @action(detail=True, methods=['get'])
    def requisitos_materiales(self, request, pk=None):
        """
        Calcula detalladamente los materiales y químicos necesarios para completar la OP.
        """
        orden = self.get_object()
        peso_total = orden.peso_neto_requerido
        
        requisitos = []
        
        # 1. Materia Prima principal (Hilo/Tela base)
        # Asumimos una relación 1:1 por simplicidad en este paso o lógica específica
        requisitos.append({
            "producto_id": orden.producto.id,
            "producto_nombre": orden.producto.descripcion,
            "tipo": orden.producto.tipo,
            "cantidad_requerida": peso_total,
            "unidad": orden.producto.unidad_medida,
            "es_base": True
        })
        
        # 2. Químicos de la Fórmula
        if orden.formula_color:
            detalles = DetalleFormula.objects.filter(fase__formula=orden.formula_color).select_related('producto')
            for d in detalles:
                if not d.producto:
                    continue
                base = d.concentracion_gr_l or d.gramos_por_kilo or Decimal('0')
                cant_quimico = (base / Decimal('1000.0')) * peso_total
                requisitos.append({
                    "producto_id": d.producto.id,
                    "producto_nombre": d.producto.descripcion,
                    "tipo": "quimico",
                    "cantidad_requerida": round(cant_quimico, 4),
                    "unidad": d.producto.unidad_medida,
                    "es_base": False
                })
        
        return Response({
            "orden_codigo": orden.codigo,
            "peso_total_op": peso_total,
            "requisitos": requisitos
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch', 'post'], url_path='cambiar_estado')
    def cambiar_estado(self, request, pk=None):
        orden = self.get_object()
        serializer = OrdenProduccionEstadoSerializer(orden, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'estado actualizado', 'estado': serializer.data['estado']})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoteProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = LoteProduccionSerializer

    def get_queryset(self):
        queryset = LoteProduccion.objects.select_related(
            'orden_produccion', 'orden_produccion__producto',
            'orden_produccion__sede', 'maquina', 'operario'
        ).all()
        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(orden_produccion__sede_id=sede_id)
        orden_produccion_id = self.request.query_params.get('orden_produccion')
        if orden_produccion_id:
            queryset = queryset.filter(orden_produccion_id=orden_produccion_id)
        return queryset
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'generate_zpl']:
            return [IsAuthenticated()]
        if self.request.user.groups.filter(name__in=['jefe_area', 'jefe_planta', 'admin_sistemas', 'admin_sede', 'empaquetado', 'operario']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def rechazar(self, request, pk=None):
        lote = self.get_object()
        orden = lote.orden_produccion
        bodega = orden.bodega
        
        # 1. Reverse Output (Remove the produced lot from stock)
        try:
             # Find the stock item. If it doesn't exist (already sold/moved), we have a problem.
             # We assume it's still there for a "rejection".
             stock_output = StockBodega.objects.select_for_update().get(
                 bodega=bodega, producto=orden.producto, lote=lote
             )
             if stock_output.cantidad < lote.peso_neto_producido:
                 return Response({"error": "No hay suficiente stock del lote para revertir (ya fue movido o vendido)."}, status=status.HTTP_400_BAD_REQUEST)
             
             stock_output.cantidad -= lote.peso_neto_producido
             stock_output._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
             stock_output.save()

             MovimientoInventario.objects.create(
                tipo_movimiento='AJUSTE', # Using AJUSTE to represent Rejection/Loss
                producto=orden.producto,
                lote=lote,
                bodega_origen=bodega, # Leaving the warehouse
                cantidad=lote.peso_neto_producido,
                usuario=request.user,
                documento_ref=f'RECHAZO-LOTE-{lote.codigo_lote}',
                saldo_resultante=stock_output.cantidad # Approximate
             )
        except StockBodega.DoesNotExist:
             return Response({"error": "El stock del lote no existe en la bodega de origen."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Reverse Inputs (Return raw materials to stock)
        # Calculate what was consumed
        
        # 2.1 Raw Material
        producto_input = orden.producto # Assuming same product input/output for simplicity or defined input
        stock_input, _ = safe_get_or_create_stock(
            StockBodega, 
            bodega=bodega, 
            producto=producto_input, 
            lote=None
        )
        stock_input.cantidad += lote.peso_neto_producido
        stock_input._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
        stock_input.save()
            
        MovimientoInventario.objects.create(
            tipo_movimiento='DEVOLUCION', # Returning to stock
            producto=producto_input,
            bodega_destino=bodega,
            cantidad=lote.peso_neto_producido,
            usuario=request.user,
            documento_ref=f'REV-LOTE-{lote.codigo_lote}'
        )

        # 2.2 Chemicals
        if orden.formula_color:
            from .models import DetalleFormula
            for detalle in DetalleFormula.objects.filter(fase__formula=orden.formula_color):
                quimico = detalle.producto
                cantidad_devuelta = (lote.peso_neto_producido * detalle.gramos_por_kilo) / Decimal('1000.0')
                
                stock_quimico, _ = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodega, 
                    producto=quimico, 
                    lote=None
                )
                stock_quimico.cantidad += cantidad_devuelta
                stock_quimico._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
                stock_quimico.save()
                
                MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto=quimico,
                    bodega_destino=bodega,
                    cantidad=cantidad_devuelta,
                    usuario=request.user,
                    documento_ref=f'REV-LOTE-{lote.codigo_lote}'
                )

        # 3. Mark Lote as rejected or delete
        # Since we don't have a status field on Lote, and "Rechazo" might imply it shouldn't exist as valid production
        # But we might want history. For now, let's delete it as it effectively "undoes" the creation.
        # Or better, if we want to keep the record that it FAILED, we should have a status.
        # Given the prompt "revierta los movimientos", deletion or zeroing is implied.
        # I'll delete it to be safe and clean.
        lote.delete()

        return Response({"message": "Lote rechazado y movimientos revertidos correctament."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def generate_zpl(self, request, pk=None):
        lote = self.get_object()
        orden = lote.orden_produccion
        
        # Prepare data for microservice
        empresa = orden.sede.nombre if orden and orden.sede else 'Sede Principal'
        ubicacion = orden.sede.location if orden and orden.sede else ''

        
        # Fallback description logic
        if hasattr(orden, 'producto_descripcion'):
             producto_desc = orden.producto_descripcion 
        elif orden and orden.producto:
             producto_desc = orden.producto.descripcion
        else:
             producto_desc = 'N/A'
             
        peso_neto = float(lote.peso_neto_producido)
        tara = float(lote.tara) if lote.tara else 0.0
        peso_bruto = float(lote.peso_bruto) if lote.peso_bruto else 0.0
        cantidad_metros = float(lote.cantidad_metros) if lote.cantidad_metros else None
        
        unidad = orden.producto.unidad_medida if orden and orden.producto else 'kg'
        lote_codigo = lote.codigo_lote
        qr_data = f"https://app.texcore.com/trazabilidad/{lote_codigo}"

        data = {
            "empresa": empresa,
            "producto_desc": producto_desc,
            "lote_codigo": lote_codigo,
            "peso_neto": peso_neto,
            "tara": tara,
            "peso_bruto": peso_bruto,
            "cantidad_metros": cantidad_metros,
            "unidad": unidad,
            "qr_data": qr_data
        }

        # Call microservice
        zpl = PrintingService.generate_zpl_label(data)
        
        if zpl:
            return Response({"zpl": zpl}, status=status.HTTP_200_OK)
        else:
            # Fallback local generation if service is down
            # (Simple fallback to ensure app doesn't crash)
            metros_text = f"Metros: {cantidad_metros}" if cantidad_metros else ""
            local_zpl = f"""
^XA
^PW800
^LL400
^FO50,50^ADN,36,20^FD{empresa}^FS
^FO50,100^ADN,18,10^FD{producto_desc} (FALLBACK)^FS
^FO50,150^ADN,18,10^FDLote/Pieza: {lote_codigo}^FS
^FO50,200^ADN,24,14^FDBruto: {peso_bruto}kg  Tara: {tara}kg^FS
^FO50,230^ADN,36,20^FDNeto: {peso_neto} {unidad} {metros_text}^FS
^FO50,280^BCN,80,Y,N,N^FD{lote_codigo}^FS
^XZ
            """
            return Response({"zpl": local_zpl.strip(), "warning": "Servicio de impresión no disponible, usando fallback local."}, status=status.HTTP_200_OK)



class PagoClienteViewSet(viewsets.ModelViewSet):
    serializer_class = PagoClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = PagoCliente.objects.select_related('cliente', 'sede').order_by('-fecha')
        
        # Filtering: Salesmen only see payments of their assigned clients
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
             queryset = queryset.filter(cliente__vendedor_asignado=user)
             
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        # Auto-assign sede from user
        if hasattr(user, 'sede') and user.sede:
             serializer.save(sede=user.sede)
        else:
             serializer.save()
        
        # Trigger Reconciliation for the client
        PaymentReconciler.reconcile_client_orders(serializer.instance.cliente)


class PedidoVentaViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoVentaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = PedidoVenta.objects.select_related('cliente', 'sede').order_by('-fecha_pedido')

        # Filtro opcional por vendedor (solo para roles con visión gerencial/sistemas)
        vendedor_id = self.request.query_params.get('vendedor_id')
        vendedor_username = self.request.query_params.get('vendedor_username')
        if (vendedor_id or vendedor_username) and (
            user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()
        ):
            if vendedor_id:
                try:
                    queryset = queryset.filter(vendedor_asignado_id=int(vendedor_id))
                except (TypeError, ValueError):
                    pass
            elif vendedor_username:
                queryset = queryset.filter(vendedor_asignado__username=vendedor_username)
        
        # Filtering: Salesmen only see their own orders
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(vendedor_asignado=user)
             
        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

        # Optional: Skip older orders to avoid memory overload (e.g., last 100) only for list action
        if self.action == 'list':
            limit = self.request.query_params.get('limit', 100)
            try:
                limit = int(limit)
            except (ValueError, TypeError):
                limit = 100
            return queryset[:limit]
            
        return queryset

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        pedido = self.get_object()
        cliente = pedido.cliente
        sede = pedido.sede
        detalles = pedido.detalles.select_related('producto').all()
        
        items = []
        for d in detalles:
            items.append({
                "producto_descripcion": d.producto.descripcion,
                "cantidad": float(d.cantidad),
                "piezas": d.piezas,
                "peso": float(d.peso),
                "precio_unitario": float(d.precio_unitario),
                "incluye_iva": d.incluye_iva
            })

        data = {
            "id": pedido.id,
            "guia_remision": pedido.guia_remision,
            "fecha_pedido": pedido.fecha_pedido.isoformat(),
            "cliente_nombre": cliente.nombre_razon_social,
            "cliente_ruc": cliente.ruc_cedula,
            "cliente_direccion": cliente.direccion_envio,
            "vendedor_nombre": pedido.vendedor_asignado.username if pedido.vendedor_asignado else None,
            "sede_nombre": sede.location if sede else "Matriz", # Mostrar ubicación como subtítulo
            "empresa_nombre": sede.nombre if sede else "Empresa Principal", # Nombre Sede como Empresa Principal
            "esta_pagado": pedido.esta_pagado,
            "valor_retencion": float(pedido.valor_retencion or 0),
            "detalles": items
        }

        # Call microservice
        pdf_content = PrintingService.generate_nota_venta_pdf(data)
        
        if pdf_content:
            from django.http import HttpResponse
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="pedido_{pedido.guia_remision or pedido.id}.pdf"'
            return response
        else:
            return Response({"error": "El servicio de impresión no está disponible temporalmente."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = {}
        
        # Auto-asignar vendedor si el usuario pertenece al grupo 'vendedor'
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
             save_kwargs['vendedor_asignado'] = user
        
        # Auto-asignar sede del usuario si no se proporcionó una explícitamente
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            save_kwargs['sede'] = user.sede
            
        serializer.save(**save_kwargs)
             
        # Trigger Reconciliation
        # Note: serializer.save() returns the instance, but perform_create doesn't return anything by default in DRF ViewSet logic unless overridden in standard create()
        # However, serializer.instance is populated.
        if serializer.instance:
             PaymentReconciler.reconcile_client_orders(serializer.instance.cliente)



class RegistrarLoteProduccionView(APIView):
    """
    API View to register a production lot and handle all related inventory movements.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, orden_id, *args, **kwargs):
        orden = get_object_or_404(OrdenProduccion, id=orden_id)

        serializer = RegistrarLoteProduccionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lote_data = serializer.validated_data
        peso_neto_producido = lote_data['peso_neto_producido']
        completar_orden = lote_data.pop('completar_orden', False)
        
        # --- 1. Generate/Validate Batch Code ---
        if not lote_data.get('codigo_lote'):
            lote_data['codigo_lote'] = orden.generate_next_lote_codigo()
        
        maquina_instance = lote_data.get('maquina')
        if maquina_instance and not isinstance(maquina_instance, Maquina):
             maquina_instance = Maquina.objects.get(pk=maquina_instance)
             lote_data['maquina'] = maquina_instance
        
        # --- 2. Consume Raw Material (Standard Production) ---
        producto_a_consumir = orden.producto
        bodega_origen = orden.bodega

        if producto_a_consumir and bodega_origen:
            try:
                stock_input = StockBodega.objects.select_for_update().get(
                    bodega=bodega_origen, producto=producto_a_consumir, lote=None
                )
                if stock_input.cantidad >= peso_neto_producido:
                    stock_input.cantidad -= peso_neto_producido
                    stock_input._justificacion_auditoria = f"Consumo automático para OP-{orden.codigo}"
                    stock_input.save()
                    MovimientoInventario.objects.create(
                        tipo_movimiento='CONSUMO', producto=producto_a_consumir, bodega_origen=bodega_origen,
                        cantidad=peso_neto_producido, usuario=request.user, documento_ref=f'OP-{orden.codigo}'
                    )
                else:
                    # Log warning or handle partial
                    logger.warning(f"Stock insuficiente para {producto_a_consumir.codigo} en bodega {bodega_origen.nombre}")
            except StockBodega.DoesNotExist:
                logger.error(f"No existe stock para el producto base {producto_a_consumir.codigo}")

        # --- 3. Consume Specific Packaging Supplies (Insumos) ---
        # Map presentation to SKU if possible, otherwise use a default "Labels"
        presentacion = lote_data.get('presentacion', '').lower()
        insumo_skus = ['INS-ETQ-01'] # Default label
        
        if 'caja' in presentacion:
            insumo_skus.append('INS-CJ-01')
        elif 'funda' in presentacion:
            insumo_skus.append('INS-FD-01')
        
        for sku in insumo_skus:
            try:
                prod_insumo = Producto.objects.get(codigo=sku)
                stock_insumo = StockBodega.objects.select_for_update().get(bodega=bodega_origen, producto=prod_insumo)
                if stock_insumo.cantidad >= 1:
                    stock_insumo.cantidad -= 1
                    stock_insumo._justificacion_auditoria = f"Uso de insumo {sku} para lote {lote_data['codigo_lote']}"
                    stock_insumo.save()
                    MovimientoInventario.objects.create(
                        tipo_movimiento='CONSUMO',
                        producto=prod_insumo,
                        bodega_origen=bodega_origen,
                        cantidad=1,
                        usuario=request.user,
                        documento_ref=f'INSUMO-LOTE-{lote_data["codigo_lote"]}'
                    )
            except (Producto.DoesNotExist, StockBodega.DoesNotExist):
                # If specific insumo doesn't exist, skip or use generic fallback if desired
                continue

        # --- 4. Create the Production Lot ---
        lote = LoteProduccion.objects.create(
            orden_produccion=orden,
            operario=request.user,
            **lote_data
        )

        # --- 5. Add the new lot to inventory ---
        producto_final = orden.producto
        bodega_destino = orden.bodega
        stock_output, created = safe_get_or_create_stock(
            StockBodega,
            bodega=bodega_destino, 
            producto=producto_final, 
            lote=lote
        )
        stock_output.cantidad += peso_neto_producido
        stock_output._justificacion_auditoria = f"Entrada por producción lote {lote.codigo_lote}"
        stock_output.save()
        
        MovimientoInventario.objects.create(
             tipo_movimiento='PRODUCCION', producto=producto_final, lote=lote,
             bodega_destino=bodega_destino, cantidad=peso_neto_producido,
             usuario=request.user, documento_ref=f'OP-{orden.codigo}'
        )

        # --- 6. Update Order Status ---
        # Calculate total produced so far
        total_producido = orden.lotes.aggregate(Sum('peso_neto_producido'))['peso_neto_producido__sum'] or 0
        
        if completar_orden or total_producido >= orden.peso_neto_requerido:
            orden.estado = 'finalizada'
            orden.fecha_fin_planificada = timezone.now().date()
        else:
            orden.estado = 'en_proceso'
            
        orden.save()

        return Response(LoteProduccionSerializer(lote).data, status=status.HTTP_201_CREATED)

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'create', 'update', 'partial_update']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]


class KPIAreaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Determine Area
        area_id = request.query_params.get('area')
        if not area_id and hasattr(request.user, 'area') and request.user.area:
            area = request.user.area
        elif area_id:
             area = get_object_or_404(Area, id=area_id)
        else:
            return Response({"error": "Área no especificada o el usuario no tiene un área asignada."}, status=status.HTTP_400_BAD_REQUEST)

        # KPIs
        # 1. Output (Producción Total)
        # Filter Lotes by Maquinas in this Area
        maquinas_area = Maquina.objects.filter(area=area)
        lotes_area = LoteProduccion.objects.filter(maquina__in=maquinas_area)
        
        total_output = lotes_area.aggregate(Sum('peso_neto_producido'))['peso_neto_producido__sum'] or 0

        # 2. Input (Consumo Estimado)
        # We estimate input = output (assuming 1:1 for now as per logic)
        # Or better, we sum the initial requirements of the orders? 
        # Let's say Yield = Output / (Output + Loss). 
        # Since we don't track loss explicitly yet, let's use Capacity Utilization.
        # "Rendimiento (Entrada vs Salida)" -> Typically Output / Input.
        # Input = Raw materials consumed. If we assume 1:1, it's 100%.
        # Let's assume Input = Peso Teórico (e.g. from Order) vs Real (Lote).
        # OR just return the total volumes.
        
        # 3. Avg Time per Operator
        # time = hora_final - hora_inicio
        avg_duration = lotes_area.annotate(
            duration=ExpressionWrapper(F('hora_final') - F('hora_inicio'), output_field=DurationField())
        ).aggregate(Avg('duration'))['duration__avg']
        
        # Format duration to hours/minutes
        avg_minutes = 0
        if avg_duration:
            avg_minutes = avg_duration.total_seconds() / 60

        return Response({
            "area": area.nombre,
            "total_produccion_kg": total_output,
            "rendimiento_yield": 1.0, # Placeholder until better input tracking
            "tiempo_promedio_lote_min": round(avg_minutes, 2)
        })
