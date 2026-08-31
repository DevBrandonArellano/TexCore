"""
Consultas de datos para reportes — extraídas de internal_api/views/reporting_views.py
para poder llamarlas EN PROCESO (sin HTTP) desde inventory/reporting_proxy.py.

Antes de esta refactorización (auditoría de performance 2026-08-31), cada reporte
hacía: nginx -> backend (reporting_proxy) -> reporting_excel -> DE VUELTA al mismo
backend (estas vistas, vía HTTP). Ese último salto tenía el timeout más corto de
toda la cadena (30s) y era el primer punto de falla bajo alta concurrencia, porque
el backend competía consigo mismo por el mismo pool de workers.

Estas funciones son la misma lógica de consulta de siempre — reporting_proxy las
llama directamente (mismo proceso, sin red) y le pasa los datos ya resueltos a
reporting_excel solo para el formateo a Excel/CSV. Las vistas de
internal_api/views/reporting_views.py delegan aquí para no duplicar lógica.
"""
from datetime import timedelta

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from gestion.models import Cliente, CustomUser, LoteProduccion, OrdenProduccion, PedidoVenta, Producto
from inventory.models import MovimientoInventario, StockBodega


def _fecha_hasta_exclusiva(fecha_hasta):
    """Ver nota en reporting_views.py — evita CAST(columna AS DATE) no-sargable."""
    parsed = parse_date(fecha_hasta) if isinstance(fecha_hasta, str) else fecha_hasta
    return parsed + timedelta(days=1) if parsed else None


def get_kardex(bodega_id, producto_id=None, fecha_desde=None, fecha_hasta=None, lote_codigo=None):
    qs = MovimientoInventario.objects.select_related(
        "producto", "bodega_origen", "bodega_destino", "lote", "usuario"
    ).filter(Q(bodega_origen_id=bodega_id) | Q(bodega_destino_id=bodega_id))
    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lt=_fecha_hasta_exclusiva(fecha_hasta))
    if producto_id:
        qs = qs.filter(producto_id=producto_id)
    if lote_codigo:
        qs = qs.filter(lote__codigo_lote=lote_codigo)
    return list(
        qs.values(
            "id", "fecha", "tipo_movimiento", "cantidad", "saldo_resultante", "documento_ref",
            producto_descripcion=F("producto__descripcion"),
            bodega_origen_nombre=F("bodega_origen__nombre"),
        )
    )


def get_productos(sede_id=None):
    qs = Producto.objects.all()
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return list(qs.values("id", "codigo", "descripcion", "tipo", "unidad_medida", "precio_base", "stock_minimo"))


def get_usuarios(sede_id=None):
    qs = CustomUser.objects.all()
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return list(qs.values("id", "username", "first_name", "last_name", "email", sede_nombre=F("sede__nombre")))


def get_stock_actual(bodega_id, producto_id=None):
    qs = StockBodega.objects.select_related("producto", "bodega", "lote").filter(
        bodega_id=bodega_id, cantidad__gt=0
    )
    if producto_id:
        qs = qs.filter(producto_id=producto_id)
    return list(
        qs.values(
            "id", "cantidad",
            producto_descripcion=F("producto__descripcion"),
            producto_codigo=F("producto__codigo"),
            bodega_nombre=F("bodega__nombre"),
            lote_codigo=F("lote__codigo_lote"),
        )
    )


def get_valorizacion(bodega_id):
    qs = StockBodega.objects.select_related("producto").filter(bodega_id=bodega_id, cantidad__gt=0)
    return list(
        qs.annotate(valor_total=F("cantidad") * F("producto__precio_base")).values(
            "id", "cantidad", "valor_total",
            producto_descripcion=F("producto__descripcion"),
            precio_base=F("producto__precio_base"),
        )
    )


def get_aging(bodega_id, dias_minimos=30):
    corte = timezone.now() - timedelta(days=int(dias_minimos))
    productos_con_movimiento_reciente = MovimientoInventario.objects.filter(
        Q(bodega_origen_id=bodega_id) | Q(bodega_destino_id=bodega_id), fecha__gte=corte
    ).values_list("producto_id", flat=True)
    qs = StockBodega.objects.select_related("producto").filter(
        bodega_id=bodega_id, cantidad__gt=0
    ).exclude(producto_id__in=productos_con_movimiento_reciente)
    return list(qs.values("id", "cantidad", producto_descripcion=F("producto__descripcion")))


def get_rotacion(bodega_id, fecha_desde=None, fecha_hasta=None):
    # Solo bodega_origen_id es intencional — ver nota en RotacionView.
    qs = MovimientoInventario.objects.filter(bodega_origen_id=bodega_id)
    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lt=_fecha_hasta_exclusiva(fecha_hasta))
    return list(
        qs.order_by().values(producto_descripcion=F("producto__descripcion")).annotate(
            total_salidas=Sum("cantidad")
        )
    )


def get_stock_cero(bodega_id):
    qs = StockBodega.objects.select_related("producto").filter(bodega_id=bodega_id, cantidad=0)
    return list(qs.values("id", "cantidad", producto_descripcion=F("producto__descripcion")))


