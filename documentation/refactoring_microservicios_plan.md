# Plan de Implementacion: Refactorizacion de Microservicios TexCore

> **Fecha:** 2026-04-21  
> **Autor:** Claude Code (claude-sonnet-4-6)  
> **Estado:** Listo para implementacion  
> **Alcance:** scanning_service · printing_service · reporting_excel  
> **Siguiente fase:** Backend Django principal (gestion/ + inventory/)  
>
> Este documento es autocontenido. Un desarrollador sin contexto previo puede
> ejecutar el plan siguiendo la **Secuencia de Ejecucion (Sección 5)** en orden.

---

## Indice rapido

1. Diagnostico: Malas practicas actuales
2. scanning_service - Refactorizacion completa
3. printing_service - Refactorizacion completa
4. reporting_excel - Refactorizacion completa
5. Secuencia de ejecucion y dependencias
6. Actualizaciones al CI/CD

---

## 1. DIAGNOSTICO DE MALAS PRACTICAS ACTUALES

### scanning_service

| Problema | Principio violado | Evidencia en codigo |
|---|---|---|
| `SessionLocal()` instanciado directamente dentro del endpoint en lugar de usar `Depends(get_db)` | DIP | `main.py:119 db = SessionLocal()` - la funcion `get_db` existe en `database.py` pero no se usa en el endpoint |
| Schemas Pydantic (request/response), logica de dominio y acceso a BD coexisten en `main.py` | SRP | `main.py:64-78` define modelos, `main.py:110-174` hace queries y logica de negocio en el mismo lugar |
| `StockBodega` tiene `producto_id` Y `lote_id`: `producto_id` es transitivamente dependiente de `lote_id` (el lote ya tiene su `orden_produccion` que tiene `producto_id`) | 3FN violada | `models.py:38-48` - la query actual en `main.py` ignora `StockBodega.producto_id` y usa `lote.orden_produccion.producto` |
| `Bodega.sede_id` es un Integer sin ForeignKey declarada, la tabla `Sede` no existe en los modelos del microservicio | Dependencia transitiva no modelada | `models.py:16-18` |
| No existe interfaz/protocolo para el repositorio, imposible intercambiar real vs mock sin parchar `sys.modules` | LSP, OCP | `tests/conftest.py:1-64` usa `sys.modules` hack porque no hay abstraccion inyectable |
| El `health` endpoint llama directamente `SessionLocal()` en lugar de usar DI | DIP | `main.py:101-107` |

### printing_service

| Problema | Principio violado | Evidencia |
|---|---|---|
| Los calculos de negocio (`subtotal`, `iva`, `total`) estan como `@property` de `NotaVentaRequest` (el schema de entrada HTTP) | SRP | `main.py:40-50` - el schema de request no deberia contener logica de negocio |
| La logica de formateo de fecha (`datetime.fromisoformat`, `strftime`) vive en el endpoint HTTP | SRP | `main.py:77-80` |
| El path de templates es relativo (`"templates"`), dependiente del cwd en ejecucion | Fragilidad operacional | `main.py:14` |
| No hay abstraccion entre "generar contenido" (Jinja2 render) y "producir output" (WeasyPrint/ZPL), la estrategia de salida esta hardcodeada | OCP | `main.py:72-110` - agregar un nuevo formato (PNG, HTML raw) requiere modificar el endpoint existente |
| Un solo schema `NotaVentaRequest` sirve como DTO de entrada Y como portador de logica de calculo | ISP | `main.py:27-50` |

### reporting_excel

| Problema | Principio violado | Evidencia |
|---|---|---|
| `generate_download_response` es una funcion utilitaria en `exports.py` que es importada por `vendedores.py`, `gerencial.py` y `produccion.py` - acoplamiento cruzado entre routers | SRP | `vendedores.py:8 from src.routers.exports import generate_download_response` |
| `execute_sp_to_dataframe` en `database.py` abre la conexion, ejecuta el SP, aplica el converter de fechas y retorna el DataFrame - son tres responsabilidades distintas | SRP | `database.py:44-72` |
| No existe capa de servicio: los routers llaman directamente a `database.py`, mezclando transporte HTTP con acceso a datos | SRP | Cada router importa `execute_sp_to_dataframe` directamente |
| El formato de salida (`csv` vs `xlsx`) se ramifica con un `if` en `generate_download_response` en lugar de usar Strategy | OCP | `exports.py:22-41` - agregar PDF requiere modificar esta funcion |
| `test_usuarios_export_empty` afirma `status_code == 404` con body `{"detail": "No se encontraron datos..."}` pero el codigo actual en `exports.py` retorna 200 con archivo vacio ("No se encontraron datos" como fila del Excel) - el test y la implementacion estan desincronizados | Deuda tecnica documentada | `test_exports.py:58-65` vs `exports.py:13-20` |
| `dataframe_to_excel_bytes` en `excel_generator.py` hace: preparacion del DataFrame + escritura Excel + formateo de encabezados + ajuste de anchos de columna | SRP | `excel_generator.py:47-86` |

---

## 2. SCANNING_SERVICE: PLAN DE REFACTORIZACION

### Estructura objetivo

```
scanning_service/
  src/
    __init__.py
    database.py          (sin cambios)
    logging_rfc5424.py   (sin cambios)
    models.py            (anadir FK de Sede, quitar producto_id de StockBodega)
    schemas/
      __init__.py
      validate.py        (ValidateRequest, LoteInfo, ValidateResponse)
    repositories/
      __init__.py
      base.py            (Protocol: ILoteRepository)
      lote_repository.py (implementacion SQLAlchemy)
    services/
      __init__.py
      validation_service.py (logica de negocio pura)
    routers/
      __init__.py
      validate.py        (endpoint /validate con Depends)
      health.py          (endpoint /health con Depends)
    main.py              (solo app factory + include_router)
  tests/
    conftest.py          (simplificado con fixture de repositorio mock)
    __init__.py
    unit/
      __init__.py
      test_validation_service.py
      test_lote_repository.py
    integration/
      __init__.py
      test_validate_endpoint.py
      test_health_endpoint.py
```

### Paso 2.1 - Normalizar modelos (models.py)

**Archivo:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/models.py`

**Cambios:**

Agregar la clase `Sede` (la tabla existe en SQL Server porque `Bodega.sede_id` apunta a ella). Agregar FK explicitamente en `Bodega`. Mantener `StockBodega.producto_id` por compatibilidad con el esquema existente de SQL Server (es la BD de produccion - no se puede alterar el esquema fisico desde el microservicio), pero documentar con comentario que es transitivamente dependiente de `lote_id -> orden_produccion_id -> producto_id`. La FK queda como informativa en el ORM.

Contenido completo del archivo resultante:

```python
"""
Modelos SQLAlchemy que mapean las tablas de SQL Server compartidas con el backend Django.

NOTA DE NORMALIZACION:
  - StockBodega.producto_id es transitivamente dependiente de lote_id:
      lote_id → orden_produccion_id → producto_id
    Se mantiene porque el esquema fisico de SQL Server lo incluye (generado por Django).
    La logica de negocio DEBE obtener el producto via lote.orden_produccion.producto,
    no via StockBodega.producto (ignorar ese campo en queries).
  - Bodega.sede_id referencia gestion_sede. Se declara FK aqui para que
    SQLAlchemy pueda hacer joins sin error. La tabla no se crea desde este servicio.
"""
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from .database import Base


class Sede(Base):
    __tablename__ = "gestion_sede"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)


class Producto(Base):
    __tablename__ = "gestion_producto"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String)
    descripcion = Column(String)
    stock_minimo = Column(Float)
    precio_base = Column(Float)


class Bodega(Base):
    __tablename__ = "gestion_bodega"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    sede_id = Column(Integer, ForeignKey("gestion_sede.id"), nullable=True)

    sede = relationship("Sede")


class OrdenProduccion(Base):
    __tablename__ = "gestion_ordenproduccion"
    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String)
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))
    peso_neto_requerido = Column(Numeric(10, 2))
    estado = Column(String)

    producto = relationship("Producto")


class LoteProduccion(Base):
    __tablename__ = "gestion_loteproduccion"
    id = Column(Integer, primary_key=True, index=True)
    codigo_lote = Column(String, unique=True, index=True)
    peso_neto_producido = Column(Numeric(10, 2))
    orden_produccion_id = Column(Integer, ForeignKey("gestion_ordenproduccion.id"))

    orden_produccion = relationship("OrdenProduccion")


class StockBodega(Base):
    __tablename__ = "inventory_stockbodega"
    id = Column(Integer, primary_key=True, index=True)
    cantidad = Column(Numeric(12, 2))
    bodega_id = Column(Integer, ForeignKey("gestion_bodega.id"))
    # producto_id: transitivamente dependiente (lote -> orden -> producto).
    # Se conserva por compatibilidad con el esquema de SQL Server.
    # NO usar en logica de negocio: usar lote.orden_produccion.producto en su lugar.
    producto_id = Column(Integer, ForeignKey("gestion_producto.id"))
    lote_id = Column(Integer, ForeignKey("gestion_loteproduccion.id"))

    bodega = relationship("Bodega")
    lote = relationship("LoteProduccion")
    # Relacion producto omitida intencionalmente para evitar uso accidental.
```

### Paso 2.2 - Crear schemas/validate.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/schemas/validate.py`

Contenido:

