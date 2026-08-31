# Servicio Satélite de Reportes Excel — TexCore

Servicio satélite FastAPI dedicado a formatear reportes masivos a Excel (.xlsx) y CSV. Opera de
forma aislada del backend Django para no bloquear el hilo de Gunicorn con operaciones
CPU-intensivas (Pandas). Se autentica con el backend mediante JWT RS256 y persiste un log de
auditoría local en SQLite.

## Arquitectura

> **Actualizado 2026-08-31** (auditoría de performance): antes, este servicio recibía los
> parámetros de un reporte y él mismo volvía a llamar a la API interna de Django por HTTP para
> obtener los datos — un salto redundante (`backend → reporting_excel → de vuelta al backend`)
> que bajo alta concurrencia era el primer punto de falla (timeout de 30s). Se invirtió el flujo:
> el backend (`inventory/reporting_proxy.py`) consulta sus propios datos EN PROCESO (sin red) y
> le manda a este servicio solo el resultado ya resuelto, para que lo formatee.

```
Backend Django (reporting_proxy)
  consulta sus propios datos EN PROCESO (sin red)
      │  JWT RS256 + {format, filename, report_type, rows}
      ▼
reporting_excel (FastAPI :8002) — POST /generate
      │
      ▼
SQLite local (/data/logs.db, report_audit_log)
```

## Responsabilidades

- Formatear a Excel/CSV los datos de reporte que le manda el backend (inventario, ventas,
  producción, etc. — ver `inventory/reporting_proxy.py` y
  `internal_api/services/report_dispatch.py` en el repo del backend para el mapeo completo).
- Registrar cada solicitud de reporte en la base de datos de auditoría local.

## Tecnologías

| Paquete | Rol |
|---|---|
| FastAPI | Framework HTTP asíncrono |
| Pandas + openpyxl / xlsxwriter | Procesamiento y exportación de datos |
| httpx | Cliente HTTP saliente solo para el healthcheck (`GET /api/health/` en Django) |
| PyJWT (RS256) | Verifica los tokens que manda el backend en cada request |
| SQLAlchemy 2.0 async + aiosqlite | Base de datos de auditoría SQLite |
| Uvicorn | Servidor ASGI |

## Endpoint

### `POST /generate`

Único endpoint de negocio del servicio. Recibe los datos ya resueltos por el backend y devuelve
el archivo formateado.

```json
{
  "format": "xlsx",           // o "csv"
  "filename": "kardex_10027",
  "report_type": "export_kardex",
  "rows": [ { "col1": "valor", "col2": 123 } ]
}
```

Si `rows` viene vacío, responde 200 con un archivo de una sola fila ("No se encontraron datos...")
y el header `X-Report-Empty: true` (nunca 404 — así lo espera el frontend).

### `GET /health`

Liveness check — reporta si además puede alcanzar la API de Django (`degraded` si no, pero
siempre 200: este servicio no depende de Django para operar).

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
│   ├── services/
│   │   ├── report_service.py   # ReportService.generate_from_rows(rows, filename)
│   │   └── report_factory.py   # Elige el OutputFormatter (xlsx/csv)
│   ├── formatters/              # ExcelFormatter, CsvFormatter
│   └── routers/
│       └── generate.py         # POST /generate — único endpoint de negocio
└── tests/
    ├── conftest.py             # bypass_jwt
    ├── test_generate.py
    └── unit/
        ├── test_report_service.py
        └── test_audit_repository.py   # 12 tests ISTQB (EP + LSP + BVA)
```

## Variables de Entorno

| Variable | Descripción |
|---|---|
| `DJANGO_INTERNAL_URL` | URL base del backend Django (solo para el healthcheck) |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave pública RSA para verificar los tokens que manda el backend |
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
