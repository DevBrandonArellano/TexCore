import logging
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import (
    OrdenProduccion, LoteProduccion, Maquina, DetalleFormula,
    ComponenteMezclaOP, ConsumoLoteDetalle,
    AreaProcessStep, OrdenProduccionSubproceso, EtapaProduccion, TransferenciaInterarea,
    TransformacionProducto
)
from gestion.permissions import (
    IsTintoreroOrAdmin, IsAdminSistemasOrSede, IsJefeAreaOrAdmin, IsJefePlantaOrAdmin,
    IsJefeAreaOrOperarioOrAdmin,
)
from gestion.serializers import (
    OrdenProduccionSerializer, OrdenProduccionEstadoSerializer,
    LoteProduccionSerializer,
    MaquinaSerializer, RegistrarLoteProduccionSerializer,
    ComponenteMezclaOPSerializer, ConsumoLoteDetalleSerializer,
    AreaProcessStepSerializer, OrdenProduccionSubprocesoSerializer,
    EtapaProduccionSerializer, TransferenciaInterareaSerializer,
    TransformacionProductoSerializer,
)
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.registro_lote import RegistroLoteService
from gestion.services.transformacion import TransformacionService
from gestion.services.trazabilidad import TrazabilidadService
from gestion.utils import PrintingService
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class MaquinaViewSet(viewsets.ModelViewSet):
    queryset = Maquina.objects.all()
    serializer_class = MaquinaSerializer
    pagination_class = None

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
            else:
                # If no area assigned, return none for safety
                return Maquina.objects.none()

        # Multi-tenancy: filter by sede if not global admin
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(area__sede=user.sede)

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


class OrdenProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = OrdenProduccionSerializer

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
            # Solo Jefe de Planta, Admin Sistemas o Admin Sede pueden crear
            return [IsAuthenticated(), IsJefeAreaOrAdmin()]
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

        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

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
        sede_id = request.query_params.get('sede_id')
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
                producto_stock_minimo=F('producto__stock_minimo'),
                bodega_nombre=F('bodega__nombre'),
            ).values(
                'producto_id', 'producto_codigo', 'producto_descripcion',
                'cantidad', 'producto_stock_minimo', 'alerta', 'bodega_nombre'
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


class LoteProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = LoteProduccionSerializer
    pagination_class = None
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['hora_final', 'hora_inicio', 'peso_neto_producido']
    ordering = ['-hora_final']

    @action(detail=True, methods=['get'], url_path='obtener-costo')
    def obtener_costo(self, request, pk=None):
        """GET /api/lotes-produccion/{id}/obtener-costo/ — F0-002.

        Calcula (o recalcula) el desglose de costos del lote: MP + químicos
        + operario + máquina. El vendedor ve el margen antes de fijar precio.
        """
        from gestion.services.costeo_service import CostoLoteService
        from gestion.serializers import CostoLoteProduccionSerializer

        lote = self.get_object()
        costo = CostoLoteService.calcular_costo(lote, request.user)
        return Response(CostoLoteProduccionSerializer(costo).data)

    def get_queryset(self):
        user = self.request.user
        queryset = LoteProduccion.objects.select_related(
            'orden_produccion', 'orden_produccion__producto_entrada',
            'orden_produccion__producto_salida',
            'orden_produccion__sede', 'maquina', 'operario'
        ).all()

        # Security: Jefe de Área only sees lots from their area
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(orden_produccion__area=user.area)
            else:
                return LoteProduccion.objects.none()

        # Filter by operario (used by Operario Dashboard for "my entries")
        operario_id = self.request.query_params.get('operario')
        if operario_id:
            queryset = queryset.filter(operario_id=operario_id)

        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(orden_produccion__sede_id=sede_id)
        orden_produccion_id = self.request.query_params.get('orden_produccion')
        if orden_produccion_id:
            queryset = queryset.filter(orden_produccion_id=orden_produccion_id)
        return queryset

    @transaction.atomic
    def perform_update(self, serializer):
        from inventory.models import StockBodega, MovimientoInventario
        from decimal import Decimal
        from inventory.utils import safe_get_or_create_stock
        from django.db.models import Sum

        lote = self.get_object()
        old_peso_neto = lote.peso_neto_producido

        # Save the updated lote
        updated_lote = serializer.save()

        new_peso_neto = updated_lote.peso_neto_producido

        if old_peso_neto != new_peso_neto:
            diff = new_peso_neto - old_peso_neto
            orden = updated_lote.orden_produccion
            # Fase 14: el flujo de transformación separa entrada/salida. La salida
            # va a bodega_salida (producto_salida) y la materia prima/químicos se
            # consumen de bodega_entrada (producto_entrada). Fallbacks por compat.
            bodega_salida = orden.bodega_salida or orden.bodega_entrada
            bodega_entrada = orden.bodega_entrada or orden.bodega_salida
            producto_salida = orden.producto_salida or orden.producto_entrada
            producto_entrada = orden.producto_entrada or orden.producto_salida

            # 1. Adjust Output Stock
            try:
                stock_output = StockBodega.objects.select_for_update().get(
                    bodega=bodega_salida, producto=producto_salida, lote=updated_lote
                )
                if stock_output.cantidad + diff < 0:
                    raise ValidationError(
                        {"peso_neto_producido": "El cambio resultaría en stock negativo de producto terminado."})

                stock_output.cantidad = (stock_output.cantidad + diff).quantize(Decimal('0.01'))
                stock_output._justificacion_auditoria = f"Correccion de lote {updated_lote.codigo_lote}"
                stock_output.save()

                MovimientoInventario.objects.create(
                    tipo_movimiento='AJUSTE',
                    producto=producto_salida,
                    lote=updated_lote,
                    bodega_destino=bodega_salida if diff > 0 else None,
                    bodega_origen=bodega_salida if diff < 0 else None,
                    cantidad=abs(diff).quantize(Decimal('0.01')),
                    usuario=self.request.user,
                    documento_ref=f'CORRECCION-LOTE-{updated_lote.codigo_lote}',
                    saldo_resultante=stock_output.cantidad
                )
            except StockBodega.DoesNotExist:
                pass

            # 2. Adjust Raw Material
            producto_input = producto_entrada
            stock_input, _ = safe_get_or_create_stock(
                StockBodega, bodega=bodega_entrada, producto=producto_input, lote=None)

            if stock_input.cantidad - diff < 0:
                raise ValidationError(
                    {"peso_neto_producido": "No hay suficiente stock de materia prima para esta corrección."})

            stock_input.cantidad = (stock_input.cantidad - diff).quantize(Decimal('0.01'))
            stock_input._justificacion_auditoria = f"Correccion de lote {updated_lote.codigo_lote}"
            stock_input.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='AJUSTE',
                producto=producto_input,
                bodega_origen=bodega_entrada if diff > 0 else None,
                bodega_destino=bodega_entrada if diff < 0 else None,
                cantidad=abs(diff).quantize(Decimal('0.01')),
                usuario=self.request.user,
                documento_ref=f'CORRECCION-LOTE-{updated_lote.codigo_lote}'
            )

            # 3. Adjust Chemicals
            if orden.formula_color:
                from gestion.models import DetalleFormula
                for detalle in DetalleFormula.objects.filter(fase__formula=orden.formula_color):
                    quimico = detalle.producto
                    cantidad_diff = ((diff * detalle.gramos_por_kilo) / Decimal('1000.0')).quantize(Decimal('0.01'))
                    if cantidad_diff != 0:
                        stock_quimico, _ = safe_get_or_create_stock(
                            StockBodega, bodega=bodega_entrada, producto=quimico, lote=None)
                        if stock_quimico.cantidad - cantidad_diff < 0:
                            raise ValidationError(
                                {"peso_neto_producido": f"No hay suficiente stock de quimico {quimico.codigo}."})
                        stock_quimico.cantidad = (stock_quimico.cantidad - cantidad_diff).quantize(Decimal('0.01'))
                        stock_quimico._justificacion_auditoria = f"Correccion de lote {updated_lote.codigo_lote}"
                        stock_quimico.save()

                        MovimientoInventario.objects.create(
                            tipo_movimiento='AJUSTE',
                            producto=quimico,
                            bodega_origen=bodega_entrada if cantidad_diff > 0 else None,
                            bodega_destino=bodega_entrada if cantidad_diff < 0 else None,
                            cantidad=abs(cantidad_diff),
                            usuario=self.request.user,
                            documento_ref=f'CORRECCION-LOTE-{updated_lote.codigo_lote}'
                        )

            # 4. Update order status
            total_producido = orden.lotes.aggregate(Sum('peso_neto_producido'))[
                'peso_neto_producido__sum'] or Decimal('0.00')
            if total_producido < orden.peso_neto_requerido and orden.estado == 'finalizada':
                orden.estado = 'en_proceso'
            elif total_producido >= orden.peso_neto_requerido and orden.estado == 'en_proceso':
                from django.utils import timezone
                orden.estado = 'finalizada'
                orden.fecha_fin_planificada = timezone.now().date()
            orden.save()

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'generate_zpl', 'genealogia']:
            return [IsAuthenticated()]
        if self.request.user.groups.filter(
            name__in=[
                'jefe_area',
                'jefe_planta',
                'admin_sistemas',
                'admin_sede',
                'empaquetado',
                'operario']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    @action(detail=True, methods=['get'])
    def genealogia(self, request, pk=None):
        """
        Retorna la genealogía y trazabilidad inversa del lote.
        Muestra la máquina, operario, fórmula de color, y químicos consumidos.
        """
        lote = self.get_object()
        orden = lote.orden_produccion

        data = {
            "lote_codigo": lote.codigo_lote,
            "producto": (lote.orden_produccion.producto_salida.descripcion
                         if lote.orden_produccion and lote.orden_produccion.producto_salida else None),
            "peso_neto": lote.peso_neto_producido,
            "peso_merma": lote.peso_merma,
            "tipo_merma": lote.get_tipo_merma_display() if lote.tipo_merma else None,
            "calidad": lote.get_clasificacion_calidad_display(),
            "operario": lote.operario.username if lote.operario else None,
            "maquina": lote.maquina.nombre if lote.maquina else None,
            "fechas": {
                "inicio": lote.hora_inicio,
                "final": lote.hora_final},
            "orden_produccion": {
                "codigo": orden.codigo if orden else None,
                "formula_color": (
                    orden.formula_color.nombre_color
                    if orden and orden.formula_color else None
                ),
            },
            "quimicos_consumidos": []}

        if orden:
            # Obtener descargas de químicos de esta OP
            from gestion.models import DescargaQuimicoOP
            descargas = DescargaQuimicoOP.objects.filter(
                orden_produccion=orden,
                estado='aplicada'
            ).select_related('producto')

            # El consumo de la OP es global, proporcionamos el listado de químicos
            # consumidos para producir todo el batch.
            for d in descargas:
                data["quimicos_consumidos"].append({
                    "quimico": d.producto.descripcion,
                    "cantidad_total_op_kg": d.cantidad_real_kg or d.cantidad_calculada_kg,
                    "fase": d.fase.get_nombre_display() if d.fase else 'N/A'
                })

        logger.info(
            "Genealogía de lote consultada",
            extra={'sd': {
                'entity': 'LoteProduccion',
                'action': 'READ_GENEALOGY',
                'lote_codigo': lote.codigo_lote,
                'user': request.user.username
            }}
        )

        return Response(data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def rechazar(self, request, pk=None):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        from gestion.services.merma_stock import MermaStockService

        lote = self.get_object()
        orden = lote.orden_produccion
        bodega_salida = orden.bodega_salida or orden.bodega_entrada
        bodega_entrada_op = orden.bodega_entrada or orden.bodega_salida
        _ = bodega_salida  # alias formerly used; bodega_entrada_op used below

        justificacion = request.data.get('justificacion', '')
        if not justificacion:
            return Response(
                {'success': False, 'error': {'message': 'Justificación requerida para rechazar un lote.'}},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Revertir consumo de mezcla (si aplica)
        if lote.consumos_detalle.exists():
            ConsumoMezclaService.revertir(lote, request.user, justificacion)

        # Revertir merma vendible (si aplica)
        MermaStockService.revertir(lote, request.user, justificacion)

        # 1. Reverse Output (Remove the produced lot from stock)
        try:
            # Find the stock item. If it doesn't exist (already sold/moved), we have a problem.
            # We assume it's still there for a "rejection".
            stock_output = StockBodega.objects.select_for_update().get(
                bodega=bodega_salida, producto=orden.producto_salida or orden.producto_entrada, lote=lote
            )
            cantidad_revertir = stock_output.cantidad
            if cantidad_revertir <= 0:
                return Response({"error": "No hay stock del lote para revertir (ya fue movido o vendido)."},
                                status=status.HTTP_400_BAD_REQUEST)

            stock_output.cantidad = Decimal('0.00')
            stock_output._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
            stock_output.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='AJUSTE',
                producto=orden.producto_salida or orden.producto_entrada,
                lote=lote,
                bodega_origen=bodega_salida,
                cantidad=cantidad_revertir,
                usuario=request.user,
                documento_ref=f'RECHAZO-LOTE-{lote.codigo_lote}',
                saldo_resultante=stock_output.cantidad
            )
        except StockBodega.DoesNotExist:
            return Response({"error": "El stock del lote no existe en la bodega de origen."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 2. Reverse Inputs (Return raw materials to stock)
        # Calculate what was consumed

        # 2.1 Raw Material
        producto_input = orden.producto_entrada or orden.producto_salida
        stock_input, _ = safe_get_or_create_stock(
            StockBodega,
            bodega=bodega_entrada_op,
            producto=producto_input,
            lote=None
        )
        stock_input.cantidad = (stock_input.cantidad + cantidad_revertir).quantize(Decimal('0.01'))
        stock_input._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
        stock_input.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='DEVOLUCION',
            producto=producto_input,
            bodega_destino=bodega_entrada_op,
            cantidad=cantidad_revertir.quantize(Decimal('0.01')),
            usuario=request.user,
            documento_ref=f'REV-LOTE-{lote.codigo_lote}'
        )

        # 2.2 Chemicals
        if orden.formula_color:
            from gestion.models import DetalleFormula
            for detalle in DetalleFormula.objects.filter(fase__formula=orden.formula_color):
                quimico = detalle.producto
                cantidad_devuelta = (
                    (cantidad_revertir
                     * detalle.gramos_por_kilo) /
                    Decimal('1000.0')).quantize(
                    Decimal('0.01'))

                stock_quimico, _ = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodega_entrada_op,
                    producto=quimico,
                    lote=None
                )
                stock_quimico.cantidad += cantidad_devuelta
                stock_quimico._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
                stock_quimico.save()

                MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto=quimico,
                    bodega_destino=bodega_entrada_op,
                    cantidad=cantidad_devuelta,
                    usuario=request.user,
                    documento_ref=f'REV-LOTE-{lote.codigo_lote}'
                )

        # 3. Mark Lote as rejected or delete
        from gestion.middleware import set_cascade_justification, clear_cascade_justification
        from django.db.models import Sum

        try:
            set_cascade_justification(f"Reversion por rechazo de lote {lote.codigo_lote}")
            lote.delete()
        finally:
            clear_cascade_justification()

        # 4. Update order status
        total_producido = orden.lotes.aggregate(Sum('peso_neto_producido'))[
            'peso_neto_producido__sum'] or Decimal('0.00')
        if total_producido < orden.peso_neto_requerido and orden.estado == 'finalizada':
            orden.estado = 'en_proceso'
            orden.save()

        return Response({"message": "Lote rechazado y movimientos revertidos correctamente."},
                        status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def generate_zpl(self, request, pk=None):
        lote = self.get_object()
        orden = lote.orden_produccion

        # Prepare data for microservice
        empresa = orden.sede.nombre if orden and orden.sede else 'Sede Principal'
        orden.sede.location if orden and orden.sede else ''

        # Fallback description logic
        if hasattr(orden, 'producto_descripcion'):
            producto_desc = orden.producto_descripcion
        else:
            producto = (orden.producto_salida or orden.producto_entrada) if orden else None
            producto_desc = producto.descripcion if producto else 'N/A'

        peso_neto = float(lote.peso_neto_producido)
        tara = float(lote.tara) if lote.tara else 0.0
        peso_bruto = float(lote.peso_bruto) if lote.peso_bruto else 0.0
        cantidad_metros = float(lote.cantidad_metros) if lote.cantidad_metros else None

        producto_op = (orden.producto_salida or orden.producto_entrada) if orden else None
        unidad = producto_op.unidad_medida if producto_op else 'kg'
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
            return Response({"zpl": local_zpl.strip(),
                             "warning": "Servicio de impresión no disponible, usando fallback local."},
                            status=status.HTTP_200_OK)


class ComponenteMezclaOPViewSet(viewsets.ModelViewSet):
    """
    CRUD de componentes de mezcla.
    ISO 27001 A.9.4: solo jefe_area o admin pueden modificar.
    """
    serializer_class = ComponenteMezclaOPSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        qs = ComponenteMezclaOP.objects.select_related(
            'producto', 'bodega', 'orden'
        )
        orden_id = self.request.query_params.get('orden')
        if orden_id:
            qs = qs.filter(orden_id=orden_id)
        sede = getattr(self.request.user, 'sede', None)
        if sede:
            qs = qs.filter(orden__sede=sede)
        return qs

    def perform_destroy(self, instance):
        justificacion = self.request.data.get('justificacion', '')
        if not justificacion:
            raise ValidationError({'justificacion': 'Justificación requerida para eliminar un componente.'})
        instance._justificacion_auditoria = justificacion
        instance.delete()


class ConsumoLoteDetalleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ISO 27001 A.12.4: ConsumoLoteDetalle es inmutable — solo lectura.
    La eliminación ocurre únicamente vía endpoint rechazar/ del lote.
    """
    serializer_class = ConsumoLoteDetalleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ConsumoLoteDetalle.objects.select_related(
            'lote_produccion', 'lote_origen'
        )
        lote_id = self.request.query_params.get('lote_produccion')
        if lote_id:
            qs = qs.filter(lote_produccion_id=lote_id)
        return qs


class RegistrarLoteProduccionView(APIView):
    """
    API View to register a production lot and handle all related inventory movements.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, orden_id, *args, **kwargs):
        user = request.user
        orden = get_object_or_404(OrdenProduccion, id=orden_id)

        # Security: Jefe de Área only can register lots for their area
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if not (hasattr(user, 'area') and user.area == orden.area):
                return Response({"detail": "No tienes permiso para registrar lotes en esta área."},
                                status=status.HTTP_403_FORBIDDEN)

        serializer = RegistrarLoteProduccionSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Fallo al validar lote de producción",
                extra={
                    "sd": {
                        "entity": "LoteProduccion",
                        "field": "serializer",
                        "reason": str(
                            serializer.errors)}})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lote_data = serializer.validated_data
        completar_orden = lote_data.pop('completar_orden', False)

        try:
            lote = RegistroLoteService.registrar_lote(
                orden=orden,
                lote_data=lote_data,
                user=user,
                completar_orden=completar_orden
            )
            return Response(LoteProduccionSerializer(lote).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.warning(f"Validation error registering lote for orden {orden.id}: {e.detail}")
            return Response({"detail": str(e.detail) if isinstance(e.detail, (list, dict))
                            else e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoValidationError as e:
            msg = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
            logger.warning(f"Django validation error registering lote for orden {orden.id}: {msg}")
            return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            logger.error(f"IntegrityError registering lote for orden {orden.id}: {str(e)}")
            return Response({"detail": "Código de lote duplicado. Intenta nuevamente."},
                            status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error registering lote: {str(e)}")
            return Response({"detail": "Error al registrar el lote. Contacta al administrador."},
                            status=status.HTTP_400_BAD_REQUEST)


class AreaProcessStepViewSet(viewsets.ModelViewSet):
    queryset = AreaProcessStep.objects.select_related('area', 'proceso')
    serializer_class = AreaProcessStepSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['area', 'tipo_flujo']
    ordering_fields = ['orden']
    ordering = ['area', 'orden']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta']).exists():
            return AreaProcessStep.objects.select_related('area', 'proceso')
        if hasattr(user, 'area') and user.area:
            return AreaProcessStep.objects.filter(area=user.area).select_related('area', 'proceso')
        return AreaProcessStep.objects.none()


class OrdenProduccionSubprocesoViewSet(viewsets.ModelViewSet):
    queryset = OrdenProduccionSubproceso.objects.select_related(
        'orden_produccion', 'area_proceso', 'area_proceso__area',
        'area_proceso__proceso', 'usuario_responsable'
    )
    serializer_class = OrdenProduccionSubprocesoSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['orden_produccion', 'estado', 'usuario_responsable', 'area_proceso__area']
    search_fields = ['orden_produccion__codigo', 'area_proceso__proceso__name']
    ordering_fields = ['fecha_inicio_real', 'fecha_fin_real', 'estado']
    ordering = ['area_proceso__orden']

    def get_queryset(self):
        user = self.request.user
        qs = OrdenProduccionSubproceso.objects.select_related(
            'orden_produccion', 'area_proceso', 'area_proceso__area',
            'area_proceso__proceso', 'usuario_responsable'
        )

        if user.is_superuser or user.groups.filter(name='Admin Sistemas').exists():
            return qs

        if hasattr(user, 'area') and user.area:
            return qs.filter(area_proceso__area=user.area)

        if hasattr(user, 'groups') and user.groups.filter(name__in=['Jefe de Área', 'Operario']).exists():
            return qs.filter(
                area_proceso__area__jefe_asignado=user
            ) | qs.filter(usuario_responsable=user)

        return qs.none()

    @action(detail=True, methods=['patch'])
    def iniciar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado != 'pendiente':
            return Response(
                {'detail': 'Solo se pueden iniciar subprocesos en estado pendiente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'en_progreso'
        subproceso.fecha_inicio_real = timezone.now()
        subproceso.usuario_responsable = request.user
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def completar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado not in ['en_progreso', 'pausado']:
            return Response(
                {'detail': 'El subproceso debe estar en progreso o pausado para completarse.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'completado'
        subproceso.fecha_fin_real = timezone.now()
        subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def rechazar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado == 'completado':
            return Response(
                {'detail': 'No se puede rechazar un subproceso completado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'rechazado'
        subproceso.motivo_rechazo = request.data.get('motivo_rechazo', '')
        subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def pausar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado != 'en_progreso':
            return Response(
                {'detail': 'Solo se pueden pausar subprocesos en progreso.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'pausado'
        subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )


class EtapaProduccionViewSet(viewsets.ModelViewSet):
    queryset = EtapaProduccion.objects.select_related(
        'area', 'maquina', 'bodega_entrada', 'bodega_salida'
    )
    serializer_class = EtapaProduccionSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['area', 'maquina']
    search_fields = ['nombre', 'area__nombre']
    ordering_fields = ['orden', 'area']
    ordering = ['area', 'orden']

    def get_queryset(self):
        user = self.request.user
        qs = EtapaProduccion.objects.select_related(
            'area', 'maquina', 'bodega_entrada', 'bodega_salida'
        )

        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta']).exists():
            return qs

        if hasattr(user, 'area') and user.area:
            return qs.filter(area=user.area)

        return qs.none()


class TransferenciaInterareaViewSet(viewsets.ModelViewSet):
    queryset = TransferenciaInterarea.objects.select_related(
        'orden_area_origen', 'orden_area_destino',
        'bodega_origen', 'bodega_destino', 'usuario_responsable'
    )
    serializer_class = TransferenciaInterareaSerializer
    filterset_fields = ['orden_area_origen', 'orden_area_destino']
    search_fields = ['orden_area_origen__codigo', 'orden_area_destino__codigo']
    ordering_fields = ['fecha_transferencia', 'cantidad_transferida']
    ordering = ['-fecha_transferencia']

    def get_permissions(self):
        # Crear/modificar/eliminar: solo Jefe de Planta y admins.
        # El Jefe de Área solo crea órdenes de producción; las transferencias
        # entre áreas son responsabilidad del Jefe de Planta.
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsJefePlantaOrAdmin()]
        # Listar/recuperar: Jefe de Área puede ver las de su área
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = TransferenciaInterarea.objects.select_related(
            'orden_area_origen', 'orden_area_destino',
            'bodega_origen', 'bodega_destino', 'usuario_responsable'
        )

        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta', 'admin_sede']).exists():
            return qs

        if hasattr(user, 'area') and user.area:
            return qs.filter(
                orden_area_origen__area=user.area
            ) | qs.filter(
                orden_area_destino__area=user.area
            )

        return qs.none()

    def perform_create(self, serializer):
        serializer.save(usuario_responsable=self.request.user)
