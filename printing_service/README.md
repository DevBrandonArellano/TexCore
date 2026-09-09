# Servicio Satélite de Impresión — TexCore

Servicio satélite FastAPI dedicado a la generación de documentos PDF (notas de venta) y etiquetas ZPL (lotes de producción). Opera de forma aislada del backend Django para no bloquear el hilo de Gunicorn con operaciones CPU-intensivas. Persiste un log de auditoría local en SQLite.

## Arquitectura

```
Backend Django
      │
      ▼
printing_service (FastAPI :8003)
      │                  │
      ▼                  ▼
Jinja2 / WeasyPrint   SQLite local
  (PDF / ZPL)         /data/logs.db
                       (print_audit_log)
```

## Responsabilidades

- Renderizar PDFs de notas de venta (WeasyPrint + Jinja2)
- Generar etiquetas ZPL para impresoras térmicas (Zebra)
- Registrar cada solicitud de impresión en la base de datos de auditoría local

## Tecnologías

| Paquete | Rol |
|---|---|
| FastAPI | Framework HTTP asíncrono |
| WeasyPrint | Renderizado PDF desde HTML/CSS |
| Jinja2 | Motor de plantillas |
| SQLAlchemy 2.0 async + aiosqlite | Base de datos de auditoría SQLite |
| Uvicorn | Servidor ASGI |

## Endpoints

### `POST /pdf/nota-venta`

Genera un PDF de nota de venta para el pedido indicado.

**Request body:** `NotaVentaRequest` — `id`, `guia_remision`, líneas de detalle, totales.

**Response:** `application/pdf` (stream) o JSON con URL del archivo.

### `POST /zpl/etiqueta`

Genera una etiqueta ZPL para un lote de producción.

**Request body:** `EtiquetaRequest` — `lote_codigo`, `producto_desc`, `peso_neto`, `tara`, `peso_bruto`, `cantidad_metros` (opcional), y los campos de gobernanza `tipo_evento` (`ORIGINAL`/`REIMPRESION`/`REETIQUETADO`), `version`, `motivo`, `usuario`, `reimpreso` (todos opcionales — ver [docs/modulos/GESTION_ETIQUETAS.md](../docs/modulos/GESTION_ETIQUETAS.md)).

**Response:** `text/plain` con el raw ZPL listo para enviar a la impresora. Si `tipo_evento` es `REIMPRESION`/`REETIQUETADO`, la etiqueta incluye un sello visual `REIMPRESION vN` / `REETIQUETADO vN`.

### `POST /pdf/etiqueta`

Fallback universal para impresoras de etiquetas sin ZPL nativo (no Zebra). Mismo `EtiquetaRequest` que `/zpl/etiqueta`, pero renderiza `etiqueta_label.html` (100×150mm) con la `PdfOutputStrategy` existente.

**Response:** `application/pdf` (stream).

### `POST /pdf/reporte-avance`

Genera el PDF de avance de producción (A4 landscape). **Request body:** `ReporteAvanceRequest` — metadatos de filtros ya resueltos por Django + `detalles` (filas ya agregadas, sin cálculos aquí). Consumido por `internal_api/views/pdf_produccion_views.py::ReporteAvancePdfView`.

### `POST /pdf/reporte-balance`

Genera el PDF de balance de masas mensual (A4 portrait). **Request body:** `BalanceMasasRequest` — `mes`, `detalles` (stock/producción/egresos ya calculados por Django, incluyendo `is_negativo`). Consumido por `internal_api/views/pdf_produccion_views.py::BalanceMasasPdfView`.

### `GET /health`

Retorna `{"status": "healthy"}`.

## Estructura

