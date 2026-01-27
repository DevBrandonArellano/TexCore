from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction, models
from decimal import Decimal
from .models import StockBodega, MovimientoInventario
from gestion.models import Bodega, Producto, LoteProduccion

class TransformacionAPIView(APIView):
    """
    API para registrar la TRANSFORMACIÓN de un producto en otro (ej. Proceso productivo simple).
    Mueve stock de Origen (Producto A) a Destino (Producto B).
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Validar datos de entrada manualmente (o crear un serializer específico)
        bodega_origen_id = request.data.get('bodega_origen_id')
        bodega_destino_id = request.data.get('bodega_destino_id')
        producto_origen_id = request.data.get('producto_origen_id')
        producto_destino_id = request.data.get('producto_destino_id')
        lote_origen_id = request.data.get('lote_origen_id')
        nuevo_lote_codigo = request.data.get('nuevo_lote_codigo')
        cantidad = request.data.get('cantidad')

        if not all([bodega_origen_id, bodega_destino_id, producto_origen_id, producto_destino_id, cantidad]):
            return Response({"error": "Faltan campos obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cantidad = Decimal(str(cantidad))
            if cantidad <= 0:
                 return Response({"error": "La cantidad debe ser positiva."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # 1. Consumir Stock de Origen (Materia Prima / Producto Base)
                # -----------------------------------------------------------
                lote_origen = None
                if lote_origen_id:
                     lote_origen = LoteProduccion.objects.get(id=lote_origen_id)

                stock_origen = StockBodega.objects.select_for_update().get(
                    bodega_id=bodega_origen_id,
                    producto_id=producto_origen_id,
                    lote=lote_origen
                )

                if stock_origen.cantidad < cantidad:
                    return Response(
                         {"error": f"Stock insuficiente en origen. Disponible: {stock_origen.cantidad}"},
                         status=status.HTTP_400_BAD_REQUEST
                    )
                
                stock_origen.cantidad -= cantidad
                stock_origen.save()

                MovimientoInventario.objects.create(
                    tipo_movimiento='CONSUMO', # O un tipo nuevo 'TRANSFORMACION_SALIDA'
                    producto_id=producto_origen_id,
                    bodega_origen_id=bodega_origen_id,
                    bodega_destino_id=bodega_destino_id, # Referencia informativa
                    lote=lote_origen,
                    cantidad=cantidad,
                    usuario=request.user,
                    documento_ref=f"TRANSF->{producto_destino_id}"
                )

                # 2. Determinar Lote de Destino
                # -----------------------------
                lote_destino = lote_origen # Por defecto mantiene el lote
                if nuevo_lote_codigo:
                    # Crear nuevo lote o buscar existente
                    lote_destino, _ = LoteProduccion.objects.get_or_create(
                        codigo_lote=nuevo_lote_codigo,
                        defaults={
                            'peso_neto_producido': cantidad,
                            'operario': request.user,
                            'maquina': 'Transformacion',
                            'turno': 'N/A',
                            'hora_inicio': models.utils.timezone.now(),
                            'hora_final': models.utils.timezone.now(),
                        }
                    )

                # 3. Ingresar Stock de Destino (Producto Transformado)
                # ----------------------------------------------------
                stock_destino, _ = StockBodega.objects.select_for_update().get_or_create(
                    bodega_id=bodega_destino_id,
                    producto_id=producto_destino_id,
                    lote=lote_destino,
                    defaults={'cantidad': 0}
                )
                stock_destino.cantidad += cantidad
                stock_destino.save()

                MovimientoInventario.objects.create(
                    tipo_movimiento='PRODUCCION', # O un tipo nuevo 'TRANSFORMACION_ENTRADA'
                    producto_id=producto_destino_id,
                    bodega_origen_id=bodega_origen_id, # Referencia informativa
                    bodega_destino_id=bodega_destino_id, 
                    lote=lote_destino,
                    cantidad=cantidad,
                    usuario=request.user,
                    documento_ref=f"TRANSF<-{producto_origen_id}"
                )

        except StockBodega.DoesNotExist:
             return Response({"error": "No existe stock del producto origen en la bodega seleccionada."}, status=status.HTTP_404_NOT_FOUND)
        except LoteProduccion.DoesNotExist:
             return Response({"error": "El lote origen especificado no existe."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
             return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Transformación registrada correctamente."}, status=status.HTTP_201_CREATED)
