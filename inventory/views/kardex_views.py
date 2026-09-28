from decimal import Decimal

from django.db import models
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from inventory.models import MovimientoInventario
from inventory.pagination import PaginacionAcotada
from inventory.permissions import IsInventoryStaffOrAdmin
from inventory.services.kardex_service import FiltroKardexInvalido, KardexService
from gestion.models import Bodega, Producto, LoteProduccion


_TIPOS_DISPLAY = dict(MovimientoInventario.TIPO_MOVIMIENTO_CHOICES)


class KardexBodegaAPIView(APIView):
    """
    GET /api/inventory/bodegas/{bodega_id}/kardex/?producto_id=&fecha_inicio=&fecha_fin=&tipo=&page=&page_size=

    Kárdex paginado de un producto en una bodega. El saldo lo calcula la base
    (KardexService): cada fila trae su 'saldo' ya acumulado desde el inicio del
    historial, así que cualquier página es correcta por sí sola, y la respuesta
    incluye 'saldo_inicial' (saldo antes de fecha_inicio). RNF-03 · TEX-22: el
    costo por petición no crece con el historial de la bodega.
    """
    permission_classes = [IsInventoryStaffOrAdmin]

    def get(self, request, bodega_id, *args, **kwargs):
        params = request.query_params
        producto_id = params.get('producto_id')
        if not producto_id:
            return Response(
                {"error": "El parámetro 'producto_id' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        get_object_or_404(Bodega, pk=bodega_id)
        get_object_or_404(Producto, pk=producto_id)

        try:
            servicio = KardexService(
                bodega_id=bodega_id, producto_id=producto_id,
                fecha_inicio=params.get('fecha_inicio'), fecha_fin=params.get('fecha_fin'),
                proveedor_id=params.get('proveedor_id'), lote_id=params.get('lote_id'),
                tipo=params.get('tipo'),
            )
        except FiltroKardexInvalido as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        paginador = PaginacionAcotada()
        pagina = paginador.paginate_queryset(servicio.movimientos(), request, view=self)
        respuesta = paginador.get_paginated_response([self._fila(f) for f in pagina])
        respuesta.data['saldo_inicial'] = servicio.saldo_inicial()
        return respuesta

    @staticmethod
    def _fila(f):
        nombre = f"{f.pop('usuario_nombre') or ''} {f.pop('usuario_apellido') or ''}".strip()
        username = f.pop('usuario_username')
        f['usuario'] = nombre or username or 'Sistema'
        f['tipo_movimiento_display'] = _TIPOS_DISPLAY.get(f['tipo_movimiento'], f['tipo_movimiento'])
        return f


class RetroKardexAPIView(APIView):
    """
    API para obtener el stock de un producto a una fecha pasada específica.
    """
    permission_classes = [IsInventoryStaffOrAdmin]

    def get(self, request, *args, **kwargs):
        producto_id = request.query_params.get('producto_id')
        fecha_corte = request.query_params.get('fecha_corte')
        bodega_id = request.query_params.get('bodega_id')
        sede_id = request.query_params.get('sede_id')

        if not producto_id or not fecha_corte:
            return Response(
                {"error": "Los parámetros 'producto_id' y 'fecha_corte' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        get_object_or_404(Producto, pk=producto_id)

        query_filter = models.Q(producto_id=producto_id, fecha__lte=fecha_corte)
        if bodega_id:
            query_filter &= (models.Q(bodega_origen_id=bodega_id) | models.Q(bodega_destino_id=bodega_id))
        if sede_id:
            query_filter &= (models.Q(bodega_origen__sede_id=sede_id) | models.Q(bodega_destino__sede_id=sede_id))

        user = request.user
        es_privilegiado = user.is_superuser or user.groups.filter(
            name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()
        if not es_privilegiado:
            bodegas_asignadas = list(user.bodegas_asignadas.values_list('id', flat=True))
            query_filter &= (
                models.Q(bodega_origen_id__in=bodegas_asignadas) | models.Q(bodega_destino_id__in=bodegas_asignadas)
            )

        movs = MovimientoInventario.objects.select_related('bodega_origen', 'bodega_destino').filter(query_filter)

        stock_por_bodega = {}
        for m in movs:
            if m.bodega_destino_id:
                if bodega_id and str(m.bodega_destino_id) != str(bodega_id):
                    pass
                else:
                    stock_por_bodega[m.bodega_destino.nombre] = stock_por_bodega.get(
                        m.bodega_destino.nombre, Decimal('0.00')) + m.cantidad
            if m.bodega_origen_id:
                if bodega_id and str(m.bodega_origen_id) != str(bodega_id):
                    pass
                else:
                    stock_por_bodega[m.bodega_origen.nombre] = stock_por_bodega.get(
                        m.bodega_origen.nombre, Decimal('0.00')) - m.cantidad

        resultados = [
            {"bodega": bodega, "stock_calculado": cantidad}
            for bodega, cantidad in stock_por_bodega.items() if cantidad != 0
        ]

        return Response(resultados, status=status.HTTP_200_OK)


class MovimientosPorLoteAPIView(APIView):
    """
    API para obtener la trazabilidad completa de un lote.
    """
    permission_classes = [IsInventoryStaffOrAdmin]

    def get(self, request, lote_codigo, *args, **kwargs):
        lote = get_object_or_404(LoteProduccion, codigo_lote=lote_codigo)

        movimientos = MovimientoInventario.objects.select_related(
            'bodega_origen', 'bodega_destino', 'producto', 'usuario'
        ).filter(lote=lote)

        user = request.user
        es_privilegiado = user.is_superuser or user.groups.filter(
            name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()
        if not es_privilegiado:
            bodegas_asignadas = user.bodegas_asignadas.values_list('id', flat=True)
            movimientos = movimientos.filter(
                models.Q(bodega_origen_id__in=bodegas_asignadas) | models.Q(bodega_destino_id__in=bodegas_asignadas)
            )

        movimientos = movimientos.order_by('fecha')

        data = []
        producto_desc = "N/A"
        for m in movimientos:
            producto_desc = m.producto.descripcion
            data.append({
                "id": m.id,
                "fecha": m.fecha,
                "tipo_movimiento": m.get_tipo_movimiento_display(),
                "bodega_origen": m.bodega_origen.nombre if m.bodega_origen else "-",
                "bodega_destino": m.bodega_destino.nombre if m.bodega_destino else "-",
                "cantidad": m.cantidad,
                "documento_ref": m.documento_ref,
                "usuario": m.usuario.get_full_name() or m.usuario.username if m.usuario else "Sistema"
            })

        return Response({
            "lote_codigo": lote.codigo_lote,
            "producto": producto_desc,
            "historial": data
        }, status=status.HTTP_200_OK)
