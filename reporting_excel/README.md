# Servicio Satélite de Reportes Excel — TexCore

Servicio satélite FastAPI dedicado a la generación masiva de reportes en formato Excel (.xlsx) y CSV. Opera de forma aislada del backend Django para no bloquear el hilo de Gunicorn con operaciones CPU-intensivas (Pandas). Se autentica con el backend mediante JWT RS256 y persiste un log de auditoría local en SQLite.

## Arquitectura

```
Backend Django (proxy autenticado)
      │  JWT RS256
      ▼
reporting_excel (FastAPI :8002)
      │                    │
      ▼                    ▼
Django Internal API    SQLite local
  (datos vía HTTP)     /data/logs.db
      │                (report_audit_log)
      ▼
texcore_db (SQL Server)
```

## Responsabilidades

- Generar reportes de inventario (kardex, stock actual, valorización, aging, rotación, etc.)
- Generar reportes de ventas por vendedor y gerenciales
- Generar reportes de producción (órdenes, lotes, tendencia)
- Registrar cada solicitud de reporte en la base de datos de auditoría local

## Tecnologías

| Paquete | Rol |
|---|---|
| FastAPI | Framework HTTP asíncrono |
| Pandas + openpyxl / xlsxwriter | Procesamiento y exportación de datos |
| httpx | Cliente HTTP para Django Internal API |
| PyJWT (RS256) | Autenticación con el backend |
| SQLAlchemy 2.0 async + aiosqlite | Base de datos de auditoría SQLite |
| Uvicorn | Servidor ASGI |

## Endpoints (15 total)

### Inventario — `GET /export/{recurso}`

| Endpoint | Descripción |
|---|---|
| `/export/kardex` | Movimientos de inventario (Kardex) |
| `/export/productos` | Catálogo de productos |
| `/export/usuarios` | Lista de usuarios |
| `/export/stock-actual` | Stock actual por bodega |
| `/export/valorizacion` | Valorización del inventario |
| `/export/aging` | Aging de inventario |
| `/export/rotacion` | Rotación de productos |
| `/export/stock-cero` | Productos sin stock |
| `/export/resumen-movimientos` | Resumen de movimientos |

### Vendedores — `GET /vendedores/{id}/...`

| Endpoint | Descripción |
|---|---|
| `/vendedores/{id}/ventas` | Ventas por vendedor |
| `/vendedores/{id}/top-clientes` | Top clientes del vendedor |
| `/vendedores/{id}/deudores` | Deudores del vendedor |

### Gerencial — `GET /gerencial/...`

| Endpoint | Descripción |
|---|---|
| `/gerencial/ventas` | Ventas globales |
| `/gerencial/top-clientes` | Top clientes globales |
| `/gerencial/deudores` | Deudores globales |

### Producción — `GET /produccion/...`

| Endpoint | Descripción |
|---|---|
| `/produccion/ordenes` | Órdenes de producción |
| `/produccion/lotes` | Lotes producidos |
| `/produccion/tendencia` | Tendencia de producción |

Todos los endpoints aceptan `?format=xlsx` (default) o `?format=csv`.

## Estructura

```
reporting_excel/
├── requirements.txt
├── pytest.ini                  # asyncio_mode = auto
├── src/
│   ├── main.py                 # App FastAPI + middleware JWT RS256
│   ├── database/
│   │   ├── engine.py           # SQLite async engine + WAL + PRAGMAs + chmod 0o600
│   │   ├── models.py           # ReportAuditLog (ORM + índices)
│   │   └── repository.py       # IAuditRepository + AuditRepository + build_report_record()
│   ├── infrastructure/
│   │   ├── django_client.py    # DjangoReportRepository (IReportRepository vía HTTP)
│   │   └── jwt_token_manager.py # Renovación automática de tokens RS256
│   └── routers/
│       ├── exports.py          # 9 endpoints inventario — Depends(get_audit_repo)
│       ├── vendedores.py       # 3 endpoints vendedor — Depends(get_audit_repo)
│       ├── gerencial.py        # 3 endpoints gerencial — Depends(get_audit_repo)
│       └── produccion.py       # 3 endpoints producción — Depends(get_audit_repo)
└── tests/
    ├── conftest.py             # bypass_jwt + mock DjangoReportRepository
    ├── test_exports.py
    ├── test_vendedores.py
    └── unit/
        └── test_audit_repository.py   # 12 tests ISTQB (EP + LSP + BVA)
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

Cada solicitud de reporte (exitosa o fallida) queda registrada en `report_audit_log`:

| Campo | Tipo | Descripción |
|---|---|---|
| `timestamp` | DATETIME | Momento del evento (UTC) |
| `requested_by` | VARCHAR(200) | JWT sub claim (quién solicitó) |
| `report_type` | VARCHAR(100) | Tipo de reporte (`kardex`, `ventas_gerencial`, etc.) |
| `endpoint` | VARCHAR(200) | Path de la petición |
| `params_json` | TEXT | Query params serializados |
| `format` | VARCHAR(10) | `'xlsx'` o `'csv'` |
| `success` | BOOLEAN | Si la generación fue exitosa |
| `error_detail` | VARCHAR(1000) | Detalle del error si `success=FALSE` |

**Índices para COBIT MEA01:** `timestamp DESC`, `requested_by`, `report_type`

**Seguridad del archivo (ISO 27001 A.10):**
- `PRAGMA journal_mode=WAL` — consistencia bajo concurrencia
- `os.chmod(db_path, 0o600)` — solo el proceso del contenedor puede acceder

## Autenticación con Backend (Fase 13)

El servicio **no accede directamente a SQL Server**. Usa el mismo mecanismo JWT RS256 que `scanning_service`:

1. Al arrancar: obtiene token RS256 con scope `reports:read`
2. En cada reporte: llama al endpoint correspondiente de `/api/internal/v1/reports/...`
3. El middleware JWT en `main.py` valida el token del usuario Django antes de procesar

**Fix de Token Type Confusion (Fase 13):** el middleware valida `type == "service_access"` e `iss == "texcore"` — un refresh token no puede usarse como access token (ISO 27001 A.9.4).

## Patrón SOLID en los Routers (DIP)

Todos los routers usan `Depends(get_audit_repo)` para inyectar `AuditRepository`:

```python
@router.get("/kardex")
async def export_kardex(
    request: Request,
    background_tasks: BackgroundTasks,
    format: str = "xlsx",
    audit: AuditRepository = Depends(get_audit_repo),   # DIP
):
    success, error_detail = True, None
    try:
        df = await repo.get_kardex(...)
        return StreamingResponse(to_excel(df), ...)
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_report_record(                    # SRP — fábrica separada
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="kardex",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)   # No bloqueante
```

## Tests (ISTQB)

```bash
cd reporting_excel
pytest tests/unit/test_audit_repository.py -v
# 12 tests: EP válido (kardex, gerencial), EP fallo BD, LSP Protocol, BVA params_json=None
```

## Despliegue

```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d reporting_excel
```

El servicio solo es accesible internamente (no expone puerto al host en producción). Las peticiones de reportes del frontend pasan siempre por el backend Django (proxy autenticado).
