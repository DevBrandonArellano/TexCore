import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, serializers
from rest_framework.decorators import action

from inventory.serializers import HistorialDespachoSerializer
from inventory.models import (
    StockBodega, MovimientoInventario, HistorialDespacho,
    DetalleHistorialDespacho, DetalleHistorialDespachoPedido,
)
from inventory.permissions import IsDespachoReader, IsDespachoWriter
from gestion.models import LoteProduccion, PedidoVenta

logger = logging.getLogger('inventory.views')


class HistorialDespachoViewSet(viewsets.ModelViewSet):
    """
    API para consultar y gestionar el Historial de Despachos.
    Artefacto RUP: ViewSet
    Caso de Uso: CU-ReversionDespacho
    Patrón: REST API + Service Layer

    Incluye:
    - Lectura con filtros por fecha
    - Reversión con justificación obligatoria
    - Auditoría completa de cambios
    """
    serializer_class = HistorialDespachoSerializer

    def get_permissions(self):
        # destroy() ejecuta la misma reversión que la acción `revertir` — deben
        # exigir el mismo permiso (IsDespachoWriter excluye a `ejecutivo` a propósito).
        if self.action == 'destroy':
            return [IsDespachoWriter()]
        return [IsDespachoReader()]

    def get_queryset(self):
        queryset = HistorialDespacho.objects.select_related(
            'usuario'
        ).prefetch_related(
            'detalles__lote',
            'detalles__producto',
            'detallehistorialdespachopedido_set__pedido__cliente',
            'pedidos'
        ).all().order_by('-fecha_despacho', '-id')
        # -id como desempate: dos despachos creados en rápida sucesión pueden
        # recibir el mismo timestamp (auto_now_add, resolución de reloj del SO),
        # dejando el orden de ORDER BY indefinido sin una clave secundaria.

        # Filtros opcionales por fecha en query params (Navegación Híbrida)
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')

        if fecha_desde:
            queryset = queryset.filter(fecha_despacho__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_despacho__lte=f"{fecha_hasta}T23:59:59")

        return queryset

    def destroy(self, request, *args, **kwargs):
        """
        Revierte un despacho con justificación obligatoria.
        HTTP 400 si falta justificación.
        HTTP 204 si reversión exitosa.

        Restaura:
        - Stock en bodegas origen
        - DescargaQuimicoOP asociadas (marca como 'revertida')
        - Estado de pedidos a 'pendiente'
        """
        from inventory.services.despacho_reversion import DespachoReversionService

        historial = self.get_object()
        justificacion = request.data.get('justificacion', '').strip() if request.data else ''

        if not justificacion:
            return Response(
                {'justificacion': 'Justificación obligatoria para revertir despacho'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                DespachoReversionService.revertir_despacho(
                    historial, request.user, justificacion
                )
                historial.delete()

            return Response(status=status.HTTP_204_NO_CONTENT)

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error revirtiendo despacho {historial.id}: {str(e)}")
            return Response(
                {'error': f'Error al revertir despacho: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='revertir', permission_classes=[IsDespachoWriter])
    def revertir(self, request, pk=None):
        """
        Endpoint explícito para revertir despacho.
        Alternativa POST amigable a DELETE con body.
        """
        historial = self.get_object()
        justificacion = request.data.get('justificacion', '').strip()

        if not justificacion:
            return Response(
                {'justificacion': 'Justificación obligatoria para revertir despacho'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from inventory.services.despacho_reversion import DespachoReversionService

            with transaction.atomic():
                resultado = DespachoReversionService.revertir_despacho(
                    historial, request.user, justificacion
                )
                historial.delete()

            return Response({
                'message': 'Despacho revertido exitosamente',
                'resultado': resultado
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.error(f"Error revirtiendo despacho {historial.id}: {str(e)}")
            return Response(
                {'error': f'Error al revertir despacho: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ValidateLoteAPIView(APIView):
    """
    Valida si un código de lote (barras) existe y tiene stock disponible.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        code = request.data.get('code')
        if not code:
            return Response({'valid': False, 'reason': 'Código no proporcionado'}, status=400)

        # Buscar lote
        try:
            lote = LoteProduccion.objects.get(codigo_lote=code)
        except LoteProduccion.DoesNotExist:
            return Response({'valid': False, 'reason': 'Lote no encontrado en el sistema'}, status=200)

        # Buscar stock disponible
        stocks = StockBodega.objects.filter(lote=lote, cantidad__gt=0)

        # Filtrar por bodegas asignadas si es necesario (opcional)
        user = request.user
        if not (
            user.is_superuser or user.groups.filter(
                name__in=[
                    'admin_sistemas',
                    'admin_sede',
                'ejecutivo']).exists()):
            assigned_bodegas = user.bodegas_asignadas.values_list('id', flat=True)
            stocks = stocks.filter(bodega_id__in=assigned_bodegas)

        if not stocks.exists():
            return Response({'valid': False, 'reason': 'Lote existe pero no tiene stock disponible (0 kg)'}, status=200)

        # Tomar el primer stock disponible (o sumar si está en varias bodegas, pero para despacho suele ser unitario)
        stock_item = stocks.first()

        # Obtener producto desde la orden de producción (salida preferida, entrada como fallback)
        op = lote.orden_produccion
        producto = (op.producto_salida or op.producto_entrada) if op else None
        if not producto:
            return Response({'valid': False, 'reason': 'Lote no tiene producto asociado'}, status=200)

        return Response({
            'valid': True,
            'lote': {
                'codigo': lote.codigo_lote,
                'producto_id': producto.id,
                'producto_nombre': producto.descripcion,
                'peso': str(stock_item.cantidad),
                'bodega_id': stock_item.bodega.id,
                'bodega_nombre': stock_item.bodega.nombre
            }
        }, status=200)


class ProcessDespachoAPIView(APIView):
    """
    Procesa el despacho de múltiples pedidos y lotes escaneados.
    Descuenta inventario y actualiza estados. Guarda historial.

    Si algún producto del pedido no está completamente cubierto por los lotes
    escaneados, devuelve HTTP 409 con `items_incompletos` para que el frontend
    muestre un modal de confirmación.  El cliente reenvía con
    `confirmar_incompleto: true` para forzar el despacho parcial.
    """
    permission_classes = [IsDespachoWriter]

    @staticmethod
    def _calcular_incompletos(pedidos_ids: list, lotes_codes: list) -> dict:
        """
        Compara requerimientos de los pedidos contra stock de los lotes escaneados.
        No lanza excepciones — los errores de lote inválido se capturan en la transacción.
        Retorna {} si todo está cubierto.
        """
        reqs: dict = {}

        for p_id in pedidos_ids:
            try:
                pedido = PedidoVenta.objects.get(id=p_id)
            except PedidoVenta.DoesNotExist:
                continue
            for det in pedido.detalles.select_related('producto'):
                pid = det.producto_id
                if pid not in reqs:
                    reqs[pid] = {
                        'nombre': det.producto.descripcion,
                        'requerido': Decimal('0'),
                        'escaneado': Decimal('0'),
                    }
                reqs[pid]['requerido'] += det.peso

        for code in lotes_codes:
            try:
                lote = LoteProduccion.objects.select_related(
                    'orden_produccion__producto_salida',
                    'orden_produccion__producto_entrada',
                ).get(codigo_lote=code)
                stock = StockBodega.objects.filter(lote=lote, cantidad__gt=0).first()
                if stock and lote.orden_produccion:
                    op = lote.orden_produccion
                    producto = op.producto_salida or op.producto_entrada
                    if producto and producto.id in reqs:
                        reqs[producto.id]['escaneado'] += stock.cantidad
            except LoteProduccion.DoesNotExist:
                pass

        return {
            info['nombre']: {
                'requerido': float(info['requerido']),
                'escaneado': float(info['escaneado']),
                'faltante': float(info['requerido'] - info['escaneado']),
            }
            for info in reqs.values()
            if info['escaneado'] < info['requerido']
        }

    def post(self, request, *args, **kwargs):
        pedidos_ids = request.data.get('pedidos', [])
        lotes_codes = request.data.get('lotes', [])
        observaciones = request.data.get('observaciones', '')
        confirmar_incompleto = bool(request.data.get('confirmar_incompleto', False))

        if not pedidos_ids or not lotes_codes:
            return Response({'error': 'Faltan pedidos o lotes para procesar'}, status=400)

        # Calcular items no despachados ANTES de la transacción para poder
        # devolver 409 sin efectos secundarios.
        items_incompletos = self._calcular_incompletos(pedidos_ids, lotes_codes)
        if items_incompletos and not confirmar_incompleto:
            logger.warning(
                "Despacho incompleto rechazado — esperando confirmación del usuario",
                extra={"sd": {"entity": "HistorialDespacho", "items": list(items_incompletos.keys())}},
            )
            return Response(
                {
                    'error': 'despacho_incompleto',
                    'message': 'Hay productos con cantidad despachada menor a la requerida.',
                    'items_incompletos': items_incompletos,
                },
                status=409,
            )

        try:
            with transaction.atomic():
                historial = HistorialDespacho.objects.create(
                    usuario=request.user,
                    total_bultos=len(lotes_codes),
                    total_peso=Decimal('0.00'),
                    observaciones=observaciones,
                    items_no_despachados=items_incompletos,
                )

                for p_id in pedidos_ids:
                    DetalleHistorialDespachoPedido.objects.create(
                        historial=historial,
                        pedido_id=p_id,
                        cantidad_despachada=0,
                    )

                total_peso_despachado = Decimal('0.00')
                processed_lotes = []

                for code in lotes_codes:
                    try:
                        lote = LoteProduccion.objects.get(codigo_lote=code)
                        stock = StockBodega.objects.select_for_update().filter(lote=lote, cantidad__gt=0).first()

                        if not stock:
                            raise serializers.ValidationError(f"El lote {code} ya no tiene stock disponible.")

                        op = lote.orden_produccion
                        producto = (op.producto_salida or op.producto_entrada) if op else None
                        if not producto:
                            raise serializers.ValidationError(f"El lote {code} no tiene un producto asociado.")

                        cantidad_a_despachar = stock.cantidad
                        total_peso_despachado += cantidad_a_despachar

                        mov_venta = MovimientoInventario.objects.create(
                            tipo_movimiento='VENTA',
                            producto=producto,
                            cantidad=cantidad_a_despachar,
                            bodega_origen=stock.bodega,
                            lote=lote,
                            usuario=request.user,
                            documento_ref=f"Despacho #{historial.id} (Pedidos: {','.join(map(str, pedidos_ids))})",
                            saldo_resultante=Decimal('0.00'),
                        )

                        DetalleHistorialDespacho.objects.create(
                            historial=historial,
                            lote=lote,
                            producto=producto,
                            peso=cantidad_a_despachar,
                            movimiento_venta=mov_venta,  # P1-007: vínculo para reversión
                        )

                        stock.cantidad = 0
                        stock._justificacion_auditoria = f"Despacho procesado: {code}"
                        stock.save()

                        processed_lotes.append(code)

                    except LoteProduccion.DoesNotExist:
                        raise serializers.ValidationError(f"Lote {code} no válido.")
                    except serializers.ValidationError:
                        raise

                historial.total_peso = total_peso_despachado
                historial.save()

                pedidos = PedidoVenta.objects.filter(id__in=pedidos_ids)
                for pedido in pedidos:
                    if pedido.estado != 'despachado':
                        pedido.estado = 'despachado'
                        pedido.fecha_despacho = timezone.now().date()
                        pedido.save()

                logger.info(
                    "Despacho procesado exitosamente",
                    extra={"sd": {"entity": "HistorialDespacho", "id": historial.id, "user": request.user.username}},
                )
                return Response({
                    'message': 'Despacho procesado correctamente',
                    'despacho_id': historial.id,
                    'pedidos_actualizados': len(pedidos),
                    'lotes_procesados': len(processed_lotes),
                    'items_no_despachados': items_incompletos,
                })

        except serializers.ValidationError as e:
            logger.warning(
                "Fallo al validar despacho",
                extra={"sd": {"entity": "HistorialDespacho", "reason": str(e.detail)}},
            )
            return Response({'error': str(e.detail[0] if isinstance(e.detail, list) else e.detail)}, status=400)
        except Exception as e:
            logger.error("Error procesando despacho", extra={"sd": {"entity": "HistorialDespacho", "error": str(e)}})
            return Response({'error': str(e)}, status=500)
