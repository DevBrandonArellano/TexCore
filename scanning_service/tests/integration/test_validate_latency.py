"""
Test de latencia del endpoint /validate.

IMPORTANTE — qué mide y qué NO mide este test: usa TestClient (llamada
in-process, sin red real) con el DjangoApiClient mockeado, así que mide
únicamente el overhead propio de FastAPI + LoteValidationService: parseo
de request, validación Pydantic, invocación del servicio y serialización
de la respuesta. NO incluye el salto de red real a través de Nginx, ni la
latencia real de la llamada HTTP a Django (httpx.get en DjangoApiClient),
ni el circuit breaker.

Es un PISO de referencia (si esto ya no está bajo 1s, el sistema real
tampoco lo estará) — no el número que importa para UX real en planta.
La medición end-to-end bajo carga real vive en
scripts/loadtest/locustfile.py (tarea UsuarioDespachoTexCore.flujo_despacho),
que golpea /api/scanning/validate a través de Nginx exactamente como lo
hace DespachoDashboard.tsx.
"""
import time

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.main import app
from src.routers.validate import get_validation_service
from src.schemas.validate import LoteInfo, ValidateResponse

UMBRAL_SEGUNDOS = 1.0


@pytest.fixture
def client_lote_valido():
    mock_svc = MagicMock()
    mock_svc.validate.return_value = ValidateResponse(
        valid=True,
        lote=LoteInfo(
            codigo="LOTE-00001",
            producto_id=1,
            producto_nombre="Hilo Nylon",
            peso="25.00",
            bodega_id=10,
            bodega_nombre="Bodega Central",
        ),
    )
    app.dependency_overrides[get_validation_service] = lambda: mock_svc
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestValidateLatency:

    def test_validate_dado_peticion_valida_cuando_se_invoca_entonces_responde_bajo_1_segundo(
        self, client_lote_valido
    ):
        inicio = time.perf_counter()
        response = client_lote_valido.post("/validate", json={"code": "LOTE-00001"})
        duracion = time.perf_counter() - inicio

        assert response.status_code == 200
        assert duracion < UMBRAL_SEGUNDOS, (
            f"El endpoint /validate tardó {duracion:.3f}s en procesar la "
            f"petición (overhead interno del servicio, sin red) — supera "
            f"el umbral de negocio de {UMBRAL_SEGUNDOS}s."
        )

    def test_validate_dado_10_peticiones_consecutivas_cuando_se_invocan_entonces_promedio_bajo_1_segundo(
        self, client_lote_valido
    ):
        duraciones = []
        for _ in range(10):
            inicio = time.perf_counter()
            client_lote_valido.post("/validate", json={"code": "LOTE-00001"})
            duraciones.append(time.perf_counter() - inicio)

        promedio = sum(duraciones) / len(duraciones)
        assert promedio < UMBRAL_SEGUNDOS, (
            f"Promedio de 10 llamadas consecutivas a /validate: "
            f"{promedio:.3f}s — supera el umbral de {UMBRAL_SEGUNDOS}s."
        )
