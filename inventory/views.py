from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from .serializers import TransferenciaSerializer, KardexSerializer, MovimientoInventarioSerializer, StockBodegaSerializer
from .models import StockBodega, MovimientoInventario
from gestion.models import Bodega, Producto

class StockBodegaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para ver el stock actual en todas las bodegas.
    """
    queryset = StockBodega.objects.select_related('bodega', 'producto', 'lote').all()
    serializer_class = StockBodegaSerializer
    permission_classes = [permissions.IsAuthenticated]

from decimal import Decimal

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    """
    API para ver y registrar movimientos de inventario genéricos como Compras o Ajustes.
    Actualiza el stock de manera atómica.
    """
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.groups.filter(name__in=['admin_sistemas', 'admin_sede']).exists():
            return MovimientoInventario.objects.all()
        return MovimientoInventario.objects.filter(usuario=user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tipo_movimiento = serializer.validated_data.get('tipo_movimiento')
        producto = serializer.validated_data.get('producto')
        cantidad = serializer.validated_data.get('cantidad')
        bodega_origen = serializer.validated_data.get('bodega_origen')
        bodega_destino = serializer.validated_data.get('bodega_destino')
        lote = serializer.validated_data.get('lote')

        try:
            with transaction.atomic():
                # Primero, crea el registro del movimiento
                movimiento = serializer.save(usuario=request.user)

                # Segundo, actualiza el stock en la bodega
                if tipo_movimiento in ['COMPRA', 'PRODUCCION', 'AJUSTE_POSITIVO', 'DEVOLUCION']:
                    if not bodega_destino:
                        raise serializers.ValidationError({"bodega_destino": "Bodega de destino es requerida para este tipo de movimiento."})
                    
                    stock, created = StockBodega.objects.get_or_create(
                        bodega=bodega_destino,
                        producto=producto,
                        lote=lote,
                        defaults={'cantidad': 0}
                    )
                    stock.cantidad += cantidad
                    stock.save()

                elif tipo_movimiento in ['VENTA', 'CONSUMO', 'AJUSTE_NEGATIVO']:
                    if not bodega_origen:
                        raise serializers.ValidationError({"bodega_origen": "Bodega de origen es requerida para este tipo de movimiento."})
                    
                    stock = StockBodega.objects.get(bodega=bodega_origen, producto=producto, lote=lote)
                    if stock.cantidad < cantidad:
                        raise serializers.ValidationError(f"Stock insuficiente. Disponible: {stock.cantidad}, Requerido: {cantidad}")
                    
                    stock.cantidad -= cantidad
                    stock.save()

                else:
                    # No se hace nada para otros tipos como TRANSFERENCIA, ya que se manejan en su propia API
                    pass
                
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except StockBodega.DoesNotExist:
            return Response({"error": "No existe stock para el producto/lote en la bodega especificada."}, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Ocurrió un error inesperado: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        # Este método es ahora manejado por el 'create' sobreescrito.
        # Se deja vacío para evitar la doble creación.
        pass

class TransferenciaStockAPIView(APIView):
    """
    API para realizar transferencias de stock entre dos bodegas.
    Garantiza la atomicidad de la operación.
    """
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
                stock_origen.save()

                # 3. Incrementar en bodega destino
                stock_destino, created = StockBodega.objects.select_for_update().get_or_create(
                    bodega=bodega_destino, producto=producto, lote=lote,
                    defaults={'cantidad': 0}
                )
                stock_destino.cantidad += cantidad_transferir
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
                )

        except StockBodega.DoesNotExist:
            return Response(
                {"error": "El producto o lote especificado no tiene stock en la bodega de origen."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            # Log the exception e
            return Response(
                {"error": f"Ocurrió un error inesperado: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({"message": "Transferencia realizada con éxito."}, status=status.HTTP_200_OK)


class KardexBodegaAPIView(APIView):
    """
    API para obtener el historial de movimientos (Kardex) de un producto
    en una bodega específica.
    """
    def get(self, request, bodega_id, *args, **kwargs):
        producto_id = request.query_params.get('producto_id')
        if not producto_id:
            return Response(
                {"error": "El parámetro 'producto_id' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        get_object_or_404(Bodega, pk=bodega_id)
        get_object_or_404(Producto, pk=producto_id)

        movimientos = MovimientoInventario.objects.filter(
            models.Q(bodega_origen_id=bodega_id) | models.Q(bodega_destino_id=bodega_id),
            producto_id=producto_id
        ).order_by('fecha')

        # Calcular saldo
        saldo = 0
        kardex_data = []
        for m in movimientos:
            if m.bodega_destino_id == bodega_id:
                saldo += m.cantidad
                entrada = m.cantidad
                salida = ""
            else: # Salida
                saldo -= m.cantidad
                entrada = ""
                salida = m.cantidad
            
            kardex_data.append({
                "fecha": m.fecha,
                "tipo_movimiento": m.get_tipo_movimiento_display(),
                "documento_ref": m.documento_ref,
                "entrada": entrada,
                "salida": salida,
                "saldo_resultante": saldo
            })
        
        return Response(kardex_data, status=status.HTTP_200_OK)

class AlertasStockAPIView(APIView):
    """
    API para listar todos los productos cuyo stock en alguna bodega
    está por debajo del mínimo definido.
    """
    def get(self, request, *args, **kwargs):
        alertas = StockBodega.objects.filter(
            cantidad__lt=models.F('producto__stock_minimo')
        ).select_related('producto', 'bodega').order_by('bodega__nombre', 'producto__descripcion')

        resultado = [
            {
                "bodega": item.bodega.nombre,
                "producto": item.producto.descripcion,
                "codigo_producto": item.producto.codigo,
                "stock_actual": item.cantidad,
                "stock_minimo": item.producto.stock_minimo,
                "faltante": item.producto.stock_minimo - item.cantidad
            }
            for item in alertas if item.producto.stock_minimo > 0
        ]
        return Response(resultado, status=status.HTTP_200_OK)