```python
"""
Schemas Pydantic especificos para el caso de uso de validacion de lotes.
Separados del modelo de dominio (SRP) y del acceso a datos (DIP).
Aplica ISP: un schema por caso de uso, no un schema "para todo".
"""
from pydantic import BaseModel, field_validator
from typing import Optional


class ValidateRequest(BaseModel):
    """Request de validacion. 'code' es el codigo escaneado (QR o barras)."""
    code: str

    @field_validator("code")
    @classmethod
    def code_no_vacio(cls, v: str) -> str:
        """BVA: rechazar string de solo espacios."""
        if not v.strip():
            raise ValueError("El codigo no puede estar vacio")
        return v.strip()


class LoteInfo(BaseModel):
    """Informacion del lote retornada cuando la validacion es exitosa."""
    codigo: str
    producto_id: int
    producto_nombre: str
    peso: str
    bodega_id: int
    bodega_nombre: str


class ValidateResponse(BaseModel):
    """Respuesta del endpoint /validate."""
    valid: bool
    lote: Optional[LoteInfo] = None
    reason: Optional[str] = None
```

**Tambien crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/schemas/__init__.py` (vacio)

### Paso 2.3 - Crear repositories/base.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/repositories/base.py`

Contenido:

```python
"""
Protocolo (interfaz) del repositorio de lotes.
Aplicando LSP y DIP: cualquier implementacion (SQL Server real, SQLite de test,
mock en memoria) es intercambiable en los servicios que dependan de ILoteRepository.
"""
from typing import Optional, Protocol, runtime_checkable
from ..models import LoteProduccion, StockBodega


@runtime_checkable
class ILoteRepository(Protocol):
    """Contrato de acceso a datos para lotes de produccion."""

    def get_lote_by_codigo(self, codigo: str) -> Optional[LoteProduccion]:
        """Retorna el LoteProduccion con sus relaciones cargadas, o None."""
        ...

    def get_stock_activo_por_lote(self, lote_id: int) -> Optional[StockBodega]:
        """Retorna el primer StockBodega con cantidad > 0 para el lote, o None."""
        ...
```

**Tambien crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/repositories/__init__.py` (vacio)

### Paso 2.4 - Crear repositories/lote_repository.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/repositories/lote_repository.py`

Contenido:

```python
"""
Implementacion SQLAlchemy del repositorio de lotes.
Responsabilidad unica: traducir operaciones de dominio a queries SQL (SRP).
La sesion se inyecta por constructor (DIP).
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session, joinedload

from ..models import LoteProduccion, StockBodega
from .base import ILoteRepository

logger = logging.getLogger(__name__)


class SqlLoteRepository:
    """
    Repositorio concreto que consulta SQL Server via SQLAlchemy.
    Implementa ILoteRepository (compatible por duck typing con el Protocol).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_lote_by_codigo(self, codigo: str) -> Optional[LoteProduccion]:
        """
        Carga el lote con eager loading de orden_produccion y producto
        para evitar N+1 queries en la capa de servicio.
        """
        return (
            self._db.query(LoteProduccion)
            .options(
                joinedload(LoteProduccion.orden_produccion)
                .joinedload(LoteProduccion.orden_produccion.property.mapper.class_.producto)
            )
            .filter(LoteProduccion.codigo_lote == codigo)
            .first()
        )

    def get_stock_activo_por_lote(self, lote_id: int) -> Optional[StockBodega]:
        """
        Retorna stock con bodega cargada (eager) para evitar lazy load
        despues de que la sesion se cierra.
        """
        return (
            self._db.query(StockBodega)
            .options(joinedload(StockBodega.bodega))
            .filter(
                StockBodega.lote_id == lote_id,
                StockBodega.cantidad > 0,
            )
            .first()
        )
```

**Nota de implementacion sobre el joinedload anidado:** El patron `joinedload(LoteProduccion.orden_produccion).joinedload(OrdenProduccion.producto)` es el correcto en SQLAlchemy 2.x. Reemplazar la segunda parte por `joinedload(LoteProduccion.orden_produccion).joinedload("producto")` si hay problemas con la referencia de clase. Importar `OrdenProduccion` en el archivo para claridad.

### Paso 2.5 - Crear services/validation_service.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/services/validation_service.py`

Contenido:

```python
"""
Servicio de validacion de lotes.
Contiene TODA la logica de negocio del dominio de despacho (SRP).
No conoce HTTP, no conoce SQLAlchemy directamente: depende de ILoteRepository (DIP).
"""
import logging
from dataclasses import dataclass
from typing import Optional

from ..repositories.base import ILoteRepository
from ..schemas.validate import LoteInfo, ValidateResponse

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Resultado interno del servicio antes de convertir al schema HTTP."""
    valid: bool
    lote_info: Optional[LoteInfo] = None
    reason: Optional[str] = None


class LoteValidationService:
    """
    Encapsula las reglas de negocio para validar si un lote puede ser despachado:
      1. El lote debe existir en el sistema.
      2. El lote debe tener una orden de produccion con producto asociado.
      3. El lote debe tener stock disponible (cantidad > 0) en alguna bodega.
    """

    def __init__(self, repository: ILoteRepository) -> None:
        """
        Args:
            repository: Implementacion de ILoteRepository. Puede ser la real
                        (SqlLoteRepository) o un mock para tests (DIP/LSP).
        """
        self._repo = repository

    def validate(self, codigo: str) -> ValidateResponse:
        """
        Valida un codigo de lote escaneado.

        Args:
            codigo: El codigo crudo del lote (ya limpio/stripped por el schema).

        Returns:
            ValidateResponse con valid=True y datos del lote, o valid=False y razon.
        """
        logger.info("Iniciando validacion de lote", extra={"sd": {"code": codigo[:8]}})

        lote = self._repo.get_lote_by_codigo(codigo)
        if lote is None:
            logger.warning("Lote no encontrado", extra={"sd": {"code": codigo[:8]}})
            return ValidateResponse(valid=False, reason="Lote no encontrado en el sistema")

        if not lote.orden_produccion or not lote.orden_produccion.producto:
            logger.warning("Lote sin orden o producto", extra={"sd": {"lote_id": lote.id}})
            return ValidateResponse(
                valid=False,
                reason="Lote no tiene orden de produccion o producto asociado",
            )

        stock = self._repo.get_stock_activo_por_lote(lote.id)
        if stock is None:
            logger.warning("Lote sin stock", extra={"sd": {"lote_id": lote.id}})
            return ValidateResponse(
                valid=False,
                reason="Lote existe pero no tiene stock disponible (0 kg)",
            )

        producto = lote.orden_produccion.producto
        bodega = stock.bodega

        logger.info(
            "Validacion exitosa",
            extra={"sd": {"valid": "true", "producto_id": producto.id, "bodega_id": bodega.id}},
        )
        return ValidateResponse(
            valid=True,
            lote=LoteInfo(
                codigo=lote.codigo_lote,
                producto_id=producto.id,
                producto_nombre=producto.descripcion,
                peso=str(stock.cantidad),
                bodega_id=bodega.id,
                bodega_nombre=bodega.nombre,
            ),
        )
```

**Tambien crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/services/__init__.py` (vacio)

### Paso 2.6 - Crear routers/validate.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/routers/validate.py`

Contenido:

```python
"""
Router HTTP para validacion de lotes.
Responsabilidad unica: traducir HTTP a llamadas de servicio y viceversa (SRP).
Toda la logica de negocio esta en LoteValidationService.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..repositories.lote_repository import SqlLoteRepository
from ..services.validation_service import LoteValidationService
from ..schemas.validate import ValidateRequest, ValidateResponse

router = APIRouter()


def get_validation_service(db: Session = Depends(get_db)) -> LoteValidationService:
    """
    Factory de dependencia: construye el grafo de objetos.
    Permite sobrescribir en tests via app.dependency_overrides.
    """
    repo = SqlLoteRepository(db)
    return LoteValidationService(repo)


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validar codigo de lote escaneado",
    description=(
        "Verifica que el codigo exista, tenga orden de produccion y producto, "
        "y que haya stock disponible (cantidad > 0) en alguna bodega."
    ),
)
def validate_lote(
    request: ValidateRequest,
    service: LoteValidationService = Depends(get_validation_service),
) -> ValidateResponse:
    """
    Valida un codigo de lote escaneado (QR o codigo de barras).

    - **code**: Codigo del lote tal como fue leido por el scanner.
    """
    return service.validate(request.code)
```

### Paso 2.7 - Crear routers/health.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/routers/health.py`

Contenido:

```python
"""
Router de health check con DI correcta.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter()


@router.get("/health", summary="Health check del servicio y la conexion a BD")
def health_check(db: Session = Depends(get_db)):
    """Verifica conectividad con SQL Server. Retorna 503 si la BD no responde."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {exc}",
        )
```

**Tambien crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/routers/__init__.py` (vacio)

### Paso 2.8 - Reescribir main.py

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/main.py`

El archivo queda reducido a app factory pura. Contenido nuevo:

