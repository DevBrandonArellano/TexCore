"""
Regresión de concurrencia del microservicio completo.

El Dockerfile levanta reporting_excel con `uvicorn src.main:app` SIN
`--workers` (un solo proceso, un solo event loop). Antes del fix, cada
`async def export_*` llamaba de forma síncrona a DjangoReportRepository
.execute_sp() (httpx.get) y a JWTTokenManager (httpx.post) — código
bloqueante ejecutado dentro de una corutina bloquea TODO el event loop,
así que mientras se generaba un reporte, el microservicio no podía
atender ninguna otra petición concurrente (ni siquiera /health).

Este test compara el tiempo de N peticiones lanzadas en SERIE contra las
mismas N peticiones lanzadas EN PARALELO (asyncio.gather), ambas contra
la app real (vía ASGITransport, sin levantar un servidor) mientras
DjangoReportRepository.execute_sp() simula una consulta lenta con
asyncio.sleep(). Comparar contra una línea base medida en el mismo
proceso (en vez de un umbral absoluto) evita falsos positivos por
overhead fijo del entorno de test (ej. el intento fallido de abrir el
SQLite de auditoría en /data, que no existe en Windows). Si el event
loop estuviera bloqueado, paralelo tardaría ~= serie; con I/O
verdaderamente async, paralelo debe ser sustancialmente más rápido.
"""
import asyncio
import time
from unittest.mock import AsyncMock, patch

import pandas as pd
from httpx import ASGITransport, AsyncClient

from src.main import app

_DELAY_SECONDS = 0.2
_N_REQUESTS = 4


async def _slow_execute_sp(sp_query, params):
    # patch() reemplaza execute_sp a nivel de clase con un Mock, que no
    # implementa el protocolo descriptor — self._repo.execute_sp(sp_query,
    # params) invoca el mock SIN bindear `self` automáticamente.
    await asyncio.sleep(_DELAY_SECONDS)
    return pd.DataFrame({"col": [1]})


async def test_export_dado_peticiones_concurrentes_cuando_backend_es_lento_entonces_no_se_serializan():
    with patch(
        "src.infrastructure.django_client.DjangoReportRepository.execute_sp",
        new=AsyncMock(side_effect=_slow_execute_sp),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": "Bearer test-token"},
        ) as client:
            start = time.monotonic()
            for _ in range(_N_REQUESTS):
                resp = await client.get("/export/productos?format=xlsx")
                assert resp.status_code == 200
            serial_elapsed = time.monotonic() - start

            start = time.monotonic()
            responses = await asyncio.gather(
                *[client.get("/export/productos?format=xlsx") for _ in range(_N_REQUESTS)]
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
