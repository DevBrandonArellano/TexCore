"""
Errores de POST /generate: el 500 no expone el detalle interno (CWE-209), pero la
auditoría sí lo registra. Mismo criterio que printing_service (5-oct-2026).
"""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app, headers={"Authorization": "Bearer test-token"})

_BODY = {"format": "xlsx", "filename": "r", "report_type": "kardex", "rows": [{"a": 1}]}


def test_generate_dado_fallo_interno_cuando_post_entonces_500_sin_detalle_interno():
    with patch(
        "src.routers.generate.ReportFactory.create",
        side_effect=RuntimeError("ruta /secreta/plantilla.xlsx no encontrada"),
    ):
        resp = client.post("/generate", json=_BODY)

    assert resp.status_code == 500
    assert resp.json() == {"detail": "Error interno al generar el reporte."}
    assert "secreta" not in resp.text


def test_generate_dado_fallo_interno_cuando_post_entonces_auditoria_registra_el_detalle():
    servicio = AsyncMock()
    servicio.generate_from_rows.side_effect = ValueError("columna rota")
    with patch("src.routers.generate.ReportFactory.create", return_value=servicio), \
         patch("src.routers.generate.build_report_record") as build:
        build.return_value = object()
        with patch("src.routers.generate.AuditRepository.save", new=AsyncMock()):
            resp = client.post("/generate", json=_BODY)

    assert resp.status_code == 500
    kwargs = build.call_args.kwargs
    assert kwargs["success"] is False
    assert kwargs["error_detail"] == "columna rota"
    assert kwargs["report_type"] == "kardex"
