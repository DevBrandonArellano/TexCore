import logging
from decimal import Decimal

from django.db import transaction, models
from django.utils import timezone

from rest_framework import status, viewsets, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from inventory.serializers import (
    MovimientoInventarioSerializer, AuditoriaMovimientoSerializer,
    MovimientoInventarioUpdateSerializer,
)
from inventory.models import StockBodega, MovimientoInventario, AuditoriaMovimiento
from inventory.permissions import IsInventoryStaffOrAdmin, IsInventoryWriterOrAdmin
from inventory.utils import safe_get_or_create_stock
from gestion.models import LoteProduccion

logger = logging.getLogger('inventory.views')


class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'auditoria'):
            return [IsInventoryStaffOrAdmin()]
        return [IsInventoryWriterOrAdmin()]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # Aislamiento por sede — igual que StockBodegaViewSet.get_queryset
        if not (user.is_superuser or user.groups.filter(
                name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()):
            queryset = queryset.filter(
                models.Q(bodega_origen__sede=user.sede) | models.Q(bodega_destino__sede=user.sede)
            )

        bodega_id = self.request.query_params.get('bodega_id')
        producto_id = self.request.query_params.get('producto_id')
        tipo = self.request.query_params.get('tipo')
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')

        if bodega_id:
            queryset = queryset.filter(models.Q(bodega_origen_id=bodega_id) | models.Q(bodega_destino_id=bodega_id))

        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)

        if fecha_desde:
            queryset = queryset.filter(fecha__gte=fecha_desde)

        if fecha_hasta:
            queryset = queryset.filter(fecha__lte=f"{fecha_hasta}T23:59:59")

        if tipo and tipo != 'all':
            if tipo == 'entrada':
                if bodega_id:
                    queryset = queryset.filter(bodega_destino_id=bodega_id)
                else:
                    queryset = queryset.filter(
                        tipo_movimiento__in=['COMPRA', 'PRODUCCION', 'DEVOLUCION', 'AJUSTE'],
                        bodega_destino__isnull=False
                    )
            elif tipo == 'salida':
                if bodega_id:
                    queryset = queryset.filter(bodega_origen_id=bodega_id)
                else:
                    queryset = queryset.filter(
                        tipo_movimiento__in=['VENTA', 'CONSUMO', 'MERMA']
                    )

        # Orden por defecto por fecha descendente
        return queryset.order_by('-fecha')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            logger.warning(
                "Fallo al validar MovimientoInventario",
                extra={
                    "sd": {
                        "entity": "MovimientoInventario",
                        "field": "serializer",
                        "reason": str(
                            e.detail)}})
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        tipo_movimiento = serializer.validated_data.get('tipo_movimiento')
        producto = serializer.validated_data.get('producto')
        cantidad = serializer.validated_data.get('cantidad')
        bodega_origen = serializer.validated_data.get('bodega_origen')
        bodega_destino = serializer.validated_data.get('bodega_destino')
        lote = serializer.validated_data.get('lote')
        lote_codigo = request.data.get('lote_codigo')

        # Nuevos campos
        proveedor = serializer.validated_data.get('proveedor')
        pais = request.data.get('pais', '')
        calidad = request.data.get('calidad', '')

        try:
            with transaction.atomic():
                # Handle Manual Batch Creation/Lookup
                if not lote and lote_codigo:
                    lote, created = LoteProduccion.objects.get_or_create(
                        codigo_lote=lote_codigo,
                        defaults={
                            'peso_neto_producido': cantidad,
                            'operario': request.user,
                            'maquina': None,
                            'turno': 'N/A',
                            'hora_inicio': timezone.now(),
                            'hora_final': timezone.now(),
                        }
                    )

                saldo_resultante = Decimal('0.00')

                # Logica para entradas (COMPRA, PRODUCCION, DEVOLUCION, AJUSTE sin signo)
                if tipo_movimiento in ['COMPRA', 'PRODUCCION', 'DEVOLUCION', 'AJUSTE']:
                    # Nota: AJUSTE sin signo se trata como entrada si hay destino
                    target_bodega = bodega_destino
                    if not target_bodega:
                        raise serializers.ValidationError(
                            {"bodega_destino": "Bodega de destino es requerida para entradas."})

                    stock, created = safe_get_or_create_stock(
                        StockBodega, bodega=target_bodega, producto=producto, lote=lote)
                    stock.cantidad += Decimal(str(cantidad))
                    stock._justificacion_auditoria = f"Entrada por {tipo_movimiento}"
                    stock.save()
                    saldo_resultante = stock.cantidad

                # Logica para salidas — MERMA es una salida: el material se
                # pierde y debe descontarse del stock igual que VENTA/CONSUMO.
                elif tipo_movimiento in ['VENTA', 'CONSUMO', 'MERMA']:
                    if not bodega_origen:
                        raise serializers.ValidationError(
                            {"bodega_origen": "Bodega de origen es requerida para salidas."})

                    stock = StockBodega.objects.select_for_update().get(
                        bodega=bodega_origen, producto=producto, lote=lote
                    )
                    if stock.cantidad < cantidad:
                        raise serializers.ValidationError(f"Stock insuficiente. Disponible: {stock.cantidad}")

                    stock.cantidad -= Decimal(str(cantidad))
                    stock._justificacion_auditoria = f"Salida por {tipo_movimiento}"
                    stock.save()
                    saldo_resultante = stock.cantidad

                # Crear el registro del movimiento
                movimiento = serializer.save(
                    usuario=request.user,
                    lote=lote,
                    saldo_resultante=saldo_resultante,
                    proveedor=proveedor,
                    pais=pais,
                    calidad=calidad
                )

                logger.info(
                    "Movimiento de inventario creado exitosamente",
                    extra={
                        "sd": {
                            "entity": "MovimientoInventario",
                            "id": movimiento.id,
                            "user": request.user.username}})
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except StockBodega.DoesNotExist:
            return Response({"error": "No existe stock para el producto/lote en la bodega especificada."},
                            status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as e:
            logger.warning(
                "Fallo validacion manual MovimientoInventario",
                extra={
                    "sd": {
                        "entity": "MovimientoInventario",
                        "field": "manual",
                        "reason": str(
                            e.detail)}})
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Error al crear MovimientoInventario",
                extra={
                    "sd": {
                        "entity": "MovimientoInventario",
                        "error": str(e)}})
            return Response({"error": f"Error inesperado: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        pass

    def destroy(self, request, *args, **kwargs):
        """
        Revierte el efecto de stock del movimiento (vía MovimientoReversionService)
        y luego lo elimina — mismo patrón que HistorialDespachoViewSet.destroy():
        justificación obligatoria, todo en una transacción, solo entonces se borra.

        Antes de este método, este ViewSet no sobreescribía destroy(): el
        destroy() genérico de DRF llamaba a instance.delete() sin setear
        _justificacion_auditoria (exigida por AuditableModelMixin), lo que
        producía un ValidationError de Django no capturado -> 500, sin
        revertir stock.
        """
        from inventory.services.movimiento_reversion import MovimientoReversionService

        movimiento = self.get_object()
        justificacion = request.data.get('justificacion', '').strip() if request.data else ''

        if not justificacion:
            return Response(
                {'justificacion': 'Justificación obligatoria para eliminar un movimiento de inventario'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                MovimientoReversionService.revertir(movimiento, request.user, justificacion)
                movimiento._justificacion_auditoria = justificacion
                movimiento.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Error al revertir/eliminar MovimientoInventario",
                extra={"sd": {"entity": "MovimientoInventario", "id": movimiento.id, "error": str(e)}},
                exc_info=True)
            return Response(
                {'error': f'Error al eliminar el movimiento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """
        Permite editar un movimiento de inventario existente.
        Solo se permiten editar movimientos de tipo COMPRA (entradas).
        Se registra auditoría y se recalcula el stock.
        """
        instance = self.get_object()
        user = request.user

        # 2. Validar que sea una entrada editable
        if instance.tipo_movimiento != 'COMPRA':
            return Response(
                {"error": "Solo se pueden editar entradas de compra. Para otros movimientos utilice ajustes."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 3. Validar datos
        update_serializer = MovimientoInventarioUpdateSerializer(data=request.data)
        if not update_serializer.is_valid():
            return Response(update_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        nueva_cantidad = update_serializer.validated_data['cantidad']
        nuevo_doc_ref = update_serializer.validated_data.get('documento_ref', instance.documento_ref)
        razon_cambio = update_serializer.validated_data['razon_cambio']

        try:
            with transaction.atomic():
                # Bloquear registro para evitar condiciones de carrera
                instance.refresh_from_db()

                cambios_realizados = []

                # 4. Auditoría y Actualización de Documento
                if instance.documento_ref != nuevo_doc_ref:
                    AuditoriaMovimiento.objects.create(
                        movimiento=instance,
                        usuario_modificador=user,
                        campo_modificado='documento_ref',
                        valor_anterior=instance.documento_ref or '',
                        valor_nuevo=nuevo_doc_ref or '',
                        razon_cambio=razon_cambio
                    )
                    cambios_realizados.append('documento_ref')
                    instance.documento_ref = nuevo_doc_ref

                # 5. Auditoría y Recalculo de Stock si cambió la cantidad
                if instance.cantidad != nueva_cantidad:
                    # Traer stock actual de la bodega destino (donde entró la mercadería)
                    stock = StockBodega.objects.select_for_update().get(
                        bodega=instance.bodega_destino,
                        producto=instance.producto,
                        lote=instance.lote
                    )

                    diferencia = nueva_cantidad - instance.cantidad

                    # Verificar que no quede stock negativo (si se reduce la entrada)
                    if diferencia < 0 and (stock.cantidad + diferencia) < 0:
                        raise serializers.ValidationError(
                            f"No se puede reducir la entrada en "
                            f"{abs(diferencia)} unidades porque el "
                            f"stock actual ({stock.cantidad}) es "
                            f"insuficiente (ya se consumió)."
                        )

                    # Actualizar stock
                    stock.cantidad += diferencia
                    stock._justificacion_auditoria = razon_cambio
                    stock.save()

                    # Registrar auditoría de cantidad
                    AuditoriaMovimiento.objects.create(
                        movimiento=instance,
                        usuario_modificador=user,
                        campo_modificado='cantidad',
                        valor_anterior=str(instance.cantidad),
                        valor_nuevo=str(nueva_cantidad),
                        razon_cambio=razon_cambio
                    )
                    cambios_realizados.append('cantidad')
                    instance.cantidad = nueva_cantidad

                if cambios_realizados:
                    instance.editado = True
                    instance.fecha_ultima_edicion = timezone.now()
                    instance._justificacion_auditoria = razon_cambio
                    instance.save()

                    return Response({
                        "message": "Movimiento actualizado con éxito",
                        "cambios": cambios_realizados
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "No se detectaron cambios"}, status=status.HTTP_200_OK)

        except StockBodega.DoesNotExist:
            return Response({"error": "No se encuentra el registro de stock asociado para recalcular."},
                            status=status.HTTP_404_NOT_FOUND)
        except serializers.ValidationError as e:
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(
                "Error al editar movimiento",
                extra={
                    'sd': {
                        'entity': 'MovimientoInventario',
                        'id': str(
                            instance.id),
                        'error': str(e)}},
                exc_info=True)
            return Response({"error": "Ocurrió un error inesperado al actualizar."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def auditoria(self, request, pk=None):
        """
        Retorna el historial de cambios de un movimiento específico.
        """
        movimiento = self.get_object()
        auditorias = movimiento.auditorias.all()
        serializer = AuditoriaMovimientoSerializer(auditorias, many=True)
        return Response(serializer.data)
