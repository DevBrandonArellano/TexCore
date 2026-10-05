import logging

from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import LoteProduccion
from gestion.permissions import filtrar_lotes_por_sede, validar_visible
from inventory.models import MovimientoInventario, StockBodega
from inventory.permissions import IsInventoryWriterOrAdmin, validar_traslado
from inventory.serializers import TransferenciaSerializer
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger('inventory.views')


class TransferenciaStockAPIView(APIView):
    """
    API para realizar transferencias de stock entre dos bodegas.
    Garantiza la atomicidad de la operación.
    """
    permission_classes = [IsInventoryWriterOrAdmin]

    def post(self, request, *args, **kwargs):
        serializer = TransferenciaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        producto = validated_data['producto']
        cantidad_transferir = validated_data['cantidad']
        bodega_origen = validated_data['bodega_origen']
        bodega_destino = validated_data['bodega_destino']
        lote = validated_data.get('lote')
        documento_ref = validated_data.get('documento_ref')
        observaciones = validated_data.get('observaciones', '')

        # OWASP A01: origen operable por el usuario, destino de la misma sede.
        try:
            validar_traslado(request.user, bodega_origen, bodega_destino, 'bodega_destino_id')
            validar_visible(filtrar_lotes_por_sede(LoteProduccion.objects.all(), request.user), lote, 'lote_id')
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Bloquear y verificar stock en origen
                stock_origen = StockBodega.objects.select_for_update().get(
                    bodega=bodega_origen, producto=producto, lote=lote
                )

                if stock_origen.cantidad < cantidad_transferir:
                    return Response(
                        {"error": f"Stock insuficiente en la bodega de origen. Disponible: {stock_origen.cantidad}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # 2. Descontar de bodega origen
                stock_origen.cantidad -= cantidad_transferir
                stock_origen._justificacion_auditoria = f"Transferencia a {bodega_destino.nombre}"
                stock_origen.save()

                # 3. Incrementar en bodega destino
                stock_destino, _created = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodega_destino,
                    producto=producto,
                    lote=lote
                )
                stock_destino.cantidad += cantidad_transferir
                stock_destino._justificacion_auditoria = f"Transferencia desde {bodega_origen.nombre}"
                stock_destino.save()

                # 4. Registrar el movimiento de inventario
                MovimientoInventario.objects.create(
                    tipo_movimiento='TRANSFERENCIA',
                    producto=producto,
                    cantidad=cantidad_transferir,
                    bodega_origen=bodega_origen,
                    bodega_destino=bodega_destino,
                    lote=lote,
                    usuario=request.user,
                    documento_ref=documento_ref,
                    observaciones=observaciones
                )

        except StockBodega.DoesNotExist:
            return Response(
                {"error": "El producto o lote especificado no tiene stock en la bodega de origen."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            logger.exception("Error inesperado en transferencia de stock")
            return Response(
                {"error": "Ocurrió un error inesperado al transferir el stock."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"message": "Transferencia realizada con éxito."}, status=status.HTTP_200_OK)