```python
"""
App factory del scanning_service.
Responsabilidad unica: crear la aplicacion FastAPI y registrar los routers.
La configuracion de logging se mantiene aqui por ser infraestructura transversal.
"""
import logging
import logging.handlers
import os
import time

from fastapi import FastAPI, Request

from .logging_rfc5424 import RFC5424Formatter
from .routers import validate as validate_router
from .routers import health as health_router


def _setup_logging() -> None:
    formatter = RFC5424Formatter(facility=18, app_name="texcore-scanning")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handlers = [handler]
    if os.path.exists("/dev/log"):
        syslog_h = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_h.setFormatter(formatter)
        handlers.append(syslog_h)
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=handlers)


_setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TexCore Scanning Service",
    description="Microservicio de validacion de codigos de barras/QR para despachos",
    version="2.0.0",
)


@app.middleware("http")
async def log_requests_rfc5424(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code if response else 500
        request_logger = logging.getLogger("http-request")
        sd = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
        }
        level = logging.ERROR if status_code >= 500 else (logging.WARNING if status_code >= 400 else logging.INFO)
        request_logger.log(level, f"{request.method} {request.url.path} {status_code}", extra={"sd": sd})


@app.get("/", include_in_schema=False)
def read_root():
    return {"service": "TexCore Scanning Service", "status": "running", "version": "2.0.0"}


app.include_router(health_router.router)
app.include_router(validate_router.router)
```

### Paso 2.9 - Tests unitarios del servicio

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/tests/unit/test_validation_service.py`

Contenido (extracto de estructura - el implementador llena los casos):

```python
"""
Tests unitarios de LoteValidationService.
NO requieren BD, HTTP ni FastAPI. Solo dependen del Protocol ILoteRepository.
Convencion ISTQB: test_[objeto]_dado_[contexto]_cuando_[accion]_entonces_[resultado]
"""
import pytest
from unittest.mock import MagicMock

from src.services.validation_service import LoteValidationService
from src.schemas.validate import ValidateResponse


def _make_producto(id=1, descripcion="Hilo Nylon"):
    p = MagicMock()
    p.id = id
    p.descripcion = descripcion
    return p


def _make_bodega(id=10, nombre="Bodega Central"):
    b = MagicMock()
    b.id = id
    b.nombre = nombre
    return b


def _make_orden(producto=None):
    o = MagicMock()
    o.producto = producto or _make_producto()
    return o


def _make_lote(codigo="LOTE-00001", orden=None):
    lote = MagicMock()
    lote.id = 1
    lote.codigo_lote = codigo
    lote.orden_produccion = orden or _make_orden()
    return lote


def _make_stock(cantidad=50, bodega=None):
    s = MagicMock()
    s.cantidad = cantidad
    s.bodega = bodega or _make_bodega()
    return s


def _make_repo(lote=None, stock=None):
    """Construye un mock de ILoteRepository con respuestas configurables."""
    repo = MagicMock()
    repo.get_lote_by_codigo.return_value = lote
    repo.get_stock_activo_por_lote.return_value = stock
    return repo


class TestLoteValidationService_LoteNoEncontrado:
    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_retorna_invalido(self):
        repo = _make_repo(lote=None)
        service = LoteValidationService(repo)
        result = service.validate("LOTE-INEXISTENTE")
        assert result.valid is False
        assert "no encontrado" in result.reason.lower()

    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_consulta_repositorio(self):
        repo = _make_repo(lote=None)
        service = LoteValidationService(repo)
        service.validate("LOTE-ABC")
        repo.get_lote_by_codigo.assert_called_once_with("LOTE-ABC")


class TestLoteValidationService_LoteSinOrden:
    def test_validate_dado_lote_sin_orden_cuando_validar_entonces_retorna_invalido(self):
        lote = _make_lote()
        lote.orden_produccion = None
        repo = _make_repo(lote=lote)
        service = LoteValidationService(repo)
        result = service.validate("LOTE-00001")
        assert result.valid is False
        assert result.reason is not None

    def test_validate_dado_lote_sin_producto_en_orden_cuando_validar_entonces_retorna_invalido(self):
        orden = _make_orden()
        orden.producto = None
        lote = _make_lote(orden=orden)
        repo = _make_repo(lote=lote)
        service = LoteValidationService(repo)
        result = service.validate("LOTE-00001")
        assert result.valid is False


class TestLoteValidationService_LoteSinStock:
    def test_validate_dado_lote_existente_sin_stock_cuando_validar_entonces_retorna_invalido(self):
        lote = _make_lote()
        repo = _make_repo(lote=lote, stock=None)
        service = LoteValidationService(repo)
        result = service.validate("LOTE-00001")
        assert result.valid is False
        assert "stock" in result.reason.lower()

    def test_validate_dado_lote_sin_stock_cuando_validar_entonces_no_consulta_stock_de_otro_lote(self):
        lote = _make_lote()
        repo = _make_repo(lote=lote, stock=None)
        service = LoteValidationService(repo)
        service.validate("LOTE-00001")
        repo.get_stock_activo_por_lote.assert_called_once_with(lote.id)


class TestLoteValidationService_LoteValido:
    def test_validate_dado_lote_con_stock_cuando_validar_entonces_retorna_valido(self):
        stock = _make_stock(cantidad=25)
        lote = _make_lote()
        repo = _make_repo(lote=lote, stock=stock)
        service = LoteValidationService(repo)
        result = service.validate("LOTE-00001")
        assert result.valid is True
        assert result.lote is not None
        assert result.lote.codigo == "LOTE-00001"

    def test_validate_dado_lote_valido_cuando_validar_entonces_retorna_nombre_bodega_correcto(self):
        bodega = _make_bodega(id=10, nombre="Bodega Sur")
        stock = _make_stock(bodega=bodega)
        lote = _make_lote()
        repo = _make_repo(lote=lote, stock=stock)
        service = LoteValidationService(repo)
        result = service.validate("LOTE-00001")
        assert result.lote.bodega_nombre == "Bodega Sur"
        assert result.lote.bodega_id == 10
```

**Crear tambien:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/tests/unit/__init__.py` (vacio)

