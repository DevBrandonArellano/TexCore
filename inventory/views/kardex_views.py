import logging
from decimal import Decimal

from django.db import models
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from inventory.models import MovimientoInventario
from inventory.permissions import IsInventoryStaffOrAdmin
from gestion.models import Bodega, Producto, LoteProduccion

logger = logging.getLogger('inventory.views')


class KardexBodegaAPIView(APIView):
    """
    API para obtener el historial de movimientos (Kardex) de un producto
    en una bodega específica.
    """
    permission_classes = [IsInventoryStaffOrAdmin]

    def get(self, request, bodega_id, *args, **kwargs):
        producto_id = request.query_params.get('producto_id')
        if not producto_id:
            return Response(
                {"error": "El parámetro 'producto_id' es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        proveedor_id = request.query_params.get('proveedor_id')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        lote_id = request.query_params.get('lote_id')

        get_object_or_404(Bodega, pk=bodega_id)
        get_object_or_404(Producto, pk=producto_id)

        query_filter = models.Q(bodega_origen_id=bodega_id) | models.Q(bodega_destino_id=bodega_id)

        if proveedor_id:
            query_filter &= models.Q(proveedor_id=proveedor_id)

        if lote_id:
            query_filter &= models.Q(lote_id=lote_id)

        # Calcular saldo anterior para el "Running Balance" inicial
        saldo_anterior = Decimal('0.00')
        if fecha_inicio:
            # Todo el historial hasta antes de fecha_inicio
            movs_anteriores = MovimientoInventario.objects.filter(
                query_filter,
                producto_id=producto_id,
                fecha__lt=fecha_inicio
            )
            for m in movs_anteriores:
                if m.bodega_destino_id == bodega_id:
                    saldo_anterior += m.cantidad
                else:
                    saldo_anterior -= m.cantidad

            # Aritmetica de filtro para la vista actual
            query_filter &= models.Q(fecha__gte=fecha_inicio)

        if fecha_fin:
            # Asumimos que la fecha visual incluy todo el dia
            query_filter &= models.Q(fecha__lte=fecha_fin)

        movimientos = MovimientoInventario.objects.select_related(
            'bodega_origen', 'bodega_destino', 'proveedor', 'producto', 'lote', 'usuario'
        ).filter(
            query_filter,
            producto_id=producto_id
        ).order_by('fecha')

        # Calcular saldo progresivo
        saldo = saldo_anterior
        kardex_data = []

        # Añadir fila virtual de Saldo Inicial si hay fecha_inicio y saldo
        if fecha_inicio:
            kardex_data.append({
                "id": "saldo_inicial",
                "fecha": fecha_inicio,
                "tipo_movimiento": "SALDO INICIAL",
                "documento_ref": "-",
                "entrada": "",
                "salida": "",
                "saldo_resultante": saldo,
                "editado": False,
                "proveedor_nombre": "",
                "codigo_producto": "",
                "descripcion_producto": "Saldo Acumulado Previo",
                "lote": "",
                "usuario": ""
            })

        for m in movimientos:
            if m.bodega_destino_id == bodega_id:
                saldo += m.cantidad
                entrada = m.cantidad
                salida = ""
            else:  # Salida
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
                "editado": m.editado,
                "proveedor_nombre": m.proveedor.nombre if m.proveedor else "",
                "codigo_producto": m.producto.codigo,
                "descripcion_producto": m.producto.descripcion,
                "lote": m.lote.codigo_lote if m.lote else "",
                "usuario": m.usuario.get_full_name() or m.usuario.username if m.usuario else "Sistema"
            })

        return Response(kardex_data, status=status.HTTP_200_OK)


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
        if not (user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()):
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
        if not (user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists()):
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
