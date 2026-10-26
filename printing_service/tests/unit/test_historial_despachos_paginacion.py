"""Aviso de paginación al pie del PDF del historial de despachos.

El PDF contiene solo la página visible del listado; cuando el filtro tiene más
registros que una página, el pie debe decir cuántos hay en total y cuántas
páginas existen.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): mas de una pagina / un solo dia / un rango / una sola pagina / request sin
  datos de paginacion.
- Análisis de valores límite (BVA): request sin datos de paginacion.
"""

from src.routers.pdf import get_pdf_strategy
from src.schemas.printing import HistorialDespachosRequest


def _despacho(i: int) -> dict:
    return {
        "id": i,
        "fecha_despacho": "16/10/2026 09:15",
        "usuario_nombre": "Despacho Demo",
        "pedidos": "Cliente A (GR-001)",
        "total_bultos": 2,
        "total_peso": 10.5,
    }


def _html(**extra) -> str:
    datos = {
        "generado_en": "2026-10-16T10:00:00Z",
        "despachos": [_despacho(i) for i in range(1, 4)],
        **extra,
    }
    contexto = HistorialDespachosRequest(**datos).model_dump()
    plantilla = get_pdf_strategy()._env.get_template("historial_despachos.html")
    return plantilla.render(**contexto)


def test_historial_dado_mas_de_una_pagina_cuando_renderiza_entonces_muestra_total_y_paginas():
    html = _html(total_registros=120, pagina=2, total_paginas=3)

    assert 'class="aviso-paginacion"' in html
    assert "120" in html
    assert "página 2 de 3" in html


def test_historial_dado_mas_de_una_pagina_cuando_renderiza_entonces_indica_cuantos_registros_faltan():
    html = _html(total_registros=120, pagina=1, total_paginas=3)

    # 3 filas impresas de 120: quedan 117 en las demás páginas.
    assert "3 de 120" in html


def test_historial_dado_un_solo_dia_cuando_renderiza_entonces_el_aviso_nombra_el_dia():
    html = _html(fecha_desde="2026-10-16", fecha_hasta="2026-10-16", total_registros=120, pagina=1, total_paginas=3)

    assert "del día 2026-10-16" in html


def test_historial_dado_un_rango_cuando_renderiza_entonces_el_aviso_habla_del_rango_filtrado():
    html = _html(fecha_desde="2026-10-01", fecha_hasta="2026-10-16", total_registros=120, pagina=1, total_paginas=3)

    assert "del rango filtrado" in html


def test_historial_dado_una_sola_pagina_cuando_renderiza_entonces_no_muestra_el_aviso():
    html = _html(total_registros=3, pagina=1, total_paginas=1)

    assert "aviso-paginacion" not in html.split("</style>")[1]


def test_historial_dado_request_sin_datos_de_paginacion_cuando_renderiza_entonces_no_muestra_el_aviso():
    html = _html()

    assert "aviso-paginacion" not in html.split("</style>")[1]


def test_historial_request_dado_sin_paginacion_cuando_se_crea_entonces_usa_valores_por_defecto():
    req = HistorialDespachosRequest(generado_en="2026-10-16T10:00:00Z", despachos=[])

    assert req.total_registros is None
    assert req.pagina == 1
    assert req.total_paginas == 1
