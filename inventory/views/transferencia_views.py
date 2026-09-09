import logging

from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from inventory.serializers import TransferenciaSerializer
from inventory.models import StockBodega, MovimientoInventario
from inventory.permissions import IsInventoryWriterOrAdmin
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
                stock_destino, created = safe_get_or_create_stock(
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
        except Exception as e:
            logger.error("Error inesperado en transferencia de stock", exc_info=True)
            return Response(
                {"error": f"Ocurrió un error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"message": "Transferencia realizada con éxito."}, status=status.HTTP_200_OK)
