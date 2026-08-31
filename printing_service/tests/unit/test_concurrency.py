"""
Regresión de concurrencia del microservicio completo.

El Dockerfile levanta printing_service con `uvicorn src.main:app` SIN
`--workers` (un solo proceso, un solo event loop). Las 7 rutas de
`/pdf/*` (routers/pdf.py) llaman a PdfOutputStrategy.render(), que
ejecuta WeasyPrint (HTML -> PDF) de forma síncrona y puede tardar
segundos en documentos grandes — trabajo CPU-bound. Si se llamara
directo desde el handler `async def` (sin run_in_threadpool), esa
llamada bloquearía el único event loop del proceso mientras dura el
render, y NINGUNA otra petición — incluyendo /zpl/etiqueta, que usa
Empaquetado/Despacho para imprimir etiquetas Zebra en piso de planta —
podría atenderse mientras tanto.

Este test compara el tiempo de N peticiones PDF lanzadas en SERIE
contra las mismas N lanzadas EN PARALELO (asyncio.gather), con
PdfOutputStrategy.render() mockeado para simular un render lento
(time.sleep, bloqueante de verdad — libera el GIL igual que las
llamadas C de WeasyPrint). Comparar contra una línea base medida en el
mismo proceso evita falsos positivos por overhead fijo del entorno de
test. Si el event loop estuviera bloqueado, paralelo tardaría ~= serie;
con run_in_threadpool, paralelo debe ser sustancialmente más rápido.
"""
import asyncio
import time
from unittest.mock import MagicMock

from fastapi import Response
from httpx import ASGITransport, AsyncClient

# No hace falta mockear weasyprint en sys.modules aquí: get_pdf_strategy se
# sobreescribe con mock_strategy más abajo, así que PdfOutputStrategy.render()
# (el único lugar con el import tardío de weasyprint) nunca se ejecuta de
# verdad en este test.
from src.main import app
from src.routers.pdf import get_pdf_strategy

_DELAY_SECONDS = 0.15
_N_REQUESTS = 4

_NOTA_VENTA_PAYLOAD = {
    "id": 1,
    "guia_remision": "GR-CONC-1",
    "fecha_pedido": "2026-01-15T10:00:00Z",
    "cliente_nombre": "Cliente Concurrencia",
    "detalles": [
        {
            "producto_descripcion": "Hilo Nylon 40/1",
            "cantidad": 10.0,
            "piezas": 5,
            "peso": 50.0,
            "precio_unitario": 12.50,
            "incluye_iva": False,
        }
    ],
    "valor_retencion": 0.0,
}


def _slow_render(template_name, context, filename):
    # time.sleep, no asyncio.sleep — simula el trabajo CPU-bound síncrono
    # real de WeasyPrint dentro del hilo que le asigne run_in_threadpool.
    time.sleep(_DELAY_SECONDS)
    return Response(content=b"%PDF-1.4", media_type="application/pdf")


async def test_pdf_dado_peticiones_concurrentes_cuando_render_es_lento_entonces_no_se_serializan():
    mock_strategy = MagicMock()
    mock_strategy.render.side_effect = _slow_render
    app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            start = time.monotonic()
            for _ in range(_N_REQUESTS):
                resp = await client.post("/pdf/nota-venta", json=_NOTA_VENTA_PAYLOAD)
                assert resp.status_code == 200
            serial_elapsed = time.monotonic() - start

            start = time.monotonic()
            responses = await asyncio.gather(
                *[client.post("/pdf/nota-venta", json=_NOTA_VENTA_PAYLOAD) for _ in range(_N_REQUESTS)]
            )
            concurrent_elapsed = time.monotonic() - start
    finally:
        app.dependency_overrides.clear()

    assert all(r.status_code == 200 for r in responses)
    # Si el event loop estuviera bloqueado (sin run_in_threadpool),
    # concurrent_elapsed sería prácticamente igual a serial_elapsed. Con el
    # render delegado a un hilo, debe ser sustancialmente menor. Margen
    # generoso (60%) para absorber ruido del entorno de test.
    assert concurrent_elapsed < serial_elapsed * 0.6, (
        f"{_N_REQUESTS} peticiones PDF en paralelo tardaron {concurrent_elapsed:.3f}s, "
        f"casi lo mismo que en serie ({serial_elapsed:.3f}s) — sugiere que el "
        f"event loop se está bloqueando en vez de atenderlas concurrentemente."
    )
