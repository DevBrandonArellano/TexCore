from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from .serializers import TransferenciaSerializer, KardexSerializer, MovimientoInventarioSerializer
from .models import StockBodega, MovimientoInventario
from gestion.models import Bodega, Producto

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    """
    API para ver y registrar movimientos de inventario.
    - Los usuarios normales solo pueden ver sus propios movimientos.
    - Los administradores pueden ver todos los movimientos.
    - Al crear un movimiento, el usuario se asigna automáticamente.
    """
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Asumiendo que 'admin_sistemas' y 'admin_sede' son los roles con permisos de supervisor
        if user.is_staff or user.groups.filter(name__in=['admin_sistemas', 'admin_sede']).exists():
            return MovimientoInventario.objects.all()
        return MovimientoInventario.objects.filter(usuario=user)

    def perform_create(self, serializer):
        # Asigna el usuario actual automáticamente al crear un movimiento.
        serializer.save(usuario=self.request.user)

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