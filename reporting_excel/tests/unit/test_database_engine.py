"""
Pruebas de src/database/engine.py — init_db, _apply_pragmas, get_session_factory.

Técnicas ISTQB aplicadas:
- Caja blanca: PRAGMAs aplicados, creación de tablas, permisos de archivo
  0o600 tras init_db(), y la fábrica de sesiones retornada por
  get_session_factory().
"""
import os
import stat

import pytest
from sqlalchemy import text

from src.database import engine as engine_module
from src.database.engine import _apply_pragmas, _make_engine, _make_session_factory, get_session_factory


@pytest.mark.asyncio
async def test_apply_pragmas_dado_conexion_cuando_aplica_entonces_ejecuta_los_5_pragmas(tmp_path):
    db_path = tmp_path / "test_pragmas.db"
    engine = engine_module.create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    try:
        async with engine.begin() as conn:
            await _apply_pragmas(conn)
            result = await conn.execute(text("PRAGMA journal_mode"))
            journal_mode = result.scalar()
        assert journal_mode.lower() == "wal"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_init_db_dado_path_temporal_cuando_ejecuta_entonces_crea_archivo_con_permisos_0600(
    tmp_path, monkeypatch,
):
    db_path = tmp_path / "audit_test.db"
    monkeypatch.setattr(engine_module, "DB_PATH", str(db_path))
    test_engine = engine_module.create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setattr(engine_module, "_engine", test_engine)

    try:
        await engine_module.init_db()

        assert os.path.exists(db_path)
        mode = stat.S_IMODE(os.stat(db_path).st_mode)
        assert mode == (stat.S_IRUSR | stat.S_IWUSR)
    finally:
        await test_engine.dispose()


def test_get_session_factory_cuando_llama_entonces_retorna_la_fabrica_del_modulo():
    factory = get_session_factory()
    assert factory is engine_module._session_factory


def test_make_session_factory_dado_engine_cuando_crea_entonces_expire_on_commit_false():
    engine = _make_engine()
    factory = _make_session_factory(engine)
    assert factory.kw.get("expire_on_commit") is False