```
printing_service/
├── requirements.txt
├── pytest.ini                  # asyncio_mode = auto
├── src/
│   ├── main.py                 # App FastAPI + _setup_logging() RFC 5424
│   ├── logging_rfc5424.py      # RFC5424Formatter (facility=19, app_name="texcore-printing")
│   ├── database/
│   │   ├── engine.py           # SQLite async engine + WAL + PRAGMAs + chmod 0o600
│   │   ├── models.py           # PrintAuditLog (ORM + índices)
│   │   └── repository.py       # IAuditRepository + AuditRepository + build_print_record()
│   ├── routers/
│   │   ├── pdf.py              # POST /pdf/nota-venta, /pdf/etiqueta, /pdf/reporte-avance, /pdf/reporte-balance
│   │   ├── zpl.py              # POST /zpl/etiqueta — Depends(get_audit_repo)
│   │   └── health.py
│   ├── schemas/
│   │   └── printing.py         # DTOs Pydantic por caso de uso (ISP)
│   ├── services/
│   │   ├── document_service.py # Cálculos nota de venta (subtotal/IVA/total)
│   │   ├── label_service.py    # Genera imágenes de barcode Code128 + QR (base64)
│   │   ├── zpl_sanitizer.py    # Neutraliza '^'/'~' en texto libre antes de interpolar en ZPL
│   │   └── output_strategy.py  # Strategy Pattern: PdfOutputStrategy / ZplOutputStrategy
│   └── templates/
│       ├── nota_venta.html
│       ├── etiqueta.zpl
│       ├── etiqueta_label.html  # F5: PDF universal 100×150mm (fallback no-Zebra)
│       ├── reporte_avance.html  # Fase 2: avance operativo (A4 landscape)
│       └── reporte_balance.html # Fase 2: balance de masas mensual (A4 portrait)
└── tests/
    └── unit/
        ├── test_audit_repository.py    # 14+ tests ISTQB (EP + LSP + BVA)
        └── test_printing_endpoints.py  # endpoints ZPL/PDF, incl. gobernanza F5
```

## Variables de Entorno

| Variable | Descripción |
|---|---|
| `AUDIT_DB_PATH` | Ruta del archivo SQLite de auditoría (default: `/data/logs.db`) |

## Auditoría Local (ISO 27001 A.12.4)

Cada solicitud de impresión (exitosa o fallida) queda registrada en `print_audit_log`:

| Campo | Tipo | Descripción |
|---|---|---|
| `timestamp` | DATETIME | Momento del evento (UTC) |
| `document_type` | VARCHAR(10) | `'PDF'` o `'ZPL'` |
| `template_used` | VARCHAR(200) | Nombre de la plantilla usada |
| `pedido_id` | INTEGER | ID del pedido (solo PDF) |
| `guia_remision` | VARCHAR(100) | Número de guía (solo PDF) |
| `lote_codigo` | VARCHAR(200) | Código del lote (solo ZPL/etiqueta) |
| `success` | BOOLEAN | Si la generación fue exitosa |
| `error_detail` | VARCHAR(1000) | Detalle del error si `success=FALSE` |
| `usuario` | VARCHAR(150) | *(F5)* Usuario que solicitó la impresión (solo etiquetas) |
| `motivo` | VARCHAR(30) | *(F5)* Código de motivo si es reimpresión/reetiquetado |
| `tipo_evento` | VARCHAR(20) | *(F5)* `ORIGINAL` / `REIMPRESION` / `REETIQUETADO` |
| `version` | INTEGER | *(F5)* Versión de datos de la etiqueta impresa |

**Seguridad del archivo (ISO 27001 A.10):**
- `PRAGMA journal_mode=WAL` — consistencia bajo concurrencia
- `PRAGMA synchronous=NORMAL` — durabilidad sin penalidad
- `os.chmod(db_path, 0o600)` — solo el proceso del contenedor puede acceder

## Patrón SOLID en los Routers (DIP)

Los routers nunca instancian `AuditRepository` directamente. La dependencia se inyecta vía FastAPI:

```python
async def generate_nota_venta_pdf(
    data: NotaVentaRequest,
    background_tasks: BackgroundTasks,
    strategy: PdfOutputStrategy = Depends(get_pdf_strategy),
    audit: AuditRepository = Depends(get_audit_repo),   # DIP
):
    success, error_detail = True, None
    try:
        result = await strategy.generate(data)
    except Exception as exc:
        success, error_detail = False, str(exc)
    finally:
        record = build_print_record(               # SRP — fábrica separada
            document_type="PDF",
            template_used="nota_venta.html",
            success=success,
            pedido_id=data.id,
            guia_remision=data.guia_remision,
            lote_codigo=None,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)   # No bloqueante
```

## Logs RFC 5424

El servicio usa `RFC5424Formatter` con `facility=19` y `app_name="texcore-printing"`. Los logs de auditoría incluyen SD-ELEMENT estructurado:

```
<158>1 2026-06-22T10:00:00Z hostname texcore-printing 1234 - [texcore@32473 rfc5424_severity="6" table="print_audit_log"] Registro de auditoría guardado
```

## Tests (ISTQB)

```bash
cd printing_service
pytest tests/unit/test_audit_repository.py -v
# 14 tests: EP PDF válido, EP ZPL válido, EP fallo BD, LSP Protocol, BVA campos None
```

## Despliegue

```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d printing
```
