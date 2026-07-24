"""
Tests unitarios de AuditRepository — scanning_service.
No requieren BD real: la session_factory se reemplaza con mocks.
ISTQB EP (Equivalence Partitioning) y BVA (Boundary Value Analysis).
Convención: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
ISO 27001 A.12.4: verificación de que el repositorio persiste eventos de auditoría.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.database.models import ScanAuditLog
from src.database.repository import AuditRepository, IAuditRepository, build_scan_record


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


def _make_scan_record(
    codigo: str = "LOTE-00001",
    valid: bool = True,
    reason: str | None = None,
) -> ScanAuditLog:
    return ScanAuditLog(
        codigo_scanned=codigo,
        valid=valid,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# EP Clase Válida: record correcto → commit llamado, sin excepción
# ---------------------------------------------------------------------------

class TestAuditRepository_RegistroValido:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_record_valido_cuando_save_entonces_no_lanza_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_scan_record()
        await repo.save(record)  # no debe lanzar

    @pytest.mark.asyncio
    async def test_auditrepository_dado_record_valido_cuando_save_entonces_commit_es_llamado(self):
        factory, session = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_scan_record()
        await repo.save(record)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auditrepository_dado_record_valido_cuando_save_entonces_add_recibe_el_record(self):
        factory, session = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_scan_record()
        await repo.save(record)
        session.add.assert_called_once_with(record)

    @pytest.mark.asyncio
    async def test_auditrepository_dado_escaneo_invalido_cuando_save_entonces_persiste_sin_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_scan_record(valid=False, reason="Lote no encontrado")
        await repo.save(record)


# ---------------------------------------------------------------------------
# EP Clase Inválida: DB falla → save() absorbe la excepción (nunca propaga)
# ---------------------------------------------------------------------------

class TestAuditRepository_FalloBaseDeDatos:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_db_no_disponible_cuando_save_entonces_no_propaga_excepcion(self):
        factory, _ = _make_session_factory(commit_side_effect=Exception("DB error"))
        repo = AuditRepository(session_factory=factory)
        record = _make_scan_record()
        await repo.save(record)  # debe absorber silenciosamente

    @pytest.mark.asyncio
    async def test_auditrepository_dado_db_no_disponible_cuando_save_entonces_loguea_warning_rfc5424(self, caplog):
        import logging
        factory, _ = _make_session_factory(commit_side_effect=Exception("connection refused"))
        repo = AuditRepository(session_factory=factory)
        record = _make_scan_record()
        with caplog.at_level(logging.WARNING, logger="src.database.repository"):
            await repo.save(record)
        assert any("auditoría" in msg.lower() or "audit" in msg.lower() for msg in caplog.messages)


# ---------------------------------------------------------------------------
# LSP: mock es intercambiable con AuditRepository (Protocol check)
# ---------------------------------------------------------------------------

class TestIAuditRepository_Protocolo:

    def test_auditrepository_dado_instancia_concreta_cuando_verificar_protocolo_entonces_cumple_interface(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        assert isinstance(repo, IAuditRepository)


# ---------------------------------------------------------------------------
# BVA: build_scan_record — valores límite de campos
# ---------------------------------------------------------------------------

class TestBuildScanRecord_ValoresLimite:

    def test_buildscanrecord_dado_codigo_un_caracter_cuando_construir_entonces_acepta(self):
        """BVA: mínimo de longitud — 1 carácter."""
        response = MagicMock()
        response.valid = False
        response.reason = "Lote no encontrado"
        response.lote = None
        record = build_scan_record("X", response)
        assert record.codigo_scanned == "X"

    def test_buildscanrecord_dado_codigo_200_caracteres_cuando_construir_entonces_acepta(self):
        """BVA: límite máximo del campo VARCHAR(200)."""
        codigo_largo = "L" * 200
        response = MagicMock()
        response.valid = True
        response.reason = None
        lote = MagicMock()
        lote.codigo = codigo_largo
        lote.producto_id = 1
        lote.producto_nombre = "Producto"
        lote.bodega_id = 1
        lote.bodega_nombre = "Bodega"
        lote.peso = "50.0"
        response.lote = lote
        record = build_scan_record(codigo_largo, response)
        assert record.codigo_scanned == codigo_largo

    def test_buildscanrecord_dado_lote_none_cuando_construir_entonces_campos_opcionales_son_none(self):
        """EP: escaneo inválido sin lote → todos los campos de lote son None."""
        response = MagicMock()
        response.valid = False
        response.reason = "Código inválido"
        response.lote = None
        record = build_scan_record("INVALIDO", response)
        assert record.lote_codigo is None
        assert record.producto_id is None
        assert record.bodega_id is None
