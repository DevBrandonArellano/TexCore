"""
Tests unitarios de AuditRepository — printing_service.
No requieren BD real: la session_factory se reemplaza con mocks.
ISTQB EP (Equivalence Partitioning) y BVA (Boundary Value Analysis).
Convención: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
ISO 27001 A.12.4: verificación de que el repositorio persiste eventos de auditoría de impresión.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.database.models import PrintAuditLog
from src.database.repository import AuditRepository, IAuditRepository, build_print_record


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


def _make_pdf_record(
    success: bool = True,
    pedido_id: int = 42,
    error_detail: str | None = None,
) -> PrintAuditLog:
    return PrintAuditLog(
        document_type="PDF",
        template_used="nota_venta.html",
        pedido_id=pedido_id,
        guia_remision="GR-001",
        lote_codigo=None,
        success=success,
        error_detail=error_detail,
    )


def _make_zpl_record(
    success: bool = True,
    lote_codigo: str = "LOTE-00099",
    error_detail: str | None = None,
) -> PrintAuditLog:
    return PrintAuditLog(
        document_type="ZPL",
        template_used="etiqueta.zpl",
        pedido_id=None,
        guia_remision=None,
        lote_codigo=lote_codigo,
        success=success,
        error_detail=error_detail,
    )


# ---------------------------------------------------------------------------
# EP Clase Válida: PDF exitoso → commit llamado, sin excepción
# ---------------------------------------------------------------------------

class TestAuditRepository_RegistroPdfValido:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_pdf_exitoso_cuando_save_entonces_no_lanza_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_pdf_record())

    @pytest.mark.asyncio
    async def test_auditrepository_dado_pdf_exitoso_cuando_save_entonces_commit_es_llamado(self):
        factory, session = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_pdf_record())
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_auditrepository_dado_pdf_fallido_cuando_save_entonces_persiste_sin_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_pdf_record(success=False, error_detail="WeasyPrint timeout"))


# ---------------------------------------------------------------------------
# EP Clase Válida: ZPL exitoso → commit llamado, sin excepción
# ---------------------------------------------------------------------------

class TestAuditRepository_RegistroZplValido:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_zpl_exitoso_cuando_save_entonces_no_lanza_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_zpl_record())

    @pytest.mark.asyncio
    async def test_auditrepository_dado_zpl_exitoso_cuando_save_entonces_add_recibe_el_record(self):
        factory, session = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        record = _make_zpl_record()
        await repo.save(record)
        session.add.assert_called_once_with(record)

    @pytest.mark.asyncio
    async def test_auditrepository_dado_zpl_fallido_cuando_save_entonces_persiste_sin_excepcion(self):
        factory, _ = _make_session_factory()
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_zpl_record(success=False, error_detail="Template no encontrado"))


# ---------------------------------------------------------------------------
# EP Clase Inválida: DB falla → save() absorbe la excepción
# ---------------------------------------------------------------------------

class TestAuditRepository_FalloBaseDeDatos:

    @pytest.mark.asyncio
    async def test_auditrepository_dado_db_no_disponible_cuando_save_pdf_entonces_no_propaga_excepcion(self):
        factory, _ = _make_session_factory(commit_side_effect=Exception("DB locked"))
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_pdf_record())

    @pytest.mark.asyncio
    async def test_auditrepository_dado_db_no_disponible_cuando_save_zpl_entonces_no_propaga_excepcion(self):
        factory, _ = _make_session_factory(commit_side_effect=Exception("no such table"))
        repo = AuditRepository(session_factory=factory)
        await repo.save(_make_zpl_record())

    @pytest.mark.asyncio
    async def test_auditrepository_dado_db_no_disponible_cuando_save_entonces_loguea_warning_rfc5424(self, caplog):
        import logging
        factory, _ = _make_session_factory(commit_side_effect=Exception("connection refused"))
        repo = AuditRepository(session_factory=factory)
        with caplog.at_level(logging.WARNING, logger="src.database.repository"):
            await repo.save(_make_pdf_record())
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
# BVA: build_print_record — valores límite
# ---------------------------------------------------------------------------

class TestBuildPrintRecord_ValoresLimite:

    def test_buildprintrecord_dado_pdf_sin_pedido_id_cuando_construir_entonces_acepta_none(self):
        """BVA: pedido_id opcional — None es válido para ZPL."""
        record = build_print_record(
            document_type="ZPL",
            template_used="etiqueta.zpl",
            success=True,
            pedido_id=None,
            lote_codigo="LOTE-99999",
        )
        assert record.pedido_id is None
        assert record.lote_codigo == "LOTE-99999"

    def test_buildprintrecord_dado_error_detail_none_cuando_construir_entonces_acepta(self):
        """EP: éxito sin error_detail → campo es None."""
        record = build_print_record(
            document_type="PDF",
            template_used="nota_venta.html",
            success=True,
        )
        assert record.error_detail is None
        assert record.success is True

    def test_buildprintrecord_dado_document_type_zpl_cuando_construir_entonces_type_es_zpl(self):
        """EP: document_type discrimina PDF vs ZPL correctamente."""
        record = build_print_record(
            document_type="ZPL",
            template_used="etiqueta.zpl",
            success=True,
        )
        assert record.document_type == "ZPL"