def get_resumen_movimientos(bodega_id, fecha_desde=None, fecha_hasta=None):
    qs = MovimientoInventario.objects.filter(
        Q(bodega_origen_id=bodega_id) | Q(bodega_destino_id=bodega_id)
    )
    if fecha_desde:
        qs = qs.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha__lt=_fecha_hasta_exclusiva(fecha_hasta))
    return list(qs.order_by().values("tipo_movimiento").annotate(total=Sum("cantidad")))


def get_ventas_vendedor(vendedor_id, fecha_desde=None, fecha_hasta=None):
    qs = PedidoVenta.objects.filter(vendedor_asignado_id=vendedor_id, anulado=False).select_related("cliente")
    if fecha_desde:
        qs = qs.filter(fecha_pedido__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
    return list(
        qs.values(
            "id", "guia_remision", "fecha_pedido", "estado", "esta_pagado",
            cliente_nombre=F("cliente__nombre_razon_social"),
        )
    )


def get_top_clientes_vendedor(vendedor_id, fecha_desde=None, fecha_hasta=None):
    qs = PedidoVenta.objects.filter(vendedor_asignado_id=vendedor_id, anulado=False)
    if fecha_desde:
        qs = qs.filter(fecha_pedido__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
    return list(
        qs.values("cliente_id", cliente_nombre=F("cliente__nombre_razon_social"))
        .annotate(total_pedidos=Count("id"))
        .order_by("-total_pedidos")[:10]
    )


def get_deudores_vendedor(vendedor_id):
    qs = Cliente.objects.filter(vendedor_asignado_id=vendedor_id, is_active=True).annotate(
        total_pagado=Coalesce(Sum("pagos__monto"), Value(0), output_field=DecimalField()),
    )
    return list(qs.values("id", "nombre_razon_social", "limite_credito", "plazo_credito_dias", "total_pagado"))


def get_ventas_gerencial(sede_id=None, fecha_desde=None, fecha_hasta=None):
    qs = PedidoVenta.objects.filter(anulado=False).select_related("cliente", "sede")
    if fecha_desde:
        qs = qs.filter(fecha_pedido__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return list(
        qs.values(
            "id", "guia_remision", "fecha_pedido", "estado", "esta_pagado",
            cliente_nombre=F("cliente__nombre_razon_social"),
            sede_nombre=F("sede__nombre"),
        )
    )


def get_top_clientes_gerencial(sede_id=None, fecha_desde=None, fecha_hasta=None):
    qs = PedidoVenta.objects.filter(anulado=False)
    if fecha_desde:
        qs = qs.filter(fecha_pedido__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return list(
        qs.values("cliente_id", cliente_nombre=F("cliente__nombre_razon_social"))
        .annotate(total_pedidos=Count("id"))
        .order_by("-total_pedidos")[:20]
    )


def get_deudores_gerencial(sede_id=None):
    qs = Cliente.objects.filter(is_active=True).annotate(
        total_pagado=Coalesce(Sum("pagos__monto"), Value(0), output_field=DecimalField()),
    )
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return list(qs.values("id", "nombre_razon_social", "limite_credito", "total_pagado"))


def get_ordenes_produccion(sede_id=None, fecha_desde=None, fecha_hasta=None):
    qs = OrdenProduccion.objects.select_related("producto_salida", "sede")
    if fecha_desde:
        qs = qs.filter(fecha_creacion__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_creacion__lte=fecha_hasta)
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    return list(
        qs.values(
            "id", "codigo", "estado", "prioridad", "fecha_creacion", "peso_neto_requerido",
            producto_descripcion=F("producto_salida__descripcion"),
            sede_nombre=F("sede__nombre"),
        )
    )


def get_lotes_produccion(sede_id=None, fecha_desde=None, fecha_hasta=None):
    qs = LoteProduccion.objects.select_related("orden_produccion__producto_salida", "orden_produccion__sede")
    if fecha_desde:
        qs = qs.filter(hora_inicio__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(hora_inicio__lt=_fecha_hasta_exclusiva(fecha_hasta))
    if sede_id:
        qs = qs.filter(orden_produccion__sede_id=sede_id)
    return list(
        qs.values(
            "id", "codigo_lote", "peso_neto_producido", "hora_inicio", "hora_final", "clasificacion_calidad",
            producto_descripcion=F("orden_produccion__producto_salida__descripcion"),
            op_codigo=F("orden_produccion__codigo"),
        )
    )


def get_tendencia_produccion(sede_id=None, fecha_desde=None, fecha_hasta=None):
    qs = LoteProduccion.objects.select_related("orden_produccion__sede")
    if fecha_desde:
        qs = qs.filter(hora_inicio__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(hora_inicio__lt=_fecha_hasta_exclusiva(fecha_hasta))
    if sede_id:
        qs = qs.filter(orden_produccion__sede_id=sede_id)
    return list(
        qs.annotate(fecha=TruncDate("hora_inicio"))
        .values("fecha")
        .annotate(total_peso=Sum("peso_neto_producido"), total_lotes=Sum(Value(1)))
        .order_by("fecha")
    )
