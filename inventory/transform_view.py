from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import StockBodega, MovimientoInventario
from gestion.models import LoteProduccion


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
        justificacion = request.data.get('_justificacion_auditoria')
        if isinstance(justificacion, str):
            justificacion = justificacion.strip()

        # Tratar 0 / "0" / vacío como "sin lote" (el front puede enviar SelectItem value="0").
        _lote_raw = lote_origen_id
        lote_origen_id = None
        if _lote_raw not in (None, '', '0', 0):
            try:
                lid = int(_lote_raw)
                if lid:
                    lote_origen_id = lid
            except (TypeError, ValueError):
                return Response({"error": "lote_origen_id inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if nuevo_lote_codigo is not None and isinstance(nuevo_lote_codigo, str):
            nuevo_lote_codigo = nuevo_lote_codigo.strip() or None

        if not all([bodega_origen_id, bodega_destino_id, producto_origen_id, producto_destino_id, cantidad]):
            return Response({"error": "Faltan campos obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        if not justificacion:
            return Response({"error": "Se requiere una justificación (_justificacion_auditoria)."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            cantidad = Decimal(str(cantidad))
            if cantidad <= 0:
                return Response({"error": "La cantidad debe ser positiva."}, status=status.HTTP_400_BAD_REQUEST)

            with transaction.atomic():
                # 1. Consumir Stock de Origen (Materia Prima / Producto Base)
                # -----------------------------------------------------------
                lote_origen = None
                stock_qs = StockBodega.objects.select_for_update().filter(
                    bodega_id=bodega_origen_id,
                    producto_id=producto_origen_id,
                )
                if lote_origen_id:
                    stock_qs = stock_qs.filter(lote_id=lote_origen_id)
                # Si llega "sin lote", o el lote elegido no tiene fila, tomamos uno con saldo.
                stock_origen = stock_qs.filter(cantidad__gt=0).order_by('-cantidad', 'id').first()
                if not stock_origen and lote_origen_id:
                    stock_origen = (
                        StockBodega.objects.select_for_update()
                        .filter(bodega_id=bodega_origen_id, producto_id=producto_origen_id, cantidad__gt=0)
                        .order_by('-cantidad', 'id')
                        .first()
                    )
                if stock_origen:
                    lote_origen = stock_origen.lote
                else:
                    raise StockBodega.DoesNotExist

                if stock_origen.cantidad < cantidad:
                    return Response(
                        {"error": f"Stock insuficiente en origen. Disponible: {stock_origen.cantidad}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                stock_origen.cantidad -= cantidad
                stock_origen._justificacion_auditoria = justificacion
                stock_origen.save()

                mov_consumo = MovimientoInventario(
                    tipo_movimiento='CONSUMO',  # O un tipo nuevo 'TRANSFORMACION_SALIDA'
                    producto_id=producto_origen_id,
                    bodega_origen_id=bodega_origen_id,
                    bodega_destino_id=bodega_destino_id,  # Referencia informativa
                    lote=lote_origen,
                    cantidad=cantidad,
                    usuario=request.user,
                    documento_ref=f"TRANSF->{producto_destino_id}",
                    saldo_resultante=stock_origen.cantidad,  # Guardamos el saldo POST-consumo
                )
                mov_consumo._justificacion_auditoria = justificacion
                mov_consumo.save()

                # 2. Determinar Lote de Destino
                # -----------------------------
                lote_destino = lote_origen  # Por defecto mantiene el lote
                if nuevo_lote_codigo:
                    # Crear nuevo lote o buscar existente
                    # maquina es ForeignKey(Maquina); no se puede asignar un string.
                    lote_destino, _ = LoteProduccion.objects.get_or_create(
                        codigo_lote=nuevo_lote_codigo,
                        defaults={
                            'peso_neto_producido': cantidad,
                            'operario': request.user,
                            'turno': 'N/A',
                            'hora_inicio': timezone.now(),
                            'hora_final': timezone.now(),
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
                stock_destino._justificacion_auditoria = justificacion
                stock_destino.save()

                mov_produccion = MovimientoInventario(
                    tipo_movimiento='PRODUCCION',  # O un tipo nuevo 'TRANSFORMACION_ENTRADA'
                    producto_id=producto_destino_id,
                    bodega_origen_id=bodega_origen_id,  # Referencia informativa
                    bodega_destino_id=bodega_destino_id,
                    lote=lote_destino,
                    cantidad=cantidad,
                    usuario=request.user,
                    documento_ref=f"TRANSF<-{producto_origen_id}",
                    saldo_resultante=stock_destino.cantidad,  # Guardamos el saldo POST-producción
                )
                mov_produccion._justificacion_auditoria = justificacion
                mov_produccion.save()

                # 4. Trazabilidad MES (Nivel 3) y Grafo DAG GenealogiaLote
                # --------------------------------------------------------
                try:
                    from gestion.models import (
                        Area,
                        CorridaProduccion,
                        OperacionProduccion,
                        ConsumoMaterial,
                        ProduccionSalida,
                        GenealogiaLote,
                    )
                    bodega_orig = StockBodega.objects.select_related('bodega__sede').get(id=stock_origen.id).bodega
                    sede = bodega_orig.sede
                    area = sede.areas.first() if sede else None
                    if not area and sede:
                        area, _ = Area.objects.get_or_create(sede=sede, defaults={'nombre': 'Área General'})

                    if sede and area:
                        corrida, _ = CorridaProduccion.objects.get_or_create(
                            codigo=f"CORR-TRANSF-{sede.id}-{timezone.now().date().strftime('%Y%m%d')}",
                            defaults={
                                'sede': sede,
                                'area': area,
                                'modalidad': 'CONTINUA',
                                'turno': 'General',
                                'fecha_jornada': timezone.now().date(),
                                'hora_inicio': timezone.now(),
                                'supervisor': request.user if request.user.is_authenticated else None,
                                'estado': 'en_proceso',
                            }
                        )
                        operacion = OperacionProduccion.objects.create(
                            corrida=corrida,
                            numero_secuencia=corrida.operaciones.count() + 1,
                            operario=request.user if request.user.is_authenticated else None,
                            hora_inicio=timezone.now(),
                            hora_fin=timezone.now(),
                            estado='completada',
                            observaciones=justificacion or f"Transformación {producto_origen_id} -> {producto_destino_id}",
                        )
                        ConsumoMaterial.objects.create(
                            operacion=operacion,
                            lote_origen=lote_origen,
                            producto_id=producto_origen_id,
                            bodega_origen_id=bodega_origen_id,
                            cantidad_consumida=cantidad,
                        )
                        ProduccionSalida.objects.create(
                            operacion=operacion,
                            lote_generado=lote_destino,
                            producto_id=producto_destino_id,
                            bodega_destino_id=bodega_destino_id,
                            cantidad_neta=cantidad,
                            clasificacion_calidad='primera',
                        )
                        if lote_origen and lote_destino and lote_origen.id != lote_destino.id:
                            GenealogiaLote.objects.get_or_create(
                                lote_padre=lote_origen,
                                lote_hijo=lote_destino,
                                operacion=operacion,
                                defaults={'cantidad_padre_usada': cantidad},
                            )
                except Exception as err:
                    import logging
                    logging.getLogger('inventory.transform').warning(f"Trazabilidad MES en transformación: {err}")

        except StockBodega.DoesNotExist:
            # 400: regla de negocio (no hay fila de stock), no confundir con 404 de ruta
            return Response(
                {
                    "error": (
                        "No hay stock registrado para ese producto en la bodega de origen "
                        "con el lote indicado (incluido «sin lote»). Cree o ajuste el stock antes."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": "Transformación registrada correctamente."}, status=status.HTTP_201_CREATED)