### Paso 2.10 - Tests de integracion del endpoint

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/tests/integration/test_validate_endpoint.py`

La clave aqui es usar `app.dependency_overrides` en lugar del hack de `sys.modules`. Esto es posible porque ahora `get_validation_service` es una dependencia inyectable en el router.

```python
"""
Tests de integracion del endpoint /validate.
Usa app.dependency_overrides para inyectar un servicio mock, sin parchar sys.modules.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.main import app
from src.routers.validate import get_validation_service
from src.schemas.validate import ValidateResponse, LoteInfo


def _mock_service(response: ValidateResponse):
    """Crea un mock del servicio que retorna una respuesta fija."""
    svc = MagicMock()
    svc.validate.return_value = response
    return svc


@pytest.fixture
def client_valido():
    """Cliente con servicio que retorna lote valido."""
    lote_info = LoteInfo(
        codigo="LOTE-00001",
        producto_id=1,
        producto_nombre="Hilo Nylon",
        peso="25.00",
        bodega_id=10,
        bodega_nombre="Bodega Central",
    )
    mock_svc = _mock_service(ValidateResponse(valid=True, lote=lote_info))
    app.dependency_overrides[get_validation_service] = lambda: mock_svc
    yield TestClient(app), mock_svc
    app.dependency_overrides.clear()


@pytest.fixture
def client_invalido():
    """Cliente con servicio que retorna lote invalido."""
    mock_svc = _mock_service(ValidateResponse(valid=False, reason="Lote no encontrado en el sistema"))
    app.dependency_overrides[get_validation_service] = lambda: mock_svc
    yield TestClient(app), mock_svc
    app.dependency_overrides.clear()


class TestValidateEndpoint_LoteValido:
    def test_validate_dado_lote_existente_con_stock_cuando_post_entonces_200_y_valid_true(self, client_valido):
        tc, _ = client_valido
        response = tc.post("/validate", json={"code": "LOTE-00001"})
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_validate_dado_lote_valido_cuando_post_entonces_retorna_datos_bodega(self, client_valido):
        tc, _ = client_valido
        data = tc.post("/validate", json={"code": "LOTE-00001"}).json()
        assert data["lote"]["bodega_nombre"] == "Bodega Central"


class TestValidateEndpoint_LoteInvalido:
    def test_validate_dado_codigo_inexistente_cuando_post_entonces_200_y_valid_false(self, client_invalido):
        tc, _ = client_invalido
        data = tc.post("/validate", json={"code": "LOTE-FAKE"}).json()
        assert data["valid"] is False
        assert data["reason"] is not None


class TestValidateEndpoint_Pydantic:
    def test_validate_dado_payload_sin_code_cuando_post_entonces_422(self):
        # Sin override: el schema rechaza antes de llegar al servicio
        client = TestClient(app)
        response = client.post("/validate", json={})
        assert response.status_code == 422

    def test_validate_dado_code_solo_espacios_cuando_post_entonces_422(self):
        client = TestClient(app)
        response = client.post("/validate", json={"code": "   "})
        assert response.status_code == 422
```

**Crear tambien:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/tests/integration/__init__.py` (vacio)

### Paso 2.11 - Simplificar conftest.py

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/tests/conftest.py`

El conftest actual parchea `sys.modules` porque `main.py` instanciaba `SessionLocal` al importar. Con la nueva arquitectura, la sesion se inyecta via `Depends(get_db)` y los tests de integracion usan `dependency_overrides`. Los tests unitarios no importan `main.py` en absoluto. El conftest se reduce a:

```python
"""
conftest.py del scanning_service.
Con la arquitectura refactorizada (DI via Depends), los tests unitarios
no requieren parchar sys.modules: LoteValidationService acepta cualquier
objeto que cumpla ILoteRepository.
Los tests de integracion usan app.dependency_overrides.
Este archivo se mantiene vacio o con fixtures compartidas entre tests de integracion.
"""
import os
import pytest

# Asegurar que PYTHONPATH incluya el raiz del microservicio
# (necesario cuando pytest se ejecuta desde el directorio raiz del repo)
```

### Paso 2.12 - Agregar pytest.ini / setup.cfg para scanning_service

El CI actual corre `pytest tests/` desde `scanning_service/`. Agregar configuracion de cobertura:

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/pytest.ini`

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --tb=short --cov=src --cov-report=term-missing --cov-fail-under=80
```

### Paso 2.13 - Actualizar requirements.txt del scanning_service

Agregar `pytest-cov` explicitamente y actualizar versiones:

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/requirements.txt`

```
fastapi==0.109.2
uvicorn==0.27.1
sqlalchemy==2.0.27
pydantic==2.6.2
python-dotenv==1.0.1
pyodbc==5.1.0
requests==2.31.0
pytest==8.1.1
pytest-cov==5.0.0
httpx>=0.24,<0.28
```

---

## 3. PRINTING_SERVICE: PLAN DE REFACTORIZACION

### Estructura objetivo

```
printing_service/
  src/
    __init__.py
    config.py            (rutas de templates, configuracion)
    schemas/
      __init__.py
      printing.py        (DetallePedido, NotaVentaRequest como DTO puro, EtiquetaRequest)
    services/
      __init__.py
      document_service.py    (logica de negocio: calculos, formateo de fecha)
      output_strategy.py     (Protocol OutputStrategy + implementaciones PDF y ZPL)
    routers/
      __init__.py
      pdf.py             (endpoint /pdf/nota-venta)
      zpl.py             (endpoint /zpl/etiqueta)
      health.py
    templates/
      nota_venta.html    (sin cambios)
      etiqueta.zpl       (sin cambios)
    main.py              (app factory pura)
  tests/
    __init__.py
    unit/
      __init__.py
      test_document_service.py    (calculos de subtotal, IVA, total, formateo fecha)
      test_output_strategy.py     (verificar que Strategy produce output correcto)
    integration/
      __init__.py
      test_pdf_endpoint.py        (mock WeasyPrint)
      test_zpl_endpoint.py
```

### Paso 3.1 - Crear config.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/config.py`

```python
"""
Configuracion centralizada del printing_service.
Elimina dependencias de cwd (fragilidad operacional).
"""
import os
from pathlib import Path

# Directorio raiz del paquete src/
_SRC_DIR = Path(__file__).parent

# Directorio de templates: siempre relativo al paquete, sin depender del cwd
TEMPLATES_DIR = str(_SRC_DIR / "templates")

REQUIRED_TEMPLATES = ["nota_venta.html", "etiqueta.zpl"]
```

### Paso 3.2 - Crear schemas/printing.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/schemas/printing.py`

La separacion clave es: `NotaVentaRequest` es un DTO puro (solo datos, sin logica). Los calculos se mueven al servicio.

```python
"""
Schemas Pydantic del printing_service.
Aplica ISP: un schema por caso de uso, sin logica de negocio embebida (SRP).
NotaVentaRequest es un DTO de entrada HTTP puro.
"""
from pydantic import BaseModel
from typing import List, Optional


class DetallePedido(BaseModel):
    """Un renglon del pedido con su peso, precio y condicion de IVA."""
    producto_descripcion: str
    cantidad: float
    piezas: int
    peso: float
    precio_unitario: float
    incluye_iva: bool = False


class NotaVentaRequest(BaseModel):
    """
    DTO de entrada para generacion de nota de venta.
    SRP: solo transporta datos del cliente HTTP al servicio.
    NO contiene logica de negocio (subtotal/iva/total se calculan en DocumentService).
    """
    id: int
    guia_remision: Optional[str] = None
    fecha_pedido: str
    cliente_nombre: Optional[str] = "Consumidor Final"
    cliente_ruc: Optional[str] = None
    cliente_direccion: Optional[str] = None
    vendedor_nombre: Optional[str] = None
    sede_nombre: Optional[str] = "Matriz"
    empresa_nombre: Optional[str] = "Empresa"
    esta_pagado: bool = False
    valor_retencion: float = 0.0
    detalles: List[DetallePedido]


class NotaVentaContexto(BaseModel):
    """
    Schema enriquecido con calculos ya realizados por DocumentService.
    Es el objeto que se pasa al template Jinja2 (ISP: schema especifico para render).
    """
    id: int
    guia_remision: Optional[str]
    fecha_pedido: str
    fecha_pedido_formatted: str
    cliente_nombre: Optional[str]
    cliente_ruc: Optional[str]
    cliente_direccion: Optional[str]
    vendedor_nombre: Optional[str]
    sede_nombre: Optional[str]
    empresa_nombre: Optional[str]
    esta_pagado: bool
    valor_retencion: float
    detalles: List[DetallePedido]
    subtotal: float
    iva: float
    total: float


class EtiquetaRequest(BaseModel):
    """DTO de entrada para generacion de etiqueta ZPL."""
    empresa: Optional[str] = "TexCore Industrial"
    producto_desc: str
    lote_codigo: str
    peso_neto: float
    unidad: Optional[str] = "kg"
    qr_data: str
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/schemas/__init__.py` (vacio)

### Paso 3.3 - Crear services/document_service.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/services/document_service.py`

```python
"""
DocumentService: logica de negocio del dominio de documentos comerciales.
Responsabilidades (SRP):
  - Calcular subtotal, IVA (15% Ecuador), total con retencion.
  - Formatear fechas ISO a formato legible.
  - Construir el contexto de datos para el template.
