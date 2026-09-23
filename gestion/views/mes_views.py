import logging
from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import (
    Area,
    Bodega,
    CorridaProduccion,
    DetallePlanProduccion,
    LineaProduccion,
    Maquina,
    OperacionProduccion,
    OrdenProduccion,
    PedidoVenta,
    PlanProduccion,
    ProcessStep,
    Sede,
)
from gestion.serializers.mes_serializers import (
    CorridaProduccionSerializer,
    CrearPlanDesdeAlertasInputSerializer,
    DetallePlanProduccionSerializer,
    GenerarOrdenDesdePlanInputSerializer,
    IniciarCorridaInputSerializer,
    OperacionProduccionSerializer,
    PlanProduccionSerializer,
    RegistroOperacionInputSerializer,
    RevertirOperacionInputSerializer,
)
from gestion.services.ejecucion_produccion import EjecucionProduccionService
from gestion.services.genealogia_service import GenealogiaService
from inventory.services.reposicion_service import ReposicionService
from ._common import parse_int_param

logger = logging.getLogger('gestion.views.mes')


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CorridaProduccionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la gestión de Corridas de Producción (Nivel 3 MES).
    Soporta operaciones continuas en planta, registro de transformaciones
    atómicas en máquina y consulta de trazabilidad mediante grafos DAG.
    """
    serializer_class = CorridaProduccionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo', 'area__nombre', 'maquina_principal__nombre', 'turno']
    ordering_fields = ['fecha_jornada', 'hora_inicio', 'codigo', 'estado']
    ordering = ['-fecha_jornada', '-hora_inicio']

    def get_queryset(self):
        user = self.request.user
        qs = CorridaProduccion.objects.select_related(
            'sede',
            'area',
            'linea',
            'maquina_principal',
            'supervisor',
            'orden_produccion',
        ).prefetch_related('operaciones')

        # Control de acceso multi-sede
        if hasattr(user, 'sede') and user.sede and not (user.is_superuser or user.is_staff):
            qs = qs.filter(sede=user.sede)

        # Filtros opcionales por query params
        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        modalidad = self.request.query_params.get('modalidad')
        if modalidad:
            qs = qs.filter(modalidad=modalidad)

        area_id = parse_int_param(self.request.query_params.get('area'), 'area')
        if area_id:
            qs = qs.filter(area_id=area_id)

        maquina_id = parse_int_param(self.request.query_params.get('maquina'), 'maquina')
        if maquina_id:
            qs = qs.filter(maquina_principal_id=maquina_id)

        linea_id = parse_int_param(self.request.query_params.get('linea'), 'linea')
        if linea_id:
            qs = qs.filter(linea_id=linea_id)

        turno = self.request.query_params.get('turno')
        if turno:
            qs = qs.filter(turno__iexact=turno.strip())

        fecha = self.request.query_params.get('fecha')
        if fecha:
            qs = qs.filter(fecha_jornada=fecha)

        return qs

    @action(detail=False, methods=['post'], url_path='iniciar-corrida')
    def iniciar_corrida(self, request):
        """
        Inicia una nueva corrida de producción (continua, contra stock o bajo pedido).
        POST /api/gestion/corridas-produccion/iniciar-corrida/
        """
        serializer = IniciarCorridaInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        sede_id = data.get('sede_id')
        if not sede_id:
            if hasattr(user, 'sede') and user.sede:
                sede_id = user.sede.id
            else:
                area = get_object_or_404(Area, pk=data['area_id'])
                sede_id = area.sede_id

        sede = get_object_or_404(Sede, pk=sede_id)
        area = get_object_or_404(Area, pk=data['area_id'])

        linea = None
        if data.get('linea_id'):
            linea = get_object_or_404(LineaProduccion, pk=data['linea_id'])

        maquina = None
        if data.get('maquina_principal_id'):
            maquina = get_object_or_404(Maquina, pk=data['maquina_principal_id'])

        op = None
        if data.get('orden_produccion_id'):
            op = get_object_or_404(OrdenProduccion, pk=data['orden_produccion_id'])

        plan = None
        if data.get('plan_produccion_id'):
            plan = get_object_or_404(PlanProduccion, pk=data['plan_produccion_id'])
        elif op and op.plan_produccion:
            plan = op.plan_produccion

        det_plan = None
        if data.get('detalle_plan_id'):
            det_plan = get_object_or_404(DetallePlanProduccion, pk=data['detalle_plan_id'])
        elif op and op.detalle_plan:
            det_plan = op.detalle_plan

        pedido = None
        if data.get('pedido_venta_id'):
            pedido = get_object_or_404(PedidoVenta, pk=data['pedido_venta_id'])
        elif op and op.pedido_venta:
            pedido = op.pedido_venta

        fecha_jornada = data.get('fecha_jornada') or timezone.now().date()
        codigo = data.get('codigo', '').strip()
        if not codigo:
            consecutivo = CorridaProduccion.objects.filter(
                sede=sede,
                fecha_jornada=fecha_jornada,
            ).count() + 1
            codigo = f"CORR-{fecha_jornada.strftime('%Y%m%d')}-{consecutivo:03d}"

        corrida = CorridaProduccion.objects.create(
            codigo=codigo,
            sede=sede,
            area=area,
            linea=linea,
            maquina_principal=maquina,
            modalidad=data.get('modalidad', 'CONTINUA'),
            orden_produccion=op,
            plan_produccion=plan,
            detalle_plan=det_plan,
            pedido_venta=pedido,
            turno=data.get('turno', 'Mañana'),
            fecha_jornada=fecha_jornada,
            hora_inicio=timezone.now(),
            estado='en_proceso',
            supervisor=user,
            observaciones=data.get('observaciones', ''),
        )

        out_serializer = CorridaProduccionSerializer(corrida)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='registrar-operacion')
    def registrar_operacion(self, request, pk=None):
        """
        Registra un paso unitario de pesaje/transformación dentro de la corrida.
        POST /api/gestion/corridas-produccion/{id}/registrar-operacion/
        """
        corrida = self.get_object()
        serializer = RegistroOperacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # El operario solo registra avance (peso) sobre el material ya
        # establecido por un supervisor — no puede elegir ni cambiar qué
        # producto/insumo se está transformando. El frontend
        # (CorridaContinuaDashboard restrictedMode) ya oculta esos campos,
        # pero eso por sí solo es cosmético: cualquiera con el token podría
        # llamar este endpoint directo con un producto distinto, así que la
        # regla se impone también aquí.
        if request.user.groups.filter(name='operario').exists():
            ultima_operacion = (
                corrida.operaciones
                .exclude(estado='revertida')
                .order_by('-numero_secuencia')
                .prefetch_related('consumos', 'salidas')
                .first()
            )
            if ultima_operacion is None:
                return Response(
                    {'error': 'Un supervisor debe registrar la primera transformación de esta corrida (producto e insumo) antes de que el operario pueda registrar avance.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            consumo_previo = ultima_operacion.consumos.first()
            salida_previa = ultima_operacion.salidas.first()
            nuevo_consumo = data['consumos'][0] if data.get('consumos') else None
            nueva_salida = data['salidas'][0] if data.get('salidas') else None
            material_cambio = (
                not consumo_previo or not salida_previa or not nuevo_consumo or not nueva_salida
                or consumo_previo.producto_id != nuevo_consumo.get('producto_id')
                or consumo_previo.bodega_origen_id != nuevo_consumo.get('bodega_origen_id')
                or salida_previa.producto_id != nueva_salida.get('producto_id')
                or salida_previa.bodega_destino_id != nueva_salida.get('bodega_destino_id')
            )
            if material_cambio:
                return Response(
                    {'error': 'El operario no puede cambiar el producto/insumo de la corrida — eso lo define un supervisor.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        operacion_data = {
            'maquina': data.get('maquina_id'),
            'operario': data.get('operario_id') or request.user,
            'proceso': data.get('proceso_id'),
            'numero_secuencia': data.get('numero_secuencia'),
            'hora_inicio': data.get('hora_inicio'),
            'hora_fin': data.get('hora_fin'),
            'observaciones': data.get('observaciones', ''),
        }

        try:
            operacion = EjecucionProduccionService.registrar_operacion(
                corrida=corrida,
                operacion_data=operacion_data,
                consumos_data=data['consumos'],
                salidas_data=data['salidas'],
                mermas_data=data.get('mermas', []),
                user=request.user,
                justificacion=data.get('justificacion'),
                tolerancia_balance=data.get('tolerancia_balance', Decimal('0.050')),
            )
        except (ValidationError, DjangoValidationError) as e:
            msg = e.messages if hasattr(e, 'messages') else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Error inesperado al registrar operación en Corrida {corrida.codigo}: {e}")
            return Response(
                {'error': f'Error interno en el motor de ejecución: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        out_serializer = OperacionProduccionSerializer(operacion)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='finalizar-corrida')
    def finalizar_corrida(self, request, pk=None):
        """
        Cierra formalmente la corrida y registra la hora de finalización.
        POST /api/gestion/corridas-produccion/{id}/finalizar-corrida/
        """
        corrida = self.get_object()
        if corrida.estado == 'finalizada':
            return Response(
                {'error': 'La corrida ya se encuentra finalizada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        corrida.estado = 'finalizada'
        corrida.hora_fin = timezone.now()
        corrida.save(update_fields=['estado', 'hora_fin', 'fecha_modificacion'])

        return Response(CorridaProduccionSerializer(corrida).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='pausar')
    def pausar(self, request, pk=None):
        """
        Pausa o reanuda una corrida de producción en proceso.
        POST /api/gestion/corridas-produccion/{id}/pausar/
        """
        corrida = self.get_object()
        if corrida.estado == 'finalizada':
            return Response(
                {'error': 'No se puede pausar una corrida ya finalizada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if corrida.estado == 'pausada':
            corrida.estado = 'en_proceso'
        else:
            corrida.estado = 'pausada'

        corrida.save(update_fields=['estado', 'fecha_modificacion'])
        return Response(CorridaProduccionSerializer(corrida).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='revertir-operacion')
    def revertir_operacion(self, request, pk=None):
        """
        Revierte una operación específica de la corrida restituyendo inventarios.
        POST /api/gestion/corridas-produccion/{id}/revertir-operacion/
        """
        corrida = self.get_object()
        serializer = RevertirOperacionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        operacion = get_object_or_404(
            OperacionProduccion,
            pk=data['operacion_id'],
            corrida=corrida,
        )

        try:
            operacion_revertida = EjecucionProduccionService.revertir_operacion(
                operacion=operacion,
                user=request.user,
                justificacion=data['justificacion'],
            )
        except (ValidationError, DjangoValidationError) as e:
            msg = e.messages if hasattr(e, 'messages') else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Error al revertir operación #{operacion.id}: {e}")
            return Response(
                {'error': f'Error al procesar reversión: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            OperacionProduccionSerializer(operacion_revertida).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='trazabilidad-lote')
    def trazabilidad_lote(self, request):
        """
        Endpoint unificado para consulta de genealogía DAG (Trace-Back y Trace-Forward Recall).
        GET /api/gestion/corridas-produccion/trazabilidad-lote/?codigo=LOT-123&direccion=atras|adelante
        """
        codigo_lote = request.query_params.get('codigo', '').strip()
        lote_id = parse_int_param(request.query_params.get('lote_id'), 'lote_id')
        direccion = request.query_params.get('direccion', 'atras').lower().strip()

        if not codigo_lote and not lote_id:
            return Response(
                {'error': 'Debe especificar el parámetro "codigo" o "lote_id".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lote_ref = lote_id if lote_id else codigo_lote
        profundidad = parse_int_param(request.query_params.get('profundidad'), 'profundidad') or 10

        try:
            if direccion == 'adelante':
                grafo = GenealogiaService.obtener_trazabilidad_hacia_adelante(
                    lote_ref=lote_ref,
                    profundidad_maxima=profundidad,
                )
            else:
                grafo = GenealogiaService.obtener_trazabilidad_hacia_atras(
                    lote_ref=lote_ref,
                    profundidad_maxima=profundidad,
                )
            return Response(grafo, status=status.HTTP_200_OK)
        except (ValidationError, DjangoValidationError) as e:
            msg = e.messages if hasattr(e, 'messages') else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Error al consultar trazabilidad de lote {lote_ref}: {e}")
            return Response(
                {'error': f'Error al consultar el grafo de trazabilidad: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class OperacionProduccionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para auditoría y consulta de Operaciones de Producción.
    """
    serializer_class = OperacionProduccionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['hora_inicio', 'numero_secuencia', 'estado']
    ordering = ['-hora_inicio']

    def get_queryset(self):
        user = self.request.user
        qs = OperacionProduccion.objects.select_related(
            'corrida',
            'maquina',
            'proceso',
            'operario',
        ).prefetch_related('consumos', 'salidas', 'mermas')

        if hasattr(user, 'sede') and user.sede and not (user.is_superuser or user.is_staff):
            qs = qs.filter(corrida__sede=user.sede)

        corrida_id = parse_int_param(self.request.query_params.get('corrida'), 'corrida')
        if corrida_id:
            qs = qs.filter(corrida_id=corrida_id)

        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        return qs


class PlanProduccionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para la Planificación y Reposición Contra Stock (Make-to-Stock / MTS).
    Permite crear y aprobar planes, consultar necesidades de stock mínimo,
    generar órdenes de producción y seguir el cumplimiento en tiempo real.
    """
    serializer_class = PlanProduccionSerializer
    pagination_class = StandardResultsSetPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['codigo', 'observaciones', 'sede__nombre']
    ordering_fields = ['fecha_inicio', 'fecha_fin', 'codigo', 'estado']
    ordering = ['-fecha_inicio', '-id']

    def get_queryset(self):
        user = self.request.user
        qs = PlanProduccion.objects.select_related('sede', 'supervisor').prefetch_related(
            'detalles__producto_objetivo'
        )
        if hasattr(user, 'sede') and user.sede and not (user.is_superuser or user.is_staff):
            qs = qs.filter(sede=user.sede)

        sede_id = parse_int_param(self.request.query_params.get('sede'), 'sede')
        if sede_id:
            qs = qs.filter(sede_id=sede_id)

        estado = self.request.query_params.get('estado')
        if estado:
            qs = qs.filter(estado=estado)

        return qs

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        plan = self.get_object()
        if plan.estado != 'borrador':
            return Response(
                {'error': f"Solo se pueden aprobar planes en estado 'borrador'. Estado actual: {plan.estado}."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.estado = 'aprobado'
        plan.save(update_fields=['estado', 'fecha_modificacion'])
        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        plan = self.get_object()
        if plan.estado in ['cerrado', 'cancelado']:
            return Response(
                {'error': f"El plan ya se encuentra en estado '{plan.estado}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.estado = 'cerrado'
        plan.save(update_fields=['estado', 'fecha_modificacion'])
        serializer = self.get_serializer(plan)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='necesidades-reposicion')
    def necesidades_reposicion(self, request):
        user = request.user
        sede_id = parse_int_param(request.query_params.get('sede'), 'sede')
        if not sede_id and hasattr(user, 'sede') and user.sede and not (user.is_superuser or user.is_staff):
            sede_id = user.sede_id

        necesidades = ReposicionService.analizar_necesidades_reposicion(sede_id=sede_id)
        return Response(necesidades, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='crear-desde-alertas')
    def crear_desde_alertas(self, request):
        serializer = CrearPlanDesdeAlertasInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            sede = Sede.objects.get(pk=data['sede_id'])
            supervisor = None
            if data.get('supervisor_id'):
                from gestion.models import CustomUser
                supervisor = CustomUser.objects.filter(pk=data['supervisor_id']).first()

            plan = ReposicionService.crear_plan_desde_alertas(
                sede=sede,
                productos_deficit=data['items'],
                supervisor=supervisor or request.user,
                codigo=data.get('codigo'),
                fecha_inicio=data.get('fecha_inicio'),
                fecha_fin=data.get('fecha_fin'),
                aprobar_inmediatamente=data.get('aprobar_inmediatamente', False),
            )
            resp_serializer = self.get_serializer(plan)
            return Response(resp_serializer.data, status=status.HTTP_201_CREATED)
        except (DjangoValidationError, ValidationError) as e:
            msg = e.messages if hasattr(e, 'messages') else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Error creando plan desde alertas: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='generar-orden')
    def generar_orden(self, request, pk=None):
        plan = self.get_object()
        serializer = GenerarOrdenDesdePlanInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            detalle_plan = plan.detalles.get(pk=data['detalle_plan_id'])
            bodega_salida = None
            if data.get('bodega_salida_id'):
                bodega_salida = Bodega.objects.get(pk=data['bodega_salida_id'])

            bodega_entrada = None
            if data.get('bodega_entrada_id'):
                bodega_entrada = Bodega.objects.get(pk=data['bodega_entrada_id'])

            maquina = None
            if data.get('maquina_asignada_id'):
                maquina = Maquina.objects.get(pk=data['maquina_asignada_id'])

            op = ReposicionService.generar_orden_desde_plan(
                detalle_plan=detalle_plan,
                user=request.user,
                bodega_salida=bodega_salida,
                bodega_entrada=bodega_entrada,
                formula_color=None,
                prioridad=data.get('prioridad', 'normal'),
                maquina_asignada=maquina,
                peso_solicitado=data.get('peso_solicitado'),
            )
            return Response({
                'mensaje': f"Orden de Producción {op.codigo} generada exitosamente.",
                'orden_id': op.pk,
                'codigo': op.codigo,
                'peso_neto_requerido': str(op.peso_neto_requerido),
                'estado': op.estado,
            }, status=status.HTTP_201_CREATED)
        except DetallePlanProduccion.DoesNotExist:
            return Response(
                {'error': f"El detalle de plan #{data['detalle_plan_id']} no pertenece al plan #{plan.pk}."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except (DjangoValidationError, ValidationError) as e:
            msg = e.messages if hasattr(e, 'messages') else str(e)
            return Response({'error': msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Error generando orden desde plan {plan.codigo}: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

