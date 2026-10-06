"""
Mapea cada report_path externo (el que expone inventory/reporting_proxy.py al
frontend) a su función de datos en internal_api/services/reporting_data.py, y
arma el nombre de archivo del reporte.

Existe para no duplicar esta lógica entre el flujo síncrono
(inventory/reporting_proxy.py) y el asíncrono (gestion/tasks.py) — ambos
llaman a resolve_report() en vez de repetir el mapeo.
"""
from collections.abc import Callable

from . import reporting_data as rd

_DIAS_AGING_VALIDOS = (30, 60, 90, 180)


def _kardex(p: dict) -> tuple[list, str]:
    producto_id = p.get("producto_id")
    producto_id = int(producto_id) if producto_id and producto_id not in ("0", "") else None
    bodega_id = p.get("bodega_id")
    rows = rd.get_kardex(
        bodega_id, producto_id=producto_id, fecha_desde=p.get("fecha_inicio"),
        fecha_hasta=p.get("fecha_fin"), lote_codigo=p.get("lote_codigo") or None, tipo=p.get("tipo") or None,
    )
    filename = f"kardex_{bodega_id}_{producto_id}" if producto_id else f"movimientos_bodega_{bodega_id}"
    return rows, filename


def _aging(p: dict) -> tuple[list, str]:
    try:
        dias = int(p.get("dias", 30))
    except (TypeError, ValueError):
        dias = 30
    if dias not in _DIAS_AGING_VALIDOS:
        dias = 30
    bodega_id = p.get("bodega_id")
    return rd.get_aging(bodega_id, dias_minimos=dias), f"aging_inventario_bodega_{bodega_id}"


def _por_bodega(funcion: str, prefijo: str, con_fechas: bool = False) -> Callable[[dict], tuple[list, str]]:
    """Reporte de una bodega; `funcion` se resuelve en rd al llamar (las pruebas lo parchean)."""
    def resolver(p: dict) -> tuple[list, str]:
        bodega_id = p.get("bodega_id")
        kwargs = {"fecha_desde": p.get("fecha_inicio"), "fecha_hasta": p.get("fecha_fin")} if con_fechas else {}
        return getattr(rd, funcion)(bodega_id, **kwargs), f"{prefijo}_bodega_{bodega_id}"
    return resolver


def _por_sede_y_rango(funcion: str, prefijo: str) -> Callable[[dict], tuple[list, str]]:
    def resolver(p: dict) -> tuple[list, str]:
        inicio, fin = p.get("fecha_inicio"), p.get("fecha_fin")
        rows = getattr(rd, funcion)(sede_id=p.get("sede_id"), fecha_desde=inicio, fecha_hasta=fin)
        return rows, f"{prefijo}_{inicio}_{fin}"
    return resolver


_REPORTES: dict[str, Callable[[dict], tuple[list, str]]] = {
    "export/kardex": _kardex,
    "export/productos": lambda p: (rd.get_productos(p.get("sede_id")), "catalogo_productos"),
    "export/usuarios": lambda p: (rd.get_usuarios(p.get("sede_id")), "directorio_usuarios"),
    "export/stock-actual": lambda p: (
        rd.get_stock_actual(p.get("bodega_id"), producto_id=p.get("producto_id")),
        f"stock_actual_bodega_{p.get('bodega_id')}",
    ),
    "export/valorizacion": _por_bodega("get_valorizacion", "valorizacion"),
    "export/aging": _aging,
    "export/rotacion": _por_bodega("get_rotacion", "rotacion", con_fechas=True),
    "export/stock-cero": _por_bodega("get_stock_cero", "stock_cero"),
    "export/stock-bajo": _por_bodega("get_stock_bajo", "stock_bajo"),
    "export/resumen-movimientos": _por_bodega("get_resumen_movimientos", "resumen_movimientos", con_fechas=True),
    "gerencial/ventas": _por_sede_y_rango("get_ventas_gerencial", "ventas_gerencial"),
    "gerencial/top-clientes": _por_sede_y_rango("get_top_clientes_gerencial", "top_clientes_gerencial"),
    "gerencial/deudores": lambda p: (
        rd.get_deudores_gerencial(sede_id=p.get("sede_id")), "clientes_deudores_gerencial"),
    "produccion/ordenes": _por_sede_y_rango("get_ordenes_produccion", "ordenes_produccion"),
    "produccion/lotes": _por_sede_y_rango("get_lotes_produccion", "lotes_produccion"),
    "produccion/tendencia": _por_sede_y_rango("get_tendencia_produccion", "tendencia_produccion"),
}


def _reporte_de_vendedor(vendedor_id: str, accion: str, p: dict) -> tuple[list, str] | None:
    inicio, fin = p.get("fecha_inicio"), p.get("fecha_fin")
    if accion == "ventas":
        rows = rd.get_ventas_vendedor(vendedor_id, fecha_desde=inicio, fecha_hasta=fin)
        return rows, f"ventas_vendedor_{vendedor_id}_{inicio}_{fin}"
    if accion == "top-clientes":
        rows = rd.get_top_clientes_vendedor(vendedor_id, fecha_desde=inicio, fecha_hasta=fin)
        return rows, f"top_clientes_vendedor_{vendedor_id}_{inicio}_{fin}"
    if accion == "deudores":
        return rd.get_deudores_vendedor(vendedor_id), f"clientes_deudores_vendedor_{vendedor_id}"
    return None


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
    resolver = _REPORTES.get(report_path)
    if resolver:
        return resolver(params)

    parts = report_path.split("/")
    if len(parts) == 3 and parts[0] == "vendedores":
        resultado = _reporte_de_vendedor(parts[1], parts[2], params)
        if resultado is not None:
            return resultado

    raise ValueError(f"Ruta de reporte no soportada: '{report_path}'")
