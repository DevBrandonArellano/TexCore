"""
Mapea cada report_path externo (el que expone inventory/reporting_proxy.py al
frontend) a su función de datos en internal_api/services/reporting_data.py, y
arma el nombre de archivo del reporte.

Existe para no duplicar esta lógica entre el flujo síncrono
(inventory/reporting_proxy.py) y el asíncrono (gestion/tasks.py) — ambos
llaman a resolve_report() en vez de repetir el mapeo.
"""
from . import reporting_data as rd


def resolve_report(report_path: str, params: dict) -> tuple[list, str]:
    """
    report_path: uno de los paths whitelisteados en reporting_proxy.py (ej.
    "export/kardex", "gerencial/ventas", "vendedores/12/ventas").
    params: dict de query params ya resueltos (sede_id ya forzado según rol
    del usuario humano — ver reporting_proxy.py).

    Retorna (rows, filename). Lanza ValueError si report_path no está
    soportado (no debería ocurrir: reporting_proxy.py ya lo valida contra
    una whitelist antes de llegar aquí).
    """
    fecha_inicio = params.get("fecha_inicio")
    fecha_fin = params.get("fecha_fin")
    sede_id = params.get("sede_id")
    bodega_id = params.get("bodega_id")

    if report_path == "export/kardex":
        producto_id = params.get("producto_id")
        producto_id = int(producto_id) if producto_id and producto_id not in ("0", "") else None
        lote_codigo = params.get("lote_codigo") or None
        rows = rd.get_kardex(
            bodega_id, producto_id=producto_id, fecha_desde=fecha_inicio,
            fecha_hasta=fecha_fin, lote_codigo=lote_codigo,
        )
        filename = f"kardex_{bodega_id}_{producto_id}" if producto_id else f"movimientos_bodega_{bodega_id}"
        return rows, filename

    if report_path == "export/productos":
        return rd.get_productos(sede_id), "catalogo_productos"

    if report_path == "export/usuarios":
        return rd.get_usuarios(sede_id), "directorio_usuarios"

    if report_path == "export/stock-actual":
        producto_id = params.get("producto_id")
        return rd.get_stock_actual(bodega_id, producto_id=producto_id), f"stock_actual_bodega_{bodega_id}"

    if report_path == "export/valorizacion":
        return rd.get_valorizacion(bodega_id), f"valorizacion_bodega_{bodega_id}"

    if report_path == "export/aging":
        dias = params.get("dias", 30)
        try:
            dias = int(dias)
        except (TypeError, ValueError):
            dias = 30
        if dias not in (30, 60, 90, 180):
            dias = 30
        return rd.get_aging(bodega_id, dias_minimos=dias), f"aging_inventario_bodega_{bodega_id}"

    if report_path == "export/rotacion":
        rows = rd.get_rotacion(bodega_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"rotacion_bodega_{bodega_id}"

    if report_path == "export/stock-cero":
        return rd.get_stock_cero(bodega_id), f"stock_cero_bodega_{bodega_id}"

    if report_path == "export/stock-bajo":
        return rd.get_stock_bajo(bodega_id), f"stock_bajo_bodega_{bodega_id}"

    if report_path == "export/resumen-movimientos":
        rows = rd.get_resumen_movimientos(bodega_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"resumen_movimientos_bodega_{bodega_id}"

    if report_path == "gerencial/ventas":
        rows = rd.get_ventas_gerencial(sede_id=sede_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"ventas_gerencial_{fecha_inicio}_{fecha_fin}"

    if report_path == "gerencial/top-clientes":
        rows = rd.get_top_clientes_gerencial(sede_id=sede_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"top_clientes_gerencial_{fecha_inicio}_{fecha_fin}"

    if report_path == "gerencial/deudores":
        return rd.get_deudores_gerencial(sede_id=sede_id), "clientes_deudores_gerencial"

    if report_path == "produccion/ordenes":
        rows = rd.get_ordenes_produccion(sede_id=sede_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"ordenes_produccion_{fecha_inicio}_{fecha_fin}"

    if report_path == "produccion/lotes":
        rows = rd.get_lotes_produccion(sede_id=sede_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"lotes_produccion_{fecha_inicio}_{fecha_fin}"

    if report_path == "produccion/tendencia":
        rows = rd.get_tendencia_produccion(sede_id=sede_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
        return rows, f"tendencia_produccion_{fecha_inicio}_{fecha_fin}"

    parts = report_path.split("/")
    if len(parts) == 3 and parts[0] == "vendedores":
        vendedor_id, accion = parts[1], parts[2]
        if accion == "ventas":
            rows = rd.get_ventas_vendedor(vendedor_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
            return rows, f"ventas_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}"
        if accion == "top-clientes":
            rows = rd.get_top_clientes_vendedor(vendedor_id, fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)
            return rows, f"top_clientes_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}"
        if accion == "deudores":
            return rd.get_deudores_vendedor(vendedor_id), f"clientes_deudores_vendedor_{vendedor_id}"

    raise ValueError(f"Ruta de reporte no soportada: '{report_path}'")