No conoce HTTP, Jinja2 ni WeasyPrint.
"""
import datetime
import logging
from typing import List

from ..schemas.printing import DetallePedido, NotaVentaRequest, NotaVentaContexto

logger = logging.getLogger(__name__)

IVA_RATE = 0.15  # Tasa IVA Ecuador vigente


class DocumentService:
    """
    Servicio que encapsula la logica de negocio para documentos comerciales.
    Metodos estaticos porque no requiere estado de instancia.
    """

    @staticmethod
    def calcular_subtotal(detalles: List[DetallePedido]) -> float:
        """
        Subtotal = suma de (peso * precio_unitario) para todos los detalles.
        El flag incluye_iva NO afecta el subtotal (base imponible total).
        """
        return sum(d.peso * d.precio_unitario for d in detalles)

    @staticmethod
    def calcular_iva(detalles: List[DetallePedido]) -> float:
        """
        IVA = 15% solo sobre los detalles con incluye_iva=True.
        """
        return sum(
            d.peso * d.precio_unitario * IVA_RATE
            for d in detalles
            if d.incluye_iva
        )

    @staticmethod
    def calcular_total(subtotal: float, iva: float, valor_retencion: float) -> float:
        """Total = subtotal + iva - retencion."""
        return subtotal + iva - valor_retencion

    @staticmethod
    def formatear_fecha(fecha_iso: str) -> str:
        """
        Convierte fecha ISO 8601 a formato de display dd/mm/YYYY HH:MM.
        Si el parsing falla, retorna el string original para no romper el documento.
        """
        try:
            dt = datetime.datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
            return dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, AttributeError):
            logger.warning("No se pudo parsear fecha: %s", fecha_iso)
            return fecha_iso

    @classmethod
    def construir_contexto(cls, request: NotaVentaRequest) -> NotaVentaContexto:
        """
        Construye el contexto enriquecido para el template a partir del DTO de entrada.
        Este es el metodo principal que orquesta todos los calculos.
        """
        subtotal = cls.calcular_subtotal(request.detalles)
        iva = cls.calcular_iva(request.detalles)
        total = cls.calcular_total(subtotal, iva, request.valor_retencion)
        fecha_formatted = cls.formatear_fecha(request.fecha_pedido)

        return NotaVentaContexto(
            **request.model_dump(),
            fecha_pedido_formatted=fecha_formatted,
            subtotal=subtotal,
            iva=iva,
            total=total,
        )
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/services/__init__.py` (vacio)

### Paso 3.4 - Crear services/output_strategy.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/services/output_strategy.py`

```python
"""
Strategy Pattern para formatos de salida del printing_service.
OCP: agregar un nuevo formato (HTML, PNG) solo requiere crear una nueva clase
que implemente OutputStrategy, sin modificar los routers ni el servicio.
"""
import io
import logging
from typing import Protocol, runtime_checkable

from fastapi.responses import StreamingResponse, PlainTextResponse, Response
from jinja2 import Environment

logger = logging.getLogger(__name__)


@runtime_checkable
class OutputStrategy(Protocol):
    """Contrato para estrategias de generacion de documentos."""

    def render(self, template_name: str, context: dict, filename: str) -> Response:
        """
        Renderiza el template con el contexto dado y retorna la Response HTTP.

        Args:
            template_name: Nombre del archivo de template (ej: "nota_venta.html").
            context: Diccionario con variables para el template.
            filename: Nombre base del archivo de descarga (sin extension).
        """
        ...


class PdfOutputStrategy:
    """Genera PDF a partir de un template HTML con WeasyPrint."""

    def __init__(self, jinja_env: Environment) -> None:
        self._env = jinja_env

    def render(self, template_name: str, context: dict, filename: str) -> StreamingResponse:
        from weasyprint import HTML  # Import tardio: WeasyPrint no disponible en tests
        template = self._env.get_template(template_name)
        html_content = template.render(**context)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
        )


class ZplOutputStrategy:
    """Genera texto ZPL a partir de un template Jinja2."""

    def __init__(self, jinja_env: Environment) -> None:
        self._env = jinja_env

    def render(self, template_name: str, context: dict, filename: str) -> PlainTextResponse:
        template = self._env.get_template(template_name)
        zpl_content = template.render(**context)
        return PlainTextResponse(zpl_content)
```

### Paso 3.5 - Crear routers/pdf.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/routers/pdf.py`

```python
"""
Router para generacion de PDFs.
Responsabilidad unica: traducir HTTP → DocumentService → PdfOutputStrategy.
"""
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader

from ..config import TEMPLATES_DIR
from ..schemas.printing import NotaVentaRequest
from ..services.document_service import DocumentService
from ..services.output_strategy import PdfOutputStrategy

router = APIRouter(prefix="/pdf", tags=["PDF"])


def get_pdf_strategy() -> PdfOutputStrategy:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    return PdfOutputStrategy(env)


@router.post(
    "/nota-venta",
    summary="Genera PDF de nota de venta",
    description="Recibe los datos del pedido, calcula totales e IVA, y retorna el PDF generado.",
)
async def generate_nota_venta_pdf(
    data: NotaVentaRequest,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
):
    """
    Genera la nota de venta en PDF.
    - **data**: Datos completos del pedido incluyendo detalles con IVA.
    """
    try:
        contexto = DocumentService.construir_contexto(data)
        filename = f"nota_venta_{data.guia_remision or data.id}"
        return strategy.render("nota_venta.html", contexto.model_dump(), filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

### Paso 3.6 - Crear routers/zpl.py y routers/health.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/routers/zpl.py`

```python
"""Router para generacion de etiquetas ZPL."""
from fastapi import APIRouter, Depends, HTTPException
from jinja2 import Environment, FileSystemLoader

from ..config import TEMPLATES_DIR
from ..schemas.printing import EtiquetaRequest
from ..services.output_strategy import ZplOutputStrategy

router = APIRouter(prefix="/zpl", tags=["ZPL"])


def get_zpl_strategy() -> ZplOutputStrategy:
    env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))
    return ZplOutputStrategy(env)


@router.post("/etiqueta", summary="Genera etiqueta ZPL para impresora Zebra")
async def generate_zpl_label(
    data: EtiquetaRequest,
    strategy: ZplOutputStrategy = Depends(get_zpl_strategy),
):
    try:
        return strategy.render("etiqueta.zpl", data.model_dump(), data.lote_codigo)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/routers/health.py`

```python
"""Health check del printing_service."""
import os
from fastapi import APIRouter, HTTPException
from ..config import TEMPLATES_DIR, REQUIRED_TEMPLATES

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    missing = [t for t in REQUIRED_TEMPLATES if not os.path.exists(os.path.join(TEMPLATES_DIR, t))]
    if missing:
        raise HTTPException(status_code=503, detail=f"Templates ausentes: {missing}")
    return {"status": "ok", "templates": "ok"}
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/routers/__init__.py` (vacio)

### Paso 3.7 - Reescribir main.py del printing_service

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/main.py`

```python
"""App factory del printing_service."""
from fastapi import FastAPI
from .routers import pdf, zpl, health

app = FastAPI(
    title="TexCore Printing Service",
    description="Microservicio para generacion de PDFs y etiquetas ZPL",
    version="2.0.0",
)

app.include_router(health.router)
app.include_router(pdf.router)
app.include_router(zpl.router)
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/__init__.py` (vacio)

### Paso 3.8 - Tests unitarios del DocumentService

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/tests/unit/test_document_service.py`

Los tests existentes en `test_nota_venta_calculos.py` prueban los `@property` de `NotaVentaRequest`. Ahora deben probar `DocumentService` directamente. Se pueden migrar con cambios minimos:

```python
"""
Tests unitarios de DocumentService.
Migrados desde test_nota_venta_calculos.py — misma logica, nueva ubicacion.
No requieren HTTP ni WeasyPrint.
"""
import pytest
from src.schemas.printing import DetallePedido, NotaVentaRequest
from src.services.document_service import DocumentService


def _make_detalle(peso: float, precio: float, incluye_iva: bool = False) -> DetallePedido:
    return DetallePedido(
        producto_descripcion="Hilo Nylon 100%",
        cantidad=1.0,
        piezas=1,
        peso=peso,
        precio_unitario=precio,
        incluye_iva=incluye_iva,
    )


class TestDocumentService_Subtotal:
    def test_subtotal_dado_un_detalle_cuando_calcular_entonces_es_peso_por_precio(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0)]
        assert DocumentService.calcular_subtotal(detalles) == pytest.approx(50.0)

    def test_subtotal_dado_lista_vacia_cuando_calcular_entonces_es_cero(self):
        assert DocumentService.calcular_subtotal([]) == pytest.approx(0.0)

    def test_subtotal_dado_detalle_con_iva_cuando_calcular_entonces_iva_no_afecta_subtotal(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)]
        assert DocumentService.calcular_subtotal(detalles) == pytest.approx(50.0)


class TestDocumentService_Iva:
    def test_iva_dado_detalle_sin_iva_cuando_calcular_entonces_es_cero(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0, incluye_iva=False)]
        assert DocumentService.calcular_iva(detalles) == pytest.approx(0.0)

    def test_iva_dado_detalle_con_iva_cuando_calcular_entonces_es_15_porciento(self):
        detalles = [_make_detalle(peso=10.0, precio=5.0, incluye_iva=True)]
        assert DocumentService.calcular_iva(detalles) == pytest.approx(7.5)


class TestDocumentService_Total:
    def test_total_dado_sin_retencion_cuando_calcular_entonces_es_subtotal_mas_iva(self):
        assert DocumentService.calcular_total(50.0, 7.5, 0.0) == pytest.approx(57.5)

    def test_total_dado_retencion_cuando_calcular_entonces_se_descuenta(self):
        assert DocumentService.calcular_total(50.0, 0.0, 5.0) == pytest.approx(45.0)


class TestDocumentService_FormatearFecha:
    def test_formatear_fecha_dado_iso_valido_cuando_formatear_entonces_retorna_ddmmyyyy(self):
        result = DocumentService.formatear_fecha("2026-03-27T10:00:00")
        assert result == "27/03/2026 10:00"

    def test_formatear_fecha_dado_string_invalido_cuando_formatear_entonces_retorna_original(self):
        result = DocumentService.formatear_fecha("no-es-fecha")
        assert result == "no-es-fecha"

    def test_formatear_fecha_dado_utc_z_cuando_formatear_entonces_parsea_correctamente(self):
        result = DocumentService.formatear_fecha("2026-03-27T10:00:00Z")
        assert "2026" in result


class TestDocumentService_ConstruirContexto:
    def test_construir_contexto_dado_request_valido_cuando_construir_entonces_tiene_subtotal(self):
        request = NotaVentaRequest(
            id=1,
            fecha_pedido="2026-03-27T10:00:00",
            detalles=[_make_detalle(peso=10.0, precio=5.0)],
        )
        ctx = DocumentService.construir_contexto(request)
        assert ctx.subtotal == pytest.approx(50.0)
        assert ctx.fecha_pedido_formatted == "27/03/2026 10:00"
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/printing_service/tests/unit/__init__.py` (vacio)

**Tambien migrar** los tests existentes de `test_nota_venta_calculos.py` para que sigan pasando durante la transicion. Dado que el CI llama `pytest tests/test_nota_venta_calculos.py`, ese archivo puede mantenerse temporalmente y ser eliminado en un segundo PR.

### Paso 3.9 - Actualizar CI para printing_service

El job `printing-service-test` en `.github/workflows/ci.yml` actualmente solo corre `tests/test_nota_venta_calculos.py`. Debe actualizarse para correr `tests/unit/` y eventualmente `tests/integration/` (estos ultimos requieren mock de WeasyPrint).

**Cambio en ci.yml** (job `printing-service-test`, step `Ejecutar tests de calculo`):

```yaml
- name: Ejecutar tests de calculo y servicio
  working-directory: printing_service
  run: |
    pytest tests/unit/ -v \
      --tb=short \
      --cov=src \
      --cov-report=term-missing \
      --cov-fail-under=80
```

---

## 4. REPORTING_EXCEL: PLAN DE REFACTORIZACION

### Estructura objetivo

```
reporting_excel/
  src/
    __init__.py         (existente)
    main.py             (ajustar imports, sacar generate_download_response)
    database.py         (refactorizar en dos clases)
    logging_rfc5424.py  (sin cambios)
    schemas/
      __init__.py
      report_params.py   (schemas Pydantic para parametros de cada reporte)
    repositories/
      __init__.py
      base.py            (Protocol IReportRepository)
      sql_repository.py  (implementacion pyodbc)
    services/
      __init__.py
      report_factory.py  (ReportFactory: crea el servicio correcto segun tipo)
      report_service.py  (ReportService: orquesta repositorio + formateador)
    formatters/
      __init__.py
      base.py            (Protocol OutputFormatter)
      excel_formatter.py (ExcelFormatter, extrae logica de excel_generator.py)
      csv_formatter.py   (CsvFormatter)
    routers/
      __init__.py
      exports.py         (refactorizado, sin generate_download_response)
      vendedores.py      (refactorizado)
      gerencial.py       (refactorizado)
      produccion.py      (refactorizado)
      health.py
  tests/
    conftest.py         (refactorizado con fixtures compartidas)
    unit/
      __init__.py
      test_excel_formatter.py
      test_report_service.py
      test_report_factory.py
    integration/
      __init__.py
      test_exports.py      (migrado)
      test_vendedores.py   (migrado)
      test_gerencial.py    (nuevo)
      test_produccion.py   (nuevo)
```

### Paso 4.1 - Crear schemas/report_params.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/schemas/report_params.py`

ISP aplicado: cada endpoint recibe un schema especifico en lugar de parametros sueltos `Query(...)`.

```python
"""
Schemas Pydantic para parametros de los reportes.
ISP: un schema por caso de uso. Facilita testing de validacion de parametros.
"""
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class KardexParams(BaseModel):
    bodega_id: int
    producto_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    lote_codigo: Optional[str] = None
    format: str = "xlsx"

    @field_validator("format")
    @classmethod
    def formato_valido(cls, v: str) -> str:
        if v not in ("xlsx", "csv"):
            raise ValueError("El formato debe ser 'xlsx' o 'csv'")
        return v


class RangoFechaParams(BaseModel):
    """Parametros comunes para reportes con rango de fechas y sede opcional."""
    fecha_inicio: date
    fecha_fin: date
    sede_id: Optional[int] = None
    format: str = "xlsx"

    @field_validator("format")
    @classmethod
    def formato_valido(cls, v: str) -> str:
        if v not in ("xlsx", "csv"):
            raise ValueError("El formato debe ser 'xlsx' o 'csv'")
        return v


class VendedorParams(BaseModel):
    """Parametros para reportes por vendedor."""
    vendedor_id: int
    fecha_inicio: date
    fecha_fin: date
    format: str = "xlsx"


class StockParams(BaseModel):
    bodega_id: int
    producto_id: Optional[int] = None
    format: str = "xlsx"
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/schemas/__init__.py` (vacio)

### Paso 4.2 - Crear repositories/base.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/repositories/base.py`

```python
"""
Protocolo del repositorio de reportes.
LSP/DIP: permite sustituir la implementacion pyodbc por una en memoria para tests.
"""
from typing import Optional, Protocol, Tuple
import pandas as pd


@runtime_checkable
class IReportRepository(Protocol):
    def execute_sp(self, sp_query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Ejecuta un stored procedure y retorna un DataFrame.
        sp_query: la cadena EXEC completa (ej: "EXEC sp_GetKardexBodega @BodegaID=?, ...")
        params: tupla de parametros posicionales para los '?' en sp_query.
        """
        ...
