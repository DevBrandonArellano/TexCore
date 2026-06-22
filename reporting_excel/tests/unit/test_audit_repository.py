"""
Tests unitarios de AuditRepository — reporting_excel.
No requieren BD real: la session_factory se reemplaza con mocks.
ISTQB EP (Equivalence Partitioning) y BVA (Boundary Value Analysis).
Convención: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
ISO 27001 A.12.4: verificación de que el repositorio persiste eventos de auditoría de reportes.
COBIT MEA01: trazabilidad de acceso a información gerencial y ejecutiva.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.database.models import ReportAuditLog
from src.database.repository import AuditRepository, IAuditRepository, build_report_record


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_session_factory(commit_side_effect=None):
    """Crea una session_factory mock con comportamiento configurable."""
    session = AsyncMock()
    session.add = MagicMock()
    if commit_side_effect:
        session.commit.side_effect = commit_side_effect
    else:
        session.commit = AsyncMock()

    session_ctx = AsyncMock()
    session_ctx.__aenter__ = AsyncMock(return_value=session)
    session_ctx.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=session_ctx)
    return factory, session


def _make_report_record(
    requested_by: str = "user@example.com",
    report_type: str = "kardex",
    success: bool = True,
    params_json: str | None = None,
    error_detail: str | None = None,
) -> ReportAuditLog:
    return ReportAuditLog(
        requested_by=requested_by,
        report_type=report_type,
        endpoint=f"/api/export/{report_type}",
        params_json=params_json,
        format="xlsx",
        success=success,
        error_detail=error_detail,
    )


# ---------------------------------------------------------------------------
# EP Clase Válida: record con requested_by y report_type → persiste sin error
# ---------------------------------------------------------------------------

class TestAuditRepository_RegistroValido:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_record_valido_cuando_save_entonces_no_lanza_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_report_record())

    @pytest.mark.asyncio
    async def test_auditrepository_dado_record_valido_cuando_save_entonces_commit_es_llamado(self):
        factory, session = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_report_record())
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auditrepository_dado_record_valido_cuando_save_entonces_add_recibe_el_record(self):
        factory, session = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_report_record()
        await repo.save(record)
        session.add.assert_called_once_with(record)

    @pytest.mark.asyncio
    async def test_auditrepository_dado_reporte_fallido_cuando_save_entonces_persiste_sin_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_report_record(success=False, error_detail="SQL Server timeout")
        await repo.save(record)

    @pytest.mark.asyncio
    async def test_auditrepository_dado_reporte_gerencial_cuando_save_entonces_no_lanza_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_report_record(
            requested_by="gerente@interfibra.com",
            report_type="ventas_gerencial",
            params_json=json.dumps({"fecha_inicio": "2026-01-01", "sede_id": 1}),
        )
        await repo.save(record)


# ---------------------------------------------------------------------------
# EP Clase Inválida: DB falla → save() absorbe la excepción (ISO 27001 A.12.4)
# ---------------------------------------------------------------------------

class TestAuditRepository_FalloBaseDeDatos:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_commit_falla_cuando_save_entonces_no_propaga_excepcion(self):
        factory, _ = _make_session_factory(commit_side_effect=Exception("disk full"))
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_report_record())

    @pytest.mark.asyncio
    async def test_auditrepository_dado_db_no_disponible_cuando_save_entonces_loguea_warning_rfc5424(self, caplog):
        import logging
        factory, _ = _make_session_factory(commit_side_effect=Exception("connection refused"))
        repo = AuditRepository(session_factory=factory)
        with caplog.at_level(logging.WARNING, logger="src.database.repository"):
            await repo.save(_make_report_record())
        assert any("auditoría" in msg.lower() or "audit" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# LSP: mock intercambiable con AuditRepository (Protocol check)
# ---------------------------------------------------------------------------

class TestIAuditRepository_Protocolo:

    def test_auditrepository_dado_instancia_concreta_cuando_verificar_protocolo_entonces_cumple_interface(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        assert isinstance(repo, IAuditRepository)


# ---------------------------------------------------------------------------
# BVA: build_report_record — valores límite de campos opcionales
# ---------------------------------------------------------------------------

class TestBuildReportRecord_ValoresLimite:

    def test_buildreportrecord_dado_params_json_none_cuando_construir_entonces_acepta(self):
        """BVA: params_json es opcional — None es válido."""
        record = build_report_record(
            requested_by="admin@interfibra.com",
            report_type="usuarios",
            endpoint="/api/export/usuarios",
            success=True,
            params_json=None,
        )
        assert record.params_json is None

    def test_buildreportrecord_dado_requested_by_vacio_cuando_construir_entonces_acepta(self):
        """BVA: JWT sub puede ser 'unknown' cuando el middleware no identifica al usuario."""
        record = build_report_record(
            requested_by="unknown",
            report_type="kardex",
            endpoint="/api/export/kardex",
            success=False,
            error_detail="Unauthorized",
        )
        assert record.requested_by == "unknown"
        assert record.success is False

    def test_buildreportrecord_dado_todos_campos_opcionales_none_cuando_construir_entonces_acepta(self):
        """EP: formato y error_detail opcionales → None no rompe el modelo."""
        record = build_report_record(
            requested_by="user@test.com",
            report_type="productos",
            endpoint="/api/export/productos",
            success=True,
            params_json=None,
            format=None,
            error_detail=None,
        )
        assert record.format is None
        assert record.error_detail is None

    def test_buildreportrecord_dado_error_detail_cuando_construir_entonces_persiste_detalle(self):
        """EP: error_detail se incluye cuando el reporte falla."""
        detalle = "EXEC sp_GetKardexBodega: Invalid column name 'BodegaID'"
        record = build_report_record(
            requested_by="user@test.com",
            report_type="kardex",
            endpoint="/api/export/kardex",
            success=False,
            error_detail=detalle,
        )
        assert record.error_detail == detalle
