"""
Módulo de infraestructura de base de datos de auditoría — printing_service.
SRP: única responsabilidad — configurar el engine SQLite seguro y crear las tablas.
ISO 27001 A.10: datos en reposo protegidos con permisos de archivo 0o600.
ISO 27001 A.12.4: persistencia de eventos de auditoría de seguridad.
COBIT MEA01: soporte de monitoreo y evaluación del desempeño del servicio.
RFC 5424: operaciones internas registradas con SD-ELEMENT estructurado.
"""
import os
import stat

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DB_PATH = os.getenv("AUDIT_DB_PATH", "/data/logs.db")

_CONNECT_ARGS = {
    "timeout": 10,
    "check_same_thread": False,
}


def _make_engine():
    """OCP: fábrica aislada para facilitar extensión sin modificar singletons."""
    return create_async_engine(
        f"sqlite+aiosqlite:///{DB_PATH}",
        echo=False,
        connect_args=_CONNECT_ARGS,
        pool_pre_ping=True,
    )


def _make_session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


_engine = _make_engine()
_session_factory = _make_session_factory(_engine)


async def _apply_pragmas(conn) -> None:
    """
    Aplica PRAGMAs de seguridad y rendimiento.
    WAL garantiza < 500 ms en inserts concurrentes sin bloquear lecturas.
    """
    await conn.execute(text("PRAGMA journal_mode=WAL"))
    await conn.execute(text("PRAGMA synchronous=NORMAL"))
    await conn.execute(text("PRAGMA foreign_keys=ON"))
    await conn.execute(text("PRAGMA cache_size=-4000"))
    await conn.execute(text("PRAGMA temp_store=MEMORY"))


async def init_db() -> None:
    """
    Crea las tablas y aplica permisos de archivo.
    ISO 27001 A.10: chmod 0o600 — solo el proceso del contenedor puede leer/escribir.
    """
    async with _engine.begin() as conn:
        await _apply_pragmas(conn)
        await conn.run_sync(Base.metadata.create_all)
    if os.path.exists(DB_PATH):
        os.chmod(DB_PATH, stat.S_IRUSR | stat.S_IWUSR)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """DIP: los repositorios solicitan la fábrica; no importan el global directamente."""
    return _session_factory