```

Agregar el import de `runtime_checkable` de `typing`.

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/repositories/__init__.py` (vacio)

### Paso 4.3 - Crear repositories/sql_repository.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/repositories/sql_repository.py`

Extrae la responsabilidad de conexion de `database.py`, que queda como modulo de configuracion.

```python
"""
Implementacion pyodbc del repositorio de reportes.
SRP: solo responsable de ejecutar queries y retornar DataFrames.
La cadena de conexion se construye en database.py (configuracion separada).
"""
import logging
from typing import Optional, Tuple

import pandas as pd
import pyodbc

from ..database import get_connection_string

logger = logging.getLogger(__name__)


class SqlReportRepository:
    """
    Ejecuta Stored Procedures de SQL Server y retorna DataFrames.
    Incluye el converter de DATETIMEOFFSET para columnas de fecha.
    """

    @staticmethod
    def _handle_datetimeoffset(dto_value) -> str:
        """Converter para el tipo DATETIMEOFFSET de SQL Server (-155 en pyodbc)."""
        try:
            if isinstance(dto_value, (bytes, bytearray)):
                return ""
            return pd.Timestamp(dto_value).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""

    def execute_sp(self, sp_query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Ejecuta el SP y retorna DataFrame. Abre y cierra la conexion en cada llamada.

        Args:
            sp_query: Cadena EXEC completa con parametros '?'.
            params: Valores para los '?' en orden.
        """
        conn_str = get_connection_string()
        try:
            with pyodbc.connect(conn_str) as conn:
                conn.add_output_converter(-155, self._handle_datetimeoffset)
                if params:
                    df = pd.read_sql(sp_query, conn, params=params)
                else:
                    df = pd.read_sql(sp_query, conn)
            return df
        except Exception as exc:
            logger.error("Error ejecutando SP '%s': %s", sp_query, exc)
            raise
```

### Paso 4.4 - Crear formatters/base.py, excel_formatter.py, csv_formatter.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/formatters/base.py`

```python
"""
Protocol para formateadores de salida (Strategy Pattern).
OCP: agregar formato PDF, JSON, etc. solo requiere nueva clase, no modificar routers.
"""
from typing import Protocol
import pandas as pd
from fastapi.responses import Response


class OutputFormatter(Protocol):
    def format(self, df: pd.DataFrame, filename: str) -> Response:
        """Convierte un DataFrame en una Response HTTP descargable."""
        ...
```

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/formatters/excel_formatter.py`

Extrae la logica de `excel_generator.py` y `generate_download_response` (la parte Excel):

```python
"""
Formateador de salida Excel.
Extrae la logica de excel_generator.py y la encapsula en el patron Strategy.
SRP: solo responsable de convertir DataFrames a archivos Excel descargables.
"""
import re
from io import BytesIO
from typing import Optional

import pandas as pd
from fastapi import Response

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _solo_ascii(s) -> str:
    if not s or not isinstance(s, str):
        return ""
    return re.sub(r"[^\x20-\x7E\u00C0-\u024F]", "", s)


def _fecha_a_texto(val) -> str:
    if pd.isna(val) or val is None or val == "":
        return ""
    if isinstance(val, (bytes, bytearray)):
        return ""
    try:
        return pd.Timestamp(val).strftime("%d-%m-%Y")
    except Exception:
        try:
            return pd.to_datetime(str(val).strip()).strftime("%d-%m-%Y")
        except Exception:
            return ""


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza el DataFrame para escritura Excel: fechas como texto, numericos redondeados."""
    df = df.copy()
    for col in df.columns:
        col_lower = str(col).lower()
        if pd.api.types.is_datetime64_any_dtype(df[col]) or col_lower == "fecha":
            df[col] = df[col].apply(lambda x: _solo_ascii(_fecha_a_texto(x)))
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype(float).round(3)
        else:
            df[col] = df[col].apply(lambda x: _solo_ascii(str(x)) if pd.notna(x) else "")
    return df


class ExcelFormatter:
    """Convierte DataFrames a archivos .xlsx descargables con formato TexCore."""

    def __init__(self, sheet_name: str = "Reporte") -> None:
        self._sheet_name = sheet_name

    def _to_bytes(self, df: pd.DataFrame) -> bytes:
        output = BytesIO()
        df = _prepare_df(df)
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name=self._sheet_name, index=False)
            workbook = writer.book
            worksheet = writer.sheets[self._sheet_name]
            header_fmt = workbook.add_format({
                "bold": True, "bg_color": "#333333", "font_color": "white",
                "align": "center", "valign": "vcenter", "border": 1,
            })
            for col_idx in range(len(df.columns)):
                worksheet.write(0, col_idx, str(df.columns[col_idx]), header_fmt)
            for col_idx, col_name in enumerate(df.columns):
                if str(col_name).lower() == "fecha":
                    for row_idx in range(len(df)):
                        val = df.iloc[row_idx][col_name]
                        txt = str(val).strip() if val and pd.notna(val) else ""
                        worksheet.write_string(row_idx + 1, col_idx, txt)
                    break
            for col_idx, col_name in enumerate(df.columns):
                try:
                    col_max = df[col_name].astype(str).str.len().max()
                except Exception:
                    col_max = 0
                max_len = max(col_max if len(df) > 0 else 0, len(str(col_name)))
                worksheet.set_column(col_idx, col_idx, min(max_len + 2, 50))
        return output.getvalue()

    def format(self, df: pd.DataFrame, filename: str) -> Response:
        """Retorna Response HTTP con el archivo Excel como adjunto."""
        return Response(
            content=self._to_bytes(df),
            media_type=EXCEL_MEDIA_TYPE,
            headers={
                "Content-Disposition": f"attachment; filename={filename}.xlsx",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
```

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/formatters/csv_formatter.py`

```python
"""Formateador de salida CSV."""
import pandas as pd
from fastapi import Response


class CsvFormatter:
    """Convierte DataFrames a archivos .csv descargables."""

    def format(self, df: pd.DataFrame, filename: str) -> Response:
        csv_data = df.to_csv(index=False)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/formatters/__init__.py` (vacio)

### Paso 4.5 - Crear services/report_service.py y services/report_factory.py

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/services/report_service.py`

```python
"""
ReportService: orquesta el repositorio con el formateador.
SRP: solo coordina la obtencion de datos y su formato de salida.
DIP: depende de abstracciones (IReportRepository, OutputFormatter), no de implementaciones.
"""
import logging
from typing import Optional, Tuple

import pandas as pd
from fastapi import Response

from ..repositories.base import IReportRepository
from ..formatters.base import OutputFormatter
from ..formatters.excel_formatter import ExcelFormatter

logger = logging.getLogger(__name__)

_EMPTY_MESSAGE = "No se encontraron datos para los parametros seleccionados."


class ReportService:
    """
    Servicio que ejecuta un SP, maneja el caso de DataFrame vacio,
    y delega el formateo al OutputFormatter correspondiente.
    """

    def __init__(
        self,
        repository: IReportRepository,
        formatter: OutputFormatter,
    ) -> None:
        self._repo = repository
        self._formatter = formatter

    def generate(
        self,
        sp_query: str,
        params: Optional[Tuple],
        filename: str,
    ) -> Response:
        """
        Ejecuta el SP y retorna la Response formateada.

        Comportamiento con DataFrame vacio:
          - Si el formatter es ExcelFormatter: retorna Excel con fila de mensaje.
          - Si el formatter es CsvFormatter: retorna CSV con fila de mensaje.
          Nunca retorna 404 (el frontend espera siempre un archivo descargable).
        """
        df = self._repo.execute_sp(sp_query, params)

        if df.empty:
            logger.info("SP retorno DataFrame vacio: %s", sp_query)
            df = pd.DataFrame([{"mensaje": _EMPTY_MESSAGE}])

        return self._formatter.format(df, filename)
```

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/services/report_factory.py`

```python
"""
ReportFactory: crea el ReportService correcto segun el formato de salida solicitado.
Factory Pattern + OCP: agregar un nuevo formato solo requiere agregar un caso aqui.
"""
from ..repositories.sql_repository import SqlReportRepository
from ..formatters.excel_formatter import ExcelFormatter
from ..formatters.csv_formatter import CsvFormatter
from .report_service import ReportService


class ReportFactory:
    """
    Construye el grafo de dependencias para un reporte dado un formato de salida.
    """

    @staticmethod
    def create(format: str) -> ReportService:
        """
        Args:
            format: "xlsx" o "csv"

        Returns:
            ReportService configurado con el formateador correcto.

        Raises:
            ValueError: Si el formato no es soportado.
        """
        repo = SqlReportRepository()

        formatters = {
            "xlsx": ExcelFormatter(),
            "csv": CsvFormatter(),
        }

        formatter = formatters.get(format)
        if formatter is None:
            raise ValueError(f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")

        return ReportService(repository=repo, formatter=formatter)
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/services/__init__.py` (vacio)

### Paso 4.6 - Refactorizar routers

La clave es: todos los routers pasan a usar `ReportFactory.create(format)` en lugar de llamar `execute_sp_to_dataframe` directamente. La funcion `generate_download_response` desaparece de `exports.py` (estaba importada entre routers, violando SRP).

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/routers/exports.py`

Patron repetido en cada endpoint (se muestra uno como ejemplo):

```python
"""
Router de exportaciones generales de inventario.
SRP: solo traduce parametros HTTP a llamadas de ReportService.
Sin logica de formato: delegada a ReportFactory.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/kardex")
def export_kardex(
    bodega_id: int = Query(...),
    producto_id: Optional[str] = Query(None),
    proveedor_id: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    lote_codigo: Optional[str] = Query(None),
    format: str = Query("xlsx"),
):
    """Exporta el Kardex de una bodega. Soporta filtros opcionales."""
    try:
        service = ReportFactory.create(format)
        query = "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?, @FechaInicio=?, @FechaFin=?, @ProveedorID=?, @LoteCodigo=?"
        params = (
            bodega_id,
            int(producto_id) if producto_id and producto_id not in ("0", "") else None,
            fecha_inicio or None,
            fecha_fin or None,
            int(proveedor_id) if proveedor_id and proveedor_id not in ("all", "") else None,
            lote_codigo or None,
        )
        filename = f"kardex_{bodega_id}_{producto_id}" if producto_id else f"movimientos_bodega_{bodega_id}"
        return service.generate(query, params, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Kardex: %s", exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el reporte")

