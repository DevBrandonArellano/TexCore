import logging
from decimal import Decimal

from django.conf import settings
from django.db import DatabaseError, transaction
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import LoteProduccion, PedidoVenta, Producto
from gestion.permissions import filtrar_por_sede
from gestion.utils import PrintingService
from inventory.models import (
    DetalleHistorialDespacho,
    DetalleHistorialDespachoPedido,
    HistorialDespacho,
    MovimientoInventario,
    StockBodega,
)
from inventory.permissions import IsDespachoReader, IsDespachoWriter, bodegas_visibles
from inventory.serializers import HistorialDespachoSerializer
from inventory.utils import INTENTOS_DEADLOCK, es_deadlock, principal_primero, stock_vendible_del_lote

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

        # OWASP A01: la sede de un despacho es la de sus pedidos (process-despacho solo
        # acepta pedidos de la sede del usuario). Sin esto se listaban, revertían y
        # borraban despachos de otras sedes.
        queryset = filtrar_por_sede(queryset, self.request.user, campo='pedidos__sede').distinct()

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
        historial = self.get_object()
        justificacion = request.data.get('justificacion', '').strip() if request.data else ''

        if not justificacion:
            return Response(
                {'justificacion': 'Justificación obligatoria para revertir despacho'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            self._revertir_y_borrar(historial, request.user, justificacion)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Error revirtiendo despacho %s", historial.id)
            return Response(
                {'error': 'Error interno al revertir el despacho.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @staticmethod
    def _revertir_y_borrar(historial, usuario, justificacion):
        """Revierte el stock y borra el historial en una transacción; la reejecuta
        si SQL Server la elige víctima de deadlock."""
        from inventory.services.despacho_reversion import DespachoReversionService

        for intento in range(1, INTENTOS_DEADLOCK + 1):
            try:
                with transaction.atomic():
                    resultado = DespachoReversionService.revertir_despacho(historial, usuario, justificacion)
                    # DetalleHistorialDespachoPedido.historial es PROTECT: sin borrar
                    # antes estas filas, historial.delete() falla con ProtectedError.
                    historial.detallehistorialdespachopedido_set.all().delete()
                    historial.delete()
                return resultado
            except DatabaseError as e:
                if intento == INTENTOS_DEADLOCK or not es_deadlock(e):
                    raise
                logger.warning("Reversión de despacho elegida víctima de deadlock; reintento %s", intento)
        # Inalcanzable: el último intento relanza; el raise documenta que nunca se devuelve None.
        raise RuntimeError("Reintentos por deadlock agotados sin resultado")

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
            resultado = self._revertir_y_borrar(historial, request.user, justificacion)
            return Response({
                'message': 'Despacho revertido exitosamente',
                'resultado': resultado
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Error revirtiendo despacho %s", historial.id)
            return Response(
                {'error': 'Error interno al revertir el despacho.'},
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

        # Filas vendibles del lote (todas salvo la merma), con la de su producto primero.
        stocks = stock_vendible_del_lote(StockBodega.objects.filter(cantidad__gt=0), [lote])
        visibles = bodegas_visibles(request.user)
        if visibles is not None:
            stocks = stocks.filter(bodega_id__in=visibles.values('id'))
        filas = principal_primero(stocks.select_related('bodega', 'producto'), lote)

        if not filas:
            return Response({'valid': False, 'reason': 'Lote existe pero no tiene stock disponible (0 kg)'}, status=200)
        stock_item = filas[0]

        pedido_id = request.data.get('pedido_id') or request.query_params.get('pedido_id')
        if pedido_id and lote.pedido_venta_reserva_id and lote.pedido_venta_reserva_id != int(pedido_id):
            return Response({
                'valid': False,
                'reason': f"El lote {lote.codigo_lote} está reservado para el Pedido #{lote.pedido_venta_reserva_id}."
            }, status=200)

        # producto/peso/bodega: los de la fila principal (contrato del escáner); un lote con
        # productos agregados a mano los informa todos en 'productos' y 'peso_total'.
        return Response({
            'valid': True,
            'lote': {
                'codigo': lote.codigo_lote,
                'producto_id': stock_item.producto_id,
                'producto_nombre': stock_item.producto.descripcion,
                'peso': str(stock_item.cantidad),
                'peso_total': str(sum(fila.cantidad for fila in filas)),
                'bodega_id': stock_item.bodega_id,
                'bodega_nombre': stock_item.bodega.nombre,
                'reservado_para_pedido': lote.pedido_venta_reserva_id,
                'stock_disponible': str(stock_item.stock_disponible),
                'stock_comprometido': str(stock_item.stock_comprometido),
                'productos': [
                    {
                        'producto_id': fila.producto_id,
                        'producto_nombre': fila.producto.descripcion,
                        'peso': str(fila.cantidad),
                        'bodega_id': fila.bodega_id,
                        'bodega_nombre': fila.bodega.nombre,
                    }
                    for fila in filas
                ],
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
                        'nombre': det.producto.descripcion if det.producto else 'Sin producto',
                        'requerido': Decimal('0'),
                        'escaneado': Decimal('0'),
                    }
                pendiente = det.peso - ya_despachado.get(pid, Decimal('0'))
                reqs[pid]['requerido'] += max(pendiente, Decimal('0'))

        # Cada fila vendible de los lotes cubre lo pedido de SU producto (un lote puede
        # traer productos agregados a mano además del de su OP).
        lotes = LoteProduccion.objects.filter(codigo_lote__in=lotes_codes)
        for stock in stock_vendible_del_lote(StockBodega.objects.filter(cantidad__gt=0), lotes):
            if stock.producto_id in reqs:
                reqs[stock.producto_id]['escaneado'] += stock.cantidad

        return {
            info['nombre']: {
                'requerido': float(info['requerido']),
                'escaneado': float(info['escaneado']),
                'faltante': float(info['requerido'] - info['escaneado']),
            }
            for info in reqs.values()
            if info['escaneado'] < info['requerido']
        }

    @staticmethod
    def _pendiente_por_pedido_producto(pedidos_obj):
        """Necesidad restante por (pedido_id, producto_id): requerido de los detalles del
        pedido, menos lo ya despachado en intentos previos NO revertidos. Se usa para asignar
        cada lote escaneado al pedido correcto cuando un despacho cubre varios pedidos."""
        from inventory.services.despacho_estado import DespachoEstadoService

        pendiente = {}
        for p_id, pedido in pedidos_obj.items():
            ya_despachado = DespachoEstadoService.peso_despachado_por_producto(pedido)
            requerido = DespachoEstadoService.requerido_por_producto(pedido)
            for producto_id, cantidad_requerida in requerido.items():
                restante = cantidad_requerida - ya_despachado.get(producto_id, Decimal('0'))
                pendiente[(p_id, producto_id)] = max(restante, Decimal('0'))
        return pendiente

    @staticmethod
    def _stock_bloqueado_por_lote(lotes_codes, ids_bodegas):
        """Todas las filas de stock en una sola consulta y en orden fijo (lote, id):
        despachos y reversiones concurrentes que comparten lotes las adquieren en el
        mismo orden y no se interbloquean (SQL Server 1205)."""
        lotes = LoteProduccion.objects.filter(codigo_lote__in=lotes_codes)
        stocks = stock_vendible_del_lote(
            StockBodega.objects.select_for_update().filter(cantidad__gt=0), lotes,
        ).order_by('lote_id', 'id')
        if ids_bodegas is not None:
            stocks = stocks.filter(bodega_id__in=ids_bodegas)
        stock_por_lote = {}
        for s in stocks:
            stock_por_lote.setdefault(s.lote_id, []).append(s)
        return stock_por_lote

    @staticmethod
    def _asignar_pedido(lote, producto, cantidad, pedidos_ids, pedidos_obj, pendiente):
        """Pedido al que se atribuye el lote; descuenta su cantidad de lo pendiente."""
        # Validación de reserva inmutable MTO
        if lote.pedido_venta_reserva_id:
            if lote.pedido_venta_reserva_id not in pedidos_ids:
                raise serializers.ValidationError(
                    f"El lote {lote.codigo_lote} está reservado exclusivamente para el Pedido "
                    f"#{lote.pedido_venta_reserva_id} y no puede ser despachado "
                    f"en los pedidos seleccionados."
                )
            clave = (lote.pedido_venta_reserva_id, producto.id)
            if clave in pendiente:
                pendiente[clave] -= cantidad
            return pedidos_obj.get(lote.pedido_venta_reserva_id)

        # Asignar este lote al primer pedido (en el orden recibido) que todavía necesite
        # este producto. Un lote es atómico (no se reparte entre pedidos): si sobra, igual
        # se atribuye a ese pedido para no perder trazabilidad de a quién se entregó.
        for p_id in pedidos_ids:
            clave = (p_id, producto.id)
            if pendiente.get(clave, Decimal('0')) > 0:
                pendiente[clave] -= cantidad
                return pedidos_obj.get(p_id)
        # Ningún pedido seleccionado necesita ya este producto (excedente escaneado) — se
        # atribuye igual al primer pedido que lo pidió, en vez de dejarlo huérfano.
        for p_id in pedidos_ids:
            if (p_id, producto.id) in pendiente:
                return pedidos_obj.get(p_id)
        return None

    @staticmethod
    def _lote_y_filas(code, stock_por_lote, productos_pedidos):
        """Lote escaneado y las filas de stock que se despachan (se retiran del mapa).

        Sale la fila del producto del lote (el de su OP) y las de otros productos del lote
        que pidan los pedidos; un producto agregado a mano que nadie pidió se queda en stock.
        """
        try:
            lote = LoteProduccion.objects.select_related('orden_produccion').get(codigo_lote=code)
        except LoteProduccion.DoesNotExist:
            raise serializers.ValidationError(f"Lote {code} no válido.") from None
        filas = stock_por_lote.pop(lote.id, [])
        if not filas:
            raise serializers.ValidationError(f"El lote {code} ya no tiene stock disponible.")
        principal = lote.producto_del_stock_id
        filas = [f for f in principal_primero(filas, lote)
                 if f.producto_id == principal or f.producto_id in productos_pedidos]
        if not filas:
            raise serializers.ValidationError(
                f"El lote {code} no tiene stock de los productos de los pedidos seleccionados.")
        return lote, filas

    @staticmethod
    def _actualizar_estados(pedidos_obj):
        from inventory.services.despacho_estado import DespachoEstadoService

        actualizados = 0
        for pedido in pedidos_obj.values():
            nuevo_estado = DespachoEstadoService.recalcular_estado(pedido)
            if nuevo_estado != pedido.estado:
                pedido.estado = nuevo_estado
                if nuevo_estado in ('despachado', 'despachado_parcial'):
                    pedido.fecha_despacho = timezone.now().date()
                pedido.save()
                actualizados += 1
        return actualizados

    def _procesar(self, request, pedidos_ids, lotes_codes, observaciones, items_incompletos, ids_bodegas):
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
            pendiente = self._pendiente_por_pedido_producto(pedidos_obj)
            stock_por_lote = self._stock_bloqueado_por_lote(lotes_codes, ids_bodegas)

            total_peso_despachado = Decimal('0.00')
            total_peso_por_pedido: dict = {p_id: Decimal('0.00') for p_id in pedidos_ids}
            documento_ref = f"Despacho #{historial.id} (Pedidos: {','.join(map(str, pedidos_ids))})"

            # Productos de las filas bloqueadas en una consulta: sin select_related, que
            # dentro del select_for_update extendería el UPDLOCK a la tabla de productos.
            productos = Producto.objects.in_bulk(
                {fila.producto_id for filas in stock_por_lote.values() for fila in filas})
            productos_pedidos = {producto_id for (_pedido_id, producto_id) in pendiente}

            for code in lotes_codes:
                lote, filas = self._lote_y_filas(code, stock_por_lote, productos_pedidos)
                for stock in filas:
                    producto = productos[stock.producto_id]
                    cantidad_a_despachar = stock.cantidad
                    total_peso_despachado += cantidad_a_despachar
                    pedido_asignado = self._asignar_pedido(
                        lote, producto, cantidad_a_despachar, pedidos_ids, pedidos_obj, pendiente)
                    if pedido_asignado is not None:
                        total_peso_por_pedido[pedido_asignado.id] += cantidad_a_despachar

                    # El producto es el de la fila (no el de la OP): un lote puede traer
                    # productos agregados a mano y el Kardex debe vender el que sale.
                    mov_venta = MovimientoInventario.objects.create(
                        tipo_movimiento='VENTA',
                        producto=producto,
                        cantidad=cantidad_a_despachar,
                        bodega_origen_id=stock.bodega_id,
                        lote=lote,
                        usuario=request.user,
                        documento_ref=documento_ref,
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
                    stock.stock_comprometido = max(
                        Decimal('0.000'), stock.stock_comprometido - cantidad_a_despachar)
                    stock._justificacion_auditoria = f"Despacho procesado: {code}"
                    stock.save()

            historial.total_peso = total_peso_despachado
            historial.save()

            for p_id in pedidos_ids:
                DetalleHistorialDespachoPedido.objects.create(
                    historial=historial,
                    pedido_id=p_id,
                    cantidad_despachada=total_peso_por_pedido.get(p_id, Decimal('0.00')),
                )

            pedidos_actualizados = self._actualizar_estados(pedidos_obj)

            logger.info(
                "Despacho procesado exitosamente",
                extra={"sd": {"entity": "HistorialDespacho", "id": historial.id, "user": request.user.username}},
            )
            return Response({
                'message': 'Despacho procesado correctamente',
                'despacho_id': historial.id,
                'pedidos_actualizados': pedidos_actualizados,
                'lotes_procesados': len(lotes_codes),
                'items_no_despachados': items_incompletos,
            })

    def post(self, request, *args, **kwargs):
        pedidos_ids = request.data.get('pedidos', [])
        lotes_codes = request.data.get('lotes', [])
        observaciones = request.data.get('observaciones', '')
        confirmar_incompleto = bool(request.data.get('confirmar_incompleto', False))

        if not pedidos_ids or not lotes_codes:
            return Response({'error': 'Faltan pedidos o lotes para procesar'}, status=400)

        try:
            pedidos_ids = [int(p) for p in pedidos_ids]
        except (TypeError, ValueError):
            return Response({'error': 'Identificador de pedido inválido.'}, status=400)
        # OWASP A01: un pedido de otra sede responde igual que uno inexistente.
        pedidos_visibles = filtrar_por_sede(PedidoVenta.objects.filter(id__in=pedidos_ids), request.user)
        if pedidos_visibles.count() != len(set(pedidos_ids)):
            return Response({'error': 'Pedido no encontrado.'}, status=404)
        # Ids resueltos antes de la transacción: como subconsulta dentro del
        # select_for_update, SQL Server extendía el UPDLOCK a las filas de
        # bodegas_asignadas y serializaba a todos los despachadores.
        visibles = bodegas_visibles(request.user)
        ids_bodegas = None if visibles is None else list(visibles.values_list('id', flat=True))

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
            for intento in range(1, INTENTOS_DEADLOCK + 1):
                try:
                    return self._procesar(
                        request, pedidos_ids, lotes_codes, observaciones, items_incompletos, ids_bodegas,
                    )
                except DatabaseError as e:
                    if intento == INTENTOS_DEADLOCK or not es_deadlock(e):
                        raise
                    logger.warning("Despacho elegido víctima de deadlock; reintento %s", intento)

        except serializers.ValidationError as e:
            logger.warning(
                "Fallo al validar despacho",
                extra={"sd": {"entity": "HistorialDespacho", "reason": str(e.detail)}},
            )
            return Response({'error': str(e.detail[0] if isinstance(e.detail, list) else e.detail)}, status=400)
        except Exception as e:
            logger.exception("Error procesando despacho",
                             extra={"sd": {"entity": "HistorialDespacho", "error": str(e)}})
            return Response({'error': 'Error interno al procesar el despacho.'}, status=500)
