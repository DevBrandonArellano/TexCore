import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions, serializers
from rest_framework.decorators import action

from gestion.utils import PrintingService
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
                # DetalleHistorialDespachoPedido.historial es PROTECT — sin
                # borrar estas filas primero, historial.delete() siempre
                # falla con ProtectedError (500) para cualquier despacho real
                # (todos tienen al menos un pedido vinculado).
                historial.detallehistorialdespachopedido_set.all().delete()
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
                # Ver comentario equivalente en destroy(): PROTECT en
                # DetalleHistorialDespachoPedido.historial impide borrar el
                # historial sin limpiar antes estas filas.
                historial.detallehistorialdespachopedido_set.all().delete()
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

    @action(detail=False, methods=['get'])
    def imprimir(self, request):
        """
        GET /inventory/historial-despachos/imprimir/?fecha_desde=&fecha_hasta=
        PDF del historial de despachos — usa los mismos filtros de fecha que
        list() (get_queryset ya los aplica leyendo request.query_params).
        """
        queryset = self.get_queryset()

        despachos = []
        for h in queryset:
            pedidos_str = ", ".join(
                f"{p.cliente.nombre_razon_social if p.cliente else 'N/A'} ({p.guia_remision})"
                for p in h.pedidos.all()
            ) or "—"
            despachos.append({
                "id": h.id,
                "fecha_despacho": h.fecha_despacho.strftime("%d/%m/%Y %H:%M"),
                "usuario_nombre": (h.usuario.get_full_name() or h.usuario.username) if h.usuario else None,
                "pedidos": pedidos_str,
                "total_bultos": h.total_bultos,
                "total_peso": float(h.total_peso),
            })

        sede_usuario = getattr(request.user, 'sede', None)
        data = {
            "empresa_nombre": sede_usuario.nombre if sede_usuario else "TexCore",
            "sede_nombre": sede_usuario.nombre if sede_usuario else "Todas las sedes",
            "fecha_desde": request.query_params.get('fecha_desde'),
            "fecha_hasta": request.query_params.get('fecha_hasta'),
            "generado_en": timezone.now().isoformat(),
            "despachos": despachos,
        }

        pdf_content = PrintingService.generate_historial_despachos_pdf(data)
        if not pdf_content:
            return Response({"error": "El servicio de impresión no está disponible temporalmente."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="historial_despachos.pdf"'
        return response

    @action(detail=True, methods=['post'], url_path='guia-remision')
    def guia_remision(self, request, pk=None):
        """
        POST /inventory/historial-despachos/{id}/guia-remision/
        Genera la Guía de Remisión (PDF informativo, NO autorizado por el
        SRI) de un despacho específico. Body: datos de transporte que el
        sistema no captura al momento de despachar (motivo_traslado,
        punto_partida, fechas de transporte, transportista/placa).
        """
        historial = self.get_object()

        motivo_traslado = (request.data.get('motivo_traslado') or '').strip()
        punto_partida = (request.data.get('punto_partida') or '').strip()
        fecha_inicio_transporte = (request.data.get('fecha_inicio_transporte') or '').strip()
        fecha_fin_transporte = (request.data.get('fecha_fin_transporte') or '').strip()
        transporte_propio = bool(request.data.get('transporte_propio', True))
        transportista_nombre = (request.data.get('transportista_nombre') or '').strip() or None
        transportista_ruc = (request.data.get('transportista_ruc') or '').strip() or None
        placa_vehiculo = (request.data.get('placa_vehiculo') or '').strip() or None

        errores = {}
        if not motivo_traslado:
            errores['motivo_traslado'] = 'Requerido.'
        if not punto_partida:
            errores['punto_partida'] = 'Requerido.'
        if not fecha_inicio_transporte:
            errores['fecha_inicio_transporte'] = 'Requerido.'
        if not fecha_fin_transporte:
            errores['fecha_fin_transporte'] = 'Requerido.'
        if not transporte_propio and not transportista_nombre:
            errores['transportista_nombre'] = 'Requerido cuando el transporte no es propio.'
        if errores:
            return Response(errores, status=status.HTTP_400_BAD_REQUEST)

        destinatarios = [
            {
                "identificacion": p.cliente.ruc_cedula if p.cliente else None,
                "razon_social": p.cliente.nombre_razon_social if p.cliente else 'Consumidor Final',
                "direccion": p.cliente.direccion_envio if p.cliente else None,
                "documento_sustento": p.guia_remision,
            }
            for p in historial.pedidos.select_related('cliente').all()
        ] or [{"razon_social": "N/A"}]

        detalles_por_producto = {}
        for d in historial.detalles.filter(es_devolucion=False).select_related('producto'):
            if not d.producto:
                continue
            info = detalles_por_producto.setdefault(d.producto.id, {
                "codigo": d.producto.codigo,
                "descripcion": d.producto.descripcion,
                "cantidad": 0.0,
                "unidad": d.producto.unidad_medida or "kg",
            })
            info["cantidad"] += float(d.peso)

        sede_usuario = getattr(request.user, 'sede', None)
        data = {
            "numero": f"001-001-{historial.id:09d}",
            "fecha_emision": timezone.now().strftime("%d/%m/%Y"),
            "empresa_nombre": sede_usuario.nombre if sede_usuario else "TexCore",
            "empresa_ruc": settings.EMPRESA_RUC or None,
            "punto_partida": punto_partida,
            "motivo_traslado": motivo_traslado,
            "fecha_inicio_transporte": fecha_inicio_transporte,
            "fecha_fin_transporte": fecha_fin_transporte,
            "transporte_propio": transporte_propio,
            "transportista_nombre": transportista_nombre,
            "transportista_ruc": transportista_ruc,
            "placa_vehiculo": placa_vehiculo,
            "destinatarios": destinatarios,
            "detalles": list(detalles_por_producto.values()),
        }

        pdf_content = PrintingService.generate_guia_remision_pdf(data)
        if not pdf_content:
            return Response({"error": "El servicio de impresión no está disponible temporalmente."},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="guia_remision_{historial.id}.pdf"'
        return response


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
    muestre un modal de confirmación. El cliente reenvía con
    `confirmar_incompleto: true` para forzar el despacho parcial.

    F5 (despacho parcial robusto): un despacho parcial ya NO marca el pedido
    como 'despachado' completo — queda en 'despachado_parcial' (ver
    DespachoEstadoService) y sigue apareciendo en la cola de despacho para
    completarlo después. Lo ya despachado en intentos previos (no revertidos)
    se resta al calcular qué falta, para no volver a pedir el 100% original.
    """
    permission_classes = [IsDespachoWriter]

    @staticmethod
    def _calcular_incompletos(pedidos_ids: list, lotes_codes: list) -> dict:
        """
        Compara lo que AÚN falta de los pedidos (requerido menos lo ya
        despachado en intentos previos no revertidos) contra el stock de los
        lotes escaneados en este intento. No lanza excepciones — los errores
        de lote inválido se capturan en la transacción. Retorna {} si todo lo
        pendiente queda cubierto.
        """
        from inventory.services.despacho_estado import DespachoEstadoService

        reqs: dict = {}

        for p_id in pedidos_ids:
            try:
                pedido = PedidoVenta.objects.get(id=p_id)
            except PedidoVenta.DoesNotExist:
                continue
            ya_despachado = DespachoEstadoService.peso_despachado_por_producto(pedido)
            for det in pedido.detalles.select_related('producto'):
                pid = det.producto_id
                if pid not in reqs:
                    reqs[pid] = {
                        'nombre': det.producto.descripcion,
                        'requerido': Decimal('0'),
                        'escaneado': Decimal('0'),
                    }
                pendiente = det.peso - ya_despachado.get(pid, Decimal('0'))
                reqs[pid]['requerido'] += max(pendiente, Decimal('0'))

        lotes = LoteProduccion.objects.select_related(
            'orden_produccion__producto_salida',
            'orden_produccion__producto_entrada',
        ).filter(codigo_lote__in=lotes_codes)
        stocks_por_lote = {
            s.lote_id: s
            for s in StockBodega.objects.filter(lote__in=lotes, cantidad__gt=0)
        }
        for lote in lotes:
            stock = stocks_por_lote.get(lote.id)
            if stock and lote.orden_produccion:
                op = lote.orden_produccion
                producto = op.producto_salida or op.producto_entrada
                if producto and producto.id in reqs:
                    reqs[producto.id]['escaneado'] += stock.cantidad

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
        from inventory.services.despacho_estado import DespachoEstadoService

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

                pedidos_obj = {
                    p.id: p for p in PedidoVenta.objects.filter(id__in=pedidos_ids).prefetch_related('detalles')
                }

                # Necesidad restante por (pedido_id, producto_id): requerido de
                # los detalles del pedido, menos lo ya despachado en intentos
                # previos NO revertidos. Se usa para asignar cada lote escaneado
                # al pedido correcto cuando un despacho cubre varios pedidos.
                pendiente_por_pedido_producto: dict = {}
                for p_id, pedido in pedidos_obj.items():
                    ya_despachado = DespachoEstadoService.peso_despachado_por_producto(pedido)
                    requerido = DespachoEstadoService.requerido_por_producto(pedido)
                    for producto_id, cantidad_requerida in requerido.items():
                        clave = (p_id, producto_id)
                        restante = cantidad_requerida - ya_despachado.get(producto_id, Decimal('0'))
                        pendiente_por_pedido_producto[clave] = max(restante, Decimal('0'))

                total_peso_despachado = Decimal('0.00')
                total_peso_por_pedido: dict = {p_id: Decimal('0.00') for p_id in pedidos_ids}
                processed_lotes = []

                for code in lotes_codes:
                    try:
                        lote = LoteProduccion.objects.select_related(
                            'orden_produccion__producto_salida',
                            'orden_produccion__producto_entrada',
                        ).get(codigo_lote=code)
                        stock = StockBodega.objects.select_for_update().filter(lote=lote, cantidad__gt=0).first()

                        if not stock:
                            raise serializers.ValidationError(f"El lote {code} ya no tiene stock disponible.")

                        op = lote.orden_produccion
                        producto = (op.producto_salida or op.producto_entrada) if op else None
                        if not producto:
                            raise serializers.ValidationError(f"El lote {code} no tiene un producto asociado.")

                        cantidad_a_despachar = stock.cantidad
                        total_peso_despachado += cantidad_a_despachar

                        # Asignar este lote al primer pedido (en el orden recibido)
                        # que todavía necesite este producto. Un lote es atómico
                        # (no se reparte entre pedidos): si sobra, igual se
                        # atribuye a ese pedido para no perder trazabilidad de a
                        # quién se entregó.
                        pedido_asignado = None
                        for p_id in pedidos_ids:
                            clave = (p_id, producto.id)
                            if pendiente_por_pedido_producto.get(clave, Decimal('0')) > 0:
                                pedido_asignado = pedidos_obj.get(p_id)
                                pendiente_por_pedido_producto[clave] -= cantidad_a_despachar
                                break
                        if pedido_asignado is None:
                            # Ningún pedido seleccionado necesita ya este producto
                            # (excedente escaneado) — se atribuye igual al primer
                            # pedido que lo pidió, en vez de dejarlo huérfano.
                            for p_id in pedidos_ids:
                                if (p_id, producto.id) in pendiente_por_pedido_producto:
                                    pedido_asignado = pedidos_obj.get(p_id)
                                    break

                        if pedido_asignado is not None:
                            total_peso_por_pedido[pedido_asignado.id] += cantidad_a_despachar

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
                            pedido=pedido_asignado,
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

                for p_id in pedidos_ids:
                    DetalleHistorialDespachoPedido.objects.create(
                        historial=historial,
                        pedido_id=p_id,
                        cantidad_despachada=total_peso_por_pedido.get(p_id, Decimal('0.00')),
                    )

                pedidos_actualizados = 0
                for pedido in pedidos_obj.values():
                    nuevo_estado = DespachoEstadoService.recalcular_estado(pedido)
                    if nuevo_estado != pedido.estado:
                        pedido.estado = nuevo_estado
                        if nuevo_estado in ('despachado', 'despachado_parcial'):
                            pedido.fecha_despacho = timezone.now().date()
                        pedido.save()
                        pedidos_actualizados += 1

                logger.info(
                    "Despacho procesado exitosamente",
                    extra={"sd": {"entity": "HistorialDespacho", "id": historial.id, "user": request.user.username}},
                )
                return Response({
                    'message': 'Despacho procesado correctamente',
                    'despacho_id': historial.id,
                    'pedidos_actualizados': pedidos_actualizados,
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