# El mismo patron se repite para /productos, /usuarios, /stock-actual, /valorizacion, /aging, /rotacion, /stock-cero, /resumen-movimientos
```

**Archivos a modificar:** `vendedores.py`, `gerencial.py`, `produccion.py` - eliminar el import de `generate_download_response` y reemplazar con `ReportFactory.create(format).generate(...)`.

### Paso 4.7 - Corregir test desincronizado (deuda tecnica documentada)

El `test_usuarios_export_empty` en `test_exports.py` afirma `status_code == 404`. El codigo real retorna 200 con un Excel que contiene la fila "No se encontraron datos...". Debe corregirse el test:

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/tests/test_exports.py`

Cambiar `test_usuarios_export_empty`:

```python
def test_usuarios_export_empty(mock_pandas_read_sql, mock_db_connection):
    """Prueba que DataFrame vacio retorna Excel con fila de mensaje (no 404)."""
    mock_pandas_read_sql.return_value = pd.DataFrame()
    response = client.get("/export/usuarios?format=xlsx")
    # El servicio siempre retorna un archivo descargable, nunca 404
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert response.content.startswith(b"PK\x03\x04")
```

### Paso 4.8 - Tests unitarios de los nuevos componentes

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/tests/unit/test_excel_formatter.py`

```python
"""Tests unitarios del ExcelFormatter. Sin BD, sin HTTP."""
import pytest
import pandas as pd
from src.formatters.excel_formatter import ExcelFormatter, _prepare_df, _fecha_a_texto


class TestFechaATexto:
    def test_fecha_a_texto_dado_none_cuando_convertir_entonces_retorna_vacio(self):
        assert _fecha_a_texto(None) == ""

    def test_fecha_a_texto_dado_bytes_cuando_convertir_entonces_retorna_vacio(self):
        assert _fecha_a_texto(b"2026-01-01") == ""

    def test_fecha_a_texto_dado_fecha_valida_cuando_convertir_entonces_retorna_ddmmyyyy(self):
        result = _fecha_a_texto(pd.Timestamp("2026-01-15"))
        assert result == "15-01-2026"


class TestPrepareDF:
    def test_prepare_df_dado_columna_numerica_cuando_preparar_entonces_redondea_3_decimales(self):
        df = pd.DataFrame({"precio": [1.23456]})
        result = _prepare_df(df)
        assert result["precio"].iloc[0] == pytest.approx(1.235)

    def test_prepare_df_dado_columna_fecha_cuando_preparar_entonces_convierte_a_texto(self):
        df = pd.DataFrame({"fecha": [pd.Timestamp("2026-01-15")]})
        result = _prepare_df(df)
        assert result["fecha"].iloc[0] == "15-01-2026"


class TestExcelFormatter:
    def test_format_dado_dataframe_valido_cuando_formatear_entonces_retorna_xlsx(self):
        df = pd.DataFrame({"col1": ["dato1"], "col2": [42.0]})
        formatter = ExcelFormatter()
        response = formatter.format(df, "test_reporte")
        assert response.status_code == 200
        assert b"PK\x03\x04" in response.body  # Magic bytes de ZIP/Office

    def test_format_dado_filename_cuando_formatear_entonces_content_disposition_correcto(self):
        df = pd.DataFrame({"col": ["val"]})
        formatter = ExcelFormatter()
        response = formatter.format(df, "mi_reporte")
        assert "mi_reporte.xlsx" in response.headers["content-disposition"]
```

**Archivo a crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/tests/unit/test_report_service.py`

```python
"""
Tests unitarios del ReportService.
Usa mocks de IReportRepository y OutputFormatter para aislar la logica del servicio.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from fastapi import Response

from src.services.report_service import ReportService


def _make_repo(df: pd.DataFrame):
    repo = MagicMock()
    repo.execute_sp.return_value = df
    return repo


def _make_formatter():
    fmt = MagicMock()
    fmt.format.return_value = Response(content=b"data", media_type="application/octet-stream")
    return fmt


class TestReportService_DFLleno:
    def test_generate_dado_df_con_datos_cuando_generar_entonces_llama_formatter(self):
        df = pd.DataFrame({"col": [1, 2]})
        repo = _make_repo(df)
        fmt = _make_formatter()
        service = ReportService(repo, fmt)
        service.generate("EXEC sp_Test", None, "reporte")
        fmt.format.assert_called_once()

    def test_generate_dado_df_con_datos_cuando_generar_entonces_pasa_df_original_al_formatter(self):
        df = pd.DataFrame({"col": [1, 2]})
        repo = _make_repo(df)
        fmt = _make_formatter()
        service = ReportService(repo, fmt)
        service.generate("EXEC sp_Test", None, "reporte")
        args = fmt.format.call_args
        assert len(args[0][0]) == 2  # DataFrame con 2 filas


class TestReportService_DFVacio:
    def test_generate_dado_df_vacio_cuando_generar_entonces_pasa_df_con_mensaje(self):
        repo = _make_repo(pd.DataFrame())
        fmt = _make_formatter()
        service = ReportService(repo, fmt)
        service.generate("EXEC sp_Test", None, "reporte")
        args = fmt.format.call_args
        df_pasado = args[0][0]
        assert "mensaje" in df_pasado.columns
        assert len(df_pasado) == 1

    def test_generate_dado_df_vacio_cuando_generar_entonces_retorna_response(self):
        repo = _make_repo(pd.DataFrame())
        fmt = _make_formatter()
        service = ReportService(repo, fmt)
        result = service.generate("EXEC sp_Test", None, "reporte")
        assert result is not None
```

**Crear:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/tests/unit/__init__.py` (vacio)

### Paso 4.9 - Actualizar conftest.py del reporting_excel

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/tests/conftest.py`

Agregar fixture de repositorio mock para tests unitarios:

