"""
Regresión de concurrencia del microservicio completo.

El Dockerfile levanta reporting_excel con `uvicorn src.main:app` SIN
`--workers` (un solo proceso, un solo event loop). Antes del fix original,
cada `async def export_*` llamaba de forma síncrona a un cliente HTTP hacia
Django — código bloqueante ejecutado dentro de una corutina bloquea TODO el
event loop, así que mientras se generaba un reporte, el microservicio no
podía atender ninguna otra petición concurrente (ni siquiera /health).

Este test compara el tiempo de N peticiones lanzadas en SERIE contra las
mismas N peticiones lanzadas EN PARALELO (asyncio.gather), ambas contra la
app real (vía ASGITransport, sin levantar un servidor) mientras
ReportService.generate_from_rows() simula un formateo lento con
asyncio.sleep(). Comparar contra una línea base medida en el mismo proceso
(en vez de un umbral absoluto) evita falsos positivos por overhead fijo del
entorno de test. Si el event loop estuviera bloqueado, paralelo tardaría ~=
serie; con I/O verdaderamente async, paralelo debe ser sustancialmente
más rápido.
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch

from fastapi import Response
from httpx import ASGITransport, AsyncClient

from src.main import app

_DELAY_SECONDS = 0.2
_N_REQUESTS = 4


async def _slow_generate(self, rows, filename):
    await asyncio.sleep(_DELAY_SECONDS)
    return Response(content=b"fake", media_type="application/octet-stream")


async def test_export_dado_peticiones_concurrentes_cuando_formateo_es_lento_entonces_no_se_serializan():
    with patch(
        "src.services.report_service.ReportService.generate_from_rows",
        new=_slow_generate,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as client:
            body = {"format": "xlsx", "filename": "test", "report_type": "kardex", "rows": []}

            start = time.monotonic()
            for _ in range(_N_REQUESTS):
                resp = await client.post("/generate", json=body)
                assert resp.status_code == 200
            serial_elapsed = time.monotonic() - start

            start = time.monotonic()
            responses = await asyncio.gather(
                *[client.post("/generate", json=body) for _ in range(_N_REQUESTS)]
            )
            concurrent_elapsed = time.monotonic() - start

    assert all(r.status_code == 200 for r in responses)
    # Si el event loop estuviera bloqueado (bug original), concurrent_elapsed
    # sería prácticamente igual a serial_elapsed (~= N * delay en ambos
    # casos). Con I/O async real, concurrent_elapsed debe ser sustancialmente
    # menor. Margen generoso (60%) para absorber ruido del entorno de test.
    assert concurrent_elapsed < serial_elapsed * 0.6, (
        f"{_N_REQUESTS} peticiones en paralelo tardaron {concurrent_elapsed:.3f}s, "
        f"casi lo mismo que en serie ({serial_elapsed:.3f}s) — sugiere que el "
        f"event loop se está bloqueando en vez de atenderlas concurrentemente."
    )
