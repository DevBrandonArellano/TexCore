from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, serializers
from rest_framework.decorators import action

from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import (
    TransferenciaSerializer, KardexSerializer, 
    MovimientoInventarioSerializer, StockBodegaSerializer,
    AuditoriaMovimientoSerializer, MovimientoInventarioUpdateSerializer
)
from .models import StockBodega, MovimientoInventario, AuditoriaMovimiento
from gestion.models import Bodega, Producto, LoteProduccion
import logging


class StockBodegaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para ver el stock actual en todas las bodegas.
    """
    serializer_class = StockBodegaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = StockBodega.objects.select_related('bodega', 'producto', 'lote').all()
        
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede']).exists():
            return queryset
            
        # Filter stock only for assigned warehouses
        assigned_bodegas = user.bodegas_asignadas.values_list('id', flat=True)
        return queryset.filter(bodega_id__in=assigned_bodegas)

from decimal import Decimal

import logging

# ... (el resto de las importaciones)

# ... (el resto del código de vistas)

class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()
    serializer_class = MovimientoInventarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            # Loguear el error de validación detallado
            logging.error(f'ValidationError en MovimientoInventarioViewSet: {e.detail}')
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        tipo_movimiento = serializer.validated_data.get('tipo_movimiento')
        producto = serializer.validated_data.get('producto')
        cantidad = serializer.validated_data.get('cantidad')
        bodega_origen = serializer.validated_data.get('bodega_origen')
        bodega_destino = serializer.validated_data.get('bodega_destino')
        lote = serializer.validated_data.get('lote')
        lote_codigo = request.data.get('lote_codigo') # Get manual batch code from request

        try:
            with transaction.atomic():
                # Handle Manual Batch Creation/Lookup if provided
                if not lote and lote_codigo:
                    # Lote without production order (Raw Material, etc)
                    lote, created = LoteProduccion.objects.get_or_create(
                        codigo_lote=lote_codigo,
                        defaults={
                            'peso_neto_producido': cantidad, # Initial quantity
                            'operario': request.user,
                            'maquina': 'Manual Entry',
                            'turno': 'N/A',
                            'hora_inicio': timezone.now(),
                            'hora_final': timezone.now(),
                        }
                    )

                saldo_resultante = Decimal('0.00')

                # Logica para entradas
                if tipo_movimiento in ['COMPRA', 'PRODUCCION', 'AJUSTE_POSITIVO', 'DEVOLUCION']:
                    if not bodega_destino:
                        raise serializers.ValidationError({"bodega_destino": "Bodega de destino es requerida para este tipo de movimiento."})
                    
                    stock, created = StockBodega.objects.select_for_update().get_or_create(
                        bodega=bodega_destino,
                        producto=producto,
                        lote=lote,
                        defaults={'cantidad': 0}
                    )
                    stock.cantidad += Decimal(str(cantidad))
                    stock.save()
                    saldo_resultante = stock.cantidad

                # Logica para salidas
                elif tipo_movimiento in ['VENTA', 'CONSUMO', 'AJUSTE_NEGATIVO']:
                    if not bodega_origen:
                        raise serializers.ValidationError({"bodega_origen": "Bodega de origen es requerida para este tipo de movimiento."})
                    
                    try:
                        stock = StockBodega.objects.select_for_update().get(bodega=bodega_origen, producto=producto, lote=lote)
                    except StockBodega.DoesNotExist:
                         raise serializers.ValidationError(f"No existe stock para el producto {producto.codigo} en la bodega seleccionada.")

                    if stock.cantidad < cantidad:
                        raise serializers.ValidationError(f"Stock insuficiente. Disponible: {stock.cantidad}, Requerido: {cantidad}")
                    
                    stock.cantidad -= Decimal(str(cantidad))
                    stock.save()
                    saldo_resultante = stock.cantidad

                else:
                    # Casos especiales como TRANSFERENCIA se manejan aparte o no aplican saldo directo aqui
                    pass
                
                # Finalmente crea el registro del movimiento con el saldo calculado
                movimiento = serializer.save(usuario=request.user, lote=lote, saldo_resultante=saldo_resultante)
                
                headers = self.get_success_headers(serializer.data)
                return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except StockBodega.DoesNotExist:
             return Response({"error": "No existe stock para el producto/lote en la bodega especificada."}, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as e:
            logging.error(f'ValidationError en la lógica de negocio de MovimientoInventario: {repr(e)}')
            return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.exception(f'Error inesperado en MovimientoInventarioViewSet: {repr(e)}')
            return Response({"error": f"Error inesperado: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



    def perform_create(self, serializer):
        pass

    def update(self, request, *args, **kwargs):
        """
        Permite editar un movimiento de inventario existente.
        Solo se permiten editar movimientos de tipo COMPRA (entradas).
        Se registra auditoría y se recalcula el stock.
        """
        instance = self.get_object()
        user = request.user
        
        # 1. Validar permisos
        allowed_groups = ['bodeguero', 'jefe_area', 'jefe_planta', 'admin_sede', 'admin_sistemas']
        if not (user.is_superuser or user.groups.filter(name__in=allowed_groups).exists()):
             return Response(
                {"error": "No tienes permisos para editar movimientos"},
                status=status.HTTP_403_FORBIDDEN
            )

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
                            f"No se puede reducir la entrada en {abs(diferencia)} unidades porque el stock actual ({stock.cantidad}) es insuficiente (ya se consumió)."
                        )
                    
                    # Actualizar stock
                    stock.cantidad += diferencia
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
                    instance.save()
                    
                    return Response({
                        "message": "Movimiento actualizado con éxito",
                        "cambios": cambios_realizados
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "No se detectaron cambios"}, status=status.HTTP_200_OK)

        except StockBodega.DoesNotExist:
            return Response({"error": "No se encuentra el registro de stock asociado para recalcular."}, status=status.HTTP_404_NOT_FOUND)
        except serializers.ValidationError as e:
             return Response({"error": e.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logging.exception(f"Error al editar movimiento {instance.id}: {str(e)}")
            return Response({"error": "Ocurrió un error inesperado al actualizar."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def auditoria(self, request, pk=None):
        """
        Retorna el historial de cambios de un movimiento específico.
        """
        movimiento = self.get_object()
        auditorias = movimiento.auditorias.all()
        serializer = AuditoriaMovimientoSerializer(auditorias, many=True)
        return Response(serializer.data)

# ... (resto del archivo)


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

        movimientos = MovimientoInventario.objects.select_related(
            'bodega_origen', 'bodega_destino'
        ).filter(
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
                "id": m.id,
                "fecha": m.fecha,
                "tipo_movimiento": m.get_tipo_movimiento_display(),
                "documento_ref": m.documento_ref,
                "entrada": entrada,
                "salida": salida,
                "saldo_resultante": saldo,
                "editado": m.editado
            })
        
        return Response(kardex_data, status=status.HTTP_200_OK)


class AlertasStockAPIView(APIView):
    """
    API para listar todos los productos cuyo stock en alguna bodega
    está por debajo del mínimo definido.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = StockBodega.objects.filter(
            cantidad__lt=models.F('producto__stock_minimo')
        ).select_related('producto', 'bodega').order_by('bodega__nombre', 'producto__descripcion')

        if not (user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede']).exists()):
            assigned_bodegas = user.bodegas_asignadas.values_list('id', flat=True)
            queryset = queryset.filter(bodega_id__in=assigned_bodegas)

        alertas = queryset

        resultado = [
            {
                "bodega": item.bodega.nombre,
                "producto": item.producto.descripcion,
                "producto_codigo": item.producto.codigo,
                "stock_actual": item.cantidad,
                "stock_minimo": item.producto.stock_minimo,
                "faltante": item.producto.stock_minimo - item.cantidad
            }
            for item in alertas if item.producto.stock_minimo > 0
        ]
        return Response(resultado, status=status.HTTP_200_OK)