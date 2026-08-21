import logging
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import OrdenProduccion, DetalleFormula
from gestion.permissions import IsTintoreroOrAdmin, IsJefeAreaOrAdmin, IsJefePlantaOrAdmin, IsJefeAreaOrOperarioOrAdmin
from gestion.serializers import (
    OrdenProduccionSerializer, OrdenProduccionEstadoSerializer,
    TransformacionProductoSerializer,
)
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.transformacion import TransformacionService
from gestion.services.trazabilidad import TrazabilidadService

from ._common import parse_int_param

logger = logging.getLogger('gestion.views')


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class OrdenProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = OrdenProduccionSerializer
    pagination_class = StandardResultsSetPagination
    # SearchFilter es nativo de DRF (búsqueda por texto). El filtrado por estado
    # y máquina se hace manualmente en get_queryset (con validación de tipo) para
    # NO depender de django-filter, que no está en requirements ni instalado —
    # importarlo hacía fallar el arranque de la app.
    filter_backends = [filters.SearchFilter]
    search_fields = ['codigo', 'producto_entrada__descripcion', 'producto_salida__descripcion']

    def get_serializer_class(self):
        if self.action == 'create':
            return OrdenProduccionSerializer  # Jefe de Planta: crear solo lo básico
        if self.action == 'completar_detalles':
            return OrdenProduccionSerializer  # Jefe de Área: completar detalles
        return OrdenProduccionSerializer

    def get_permissions(self):
        if self.action == 'stock_quimicos':
            return [IsAuthenticated(), IsTintoreroOrAdmin()]
        if self.action == 'create':
            # Regla de negocio: la OP la genera el Jefe de Planta (o Admin) para
            # un área específica. El Jefe de Área NO crea OPs, solo asigna sus
            # propios recursos (máquina/operario) a las OPs ya creadas.
            return [IsAuthenticated(), IsJefePlantaOrAdmin()]
        if self.action == 'completar_detalles':
            # Solo Jefe de Área puede completar detalles
            return [IsAuthenticated(), IsJefeAreaOrAdmin()]
        if self.action == 'registrar_transformacion':
            # Jefe de Área u Operario del área (el Bodeguero queda excluido)
            return [IsAuthenticated(), IsJefeAreaOrOperarioOrAdmin()]
        if self.action in ['list', 'retrieve', 'update', 'partial_update',
                           'transformaciones', 'trazabilidad']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        queryset = OrdenProduccion.objects.select_related(
            'producto_entrada',
            'formula_color',
            'sede',
            'area',
            'maquina_asignada',
            'operario_asignado',
            'bodega_entrada').prefetch_related('lotes').all()

        # Filter by area if user is a Jefe de Área
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)

        # Filter for operators: only show assigned orders
        if user.groups.filter(name='operario').exists() and not user.is_superuser:
            queryset = queryset.filter(operario_asignado=user)

        sede_id = parse_int_param(self.request.query_params.get('sede_id'), 'sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

        # Filtros de la UI (reemplazan a filterset_fields de django-filter):
        estado = self.request.query_params.get('estado')
        if estado:
            queryset = queryset.filter(estado=estado)

        maquina_id = parse_int_param(
            self.request.query_params.get('maquina_asignada'), 'maquina_asignada')
        if maquina_id:
            queryset = queryset.filter(maquina_asignada_id=maquina_id)

        return queryset

    def perform_create(self, serializer):
        """Jefe de Planta crea orden básica: código, peso, área"""
        user = self.request.user
        try:
            if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
                orden = serializer.save(sede=user.sede)
            else:
                orden = serializer.save()

            logger.info(
                "Orden de produccion creada por Jefe de Planta",
                extra={
                    "sd": {
                        "entity": "OrdenProduccion",
                        "id": orden.id,
                        "user": user.username}})

            # Descarga automática de químicos si la OP ya nace con fórmula y bodega
            # de químicos (creación en un solo paso). El servicio es idempotente vía
            # inventario_descontado y atómico internamente.
            if orden.formula_color and orden.bodega_quimicos and not orden.inventario_descontado:
                DescargaQuimicosService.descargar_para_op(orden, user)
                logger.info(
                    "Descarga automática de químicos al crear OP",
                    extra={
                        "sd": {
                            "entity": "OrdenProduccion",
                            "id": orden.id,
                            "user": user.username}})
        except Exception as e:
            logger.error(
                "Error al crear Orden de produccion",
                extra={
                    "sd": {
                        "entity": "OrdenProduccion",
                        "error": str(e)}})
            raise

    @action(detail=True, methods=['patch'])
    def completar_detalles(self, request, pk=None):
        """
        Jefe de Área completa los detalles de la orden:
        - Selecciona producto (entrada/salida)
        - Selecciona bodega (entrada/salida)
        - Asigna máquinas
        - Asigna operarios
        """
        orden = self.get_object()
        user = request.user

        # Verificar que el usuario es jefe del área correcta
        if hasattr(user, 'area') and user.area and user.area != orden.area:
            return Response(
                {'detail': 'Solo el jefe del área asignada puede completar detalles.'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        campos_permitidos = {
            'producto_entrada', 'producto_salida', 'bodega_entrada', 'bodega_salida',
            'maquina_asignada', 'operario_asignado', 'formula_color', 'bodega_quimicos'
        }

        try:
            # Actualizar solo campos permitidos. Todos son FKs: se asignan por id
            # (`<campo>_id`) porque el payload JSON envía identificadores, no instancias.
            for campo in campos_permitidos:
                if campo in data:
                    setattr(orden, f"{campo}_id", data[campo])

            orden.save()

            # Descarga automática de químicos si la OP tiene fórmula
            if orden.formula_color and orden.bodega_quimicos:
                DescargaQuimicosService.descargar_para_op(orden, user)
                logger.info(
                    f"Descarga de químicos ejecutada para OP-{orden.codigo}",
                    extra={
                        "sd": {
                            "entity": "OrdenProduccion",
                            "id": orden.id}})

            logger.info(
                "Detalles de OP completados por Jefe de Área",
                extra={
                    "sd": {
                        "entity": "OrdenProduccion",
                        "id": orden.id,
                        "user": user.username}})
            return Response(OrdenProduccionSerializer(orden).data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(
                "Error al completar detalles de OP",
                extra={
                    "sd": {
                        "entity": "OrdenProduccion",
                        "error": str(e)}})
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        user = self.request.user
        orden_actual = self.get_object()
        justificacion = self.request.data.get('justificacion', '')

        # Validar justificación si ya hay descarga de químicos
        if orden_actual.inventario_descontado and not justificacion:
            raise ValidationError(
                {'justificacion': 'Justificación requerida para modificar una OP con químicos ya descontados.'})

        try:
            orden = serializer.save()

            # Ajustar descarga si ya estaba descontada y hay cambios en peso o fórmula
            peso_changed = orden.peso_neto_requerido != orden_actual.peso_neto_requerido
            formula_changed = orden.formula_color != orden_actual.formula_color
            if orden.inventario_descontado and (peso_changed or formula_changed):
                DescargaQuimicosService.ajustar_descarga_op(orden, user, justificacion)
                logger.info(
                    f"Descarga de químicos ajustada para OP-{orden.codigo}",
                    extra={
                        "sd": {
                            "entity": "OrdenProduccion",
                            "id": orden.id,
                            "user": user.username}})
            elif (
                orden.formula_color
                and orden.bodega_quimicos
                and not orden.inventario_descontado
            ):
                # Primera descarga si no se había hecho
                DescargaQuimicosService.descargar_para_op(orden, user)
                logger.info(
                    f"Descarga de químicos ejecutada para OP-{orden.codigo}",
                    extra={
                        "sd": {
                            "entity": "OrdenProduccion",
                            "id": orden.id,
                            "user": user.username}})

            logger.info(
                "Orden de produccion actualizada exitosamente",
                extra={
                    "sd": {
                        "entity": "OrdenProduccion",
                        "id": orden.id,
                        "user": user.username}})
        except Exception as e:
            logger.error("Error al actualizar Orden de produccion", extra={
                         "sd": {"entity": "OrdenProduccion", "error": str(e)}})
            raise

    def destroy(self, request, *args, **kwargs):
        user = request.user
        orden = self.get_object()
        justificacion = request.data.get('justificacion', '')

        # Validar justificación obligatoria para eliminar OP
        if not justificacion:
            return Response(
                {'justificacion': 'Justificación requerida para eliminar una orden de producción.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Revertir descarga de químicos si ya estaba descontada
                if orden.inventario_descontado:
                    DescargaQuimicosService.revertir_descarga_op(orden, user, justificacion)
                    logger.info(
                        f"Descarga de químicos revertida para OP-{orden.codigo}",
                        extra={
                            "sd": {
                                "entity": "OrdenProduccion",
                                "id": orden.id,
                                "user": user.username}})

                orden.delete()
                logger.info("Orden de produccion eliminada exitosamente", extra={
                            "sd": {"entity": "OrdenProduccion", "user": user.username}})

            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error("Error al eliminar Orden de produccion", extra={
                         "sd": {"entity": "OrdenProduccion", "error": str(e)}})
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def requisitos_materiales(self, request, pk=None):
        """
        Calcula detalladamente los materiales y químicos necesarios para completar la OP.
        """
        orden = self.get_object()
        peso_total = orden.peso_neto_requerido

        requisitos = []

        # 1. Materia Prima principal (Hilo/Tela base)
        # Asumimos una relación 1:1 por simplicidad en este paso o lógica específica.
        # producto_entrada es el material base consumido (Fase 14: renombrado de 'producto').
        producto_base = orden.producto_entrada or orden.producto_salida
        if producto_base:
            requisitos.append({
                "producto_id": producto_base.id,
                "producto_nombre": producto_base.descripcion,
                "tipo": producto_base.tipo,
                "cantidad_requerida": peso_total,
                "unidad": producto_base.unidad_medida,
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

        # 3. Adjuntar stock disponible
        # Se requiere buscar el stock en la bodega general (o bodega_quimicos)
        # para validar si se puede iniciar.
        from inventory.models import StockBodega
        from django.db.models import Sum

        for req in requisitos:
            bodegas_a_revisar = [orden.bodega_entrada_id, orden.bodega_quimicos_id]
            stock = StockBodega.objects.filter(
                producto_id=req["producto_id"],
                bodega_id__in=[b for b in bodegas_a_revisar if b is not None]
            ).aggregate(total=Sum("cantidad"))["total"] or Decimal("0.0")
            req["stock_disponible"] = round(float(stock), 4)

        return Response({
            "orden_codigo": orden.codigo,
            "peso_total_op": peso_total,
            "requisitos": requisitos
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='stock-quimicos',
            permission_classes=[IsAuthenticated, IsTintoreroOrAdmin])
    def stock_quimicos(self, request):
        """
        ISP: Endpoint específico para tintorero para consultar stock de químicos disponibles.
        Retorna lista de productos tipo='quimico' con stock actual, mínimo y estado de alerta.
        """
        sede_id = parse_int_param(request.query_params.get('sede_id'), 'sede_id')
        if not sede_id and hasattr(request.user, 'sede') and request.user.sede:
            sede_id = request.user.sede.id
        elif not sede_id:
            return Response({'error': 'sede_id requerido'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from inventory.models import StockBodega
            from django.db.models import F, Case, When, BooleanField

            # Filtrar stock de químicos en bodegas de la sede
            stock_quimicos = StockBodega.objects.filter(
                bodega__sede_id=sede_id,
                producto__tipo='quimico',
                lote__isnull=True  # Solo stock sin lote (químicos de uso general)
            ).select_related('producto', 'bodega').annotate(
                alerta=Case(
                    When(cantidad__lt=F('producto__stock_minimo'), then=True),
                    default=False,
                    output_field=BooleanField()
                )
            ).annotate(
                producto_codigo=F('producto__codigo'),
                producto_descripcion=F('producto__descripcion'),
                stock_minimo=F('producto__stock_minimo'),
                bodega_nombre=F('bodega__nombre'),
            ).values(
                'producto_id', 'producto_codigo', 'producto_descripcion',
                'cantidad', 'stock_minimo', 'alerta', 'bodega_nombre'
            ).order_by('-alerta', 'producto_codigo')

            return Response(stock_quimicos, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error obteniendo stock de químicos: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['patch', 'post'], url_path='cambiar_estado')
    def cambiar_estado(self, request, pk=None):
        orden = self.get_object()
        serializer = OrdenProduccionEstadoSerializer(orden, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'estado actualizado', 'estado': serializer.data['estado']})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ------------------------------------------------------------------
    # Trazabilidad de transformaciones máquina a máquina
    # ------------------------------------------------------------------
    def _puede_operar_area(self, user, orden):
        """Aislamiento por área/sede: admins y jefe de planta ven todo; el
        jefe de área y el operario solo operan en su propia área Y sede.
        El doble chequeo (área + sede) es defensa en profundidad ante una
        asignación de área inconsistente con la sede del usuario."""
        if user.is_superuser or user.groups.filter(
            name__in=['admin_sistemas', 'admin_sede', 'jefe_planta']
        ).exists():
            return True
        return (
            bool(getattr(user, 'area_id', None))
            and user.area_id == orden.area_id
            and user.sede_id == orden.sede_id
        )

    @action(detail=True, methods=['post'], url_path='registrar-transformacion')
    def registrar_transformacion(self, request, pk=None):
        """Registra una transformación (un paso de máquina) en la OP.

        Solo Jefe de Área / Operario del área (o admins). El producto de entrada
        y la merma se derivan/calculan en el servicio y el modelo.
        """
        orden = get_object_or_404(OrdenProduccion, pk=pk)
        user = request.user
        if not self._puede_operar_area(user, orden):
            return Response(
                {'detail': 'No pertenece al área de la orden de producción.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            transformacion = TransformacionService.registrar(orden, request.data, user)
        except DjangoValidationError as e:
            detalle = e.message_dict if hasattr(e, 'message_dict') else e.messages
            return Response({'detail': detalle}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            TransformacionProductoSerializer(transformacion).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['get'], url_path='transformaciones')
    def transformaciones(self, request, pk=None):
        """Lista las transformaciones de la OP en orden de secuencia."""
        orden = get_object_or_404(OrdenProduccion, pk=pk)
        if not self._puede_operar_area(request.user, orden):
            return Response(
                {'detail': 'No pertenece al área de la orden de producción.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = orden.transformaciones.select_related(
            'producto_entrada', 'producto_salida', 'maquina', 'operario'
        ).order_by('numero_secuencia')
        return Response(TransformacionProductoSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'], url_path='trazabilidad')
    def trazabilidad(self, request, pk=None):
        """Devuelve el flujo completo de la OP: pasos, mermas y siguiente área."""
        orden = get_object_or_404(OrdenProduccion, pk=pk)
        if not self._puede_operar_area(request.user, orden):
            return Response(
                {'detail': 'No pertenece al área de la orden de producción.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(TrazabilidadService.construir(orden))
