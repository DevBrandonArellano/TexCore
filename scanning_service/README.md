# Servicio Satélite de Escaneo — TexCore

Servicio satélite FastAPI dedicado a la validación de códigos QR/barras de lotes de producción durante el proceso de despacho. Opera con latencia ultrabaja (<500 ms) y persiste un log de auditoría local en SQLite.

## Arquitectura

```
Frontend (React)
      │
      ▼
   Nginx (API Gateway)
      │
      ▼
scanning_service (FastAPI :8001)
      │                  │
      ▼                  ▼
Django Internal API   SQLite local
  (JWT RS256)         /data/logs.db
      │               (audit_log)
      ▼
 texcore_db (SQL Server)
```

## Responsabilidades

- Validar códigos de lotes escaneados en tiempo real
- Retornar datos de producto, bodega y stock disponible
- Persistir cada evento de validación en la base de datos de auditoría local

## Tecnologías

| Paquete | Rol |
|---|---|
| FastAPI | Framework HTTP asíncrono |
| httpx | Cliente HTTP para Django Internal API |
| PyJWT (RS256) | Autenticación con el backend |
| SQLAlchemy 2.0 async + aiosqlite | Base de datos de auditoría SQLite |
| Pydantic | Validación de esquemas de entrada/salida |
| Uvicorn | Servidor ASGI |

## Endpoints

### `POST /scanning/validate`

Valida un código de lote y registra el evento en auditoría.

**Request:**
```json
{ "code": "LOTE-2025-001" }
```

**Response (lote válido):**
```json
{
  "valid": true,
  "lote": {
    "codigo": "LOTE-2025-001",
    "producto_id": 42,
    "producto_nombre": "Hilo Nylon 70D",
    "peso": "120.50",
    "bodega_id": 3,
    "bodega_nombre": "Bodega Despacho"
  }
}
```

**Response (lote inválido):**
```json
{
  "valid": false,
  "reason": "Lote no encontrado en el sistema"
}
```

### `GET /health`

Verifica conectividad con Django Internal API.

## Estructura

```
scanning_service/
├── requirements.txt
├── pytest.ini                  # asyncio_mode = auto
├── src/
│   ├── main.py                 # App FastAPI + _setup_logging() RFC 5424
│   ├── logging_rfc5424.py      # RFC5424Formatter (facility=16, app_name="texcore-scanning")
│   ├── database/
│   │   ├── engine.py           # SQLite async engine + WAL + PRAGMAs + chmod 0o600
│   │   ├── models.py           # ScanAuditLog (ORM + índices)
│   │   └── repository.py       # IAuditRepository + AuditRepository + build_scan_record()
│   ├── domain/
│   │   └── models.py           # Dataclasses puras (Producto, LoteProduccion, etc.)
│   ├── infrastructure/
│   │   ├── django_client.py    # DjangoApiClient (ILoteRepository vía HTTP + circuit breaker)
│   │   └── jwt_token_manager.py # Renovación automática de tokens RS256
│   ├── routers/
│   │   ├── validate.py         # POST /validate — Depends(get_audit_repo)
│   │   └── health.py           # GET /health
│   └── services/
│       └── validation_service.py
└── tests/
    ├── unit/
    │   ├── test_audit_repository.py   # 12 tests ISTQB (EP + LSP + BVA)
    │   └── test_validation_service.py
    ├── integration/
    │   └── test_validate_endpoint.py
    └── test_jwt_token_manager.py
```

## Variables de Entorno

| Variable | Descripción |
|---|---|
| `DJANGO_INTERNAL_URL` | URL base del backend Django |
| `SERVICE_NAME` | Nombre del servicio para autenticación JWT |
| `SERVICE_SECRET` | Secret para obtener tokens RS256 |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave pública RSA para verificar tokens |
| `AUDIT_DB_PATH` | Ruta del archivo SQLite de auditoría (default: `/data/logs.db`) |

## Auditoría Local (ISO 27001 A.12.4)

Cada escaneo (válido o inválido) queda registrado en `scan_audit_log`:

| Campo | Tipo | Descripción |
|---|---|---|
| `timestamp` | DATETIME | Momento del evento (UTC) |
| `codigo_scanned` | VARCHAR(200) | Código escaneado |
| `valid` | BOOLEAN | Resultado de validación |
| `reason` | VARCHAR(500) | Motivo si `valid=FALSE` |
| `lote_codigo` | VARCHAR(200) | Código del lote si `valid=TRUE` |
| `producto_nombre` | VARCHAR(500) | Nombre del producto |
| `bodega_nombre` | VARCHAR(200) | Nombre de la bodega |
| `peso_kg` | VARCHAR(50) | Peso disponible |

**Seguridad del archivo (ISO 27001 A.10):**
- `PRAGMA journal_mode=WAL` — consistencia bajo concurrencia
- `PRAGMA synchronous=NORMAL` — durabilidad sin penalidad de rendimiento
- `os.chmod(db_path, 0o600)` — solo el proceso del contenedor puede acceder

## Autenticación con Backend (Fase 13)

El servicio **no accede directamente a SQL Server**. Se autentica con el backend Django mediante tokens RS256 de corta duración:

1. Al arrancar: `POST /api/internal/v1/auth/token/` con `SERVICE_NAME` + `SERVICE_SECRET`
2. En cada validación: `GET /api/internal/v1/scanning/lotes/{codigo}/validate/` con `Authorization: Bearer <token>`
3. El `JWTTokenManager` renueva el token automáticamente cuando quedan <30 s para expirar

**Circuit breaker:** 3 errores consecutivos al backend → `RuntimeError` (evita cascada de reintentos)

## Logs RFC 5424

Todos los eventos de auditoría emiten logs con SD-ELEMENT estructurado:

```
<134>1 2026-06-22T10:00:00Z hostname texcore-scanning 1234 - [texcore@32473 rfc5424_severity="6" table="scan_audit_log"] Registro de auditoría guardado
```

## Tests (ISTQB)

```bash
cd scanning_service
pytest tests/unit/test_audit_repository.py -v
# 12 tests: EP válido, EP fallo BD, LSP Protocol, BVA límites
```

## Despliegue

```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d scanning
```

El servicio espera `backend: service_healthy` antes de arrancar.