```python
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app, INTERNAL_KEY

# Cliente global con autenticacion
client = TestClient(app, headers={"X-Internal-Key": INTERNAL_KEY})


@pytest.fixture
def mock_db_connection():
    with patch("src.database.pyodbc.connect") as mock_connect:
        yield mock_connect


@pytest.fixture
def mock_pandas_read_sql():
    with patch("src.database.pd.read_sql") as mock_read:
        yield mock_read


@pytest.fixture
def mock_repo():
    """Mock de IReportRepository para tests unitarios de ReportService."""
    repo = MagicMock()
    repo.execute_sp.return_value = pd.DataFrame()
    return repo
```

### Paso 4.10 - Actualizar CI para reporting_excel

En `.github/workflows/ci.yml`, el job `reporting-excel-test` debe:
1. Correr tests unitarios y de integracion por separado.
2. Aumentar el umbral de cobertura de 60% a 80%.

```yaml
- name: Ejecutar tests unitarios
  working-directory: reporting_excel
  env:
    PYTHONPATH: "."
    REPORTING_INTERNAL_KEY: "ci-test-internal-key"
  run: |
    pytest tests/unit/ -v \
      --tb=short \
      --cov=src \
      --cov-report=term-missing

- name: Ejecutar tests de integracion
  working-directory: reporting_excel
  env:
    PYTHONPATH: "."
    REPORTING_INTERNAL_KEY: "ci-test-internal-key"
  run: |
    pytest tests/integration/ -v \
      --tb=short \
      --cov=src \
      --cov-append \
      --cov-report=term-missing \
      --cov-fail-under=80
```

---

## 5. SECUENCIA DE EJECUCION Y DEPENDENCIAS

La siguiente tabla indica el orden estricto de implementacion. Los pasos dentro de un mismo bloque pueden hacerse en paralelo si hay varios desarrolladores.

### Bloque A - scanning_service (sin dependencias externas, hacer primero)

```
A1  models.py          → agregar Sede, FK en Bodega
A2  schemas/__init__.py + schemas/validate.py
A3  repositories/__init__.py + repositories/base.py
A4  repositories/lote_repository.py      (depende de A3, A1)
A5  services/__init__.py + services/validation_service.py   (depende de A3, A2)
A6  routers/__init__.py + routers/health.py + routers/validate.py   (depende de A5)
A7  main.py refactorizado                (depende de A6)
A8  tests/unit/__init__.py + tests/unit/test_validation_service.py  (depende de A5)
A9  tests/integration/__init__.py + tests/integration/test_validate_endpoint.py (depende de A7)
A10 tests/conftest.py simplificado
A11 pytest.ini
A12 requirements.txt actualizado
```

**Verificacion:** `cd scanning_service && pytest tests/ -v` debe pasar al 100%.

### Bloque B - printing_service (independiente de A)

```
B1  src/__init__.py
B2  src/config.py
B3  src/schemas/__init__.py + src/schemas/printing.py
B4  src/services/__init__.py + src/services/document_service.py  (depende de B3)
B5  src/services/output_strategy.py     (depende de B2)
B6  src/routers/__init__.py + src/routers/health.py   (depende de B2)
B7  src/routers/pdf.py                  (depende de B4, B5, B6)
B8  src/routers/zpl.py                  (depende de B5)
B9  src/main.py refactorizado           (depende de B7, B8, B6)
B10 tests/unit/__init__.py + tests/unit/test_document_service.py  (depende de B4)
B11 Actualizar ci.yml para printing_service (tests/unit/ en lugar de archivo especifico)
```

**Verificacion:** `cd printing_service && pytest tests/unit/ -v` debe pasar. Los calculos de `test_nota_venta_calculos.py` existentes deben seguir pasando (backward compatibility).

### Bloque C - reporting_excel (puede empezar en paralelo con B)

```
C1  src/schemas/__init__.py + src/schemas/report_params.py
C2  src/repositories/__init__.py + src/repositories/base.py
C3  src/repositories/sql_repository.py  (depende de C2 y src/database.py existente)
C4  src/formatters/__init__.py
C5  src/formatters/excel_formatter.py   (extrae logica de excel_generator.py existente)
C6  src/formatters/csv_formatter.py
C7  src/services/__init__.py + src/services/report_service.py  (depende de C2, C4)
C8  src/services/report_factory.py      (depende de C3, C5, C6, C7)
C9  src/routers/exports.py refactorizado  (depende de C8)
C10 src/routers/vendedores.py refactorizado
C11 src/routers/gerencial.py refactorizado
C12 src/routers/produccion.py refactorizado
C13 src/main.py: quitar generate_download_response (ya no se exporta)
C14 tests/unit/test_excel_formatter.py  (depende de C5)
C15 tests/unit/test_report_service.py   (depende de C7)
C16 tests/integration/test_exports.py migrado + test desincronizado corregido
C17 tests/conftest.py actualizado
C18 Actualizar ci.yml: umbral 60% → 80%
```

**Verificacion:** `cd reporting_excel && pytest tests/ -v --cov=src --cov-fail-under=80`.

### Bloque D - PR y CI (al finalizar cada bloque)

Crear un PR por microservicio (no mezclar los tres en un solo PR). El Quality Gate del CI valida todos los jobs.

---

## 6. ACTUALIZACIONES AL CI/CD

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/.github/workflows/ci.yml`

### Job scanning-service-test

Agregar `--cov-fail-under=80` y correr tests de `unit/` e `integration/`:

```yaml
- name: Ejecutar tests del scanning_service
  working-directory: scanning_service
  run: |
    pytest tests/unit/ tests/integration/ -v \
      --tb=short \
      --cov=src \
      --cov-report=term-missing \
      --cov-fail-under=80
```

### Job printing-service-test

Cambiar de correr un archivo especifico a correr `tests/unit/`:

```yaml
- name: Ejecutar tests de calculo y servicio
  working-directory: printing_service
  run: |
    pytest tests/unit/ -v \
      --tb=short \
      --cov=src \
      --cov-report=term-missing \
      --cov-fail-under=80
```

Nota: el paso de instalacion de dependencias ya excluye WeasyPrint. La importacion de `weasyprint` en `output_strategy.py` es un import tardia (`from weasyprint import HTML` dentro del metodo `render`), por lo que los tests unitarios de `DocumentService` y de la estructura de la app pasan sin instalar WeasyPrint.

### Job reporting-excel-test

Cambiar umbral de 60% a 80% y separar en dos steps (unitarios + integracion) como se describio en el Paso 4.10.

---

## 7. README POR MICROSERVICIO

Cada microservicio debe tener un README actualizado. La estructura minima:

**Archivo a modificar:** `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/README.md`

Secciones: Descripcion del servicio, Arquitectura de capas (diagrama ASCII), Variables de entorno requeridas, Como correr los tests, Como correr en desarrollo, Endpoints documentados.

Los otros dos microservicios siguen el mismo patron. Los READMEs de `printing_service/` y `reporting_excel/` deben crearse (actualmente `printing_service` no tiene README, y `reporting_excel` tampoco).

---

## Resumen de malas practicas y su resolucion

| Microservicio | Mala practica | Principio violado | Solucion |
|---|---|---|---|
| scanning | `SessionLocal()` directo en endpoint | DIP | `Depends(get_validation_service)` con `SqlLoteRepository` |
| scanning | Schemas + logica + BD en `main.py` | SRP | Capas `schemas/`, `services/`, `repositories/` |
| scanning | Tests parchean `sys.modules` | LSP/testabilidad | `app.dependency_overrides` con Protocol inyectable |
| scanning | `StockBodega.producto_id` redundante | 3FN | Documentado con comentario, relacion `producto` eliminada del ORM |
| scanning | `Bodega.sede_id` sin FK ni modelo `Sede` | Integridad referencial | Agregada clase `Sede` y FK en `Bodega` |
| printing | Calculos en schema Pydantic | SRP | Movidos a `DocumentService` con metodos estaticos |
| printing | Path de templates relativo al cwd | Fragilidad | `config.py` con `Path(__file__).parent / "templates"` |
| printing | Formato hardcodeado en endpoint | OCP | `OutputStrategy` Protocol + `PdfOutputStrategy` / `ZplOutputStrategy` |
| printing | `NotaVentaRequest` como DTO y portador de logica | ISP | Separado en `NotaVentaRequest` (DTO) y `NotaVentaContexto` (para template) |
| reporting | `generate_download_response` compartida entre routers | SRP (acoplamiento) | Movida a `formatters/` con Strategy Pattern |
| reporting | Routers llaman `execute_sp_to_dataframe` directamente | SRP | Capa `repositories/` + `services/` intermediaria |
| reporting | Formato de salida con `if csv/else xlsx` | OCP | `OutputFormatter` Protocol + `ExcelFormatter` / `CsvFormatter` |
| reporting | Test `test_usuarios_export_empty` desincronizado | Deuda tecnica | Corregido para afirmar 200 con Excel vacio en lugar de 404 |
| reporting | `execute_sp_to_dataframe` tiene 3 responsabilidades | SRP | Separado en `SqlReportRepository.execute_sp()` y helpers privados |

---

### Critical Files for Implementation

- `/home/barellano/Documents/Desarrollo/TexCore/scanning_service/src/main.py`
- `/home/barellano/Documents/Desarrollo/TexCore/printing_service/src/main.py`
- `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/routers/exports.py`
- `/home/barellano/Documents/Desarrollo/TexCore/reporting_excel/src/services/report_service.py` (archivo nuevo - el mas critico del reporting_excel)
- `/home/barellano/Documents/Desarrollo/TexCore/.github/workflows/ci.yml`
