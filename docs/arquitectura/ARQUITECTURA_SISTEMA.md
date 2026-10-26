# TexCore — Arquitectura del Sistema
## Referencia Técnica Definitiva

> **Version:** 1.2 | **Fecha:** 2026-10-13
> **Alcance:** Referencia exhaustiva para desarrolladores nuevos y revisiones arquitectónicas
> **Marco de referencia:** ISO/IEC 25010 (Calidad), ISO 27001 A.9 (Seguridad), COBIT 2019 (Gobierno)

---

## Tabla de Contenidos

1. [Vision General del Sistema](#1-vision-general-del-sistema)
2. [Diagrama de Arquitectura C4](#2-diagrama-de-arquitectura-c4)
3. [Servicios y Componentes](#3-servicios-y-componentes)
4. [Autenticacion y Seguridad](#4-autenticacion-y-seguridad)
5. [Modelos de Datos](#5-modelos-de-datos)
6. [APIs y Contratos](#6-apis-y-contratos)
7. [Flujos de Negocio Criticos](#7-flujos-de-negocio-criticos)
8. [Infraestructura y Despliegue](#8-infraestructura-y-despliegue)
9. [Testing y Calidad](#9-testing-y-calidad)
10. [Decisiones de Arquitectura (ADRs)](#10-decisiones-de-arquitectura-adrs)

---

## 1. Vision General del Sistema

### 1.1 Proposito

TexCore es un **sistema de gestión de órdenes de producción** con funciones de MES (Manufacturing Execution System) para la industria textil. Gestiona el ciclo completo de operaciones de cuatro empresas textiles (Interfibra, Ribel, Hiltexpoy, Jaltextiles) bajo una unica plataforma multi-sede.

### 1.2 Capacidades Principales

| Dominio | Descripcion |
|---------|-------------|
| **Produccion** | Ordenes de produccion, lotes, control de maquinaria y operarios, mermas, paros de maquina (OEE), celulas de manufactura flexibles |
| **Inventario** | Kardex en tiempo real, transferencias, alertas de stock minimo por bodega, trazabilidad por lote (QR) |
| **Planificacion** | Plan maestro MTS desde la necesidad de produccion, MRP por sede con sugerencias de compra informativas (ADR-012) |
| **Despacho** | Escaneo de lotes, validacion de pedidos, despacho con incompletos, historial |
| **Ventas** | Pedidos de venta, clientes con credito, facturacion, reportes por vendedor |
| **Tintoreria** | Formulas de color con versionado inmutable (aprobacion, historial y diff), catalogo de procesos por sede, fases de receta, descarga automatica de quimicos, hoja de dosificacion imprimible |
| **Empaquetado** | Configuracion de bultos, etiquetas ZPL para impresoras Zebra, reetiquetado in-situ con supervisor override |
| **Reportes** | Excel y PDF: Kardex, stock, valorizacion, ventas, deudores, tendencias, avance y balance de produccion, guia de remision |
| **Auditoria** | Trazabilidad completa de cambios con AuditLog polimórfico |

### 1.3 Caracteristicas Tecnicas Clave

- **Usuarios simultaneos:** 100 medidos con 0 % de errores; 250 con la VM ampliada (`REQUISITOS_INFRAESTRUCTURA.md`)
- **Multi-sede:** Una sola instancia para todas las sedes, segregacion de datos por `sede_id`
- **Trazabilidad completa:** Cada cambio en modelos criticos genera un `AuditLog`
- **Arquitectura híbrida:** Monolito Django para lógica core + servicios satélites FastAPI para operaciones especializadas
- **Sin acceso directo a BD desde servicios satélites:** Toda comunicación pasa por la API interna con JWT RS256

### 1.4 Stack Tecnologico

| Capa | Tecnologia | Version |
|------|-----------|---------|
| Backend core | Python + Django + Django REST Framework + Gunicorn | 3.12 / 5.2.17 / 3.17.2 / 25.1 |
| Servicios Satélites | FastAPI + Uvicorn | 0.135.1 / 0.42.0 |
| Frontend | React + TypeScript + Vite + TanStack Query | 18.3 / 5.2 / 7.3 / 5.90 |
| Base de datos | Microsoft SQL Server (mssql-django 1.6, ODBC Driver 18) | 2022 |
| Proxy inverso | Nginx Alpine | imagen `nginx:alpine` |
| Contenedores | Docker Engine + Docker Compose | 24+ / 2.21+ |
| Tareas asincronas (solo desarrollo) | Redis + Celery | 6-alpine / 5.4 |
| Autenticacion usuarios | SimpleJWT (HS256) con cookies httpOnly | 5.5.1 |
| Autenticacion servicios | JWT RS256 (PyJWT) con claves RSA 2048 | 2.15.0 |
| Generacion reportes | Pandas + openpyxl / WeasyPrint | 2.2+ / 3.1+ / 70.0 |
| Etiquetas ZPL | Jinja2 templates para impresoras Zebra | 3.1.6 |


---

## 2. Diagrama de Arquitectura C4

### 2.1 Nivel 1 — Contexto del Sistema

```
╔══════════════════════════════════════════════════════════════════════════╗
║                         CONTEXTO TEXCORE                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║   [Operario]         [Bodeguero]       [Jefe de Area]    [Ejecutivo]     ║
║   [Vendedor]         [Despacho]        [Jefe de Planta]  [Admin]         ║
║        │                  │                   │               │          ║
║        └──────────────────┴───────────────────┴───────────────┘          ║
║                                    │                                     ║
║                           HTTPS (Browser)                                ║
║                                    │                                     ║
║                        ┌───────────▼───────────┐                        ║
║                        │    SISTEMA TEXCORE     │                        ║
║                        │  Sistema de gestión de órdenes de producción Textil        │                        ║
║                        └───────────┬───────────┘                        ║
║                                    │                                     ║
║        ┌───────────────────────────┼──────────────────────┐             ║
║        │                           │                       │             ║
║  [Impresora Zebra]         [SQL Server 2022]        [Email/SMTP]         ║
║  (ZPL via red local)       (Base de Datos)          (Notificaciones)     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### 2.2 Nivel 2 — Contenedores (Docker Compose)

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║        REDES DOCKER: dmz_net (nginx, backend, scanning) e internal_net          ║
║        (db, printing, reporting_excel, backend; sin salida a internet)          ║
║                                                                                  ║
║  ┌─────────────────────────────────────────────────────────────────────────┐    ║
║  │  CLIENTE (Browser)                                                       │    ║
║  │  React SPA (compilado, servido por Nginx)                                │    ║
║  └───────────────────────────┬─────────────────────────────────────────────┘    ║
║                              │ HTTPS :443 / HTTP :80                            ║
║  ┌───────────────────────────▼─────────────────────────────────────────────┐    ║
║  │  NGINX (Alpine)  — Puertos: 80 (solo 301 a HTTPS), 443                   │    ║
║  │  · Sirve React SPA desde /usr/share/nginx/html                           │    ║
║  │  · Sirve archivos estaticos Django desde volumen prod_django_static       │    ║
║  │  · Proxy: /api/ → backend:8000                                           │    ║
║  │  · Proxy: /api/scanning/* → scanning:8000                                │    ║
║  │  · Rate limiting, Security Headers, SSL/TLS                              │    ║
║  └──────┬──────────────────────────────────────────────────────────────────┘    ║
║         │                                                                        ║
║  ┌──────▼──────────────────────────┐  expose:8001                               ║
║  │  BACKEND (Django + Gunicorn)    │◄──────────────────┐                        ║
║  │  Puerto interno: 8000            │                    │                        ║
║  │  User: appuser                   │   JWT RS256        │                        ║
║  │  Volumen: staticfiles            │   ← →              │                        ║
║  │  Apps: gestion, inventory,       │         ┌──────────┴───────────┐           ║
║  │        internal_api              │         │  SCANNING (FastAPI)   │           ║
║  │  Depende de: db (healthy)        │         │  expose:8000          │           ║
║  └──────┬─────────────┬────────────┘         └──────────────────────┘           ║
║         │             │ POST /generate y /pdf/* con JWT RS256 (backend → servicio) ║
║         │    ┌────────▼──────────────────┐  expose:8002                         ║
║         │    │  REPORTING EXCEL (FastAPI) │                                       ║
║         │    │  expose:8002               │                                       ║
║         │    │  Pandas + openpyxl         │                                       ║
║         │    └───────────────────────────┘                                       ║
║         │                                                                         ║
║         │    ┌───────────────────────────┐  expose:8001                          ║
║         │    │  PRINTING (FastAPI)        │                                       ║
║         │    │  expose:8001               │                                       ║
║         │    │  ZPL + WeasyPrint (PDF)    │                                       ║
║         │    └───────────────────────────┘                                       ║
║         │                                                                         ║
║  ┌──────▼──────────────────────────┐                                             ║
║  │  DB (SQL Server 2022)            │                                             ║
║  │  expose:1433 (solo red interna)  │                                             ║
║  │  Volumen: mssql_data             │                                             ║
║  │  Healthcheck: sqlcmd SELECT 1    │                                             ║
║  └──────────────────────────────────┘                                             ║
║                                                                                   ║
║  Solo en el compose de desarrollo: REDIS + CELERY WORKER (exportes asincronos)   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

### 2.3 Nivel 3 — Componentes del Backend Django

```
╔════════════════════════════════════════════════════════════════════╗
║              BACKEND DJANGO — Componentes Internos                 ║
╠════════════════════════════════════════════════════════════════════╣
║                                                                    ║
║  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐ ║
║  │   APP: gestion   │  │  APP: inventory   │  │ APP: internal_api│ ║
║  │                  │  │                   │  │                  │ ║
║  │ · Modelos core   │  │ · StockBodega     │  │ · ServiceCred.   │ ║
║  │ · RBAC / Groups  │  │ · MovimientoInv.  │  │ · JWTServiceAuth │ ║
║  │ · AuditLog       │  │ · HistorialDesp.  │  │ · HasScope perm. │ ║
║  │ · AuditMixin     │  │ · AuditLog Inv.   │  │ · /auth/token/   │ ║
║  │ · FormulaColor   │  │ · Kardex          │  │ · /lotes/validate│ ║
║  │ · OrdenProd.     │  │ · Transferencias  │  │ · /reports/*     │ ║
║  │ · LoteProd.      │  │ · Alertas stock   │  │                  │ ║
║  │ · PedidoVenta    │  │ · Requerimientos  │  │                  │ ║
║  │ · EmpaqueService │  │ · MRP por sede    │  │                  │ ║
║  └────────┬─────────┘  └────────┬──────────┘  └────────┬─────────┘ ║
║           │                      │                       │          ║
║           └──────────────────────┴───────────────────────┘          ║
║                                  │                                  ║
║  ┌───────────────────────────────▼──────────────────────────────┐  ║
║  │              INFRAESTRUCTURA TRANSVERSAL                       │  ║
║  │                                                                │  ║
║  │  · AuditMiddleware (get_current_user, get_current_ip)          │  ║
║  │  · CookieJWTAuthentication (httpOnly cookies)                  │  ║
║  │  · texcore_exception_handler (errores sin stack trace)         │  ║
║  │  · RFC5424Formatter (logging estructurado syslog)              │  ║
║  │  · drf_spectacular (OpenAPI 3.1 en /api/docs/)                 │  ║
║  └───────────────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════════════╝
```

### 2.4 Flujo de Request Tipico

```
Browser → Nginx → [Rate Limit] → Django → [Auth] → View → Service → ORM → SQL Server
              ↑                                                              ↓
           TLS/SSL                                                    Respuesta JSON
```

---

## 3. Servicios y Componentes

### 3.1 Nginx (Proxy Inverso y Gateway)

**Imagen:** Alpine multi-stage (node→nginx). El Dockerfile construye el frontend React con Node en la primera etapa y copia el `dist/` al contenedor Nginx en la segunda etapa.

**Funcion:** Unico punto de entrada al sistema. Enruta trafico, aplica seguridad y sirve activos estaticos.

| Ubicacion de configuracion | `nginx/nginx.conf` |
|---------------------------|-------------------|

**Routing detallado:**

En producción (`NGINX_REDIRIGIR_HTTP=1`) el puerto 80 responde 301 hacia HTTPS antes de evaluar cualquier ruta; el enrutamiento siguiente aplica al 443.

| Path | Destino | Rate Limit |
|------|---------|-----------|
| `POST /api/token/` | `backend:8000` | 5 req/min, burst 3 |
| `POST /api/token/refresh/` | `backend:8000` | 10 req/min, burst 5 |
| `/api/internal/v1/reports/produccion/reporte-avance/` y `reporte-balance/` | `backend:8000` (excepción: aceptan la cookie del usuario) | 100 req/s, burst 200 |
| `/api/internal/*` (resto) | **Bloqueado — `return 404`, no llega a `backend`** | — |
| `/api/scanning/*` | `scanning:8000` (path rewritten) | Sin limite especifico |
| `/api/*` | `backend:8000` | 100 req/s, burst 200 |
| `/static/*` | Volumen `prod_django_static` (alias), con respaldo en los activos de React | Sin limite |
| `/trazabilidad*` | SPA React, **solo desde `192.168.1.0/24`** (otras IP: `444`, conexión cerrada) | Sin limite |
| `/` | SPA React (`/usr/share/nginx/html`) | Sin limite |

**`/api/internal/*` bloqueado explicitamente** (`location ^~ /api/internal/ { return 404; }`, antepuesto a `/api/*` en ambos server blocks HTTP/HTTPS): antes de este bloqueo, el catch-all `/api/*` reenviaba tambien las rutas de `internal_api` al backend, exponiendo publicamente el handshake de servicio (`auth/token/`) y los endpoints de reporting/scanning internos a cualquiera en internet. Los servicios satelite (`scanning_service`, `reporting_excel`) llaman a `internal_api` directo por DNS interno de Docker (`http://backend:8000/api/internal/v1/...`), sin pasar por Nginx, asi que el bloqueo no los afecta. Ver `internal_api/README.md` para el resto de las capas de defensa (throttling + IP check en el handshake, scopes, red Docker segmentada).

**Configuracion SSL/TLS:**

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
ssl_ecdh_curve secp384r1;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;  # Evita session ticket reuse (forward secrecy)
```

**Cabeceras de seguridad HTTP:**

| Cabecera | Valor |
|----------|-------|
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (solo HTTPS) |

**Nota arquitectonica critica:** Nginx usa `resolver 127.0.0.11 valid=10s` (DNS interno Docker) y la variable `set $upstream http://backend:8000` para evitar que las IPs de contenedores queden cacheadas al reiniciar backend. Sin este patron, Nginx retiene la IP vieja y responde 502.

---

### 3.2 Backend (Django + Gunicorn)

**Imagen:** `infrastructure/docker/Dockerfile.prod` — Python 3.12, usuario no-root `appuser`, colecta de estaticos en build.

**Configuracion clave (`TexCore/settings.py`):**

```python
INSTALLED_APPS = [
    # Django built-ins ...
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # Requiere migrate
    'corsheaders',
    'drf_spectacular',    # OpenAPI 3.1 en /api/docs/ (solo admin en produccion)
    'gestion.apps.GestionConfig',   # Carga señales de auditoria en ready()
    'inventory.apps.InventoryConfig',
    'internal_api.apps.InternalApiConfig',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('gestion.auth_backends.CookieJWTAuthentication',),
    'EXCEPTION_HANDLER': 'gestion.exceptions.texcore_exception_handler',
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

**Variables de entorno:** el compose de producción fija `DEBUG=0`, `DB_ENGINE=mssql`, `DB_NAME=texcore_db`, `DB_USER=sa`, `DB_HOST=db`, `DB_PORT=1433`, `DB_DRIVER`, `STATIC_ROOT`, `REPORTING_SERVICE_URL` y `PRINTING_SERVICE_URL`. Desde `.env.prod` llegan:

| Variable | Descripcion |
|----------|-------------|
| `SECRET_KEY` | Django secret key (produccion) |
| `FIELD_ENCRYPTION_KEYS` | Claves Fernet del cifrado de datos personales en reposo (RS-19); lista separada por comas, la primera cifra |
| `BLIND_INDEX_KEY` | Clave HMAC del indice ciego de la identificacion (RS-19) |
| `DB_PASSWORD` | Contraseña de `sa` en SQL Server |
| `ALLOWED_HOSTS` | Dominio(s) separados por coma; el primero lo usa el `HEALTHCHECK` |
| `TRAZABILIDAD_BASE_URL` | URL base del QR de cada lote |
| `CORS_ALLOWED_ORIGINS` | Origins permitidos (sin comodin) |
| `CSRF_TRUSTED_ORIGINS` | Origins CSRF confiables |
| `INTERNAL_JWT_PRIVATE_KEY` | Clave privada RSA 2048 (PEM) — solo backend |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave publica RSA 2048 (PEM) |
| `SCANNING_SERVICE_SECRET` | Secret del scanning_service para registrar credencial |
| `REPORTING_SERVICE_SECRET` | Secret del reporting_excel para registrar credencial |

**Middleware stack (orden importa):**

```
SecurityMiddleware → SessionMiddleware → CommonMiddleware →
CorsMiddleware → CsrfViewMiddleware → AuthenticationMiddleware →
MessageMiddleware → XFrameOptionsMiddleware → AuditMiddleware
```

`AuditMiddleware` (custom) captura el usuario autenticado y la IP real del request y los almacena en `threading.local()` para que `AuditableModelMixin.save()` pueda acceder a ellos sin inyeccion explicita.

**Aplicaciones Django:**

| App | Responsabilidad |
|-----|----------------|
| `gestion` | Modelos de dominio, RBAC, auditoria, formulas, produccion, ventas |
| `inventory` | Kardex, stock, movimientos, despacho, requerimientos de compra |
| `internal_api` | API servicio-a-servicio: autenticacion RS256, escaneo, reportes |

---

### 3.3 Scanning Service (FastAPI)

**Puerto:** `expose:8000` (no expuesto al host)
**Tecnologia:** FastAPI + Uvicorn, Python 3.12
**Version:** 3.0.0 — completamente autonomo, sin acceso a BD

**Principio de diseño:** Recibe peticiones de Nginx (`/api/scanning/*`), obtiene un JWT propio, y llama a la API interna de Django para validar lotes. Nunca accede a SQL Server directamente.

**Variables de entorno:**

| Variable | Descripcion |
|----------|-------------|
| `DJANGO_INTERNAL_URL` | `http://backend:8000` |
| `SERVICE_NAME` | `scanning_service` |
| `SERVICE_SECRET` | Secret para autenticarse con Django |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave publica RSA para verificar tokens recibidos |

**Componentes internos:**

```
scanning_service/src/
├── main.py              # App factory FastAPI, middleware RFC5424, singletons
├── infrastructure/
│   ├── jwt_token_manager.py   # Cache de token con renovacion automatica
│   └── django_client.py       # Cliente HTTP httpx hacia Django API interna
├── repositories/
│   └── django_lote_repository.py  # Implementa ILoteRepository via Django API
├── services/
│   └── validation_service.py  # Logica de negocio: validar lote despachable
├── routers/
│   ├── validate.py            # POST /validate/{codigo}
│   └── health.py              # GET /health
└── schemas/
    └── validate.py            # Pydantic: LoteInfo, ValidateResponse
```

**Reglas de validacion de lote (LoteValidationService):**

1. El lote debe existir en el sistema (por codigo de barras)
2. El lote debe tener una OrdenProduccion con `producto_salida` definido
3. El lote debe tener stock activo (`cantidad > 0`) en alguna bodega

**Logging:** RFC5424 estructurado (syslog facility 18, app-name: `texcore-scanning`). Si `/dev/log` existe, tambien emite a syslog del SO.

---

### 3.4 Reporting Excel Service (FastAPI)

**Puerto:** `expose:8002`
**Tecnologia:** FastAPI + Uvicorn + Pandas + openpyxl
**CORS:** Restringido a `http://backend:8000` (no permite browser directo)

**Flujo de datos (desde el fix del 31 de agosto de 2026 — "salto redundante de reportes"):** `reporting_excel` ya NO llama de regreso a Django. El backend (`inventory/reporting_proxy.py`) consulta sus propios datos EN PROCESO (sin red) via `internal_api/services/reporting_data.py` + `report_dispatch.py`, y le hace un único `POST /generate` a `reporting_excel` con el body `{format, filename, report_type, rows}` ya resuelto. `reporting_excel` solo formatea esas filas a Excel/CSV (`ReportService.generate_from_rows()`) — no tiene cliente HTTP saliente de negocio, solo un `httpx.get` de healthcheck contra `/api/health/` de Django.

**Variables de entorno:**

| Variable | Descripcion |
|----------|-------------|
| `DJANGO_INTERNAL_URL` | `http://backend:8000` (usado solo para el healthcheck) |
| `CORS_ALLOWED_ORIGINS` | `http://backend:8000` |

> `SERVICE_NAME`/`SERVICE_SECRET` ya NO aplican a `reporting_excel` (se quitaron de `docker-compose.yml`/`docker-compose.prod.yml` para este contenedor tras el fix del 31 de agosto de 2026): el servicio ya no llama a Django, así que no necesita generar su propio token de servicio. `INTERNAL_JWT_PUBLIC_KEY` **sí sigue aplicando** — ahora en el otro sentido: Django es quien llama `POST /generate` en `reporting_excel`, y el middleware de `reporting_excel` (`main.py`) verifica ese token entrante con esa clave pública (`_get_required_env`, falla al arrancar si falta). `scanning_service` sí sigue usando `SERVICE_NAME`/`SERVICE_SECRET` (ver sección 3.3) con su propio valor.

**Estructura actual:**

```
reporting_excel/src/
├── routers/
│   └── generate.py        → POST /generate  (único endpoint de reporte)
├── services/
│   ├── report_service.py  → ReportService.generate_from_rows(rows, filename)
│   └── report_factory.py  → Instancia el formateador (xlsx/csv)
├── formatters/
│   ├── excel_formatter.py
│   └── csv_formatter.py
└── database/
    └── repository.py      → AuditRepository (auditoría local de reportes generados)
```

No hay paquetes `infrastructure/` ni `repositories/`: `django_client.py`, `jwt_token_manager.py` y el Protocol `IReportRepository` se eliminaron el 31 de agosto de 2026 al quitar las llamadas salientes de negocio hacia Django.

---

### 3.5 Printing Service (FastAPI)

**Puerto:** `expose:8001`
**Tecnologia:** FastAPI + Uvicorn + WeasyPrint (PDF) + Jinja2 (ZPL)
**Acceso a BD:** Ninguno. Recibe datos completos en el payload del request.

**Endpoints:**

Todos los `POST` exigen el JWT RS256 que firma el backend; solo el backend los llama.

| Endpoint | Descripcion |
|----------|-------------|
| `POST /zpl/etiqueta` | Etiqueta ZPL para impresora Zebra a partir de datos del lote |
| `POST /pdf/etiqueta` | Etiqueta en PDF (vista previa / impresora de oficina) |
| `POST /pdf/nota-venta` | Nota de venta |
| `POST /pdf/guia-remision` | Guia de remision del despacho |
| `POST /pdf/historial-despachos` | Historial de despachos |
| `POST /pdf/reporte-avance` | Avance de produccion |
| `POST /pdf/reporte-balance` | Balance de produccion |
| `POST /pdf/produccion-por-producto` | Produccion por producto |
| `POST /pdf/formula-dosificacion` | Hoja de dosificacion de una formula (version oficial o borrador) |
| `GET /health` | Health check del servicio |

**Template ZPL (`etiqueta.zpl`):**

```zpl
^XA
^PW800
^LL400
^FO50,30^ADN,36,20^FD{{ empresa }}^FS
^FO50,75^ADN,18,10^FDProducto: {{ producto_desc }}^FS
^FO50,110^ADN,18,10^FDLote: {{ lote_codigo }}^FS
^FO50,145^ADN,26,15^FDPeso Neto: {{ peso_neto }} {{ unidad }}^FS
^FO50,240^BY3
^BCN,90,Y,N,N          ← Codigo de barras Code128
^FD{{ lote_codigo }}^FS
^FO550,50^BQN,2,5
^FDQA,{{ qr_data }}^FS  ← QR con datos del lote
^XZ
```

**Servicio de empaquetado (`EmpaqueService`):**

El backend Django incluye un servicio dedicado que coordina la generacion de `BultoEmpaque` para un `LoteProduccion`. Aplica una jerarquia de configuracion por prioridad:
1. Configuracion especifica del lote
2. Configuracion del area
3. Configuracion global de la sede

Genera DTO `EtiquetaBulto` que se serializa con `to_print_payload()` y se envia al printing_service.

---

### 3.6 Base de Datos (SQL Server 2022)

**Imagen:** `database/Dockerfile` — `mcr.microsoft.com/mssql/server:2022-latest` más `mssql-tools18` (para el healthcheck y los respaldos con `sqlcmd`)
**Edición:** `MSSQL_PID` (Developer en desarrollo; la edición licenciada, Standard o Enterprise, en producción)
**Acceso:** Solo la red `internal_net` (`expose:1433`, sin `ports:`)
**Volumen:** `mssql_data` (persistente entre reinicios)
**Memoria:** `mem_limit` del contenedor y `MSSQL_MEMORY_LIMIT_MB` salen del mismo `DB_MEMORY_LIMIT_MB`, para que SQL Server no crea tener más RAM de la asignada.

**Conexion Django:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'mssql',     # mssql-django 1.6
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=yes;TrustServerCertificate=yes'
        }
    }
}
```

**Esquema y optimizaciones.** El esquema lo crean las migraciones de Django: `gestion` 0001–0008, `inventory` 0001–0003 e `internal_api` 0001. En cada arranque, el entrypoint del backend ejecuta `scripts/create_db.py`, `migrate` y después `manage.py apply_sql_optimizations`. Este último aplica los scripts de `database/` con la conexión de Django, lote por lote; todos son idempotentes:

| Script | Contenido |
|--------|-----------|
| `V2__optimize_sqlserver2022_texcore.sql` | `READ_COMMITTED_SNAPSHOT` y `ALLOW_SNAPSHOT_ISOLATION` (RCSI: las lecturas de reportes no bloquean las escrituras de planta); CHECK `CK_lote_unidades_empaque_positivo` y `CK_transf_merma_no_negativa`; índices filtrados de pedidos y órdenes activas; índices de Kardex por destino y de transferencias; índice columnstore no agrupado sobre `inventory_movimientoinventario` para agregaciones |
| `V4__indices_reportes_carga_concurrente.sql` | Índices de reportes medidos bajo carga: movimientos por origen y fecha, pedidos por vendedor y fecha, detalle de pedido, stock por bodega y producto |
| `V5__optimizacion_indices_mes.sql` | Índices del MES: corridas activas por sede, genealogía de lotes en ambos sentidos, operaciones por corrida, reservas de lotes, stock comprometido, planes por sede y estado |
| `V6__drop_obsolete_stored_procedures.sql` | Elimina los 21 stored procedures de reportes que dejaron de usarse: los reportes se sirven desde el ORM y `internal_api` |

**Restricciones e índices declarados en los modelos** (viajan con las migraciones): 23 `CheckConstraint` (por ejemplo, cantidades, saldos y stock comprometido no negativos, y porcentajes de mezcla entre 0 y 100), 9 `UniqueConstraint` (por ejemplo, stock único por bodega y producto con o sin lote, y una sola versión oficial por fórmula) e índices compuestos como `idx_mov_bodega_fecha_incl` del Kardex y los de auditoría por fecha y sede (`gestion/0004` y `0008`, hoy dentro de `0003_squashed_0009_paromaquina_origen`; ADR-010).

**Healthcheck:**

```yaml
test: ["CMD-SHELL", "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P '${DB_PASSWORD}' -C -N -Q 'SELECT 1' || exit 1"]
interval: 10s
timeout: 5s
retries: 5
start_period: 120s
```

El backend espera a que el healthcheck sea exitoso antes de arrancar (`condition: service_healthy`).

---

### 3.7 Redis y Celery (solo desarrollo)

El compose de desarrollo (`infrastructure/docker/docker-compose.yml`) levanta `redis` (`redis:6-alpine`) y `celery_worker` (mismo código que el backend, `celery -A TexCore worker`). Con `REPORTES_ASYNC_HABILITADO=true`, los exportes de reportes con `?async=true` se encolan en `gestion/tasks.py` (`async_export_report`).

El compose de **producción no incluye Redis ni Celery**: `REPORTES_ASYNC_HABILITADO` queda en `false` y la API responde 503 a `?async=true`. El frontend no usa el modo asíncrono: todos los exportes se generan al momento.

---

### 3.8 Frontend (React SPA)

**Tecnologia:** React 18 + TypeScript + Vite + TanStack Query + Tailwind CSS 4 (CSS-first, plugin de Vite) + shadcn/ui

**Compilado:** El build de produccion (`npm run build`) genera `dist/` que es copiado a Nginx en la imagen multi-stage.

**Estructura de dashboards por rol:**

| Dashboard | Rol(es) |
|-----------|---------|
| `AdminSistemasDashboard` | admin_sistemas |
| `AdminSedeDashboard` | admin_sede |
| `JefePlantaDashboard` | jefe_planta (incluye Plan Maestro MTS) |
| `JefeAreaDashboard` | jefe_area |
| `EjecutivosDashboard` | ejecutivo (incluye MRP de todas las sedes) |
| `VendedorDashboard` | vendedor |
| `BodegueroDashboard` | bodeguero (incluye MRP de su sede y alertas de stock) |
| `OperarioDashboard` | operario |
| `EmpaquetadoDashboard` | empaquetado |
| `DespachoDashboard` + `HistorialDespachos` (`/despacho/historial`) | despacho |
| `TintoreroDashboard` | tintorero |

La ruta pública `/trazabilidad/:codigo` (`TrazabilidadPorCodigoPage`) abre la ficha de un lote desde su QR; exige sesión iniciada y nginx solo la sirve en la red interna.

**Patrones de estado:**

```typescript
// Estado de servidor (cache + sincronizacion)
const { data, isLoading } = useQuery({
  queryKey: ['stock', bodegaId, page],
  queryFn: () => apiClient.get(`/inventory/stock/?page=${page}`),
})

// Estado de URL (filtros, paginacion, tabs — persistibles y compartibles)
const [searchParams, setSearchParams] = useSearchParams()
const page = parseInt(searchParams.get('page') ?? '1')

// Mutacion con invalidacion de cache
const mutation = useMutation({
  mutationFn: (data) => apiClient.post('/inventory/transferencias/', data),
  onSuccess: () => queryClient.invalidateQueries(['stock']),
})
```

**Autenticacion frontend:** Tokens almacenados en cookies `httpOnly` (`access_token`, `refresh_token`). El browser las envia automaticamente en cada request. `CookieJWTAuthentication` en Django las lee del header de Cookie, no del header `Authorization`. Esto previene acceso de JavaScript malicioso (XSS).

---

## 4. Autenticacion y Seguridad

### 4.1 Capa 1: Autenticacion de Usuarios Finales (SimpleJWT + Cookies httpOnly)

```
Usuario → POST /api/token/ {username, password}
       ← Set-Cookie: access_token=<JWT HS256>; HttpOnly; SameSite=Lax; Secure
       ← Set-Cookie: refresh_token=<JWT>; HttpOnly; SameSite=Lax; Secure

Requests subsiguientes:
Browser → GET /api/inventory/stock/ [Cookie: access_token=...]
Django: CookieJWTAuthentication lee la cookie → valida JWT → autentica usuario
```

**Configuracion SIMPLE_JWT:**

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SECURE': not DEBUG,  # True en produccion (DEBUG=0): solo HTTPS
    'AUTH_COOKIE_SAMESITE': 'Lax',
}
```

**Logout:** El refresh token es agregado a la JWT Blacklist (`rest_framework_simplejwt.token_blacklist`) para invalidarlo inmediatamente. Requiere que la tabla de blacklist exista en BD (`migrate`).

### 4.2 Roles y Permisos (RBAC via Django Groups — 11 Grupos)

| Grupo Slug | Permisos Principales y Modelos Asignados |
|------------|------------------------------------------|
| `admin_sistemas` | Acceso total y administración de todos los modelos (CRUD completo) |
| `admin_sede` | CRUD completo en Sede, Area, CustomUser, Producto, Bodega, OPs, Lotes, Pedidos, Clientes, Stock y Movimientos locales |
| `jefe_planta` | CRUD completo en OPs, Lotes, Transformaciones, Productos, Bodegas, Formulas, Stock y Movimientos de planta |
| `jefe_area` | Add/Change/View en Area, Producto, CustomUser, Stock, Movimientos, OPs, Lotes, Transformaciones y Paros de máquina |
| `operario` | Add/Change/View en LoteProduccion, TransformacionProducto y MovimientoInventario |
| `tintorero` | Add/Change/View en FormulaColor, DetalleFormula, Producto, OPs, Lotes, Transformaciones, Stock y Movimientos |
| `empaquetado` | Add/Change/View en LoteProduccion, OrdenProduccion, StockBodega y MovimientoInventario |
| `despacho` | Add/Change/View en PedidoVenta, DetallePedido, LoteProduccion, Bodega, Stock, Movimientos e HistorialDespacho |
| `bodeguero` | Add/Change/View en StockBodega, MovimientoInventario, Producto, Bodega y LoteProduccion |
| `vendedor` | Add/Change/View en Cliente, PedidoVenta, DetallePedido y Producto |
| `ejecutivo` | Permisos exclusivamente de lectura (`view`) en Producto, Cliente, PedidoVenta, DetallePedido, OrdenProduccion y StockBodega |


Los permisos DRF se generan con `make_group_permission()` (factory interna) para evitar duplicacion de clases.

### 4.3 Capa 2: Autenticacion Servicio-a-Servicio (JWT RS256)

**Proposito:** Permite que los servicios satélite (scanning, reporting) llamen a la API interna de Django con identidad verificada criptograficamente, sin compartir contraseñas de usuarios.

**Generacion de claves:**

```bash
# Imprime INTERNAL_JWT_PRIVATE_KEY e INTERNAL_JWT_PUBLIC_KEY en una línea con \n,
# listas para pegar en .env.prod (usa la librería cryptography, RSA 2048).
python scripts/generate_rsa_keys.py
```

**Distribucion de claves:**

| Clave | Ubicacion |
|-------|----------|
| Privada (firma tokens) | Solo en backend Django (`INTERNAL_JWT_PRIVATE_KEY`) |
| Publica (verifica tokens) | Backend + scanning + reporting_excel (`INTERNAL_JWT_PUBLIC_KEY`) — `reporting_excel` la sigue necesitando para verificar el token que Django le manda al llamar `POST /generate` (ver §3.4); lo que ya no usa desde el 31-ago-2026 es `SERVICE_NAME`/`SERVICE_SECRET` (ya no llama a Django, así que no genera token propio) |

**Flujo de autenticacion de servicio:**

```
scanning_service                     Django Backend
      │                                    │
      │  POST /api/internal/auth/token/    │
      │  Body: {service_name, service_secret}
      │─────────────────────────────────►  │
      │                                    │ 1. Busca ServiceCredential en BD
      │                                    │ 2. Verifica PBKDF2 hash del secret
      │                                    │ 3. Comprueba is_active=True
      │                                    │ 4. Genera JWT RS256 (5 min, scopes)
      │  {access_token: "eyJhbGci..."}    │
      │◄─────────────────────────────────  │
      │                                    │
      │  GET /api/internal/v1/lotes/{codigo}/validate/
      │  Authorization: Bearer <JWT RS256> │
      │─────────────────────────────────►  │
      │                                    │ 1. JWTServiceAuthentication
      │                                    │ 2. jwt.decode(RS256, public_key)
      │                                    │ 3. Verifica type="service_access"
      │                                    │ 4. HasScope("lotes:read")
      │                                    │ 5. Ejecuta logica de negocio
      │  {valid: true, lote: {...}}        │
      │◄─────────────────────────────────  │
```

**Payload del JWT de servicio:**

```json
{
  "iss": "texcore",
  "sub": "scanning_service",
  "type": "service_access",
  "scope": ["lotes:read"],
  "iat": 1748000000,
  "exp": 1748000300,
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Duracion: 5 minutos** (ISO 27001 A.9.4 — tokens de corta duracion para reducir ventana de ataque).

**Modelo `ServiceCredential`:**

```python
class ServiceCredential(models.Model):
    name = models.CharField(max_length=100, unique=True)
    secret_hash = models.CharField(max_length=255)  # PBKDF2
    is_active = models.BooleanField(default=True)
    allowed_scopes = models.JSONField(default=list)  # ["lotes:read", "reports:read"]
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
```

**Scopes definidos:**

| Scope | Uso |
|-------|-----|
| `lotes:read` | Validar lotes en escaneo (scanning_service) |
| `reports:read` | Acceder a datos de reportes (reporting_excel) |

### 4.4 Modelo de Auditoria

**`AuditableModelMixin`:** Mixin abstracto Django que sobreescribe `save()` y `delete()` para generar automaticamente registros `AuditLog`.

**Funcionamiento:**
1. En `__init__`, captura el estado inicial del objeto (`_initial_state`)
2. En `save()`, compara estado actual vs inicial
3. Si hay cambios, crea `AuditLog` con `valor_anterior`, `valor_nuevo`, usuario e IP
4. La IP y el usuario se obtienen del thread-local que populate `AuditMiddleware`

**Modelos que implementan auditoria obligatoria (`requiere_justificacion_auditoria = True`):**
- `StockBodega` — cambios de stock requieren justificacion
- `MovimientoInventario` — trazabilidad del Kardex
- `FormulaColor`, `DetalleFormula` — recetas de produccion
- `Cliente` — limites de credito y datos financieros

**`AuditLog` (modelo polimórfico):**

```
AuditLog
├── usuario FK → CustomUser (SET_NULL)
├── fecha_hora DateTimeField (auto, indexed)
├── ip_address GenericIPAddressField
├── content_type FK → ContentType   ← Relacion polimórfica
├── object_id PositiveIntegerField  ← ID del objeto afectado
├── object_sede_id PositiveIntegerField (denormalizado para queries)
├── accion: CREATE | UPDATE | DELETE
├── valor_anterior JSONField
├── valor_nuevo JSONField
└── justificacion TextField
```

### 4.5 Proteccion contra IP Spoofing

`AuditMiddleware` valida que `X-Forwarded-For` solo sea procesado si `REMOTE_ADDR` proviene de `_TRUSTED_PROXY_NETWORKS` (redes configuradas como proxies confiables). Si el request viene directamente de internet (sin Nginx), se usa `REMOTE_ADDR` directamente.

---

## 5. Modelos de Datos

### 5.1 Diagrama ERD — App `gestion`

```
Sede (1)────────────(N) Area (1)────────────(N) Maquina
 │                        │                        │
 │                        │                   bodega_entrada FK
 │                        │                   bodega_salida FK
 │                        │
 └──(N) Bodega (1)────────┘
         │
         └──(N) StockBodega ←────── LoteProduccion

CustomUser (AbstractUser)
 ├── sede FK → Sede
 ├── area FK → Area
 └── bodegas_asignadas M2M → Bodega

Producto
 ├── tipo: hilo|tela|subproducto (fabricados) · materia_prima|quimico|colorante|insumo (comprados)
 ├── unidad_medida: kg|gr|lb|l|ml|gl|metros|yardas|unidades
 └── stock_minimo Decimal(12,3)   (stock de seguridad en el MRP, ADR-012)

OrdenProduccion
 ├── codigo CharField
 ├── producto_entrada FK → Producto
 ├── producto_salida FK → Producto
 ├── formula_color FK → FormulaColor (nullable, PROTECT)
 ├── version_formula FK → VersionFormula (nullable, PROTECT; se congela al lanzar)
 ├── area FK → Area
 ├── maquina_asignada FK → Maquina
 ├── operario_asignado FK → CustomUser
 ├── bodega_entrada FK → Bodega
 ├── bodega_salida FK → Bodega
 ├── bodega_quimicos FK → Bodega
 ├── peso_neto_requerido Decimal
 ├── estado: pendiente|en_proceso|finalizada
 ├── prioridad: baja|normal|alta|urgente
 └── sede FK → Sede

LoteProduccion
 ├── codigo_lote CharField
 ├── orden_produccion FK → OrdenProduccion
 ├── peso_neto_producido Decimal(12,3)
 ├── peso_merma Decimal(12,3)
 ├── peso_bruto Decimal(12,3)
 ├── tara Decimal(12,3)
 ├── unidades_empaque Integer
 ├── cantidad_metros Decimal(12,4) (telas; nullable)
 ├── presentacion CharField (texto libre: baño, funda, cono, caja...)
 ├── clasificacion_calidad: primera|segunda|saldo
 ├── operario FK → CustomUser
 ├── maquina FK → Maquina
 └── turno CharField

FormulaColor
 ├── codigo CharField            [unique por sede]
 ├── nombre_color CharField      [unique por sede]
 ├── tipo_sustrato: algodon|poliester|nylon|mixto|otro
 ├── version PositiveInteger     (numero de la version oficial vigente; solo lectura)
 ├── estado: en_pruebas|aprobada (solo cambia via POST /aprobar/)
 └── sede FK → Sede

VersionFormula (version inmutable de una receta)
 ├── formula FK → FormulaColor
 ├── numero PositiveInteger      [unique por formula]
 ├── snapshot JSON               (receta completa congelada: fases, procesos, insumos)
 ├── motivo Text (>= 10 caracteres)
 ├── creada_por FK → CustomUser
 ├── fecha DateTime
 └── es_oficial Boolean          [UniqueConstraint condicional: una oficial por formula]
     (solo es_oficial puede cambiar; update del resto y delete se rechazan)

ProcesoTintoreria (catalogo por sede)
 ├── codigo CharField            [unique por sede]
 ├── nombre CharField
 ├── tipo: pre_tratamiento|colorante|auxiliar|lavado|acabado
 ├── activo Boolean
 └── sede FK → Sede

MaquinaProceso (procesos que ejecuta una maquina)
 ├── maquina FK → Maquina
 └── proceso FK → ProcesoTintoreria   [par unico; misma sede]

FaseReceta (fase de FormulaColor)
 ├── formula FK → FormulaColor
 ├── proceso FK → ProcesoTintoreria (PROTECT)
 ├── ciclo PositiveInteger (nullable)
 ├── orden PositiveInteger       [unique por formula]
 ├── temperatura Integer (°C)
 └── tiempo Integer (minutos)

DetalleFormula (quimico por fase)
 ├── fase FK → FaseReceta
 ├── producto FK → Producto (quimico)
 ├── tipo_calculo: gr_l|pct
 └── concentracion/porcentaje Decimal

Cliente
 ├── ruc_cedula CharField
 ├── nombre_razon_social CharField
 ├── limite_credito Decimal(12,3)
 ├── nivel_precio: mayorista|normal
 ├── plazo_credito_dias Integer (0 = contado)
 ├── vendedor_asignado FK → CustomUser
 └── sede FK → Sede
     (cartera_vencida se calcula con una subconsulta en ClienteManager, no se guarda)

PedidoVenta
 ├── cliente FK → Cliente
 ├── vendedor_asignado FK → CustomUser
 ├── guia_remision CharField
 ├── estado: pendiente|despachado_parcial|despachado|facturado
 ├── esta_pagado Boolean
 ├── monto_pagado Decimal(12,3)
 ├── valor_retencion Decimal
 ├── anulado Boolean (indexed)
 └── sede FK → Sede

DetallePedido
 ├── pedido_venta FK → PedidoVenta (related_name='detalles')
 ├── producto FK → Producto
 ├── lote FK → LoteProduccion (nullable)
 ├── cantidad Integer
 ├── piezas Integer
 ├── peso Decimal(12,3)
 ├── precio_unitario Decimal(12,3)
 ├── incluye_iva Boolean
 ├── subtotal Decimal (desnormalizado: peso × precio)
 ├── total_con_iva Decimal (desnormalizado: subtotal × 1.15 si iva)
 ├── cantidad_fabricada Decimal   (lo que ya cubrió producción; resta en la necesidad del MTS)
 └── estado_fabricacion: pendiente|en_proceso|fabricado

ComponenteMezclaOP (receta de mezcla para OP)
 ├── orden FK → OrdenProduccion
 ├── producto FK → Producto
 ├── bodega FK → Bodega
 ├── porcentaje Decimal(5,2)  [CHECK: 0 < porcentaje <= 100]
 └── cantidad_kg Decimal(12,3)

DescargaQuimicoOP
 ├── orden_produccion FK → OrdenProduccion
 ├── producto FK → Producto
 ├── fase FK → FaseReceta
 ├── bodega FK → Bodega
 ├── cantidad_calculada_kg Decimal(12,6)
 ├── cantidad_real_kg Decimal(12,6)
 └── estado: aplicada|revertida

BultoEmpaque
 └── (ver EmpaqueService en gestion/services/empaque_service.py)

ConfiguracionEmpaque
 └── bultos_por_lote, unidades_por_bulto, tara_bulto
     (jerarquia: lote > area > sede global)
```

**Otros modelos de `gestion`** (detalle de campos en `docs/arquitectura-bd/MODELO_DATOS.md`):

| Grupo | Modelos |
|-------|---------|
| Planificacion | `PlanProduccion` (borrador, aprobado, en_ejecucion, cerrado, cancelado), `DetallePlanProduccion` |
| MES | `CorridaProduccion` (CONTINUA, STOCK, PEDIDO), `OperacionProduccion`, `ConsumoMaterial`, `ProduccionSalida`, `MermaDesperdicio`, `GenealogiaLote` |
| Trazabilidad y etiquetas | `MateriaPrimaLote`, `ConsumoMateriaPrima`, `ConsumoLoteDetalle`, `EventoEtiqueta` (original, reimpresion, reetiquetado) |
| Planta | `ParoMaquina` (categorias OEE y `origen` manual/estado, ADR-013), `LineaProduccion`, `ProcessStep`, `AreaProcessStep`, `OrdenProduccionSubproceso`, `EtapaProduccion`, `TransferenciaInterarea`, `TransformacionProducto` |
| Costeo | `TarifaOperario`, `CostoHoraMaquina`, `CostoLoteProduccion` |
| Ventas | `PagoCliente` |
| Configuracion por sede | `ConfiguracionEmpaqueSede` (equivalencias de empaque, ADR-011) |

### 5.2 Diagrama ERD — App `inventory`

```
StockBodega
 ├── bodega FK → Bodega
 ├── producto FK → Producto
 ├── lote FK → LoteProduccion (nullable)
 ├── cantidad Decimal(12,3)
 ├── stock_comprometido Decimal(12,3)  [CHECK: >= 0] (reservado para pedidos MTO)
 └── UNIQUE: (bodega, producto) sin lote
           (bodega, producto, lote) con lote

MovimientoInventario
 ├── fecha DateTimeField (auto, indexed)
 ├── tipo_movimiento: COMPRA|PRODUCCION|TRANSFERENCIA|AJUSTE|
 │                    VENTA|DEVOLUCION|CONSUMO|MERMA
 ├── producto FK → Producto (PROTECT, indexed)
 ├── lote FK → LoteProduccion (nullable)
 ├── bodega_origen FK → Bodega (nullable, PROTECT)
 ├── bodega_destino FK → Bodega (nullable, PROTECT)
 ├── cantidad Decimal(12,3)  [CHECK: >= 0]
 ├── saldo_resultante Decimal(12,3)  [CHECK: >= 0]
 ├── estado_movimiento: solicitado|en_transito|completado|revertido
 ├── documento_ref CharField (indexed)
 ├── usuario FK → CustomUser
 ├── proveedor FK → Proveedor (nullable)
 ├── observaciones CharField
 ├── editado Boolean
 └── fecha_ultima_edicion DateTimeField (nullable)

Index compuesto: (bodega_origen, fecha) INCLUDE (producto, cantidad, saldo_resultante)
→ Optimiza queries de Kardex por bodega

AuditoriaMovimiento (cuando se edita un MovimientoInventario)
 ├── movimiento FK → MovimientoInventario
 ├── usuario_modificador FK → CustomUser
 ├── campo_modificado CharField
 ├── valor_anterior TextField
 ├── valor_nuevo TextField
 └── razon_cambio TextField

HistorialDespacho
 ├── fecha_despacho DateTimeField (auto)
 ├── usuario FK → CustomUser
 ├── pedidos M2M → PedidoVenta (through DetalleHistorialDespachoPedido)
 ├── total_bultos Integer
 ├── total_peso Decimal(12,3)
 ├── observaciones TextField
 └── items_no_despachados JSONField
     {"producto_desc": {"requerido": 100.0, "escaneado": 60.0, "faltante": 40.0}}

DetalleHistorialDespachoPedido (tabla pivote M2M)
 ├── historial FK → HistorialDespacho
 ├── pedido FK → PedidoVenta
 └── cantidad_despachada Decimal(12,3)

DetalleHistorialDespacho (lotes fisicamente despachados)
 ├── historial FK → HistorialDespacho (related_name='detalles', CASCADE)
 ├── lote FK → LoteProduccion (SET_NULL)
 ├── producto FK → Producto (SET_NULL)
 ├── peso Decimal(12,3)
 └── es_devolucion Boolean

MRPEjecucion (una corrida del MRP en una sede — ADR-012)
 ├── sede FK → Sede
 ├── iniciada_por FK → CustomUser
 ├── inicio / fin DateTime
 ├── estado: completada|fallida
 ├── requerimientos, sugerencias_compra, productos_a_producir (conteos)
 ├── advertencias JSON   (p. ej. "OP X sin peso requerido", unidad incompatible)
 └── mensaje_error Text

RequerimientoMaterial (lo que pide cada orden abierta)
 ├── ejecucion FK → MRPEjecucion (CASCADE)
 ├── orden_produccion FK → OrdenProduccion
 ├── producto_requerido FK → Producto
 ├── cantidad_necesaria Decimal(12,3) (kg)
 ├── sede FK → Sede
 └── fecha_requerida Date (fecha planificada de la orden)

OrdenCompraSugerida (informativa, sin estados)
 ├── ejecucion FK → MRPEjecucion (CASCADE)
 ├── producto FK → Producto (comprado)
 ├── sede FK → Sede
 ├── requerido, stock_minimo, stock_disponible Decimal(12,3)
 ├── cantidad_sugerida Decimal(12,3) = requerido + stock_minimo − disponible
 └── UNIQUE: (ejecucion, producto)

La necesidad de producción de los productos fabricados no se guarda: se calcula
en vivo (inventory/services/mrp/necesidades_produccion.py) y la consumen el MRP
y el Plan Maestro MTS.
```

### 5.3 Diagrama ERD — App `internal_api`

```
ServiceCredential (tabla: internal_service_credential)
 ├── name CharField(100) unique
 ├── secret_hash CharField(255)  ← PBKDF2 via Django make_password()
 ├── is_active Boolean
 ├── allowed_scopes JSONField    ← ["lotes:read", "reports:read"]
 ├── created_at DateTimeField (auto)
 └── last_used_at DateTimeField (nullable)
```

### 5.4 Tablas de Referencia — Choices Importantes

**Tipos de movimiento de inventario:**

| Tipo | Descripcion | bodega_origen | bodega_destino |
|------|-------------|---------------|----------------|
| `COMPRA` | Ingreso de proveedor | null | Bodega destino |
| `PRODUCCION` | Salida de proceso productivo | null | Bodega salida OP |
| `TRANSFERENCIA` | Movimiento entre bodegas | Origen | Destino |
| `AJUSTE` | Correccion manual | null o origen | null o destino |
| `VENTA` | Salida por despacho | Bodega stock | null |
| `DEVOLUCION` | Retorno de cliente | null | Bodega receptor |
| `CONSUMO` | Consumo de MP en produccion | Bodega MP | null |
| `MERMA` | Desperdicio del proceso | Bodega | null |

---

## 6. APIs y Contratos

### 6.1 Convenciones Generales

- **Estilo:** REST, JSON, `snake_case` en todos los campos
- **Encoding:** UTF-8
- **Autenticacion:** Cookie `access_token` (usuarios) o `Authorization: Bearer <JWT RS256>` (servicios)
- **Errores de validacion:** `{"field": ["mensaje de error"]}`
- **Errores de negocio:** `{"error": "descripcion"}` o `{"detail": "descripcion"}`
- **Paginacion:** `{"count": N, "next": "url", "previous": "url", "results": [...]}`
- **Tamaño de pagina por defecto:** 50
- **Texto opcional:** los campos de texto sin valor viajan como `""`, nunca `null`; los serializers rechazan `null` en ellos con 400 (ADR-008)

### 6.2 Endpoints Publicos (Usuarios)

#### Autenticacion

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/api/token/` | Login: `{username, password}` → cookies httpOnly |
| `POST` | `/api/token/refresh/` | Renovar access token usando refresh cookie |
| `POST` | `/api/token/logout/` | Logout: blacklist refresh token, limpiar cookies |

#### Inventario (`/api/inventory/`)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `GET` | `/api/inventory/stock/` | Lista StockBodega con filtros |
| `GET/POST` | `/api/inventory/movimientos/` | Listado de movimientos paginado (`page`, `page_size` ≤ 500, filtros `bodega_id`/`producto_id`/`tipo`/`fecha_desde`/`fecha_hasta`) / crear movimiento manual |
| `POST` | `/api/inventory/transferencias/` | Transferencia entre bodegas |
| `POST` | `/api/inventory/transformaciones/` | Transformación de un producto en otro: consume el origen, ingresa el destino (lote nuevo opcional con `nuevo_lote_codigo`) y deja trazabilidad MES *best-effort*, en su propio savepoint. Obligatorios: bodegas, productos, `cantidad` y `_justificacion_auditoria`. Responde 400 si la `cantidad` no es numérica o no es positiva, si falta stock o si el recurso está fuera del alcance de la sede; 201 si la transformación se registra |
| `GET` | `/api/inventory/bodegas/{id}/kardex/` | Kárdex de un producto en la bodega, paginado (`producto_id` obligatorio; `fecha_inicio`, `fecha_fin`, `tipo`, `proveedor_id`, `lote_id`, `page`, `page_size` ≤ 500). Responde `{count, next, previous, saldo_inicial, results}`; cada fila trae `entrada`, `salida` y `saldo` calculado por la base (`KardexService`: `SUM` + `SUM() OVER`). Filtro inválido → 400 |
| `GET` | `/api/inventory/alertas-stock/` | Stock frente al minimo por producto: estado `bajo`/`ok`/`sin_minimo`; filtros `bodega_id` y `search` |
| `POST` | `/api/inventory/process-despacho/` | Procesar despacho (ver flujo §7.2) |
| `GET/POST` | `/api/inventory/historial-despachos/` | Historial de despachos |
| `GET` | `/api/inventory/audit-logs/` | Registros de auditoria |
| `GET` | `/api/inventory/requerimientos-material/` | Requerimientos de la ultima ejecucion MRP por orden (`sede_id`; paginado) |
| `GET` | `/api/inventory/sugerencias-compra/` | Sugerencias de compra informativas (`sede_id`; paginado) |
| `POST` | `/api/inventory/sugerencias-compra/ejecutar-mrp/` | Ejecuta el MRP de forma sincrona: `{sede_id}` o `{todas: true}` (solo roles globales; el bodeguero solo su sede, 403 si pide otra). Responde el resumen de cada ejecucion: estado, conteos y advertencias |
| `GET` | `/api/inventory/sugerencias-compra/ultima-ejecucion/` | Ultima `MRPEjecucion` de la sede |
| `GET` | `/api/inventory/sugerencias-compra/necesidades-produccion/` | Necesidad de produccion en vivo, con su desglose (pedidos, interna, minimo, disponible, en produccion) |

#### Gestion (`/api/`)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `GET/POST` | `/api/ordenes-produccion/` | CRUD de OPs |
| `GET` | `/api/ordenes-produccion/{id}/requisitos_materiales/` | Materiales que pide la OP (misma regla que el MRP: g/L y %, version congelada, quimicos ya descargados) frente al stock disponible |
| `GET/POST` | `/api/planes-produccion/` | Plan Maestro MTS; `necesidades-reposicion/` (necesidad de produccion de la sede del usuario), `crear-desde-alertas/` (el plan nace aprobado en la sede del usuario), `aprobar/`, `cerrar/`, `generar-orden/` |
| `GET/POST` | `/api/corridas-produccion/` | Corridas MES: `iniciar-corrida/`, `registrar-operacion/`, `pausar/`, `finalizar-corrida/`, `revertir-operacion/`, `trazabilidad-lote/` |
| `GET` | `/api/trazabilidad-lote/{codigo_lote}/` | Ficha de trazabilidad del lote (destino del QR) |
| `GET/POST` | `/api/lotes-produccion/` | CRUD de lotes |
| `GET/POST` | `/api/pedidos-venta/` | CRUD de pedidos |
| `GET/POST` | `/api/clientes/` | CRUD de clientes |
| `GET/POST/PUT/DELETE` | `/api/formula-colors/` | Formulas de tintura. Editar una aprobada exige `motivo` y crea la version N+1 oficial; `estado` no se cambia por PUT/POST; borrar una con OPs → 409 |
| `POST` | `/api/formula-colors/{id}/aprobar/` | Crea la version oficial (body `{motivo}`, tintorero/admin) |
| `GET` | `/api/formula-colors/{id}/versiones/` | Historial de versiones (mas reciente primero) |
| `GET` | `/api/formula-colors/{id}/versiones/{n}/` | Una version con su snapshot (sin PUT/DELETE) |
| `GET` | `/api/formula-colors/{id}/versiones/{a}/diff/{b}/` | Cambios de la version A a la B |
| `POST` | `/api/formula-colors/{id}/duplicar/` | Crea una variante en pruebas, sin versiones (body `{codigo, nombre_color}`) |
| `POST` | `/api/formula-colors/{id}/derivar/` · `GET .../derivadas/` | Formula derivada de otra y su listado |
| `POST` | `/api/formula-colors/{id}/versiones/{n}/marcar-oficial/` | Cambia la version oficial |
| `POST` | `/api/formula-colors/{id}/calcular-dosificacion/` | Dosificacion por insumo para `{peso, litros}` |
| `POST` | `/api/formula-colors/{id}/imprimir-dosificacion/` | PDF de la hoja de dosificacion (version oficial; sin oficial, la receta viva marcada «BORRADOR») |
| `GET/POST` | `/api/procesos-tintoreria/` | Catalogo de procesos por sede (`?activo=true`) |
| `GET` | `/api/maquinas/{id}/procesos/` | Procesos que ejecuta una maquina |
| `GET/POST` | `/api/maquinas/` | Maquinaria. El `PATCH` del `estado` abre o cierra el paro automatico (ADR-013) |
| `GET/POST` | `/api/paros-maquina/` | Paros de maquina del area (downtime con reason code OEE) |
| `GET` | `/api/paros-maquina/historial/` | Historial de mantenimiento y paros: resumen por maquina, totales y detalle paginado (`fecha_desde`, `fecha_hasta`, `maquina`, `categoria`, `planificado`) |
| `POST` | `/api/paros-maquina/imprimir-historial/` | PDF del historial con el rango completo (A4 horizontal) |
| `GET/POST` | `/api/bodegas/` | Bodegas |
| `GET/POST` | `/api/sedes/` | Sedes |
| `GET` | `/api/kpis/` | KPIs por rol |

#### Escaneo (via Nginx → scanning_service)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/api/scanning/validate/{codigo}` | Validar lote por codigo de barras |

### 6.3 Endpoints Internos (Servicios)

> Acceso exclusivo con `Authorization: Bearer <JWT RS256>`. Nginx bloquea `/api/internal/*` con 404 (`location ^~ /api/internal/`, ver §3.1) — no llega al backend via el proxy publico. Los servicios satelite llaman directo por DNS interno de Docker.

| Metodo | Endpoint | Scope requerido | Descripcion |
|--------|----------|----------------|-------------|
| `POST` | `/api/internal/auth/token/` | - | Obtener JWT de servicio. `ServiceAuthThrottle` (10/min) + solo IP privada/loopback — protege el camino directo `backend:8000` que el bloqueo de Nginx no cubre. |
| `POST` | `/api/internal/auth/refresh/` | - | Renovar JWT de servicio. Mismo throttle + validacion de IP que `auth/token/`. |
| `GET` | `/api/internal/v1/lotes/{codigo}/validate/` | `lotes:read` | Datos de lote para escaneo |
| `GET` | `/api/internal/v1/reports/kardex/` | `reports:read` | Datos Kardex (misma consulta que la pantalla: `KardexService`; `bodega_id`, `producto_id`, `fecha_desde`, `fecha_hasta`, `lote_codigo`, `tipo`) |
| `GET` | `/api/internal/v1/reports/stock-actual/` | `reports:read` | Stock actual |
| `GET` | `/api/internal/v1/reports/valorizacion/` | `reports:read` | Valorizacion inventario |
| `GET` | `/api/internal/v1/reports/aging/` | `reports:read` | Antigüedad de cartera |
| `GET` | `/api/internal/v1/reports/rotacion/` | `reports:read` | Rotacion de inventario |
| `GET` | `/api/internal/v1/reports/stock-cero/` | `reports:read` | Productos sin stock |
| `GET` | `/api/internal/v1/reports/resumen-movimientos/` | `reports:read` | Resumen de movimientos |
| `GET` | `/api/internal/v1/vendedores/{id}/ventas/` | `reports:read` | Ventas por vendedor |
| `GET` | `/api/internal/v1/vendedores/{id}/top-clientes/` | `reports:read` | Top clientes del vendedor |
| `GET` | `/api/internal/v1/vendedores/{id}/deudores/` | `reports:read` | Deudores del vendedor |
| `GET` | `/api/internal/v1/gerencial/ventas/` | `reports:read` | Ventas gerenciales |
| `GET` | `/api/internal/v1/gerencial/top-clientes/` | `reports:read` | Top clientes gerencial |
| `GET` | `/api/internal/v1/gerencial/deudores/` | `reports:read` | Deudores gerencial |
| `GET` | `/api/internal/v1/produccion/ordenes/` | `reports:read` | Ordenes de produccion |
| `GET` | `/api/internal/v1/produccion/lotes/` | `reports:read` | Lotes de produccion |
| `GET` | `/api/internal/v1/produccion/tendencia/` | `reports:read` | Tendencia de produccion |
| `GET` | `/api/internal/v1/reports/productos/` · `reports/usuarios/` | `reports:read` | Catalogo de productos y usuarios |
| `POST` | `/api/internal/v1/reports/produccion/reporte-avance/` · `reporte-balance/` | `reports:read`, o cookie de jefe de planta, jefe de area, administradores o ejecutivo | PDF de avance y balance (unica excepcion publicada por nginx, §3.1) |
| `GET` | `/api/internal/v1/planta/pulso-diario/` | `reports:read` | Pulso diario de planta |

Desde el 31-ago-2026 `reporting_excel` ya no llama a estos endpoints de reportes: el backend ejecuta las mismas funciones (`internal_api/services/reporting_data.py`) en proceso y le envia las filas a `POST /generate` (§7.3). Los endpoints siguen disponibles para integraciones con scope `reports:read`.

### 6.4 Respuestas de Error Estandar

```json
// Error de validacion DRF (400)
{
  "codigo_lote": ["Este campo es requerido."],
  "peso": ["Ensure this value is greater than or equal to 0."]
}

// Error de negocio (400)
{"error": "El lote ya tiene bultos generados"}

// No autenticado (401)
{"detail": "Authentication credentials were not provided."}

// Sin permiso (403)
{"detail": "You do not have permission to perform this action."}

// Conflicto — incompletos en despacho (409)
{
  "items_incompletos": {
    "Hilo Nylon 40/2": {"requerido": 150.0, "escaneado": 90.0, "faltante": 60.0}
  }
}

// Rate limit excedido (429)
{"detail": "Request was throttled."}
```

### 6.5 Documentacion Interactiva

Disponible en `/api/docs/` (solo para `IsAdminUser` — en produccion requiere login de admin).

```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'TexCore API',
    'DESCRIPTION': 'Sistema Integral de Gestion Textil — API REST',
    'VERSION': '1.0.0',
}
```

---

## 7. Flujos de Negocio Criticos

### 7.1 Flujo de Produccion

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FLUJO DE PRODUCCION                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. JEFE DE AREA crea OrdenProduccion                                │
│     POST /api/ordenes-produccion/                                    │
│     {codigo, producto_entrada, producto_salida, peso_neto_requerido, │
│      area, maquina_asignada, operario_asignado, formula_color?}      │
│     Estado inicial: "pendiente"                                      │
│                                                                      │
│  2. (Opcional) JEFE DE AREA configura receta de mezcla               │
│     POST /api/ordenes/{id}/componentes-mezcla/                       │
│     [{producto, bodega, porcentaje, cantidad_kg}]                    │
│     Validacion: sum(porcentaje) == 100                               │
│                                                                      │
│  2b. LANZAMIENTO: al salir de "pendiente" (1er lote o PATCH estado)  │
│     OrdenProduccion.save() congela version_formula = version oficial │
│     de la formula. Sin version oficial → 400 y se revierte todo.     │
│     Una OP lanzada ya no cambia de formula ni de version.            │
│                                                                      │
│  3. (Opcional) TINTORERIA descarga quimicos automaticamente          │
│     Sobre la version congelada: g/L × litros de baño, % × kg de      │
│     material (sin litros: relacion de baño 1:10)                     │
│     → DescargaQuimicoOP "aplicada" + MovimientoInventario CONSUMO    │
│     → StockBodega de quimicos decrementado                           │
│     (el MRP ya no vuelve a pedir esos quimicos)                      │
│                                                                      │
│  4. OPERARIO registra LoteProduccion                                 │
│     POST /api/lotes-produccion/                                      │
│     {orden_produccion, codigo_lote, peso_neto_producido,             │
│      peso_merma, maquina, turno, hora_inicio, hora_final,            │
│      clasificacion_calidad, presentacion, unidades_empaque}          │
│     → MovimientoInventario PRODUCCION creado                         │
│     → StockBodega en bodega_salida incrementado                      │
│                                                                      │
│  5. OPERARIO/EMPAQUETADOR genera bultos                              │
│     POST /api/lotes/{id}/generar-bultos/                             │
│     EmpaqueService resuelve ConfiguracionEmpaque (jerarquia)         │
│     → N BultoEmpaque creados                                         │
│     → N EtiquetaBulto DTOs generados                                 │
│                                                                      │
│  6. Sistema envia a printing_service (JWT RS256 del backend)        │
│     POST http://printing:8001/zpl/etiqueta                           │
│     → Etiqueta ZPL retornada                                         │
│     → Impresora Zebra imprime etiqueta fisica                        │
│                                                                      │
│  7. Lote queda DISPONIBLE para despacho                              │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 Flujo de Despacho (con validacion de incompletos)

```
┌──────────────────────────────────────────────────────────────────────┐
│                      FLUJO DE DESPACHO                               │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  FASE 1: SELECCION DE PEDIDOS                                        │
│  ─────────────────────────────                                       │
│  Encargado Despacho → DespachoDashboard                              │
│  GET /api/pedidos-venta/?estado=pendiente                            │
│  Selecciona 1..N pedidos a despachar en esta salida                  │
│                                                                      │
│  FASE 2: ESCANEO DE LOTES (por cada caja/fardo fisico)               │
│  ─────────────────────────────────────────────────────               │
│                                                                      │
│  Frontend → POST /api/scanning/validate/{codigo_barras}              │
│             [Cookie: access_token] → Nginx (rate limit) →            │
│             scanning:8000/validate/{codigo_barras}                   │
│                                                                      │
│    scanning_service:                                                  │
│    a) JWTTokenManager obtiene/renueva token propio (TTL 5min)        │
│    b) GET /api/internal/v1/lotes/{codigo}/validate/                  │
│       Authorization: Bearer <JWT RS256>                              │
│    c) Django: JWTServiceAuthentication + HasScope("lotes:read")      │
│    d) ValidateLoteView → LoteValidationService:                      │
│       - Lote existe?                                                  │
│       - Tiene orden_produccion.producto_salida?                       │
│       - Tiene stock > 0?                                              │
│    e) Respuesta: {valid, lote: {codigo, producto, peso, bodega}}      │
│                                                                      │
│    Frontend acumula lotes escaneados en estado local                 │
│                                                                      │
│  FASE 3: CONFIRMACION DE SALIDA (primera pasada)                     │
│  ────────────────────────────────────────────────                    │
│  Frontend → POST /api/inventory/process-despacho/                    │
│  {                                                                    │
│    pedidos: [id1, id2],                                              │
│    lotes: [{codigo, producto_id, peso, bodega_id}, ...],             │
│    confirmar_incompleto: false                                        │
│  }                                                                   │
│                                                                      │
│  Backend._calcular_incompletos():                                    │
│  - Suma DetallePedido.peso por producto (requerido)                  │
│  - Compara vs sum(lotes.peso) por producto (escaneado)               │
│  - Si hay faltantes → HTTP 409:                                      │
│    {"items_incompletos": {"Hilo Azul": {req:150, esc:90, falt:60}}} │
│                                                                      │
│  FASE 4 (si hay faltantes): DECISION DEL USUARIO                     │
│  ────────────────────────────────────────────────                    │
│  Frontend muestra modal con tabla de faltantes                       │
│  Usuario puede:                                                       │
│    A) Ir a buscar mas lotes → vuelve a Fase 2                        │
│    B) Confirmar despacho incompleto → Fase 5                         │
│                                                                      │
│  FASE 5: DESPACHO ATOMICO (transaction.atomic())                     │
│  ───────────────────────────────────────────────                     │
│  Frontend → POST /api/inventory/process-despacho/                    │
│  { ...mismo payload..., confirmar_incompleto: true }                 │
│                                                                      │
│  Backend (transaction atomica):                                      │
│  1. Crea HistorialDespacho                                           │
│  2. Crea DetalleHistorialDespachoPedido[] (1 por pedido)             │
│  3. Por cada lote escaneado:                                         │
│     a. Crea DetalleHistorialDespacho                                 │
│     b. Crea MovimientoInventario VENTA                               │
│     c. StockBodega.cantidad = 0 (lote despachado completamente)      │
│  4. PedidoVenta.estado = "despachado" para cada pedido               │
│  5. Si hubo incompletos: guarda en HistorialDespacho.items_no_despachados│
│                                                                      │
│  Si cualquier paso falla → ROLLBACK completo (atomicidad ACID)       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.3 Flujo de Generacion de Reportes Excel

```
┌──────────────────────────────────────────────────────────────────────┐
│                    FLUJO DE REPORTES EXCEL                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Usuario → EjecutivosDashboard → Click "Exportar Kardex"         │
│                                                                      │
│  2. Frontend → GET /api/reporting/kardex/?bodega=5&desde=2026-01-01  │
│     [Cookie: access_token → usuario autenticado]                     │
│                                                                      │
│  3. Django (reporting_proxy.py), TODO EN PROCESO, sin red:           │
│     a. Valida permisos del usuario (rol ejecutivo/bodeguero)         │
│     b. report_dispatch.resolve_report(report_path, params) →         │
│        llama la función pura correspondiente de                      │
│        internal_api/services/reporting_data.py (misma lógica que     │
│        antes tenían las vistas HTTP, ahora invocada directo)         │
│        → obtiene (rows, filename)                                    │
│     c. _json_safe(rows) serializa Decimal/datetime a tipos JSON      │
│     d. UN SOLO HTTP POST a reporting_excel:8002/generate              │
│        Body: {format, filename, report_type, rows}                   │
│        Authorization: Bearer <JWT RS256 firmado por el backend>      │
│        (reporting_excel lo verifica con la clave publica y no        │
│        vuelve a llamar a Django)                                     │
│                                                                      │
│  4. reporting_excel recibe request (routers/generate.py):            │
│     a. ReportService.generate_from_rows(rows, filename)              │
│     b. pd.DataFrame(rows) → formatter (xlsx/csv) → bytes del archivo │
│     (no hay paso de ida y vuelta a Django — las filas ya venían      │
│     resueltas en el body)                                             │
│                                                                      │
│  5. reporting_excel retorna blob xlsx al backend Django              │
│                                                                      │
│  6. Backend Django retorna blob al frontend con:                     │
│     Content-Type: application/vnd.openxmlformats-officedocument...   │
│     Content-Disposition: attachment; filename="kardex_2026.xlsx"     │
│                                                                      │
│  7. Browser descarga el archivo Excel automaticamente                │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.4 Flujo de Autenticacion de Servicio (Token Refresh Automatico)

```
scanning_service arranca:
  JWTTokenManager.__init__() → token = None, expires_at = 0

Primera llamada a validate:
  JWTTokenManager.get_token()
    → token expirado (None) → llama _refresh_token()
      → POST /api/internal/auth/token/ {service_name, service_secret}
      → Guarda token + expires_at = now + 300s - 30s (margen)

Llamadas subsiguientes (dentro de los 4.5 min):
  JWTTokenManager.get_token()
    → token vigente → retorna inmediatamente (sin HTTP)

A los 4.5 min, siguiente llamada:
  JWTTokenManager.get_token()
    → token por vencer → _refresh_token() en background
    → Nuevo token sin corte de servicio
```

---

## 8. Infraestructura y Despliegue

### 8.1 Docker Compose (Produccion)

**Archivo:** `infrastructure/docker/docker-compose.prod.yml`

```
Servicios y sus dependencias:
nginx → backend (started)
backend → db (healthy)
scanning → backend (started)
reporting_excel → backend (started)
printing (independiente)
```

**Proyecto de Compose:** `texcore-prod` (scripts, workflows y guía usan el mismo nombre, así que los contenedores son `texcore-prod-<servicio>-1`).

**Redes Docker** (segmentadas; la red plana por defecto de Compose ya no se usa):

| Red | `internal` | Miembros | Proposito |
|-----|-----------|----------|-----------|
| `dmz_net` | `false` | `nginx`, `backend`, `scanning` | nginx proxea directo a `backend` (`/api/`) y a `scanning` (`/api/scanning/`) — solo nginx publica puertos al host (80/443). |
| `internal_net` | `true` | `backend`, `db`, `printing`, `reporting_excel` | Sin ruta de salida a internet; `db`/`printing`/`reporting_excel` no son alcanzables desde nginx ni desde `scanning`. `backend` esta en ambas redes — es el unico puente. |

`db` conserva un `dns: [8.8.8.8]` heredado que no tiene efecto dentro de `internal_net`; el stack completo arranca con los seis contenedores `healthy` (verificado el 13-oct-2026).

**Volumenes:**

| Volumen | Descripcion | Montaje |
|---------|-------------|---------|
| `mssql_data` | Datos SQL Server | `/var/opt/mssql` (db) |
| `prod_django_static` | Archivos estaticos Django | `/home/appuser/app/staticfiles` (backend) + `/var/www/django_static:ro` (nginx) |
| `printing_audit_data`, `scanning_audit_data`, `reporting_audit_data` | Auditoria local (SQLite) de cada servicio satelite | `/data` |
| `./nginx/certs` | Certificados SSL | `/etc/nginx/certs:ro` (nginx) |

**Politica de reinicio:** `restart: always` en todos los servicios.

### 8.2 Estrategia de Imagenes Docker

| Servicio | Imagen en el GitLab Container Registry | Tag |
|----------|----------|-----|
| backend | `<host>:5050/<grupo>/texcore/backend:<SHA>` | SHA commit |
| nginx | `<host>:5050/<grupo>/texcore/nginx:<SHA>` | SHA commit |
| scanning | `<host>:5050/<grupo>/texcore/scanning_service:<SHA>` | SHA commit |
| reporting_excel | `<host>:5050/<grupo>/texcore/reporting_excel:<SHA>` | SHA commit |
| printing | `<host>:5050/<grupo>/texcore/printing_service:<SHA>` | SHA commit |

Las imagenes son **inmutables por SHA** — el mismo SHA siempre corresponde al mismo binario. En el registro, `latest` apunta a la ultima imagen publicada. En el servidor, antes de cada deploy, el CD etiqueta como `:backup` las cinco imagenes en ejecucion; `rollback.yml` las usa si no se le indica un SHA.

**Despliegue sin CI/CD:** `scripts/deploy_production.sh` (o `.ps1`) construye las imagenes en el servidor con `CI_REGISTRY_IMAGE`/`TAG` de `.env.prod`. Ver `GUIA_DESPLIEGUE.md`.

### 8.3 CI/CD — GitLab CI

GitLab CE autoalojado es la plataforma principal del CI/CD y del registro de imagenes (§5.3 de la tesis; decision en `ADR_014_GITLAB_CI_AUTOALOJADO.md`). GitHub es un espejo del codigo y no ejecuta nada. Instalacion, runners y variables: `GUIA_GITLAB.md`.

**Flujo de ramas** (el job `ramas:politica` exige que los MR a `master` vengan de `staging`):

```
feature/* ─── MR ──► staging ─── (CI pasa) ──► MR staging → master
                        CI                             CI re-corre
                                                          │
                                                    merge a master
                                                          │
                                       build → scan → staging efimero
                                                          │
                                  deploy:produccion (manual, un clic)
```

**Archivo `.gitlab-ci.yml` — Etapas:** `lint → test → build → scan → staging → deploy → rollback`.

```
ramas:politica · lint:pipeline (yamllint + shellcheck) ───────┐
lint:backend (Ruff, detect-secrets, mypy) ────────────────────┤
lint:istqb (convencion de nombres y tecnicas ISTQB) ──────────┤
lint:permisos (auditor de rutas, RNF-02) ─────────────────────┤
sast:semgrep ─────────────────────────────────────────────────┤
test:backend (needs: lint:backend; SQL Server 2022 como service) ┤
test:scanning · test:printing · test:reporting ───────────────┤→ build (solo master)
test:frontend (tsc, ESLint, Vitest con cobertura, build) ─────┤
audit:dependencias (pip-audit) · audit:npm ───────────────────┘
build:validacion (solo staging: construye backend y nginx sin publicar)
```

**Runners** (`infrastructure/gitlab/`): `texcore-ci` (sin etiqueta, sin socket de Docker), `texcore-staging` (etiqueta `staging`, protegido: construye y levanta el staging efimero) y `texcore-produccion` (etiqueta `produccion`, en la VM, protegido). Un job de feature nunca llega a un runner con socket.

**Herramientas de analisis estatico:**

| Herramienta | Proposito | Bloquea merge? |
|-------------|-----------|----------------|
| Ruff 0.16.10 | Estilo, errores y reglas de seguridad `S` (reemplaza a flake8 y bandit; ADR-015) | Si |
| Semgrep 1.179.0 | SAST (`p/django`, `p/python`, `p/secrets`, `p/jwt`), severidad ERROR | Si |
| detect-secrets 1.5.0 | Credenciales expuestas; la linea base debe estar auditada por completo | Si |
| mypy 1.15.0 | Tipos estaticos de `gestion`, `inventory` e `internal_api` | Si |
| yamllint + shellcheck | Sintaxis del pipeline y de los scripts | Si |
| `auditar_convencion_pruebas.py` | Convencion de nombres ISTQB y tecnica declarada en cada archivo de prueba | Si |
| `auditar_permisos_backend.py` | Ruta publica fuera de la lista blanca (RNF-02) | Si |
| pip-audit 2.10.1 | CVEs en las dependencias de los 4 servicios | Si (`audit:dependencias`, `seguridad:dependencias`) |
| `npm audit` | CVEs en dependencias JS: moderada+ en produccion, critica en desarrollo | Si (`audit:npm`, `seguridad:npm`) |
| Trivy 0.75.0 | CVEs en las 6 imagenes Docker, por digest | Si (`scan:trivy`, `seguridad:contenedores`) |

**Release en `master`** (se dispara en el merge del MR `staging -> master`):

```
build:imagenes (matriz de 6 imagenes sin cache y con bases actualizadas; push al
                GitLab Container Registry; cosign attest (SLSA) + cosign sign con clave)
    │
imagenes:unir (fija la referencia por digest: imagenes.env, una linea por servicio)
    │
scan:trivy (las 6 imagenes por digest; reporte JSON como artefacto)
    │
staging:efimero (scripts/staging_efimero.sh: las 6 imagenes + SQL Server desechable,
                 base desde cero, siembra y scripts/smoke_test.py con los 11 roles)
    │
deploy:produccion (MANUAL, runner `texcore-produccion`, environment `production`:
                   cosign verify --key cosign.pub -> scripts/desplegar_release.sh:
                   respaldo :backup de las 6 imagenes, pull por digest, respaldo de la
                   BD, preparar_bd.sh y up -d --wait; luego GET https://<host>/api/health/
                   y /api/scanning/health, 15 intentos; aviso por webhook opcional)
```

Las imagenes se construyen **una sola vez**: la misma, por digest, es la que se escanea, se prueba en staging, se firma y se despliega. Las migraciones salieron del `entrypoint.sh` (`MIGRAR_AL_INICIAR=0` en produccion): corren una vez por despliegue, despues del respaldo de la base y antes de levantar los servicios.

**`rollback:produccion`** (manual, «un solo clic»): vuelve a las imagenes de un SHA anterior (`ROLLBACK_SHA`, verificando su firma) o a las `:backup`. El motivo (`ROLLBACK_MOTIVO`) llega por variable y solo se usa como argumento de `jq`. Corre en el mismo runner propio que el deploy (sin SSH), no toca `.env.prod` y espera a que los servicios esten sanos.

**Pipelines programados** (lunes): `seguridad` (pip-audit, npm audit y Trivy de las imagenes `latest`), `gobierno` (metricas DORA con `scripts/metricas_dora.py` sobre la API de GitLab) y `dependencias` (Renovate, MR hacia `staging`).

**Configuracion requerida en GitLab** (los secretos de la aplicacion no pasan por GitLab: viven en el `.env.prod` del servidor, y el deploy no usa SSH sino un runner propio):

```
COSIGN_PRIVATE_KEY / COSIGN_PASSWORD  # firma de las imagenes (protegidas); cosign.pub va en el repositorio
GITLAB_CA_CRT                         # CA del certificado propio (archivo)
PRODUCCION_HOST                       # Dominio o IP del servidor (URL del environment)
TEXCORE_DIR                           # Directorio del servidor con .env.prod, nginx/certs y respaldos/
GITLAB_TOKEN · RENOVATE_TOKEN         # DORA (read_api) y Renovate
DEPLOY_NOTIFY_WEBHOOK                 # (Opcional) webhook de notificaciones
runner `texcore-produccion`           # Etiqueta `produccion` (GUIA_GITLAB.md §6)
```

### 8.4 GitHub (espejo)

El 5-oct-2026 se retiro un primer `.gitlab-ci.yml` porque el repositorio vivia en GitHub y los dos pipelines divergian (Node 20 frente a 24, escaneo de satelites solo en GitLab). El 20-oct-2026 se invirtio la decision (ADR-014): GitLab es la plataforma principal, como pide la tesis, y los workflows de GitHub Actions y Dependabot se eliminaron en el mismo cambio. GitHub conserva una copia del codigo por *push mirror*; no ejecuta nada. El 26-oct-2026 se reescribieron `MES`, `staging` y `master` en GitHub para quitar los coautores de IA de los mensajes de commit, y se eliminó la rama `main`; la rama por defecto es `master`. Ver el `CHANGELOG.md` del 5-oct, 13-oct, 14-oct, 20-oct y 26-oct-2026.

### 8.5 Despliegue y operacion manual

Instalacion desde cero, actualizacion, respaldos, restauracion y rollback manual: `docs/arquitectura/GUIA_DESPLIEGUE.md`.

### 8.6 Health Checks

| Servicio | Endpoint | Comando |
|----------|----------|---------|
| db | `SELECT 1` via sqlcmd | `healthcheck` del compose (start_period 120 s) |
| backend | `/api/health/` | `HEALTHCHECK` de `Dockerfile.prod` (`infrastructure/docker/healthcheck.py`; start_period 600 s para migraciones largas) y curl en el CD |
| nginx | `https://127.0.0.1/` | `HEALTHCHECK` de `nginx/Dockerfile` |
| scanning | `/health` | `HEALTHCHECK` de su Dockerfile |
| printing | `/health` | `HEALTHCHECK` de su Dockerfile |
| reporting_excel | `/health` | `HEALTHCHECK` de su Dockerfile |

Como todos los servicios tienen healthcheck, `docker compose up --wait` (scripts y workflows) termina solo cuando los seis estan `healthy`.

### 8.7 Logging

**Estandar:** RFC 5424 (IETF Syslog Protocol)

**Formato:**
```
<PRI>1 TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD-ELEMENT] MSG
```

| Servicio | Facility | App-Name |
|----------|---------|---------|
| Django backend | 16 (local0) | `texcore-backend` |
| scanning_service | 18 | `texcore-scanning` |
| Otros servicios satélite | - | Nombre del servicio |

**Destinos:** stdout (capturado por Docker), archivo rotativo en `/logs/` (backend), syslog del SO si `/dev/log` existe.

---

## 9. Testing y Calidad

### 9.1 Distribucion de Tests

Conteo del 13-oct-2026:

| Suite | Framework | Pruebas | Cobertura minima (gate del CI) |
|-------|-----------|---------|-------------------------------|
| Backend (`gestion`, `inventory`, `internal_api`) | Django test runner sobre SQL Server 2022 | 1814 | 90 % de lineas y ramas (`.coveragerc`); medida: 92,2 % |
| scanning_service | pytest + httpx | 58 | 90 % |
| reporting_excel | pytest + httpx | 76 | 90 % |
| printing_service | pytest + httpx | 107 | 95 % |
| Frontend | Vitest + Testing Library | 1972 | lineas 95 %, funciones 91 %, ramas 89 %, sentencias 94 % |

### 9.2 Convencion de Nomenclatura (ISTQB CTFL v4.0)

```
test_[objeto]_dado_[contexto]_cuando_[accion]_entonces_[resultado]
```

**Ejemplos reales del proyecto:**

```python
def test_cliente_dado_limite_credito_negativo_cuando_guardar_entonces_falla_constraint_bd():
    ...

def test_orden_dado_estado_pendiente_cuando_mover_a_en_proceso_entonces_transicion_exitosa():
    ...

def test_lote_dado_stock_cero_cuando_validar_escaneo_entonces_retorna_valid_false():
    ...
```

### 9.3 Tecnicas de Testing Aplicadas

| Tecnica | Aplicacion |
|---------|-----------|
| **Particion de Equivalencia (EP)** | Valores validos/invalidos de campos (peso, cantidad, porcentaje) |
| **Analisis de Valor Limite (BVA)** | Limite de credito de cliente, stock minimo, peso >= 0 |
| **Tabla de Decision (STT)** | Transiciones de estado (OrdenProduccion, PedidoVenta) |
| **Mocking** | DjangoApiClient en scanning_service, JWT en tests de autenticacion |

### 9.4 Configuracion de Cobertura

```ini
# .coveragerc
[run]
source = gestion, inventory, internal_api
branch = True
omit = */migrations/*, */tests/*, */settings*.py, manage.py

[report]
fail_under = 90
```

### 9.5 Entorno de Test CI

```yaml
# Servicio SQL Server en GitLab CI (.gitlab-ci.yml, job test:backend)
services:
  - name: mcr.microsoft.com/mssql/server:2022-CU27-GDR1-ubuntu-22.04@sha256:cf8f0ab2...
    alias: sqlserver
    variables:
      ACCEPT_EULA: "Y"
      MSSQL_SA_PASSWORD: "CI_Pass1234!"
      MSSQL_PID: "Developer"

# Settings especificos para CI
DJANGO_SETTINGS_MODULE: TexCore.settings_test
DB_ENGINE: mssql
DB_NAME: texcore_ci
DB_HOST: sqlserver
```

El job instala `ODBC Driver 18 for SQL Server` en la imagen Debian del runner antes de ejecutar los tests.

### 9.6 Estandares de Calidad

| Estandar | Aplicacion |
|----------|-----------|
| **ISO/IEC 25010** | Cobertura minima 90 % (backend y servicios), analisis de tipos (mypy) |
| **ISO/IEC 27001 A.14.2.1** | SAST con Ruff (reglas `S`) y Semgrep en cada CI |
| **OWASP DevSecOps** | Shift-left security: Ruff `S`, Semgrep, detect-secrets, pip-audit, npm audit, Trivy, yamllint |
| **Conventional Commits** | Trazabilidad de cambios en commits y PRs |
| **PEP 8** | Ruff (configuracion en `pyproject.toml`), excluye migrations |

---

## 10. Decisiones de Arquitectura (ADRs)

ADR-001 a ADR-008 se registran en esta seccion; ADR-009 en adelante tienen archivo propio en `docs/arquitectura/ADR/`. El archivo `ADR_001_NAVEGACION_HIBRIDA.md` es el detalle de la ADR-004 de esta seccion y `ADR_008_TEXTO_VACIO_SIN_NULL.md` el de la ADR-008.

### ADR-001: Arquitectura de Monolito con Servicios Satélites

**Contexto:** Sistema de gestión de órdenes de producción textil con dominios de naturaleza muy diferente: lógica relacional compleja, operaciones en tiempo real de baja latencia, y procesamiento pesado de CPU/IO.

**Decisión:** Monolito Django para el core + servicios satélites FastAPI para los extremos especializados.

**Justificación:**

| Alternativa | Problema |
|-------------|----------|
| Monolito puro | Pandas y WeasyPrint bloquean workers Gunicorn → timeouts en operaciones críticas |
| Microservicios completos | Complejidad operativa excesiva para 100–250 usuarios; modelo de datos relacional no se fragmenta bien |
| Monolito con Servicios Satélites (elegida) | Aislamiento de carga pesada sin fragmentar el core |

**Consecuencias:** Los servicios satélites no acceden a la BD directamente. `scanning_service` consulta la API interna de Django; `printing_service` y `reporting_excel` reciben del backend los datos ya resueltos. Esto simplifica la seguridad y la consistencia de datos.

---

### ADR-002: JWT RS256 para Comunicacion Servicio-a-Servicio

**Contexto:** Los servicios satélite necesitan acceder a datos en Django sin exponer credenciales de usuarios ni la conexion a la BD.

**Decision:** JWT asimetrico RS256. Django firma con clave privada; los servicios satélite verifican con clave publica.

**Alternativas descartadas:**

| Alternativa | Problema |
|-------------|----------|
| API Key compartida | Si se compromete un servicio satélite, el atacante tiene acceso permanente |
| mTLS | Complejidad de gestion de certificados en Docker Compose |
| OAuth2 completo | Overhead excesivo para comunicacion interna |

**Consecuencias:** Tokens de 5 minutos reducen la ventana de ataque (ISO 27001 A.9.4). Los servicios satélite no pueden forjar tokens propios. Si se rota la clave publica, todos los servicios satélite deben actualizarse simultaneamente.

---

### ADR-003: Cookies httpOnly para Autenticacion de Usuarios Finales

**Contexto:** Los tokens JWT de usuario necesitan proteccion contra XSS, que es el vector de ataque mas comun en aplicaciones React.

**Decision:** Tokens en cookies `httpOnly; SameSite=Lax; Secure`.

**Alternativas descartadas:**

| Alternativa | Problema |
|-------------|----------|
| localStorage | Vulnerable a XSS (cualquier script puede leer el token) |
| sessionStorage | Mismo problema que localStorage |
| Authorization header manual | Requiere que React gestione el token, exponiendo a XSS |

**Consecuencias:** El JavaScript de la aplicacion nunca puede leer el token. El browser lo envia automaticamente. CSRF mitigado por `SameSite=Lax` y CSRF Token de Django.

---

### ADR-004: Navegacion Hibrida SPA + URL State

**Contexto:** Los usuarios necesitan compartir enlaces exactos a vistas de datos (ej: "Kardex, filtro bodega Matriz, pagina 3"). El estado solo en `useState` de React no es persistible ni compartible.

**Decision:** Sincronizar filtros, paginacion y tabs activas con `useSearchParams` (React Router). La URL es la unica fuente de verdad para el estado de consulta.

**Alternativas descartadas:**

| Alternativa | Problema |
|-------------|----------|
| Solo useState | No persistible; se pierde al recargar |
| Migracion a SSR (Next.js) | Requiere cambio radical del pipeline CI/CD y los contenedores Docker |
| Zustand/Redux global | Estado global no compartible via URL |

**Consecuencias:** El backend Django no necesita cambios (DRF ya consume query params nativamente). Los componentes de tablas y reportes usan `useSearchParams` en lugar de `useState`.

---

### ADR-005: SQL Server 2022 como Base de Datos Principal

**Contexto:** La organizacion ya licencia SQL Server y el equipo tiene experiencia con T-SQL.

**Decision:** SQL Server 2022 con `mssql-django` (backend ORM) y `ODBC Driver 18`.

**Alternativas descartadas:**

| Alternativa | Problema |
|-------------|----------|
| PostgreSQL | Fuera del licenciamiento y de la experiencia operativa de la organizacion |
| MySQL | Menor soporte de RCSI, indices columnstore y CHECK nativos |

**Consecuencias:** La imagen Docker base de SQL Server es mas pesada que PostgreSQL. La logica de reportes vive en el ORM de Django (`internal_api/services/reporting_data.py`), apoyada en RCSI e indices nativos (§3.6). Los stored procedures de reportes que llego a tener el proyecto nunca se usaron y `database/V6` los elimina.

---

### ADR-006: AuditableModelMixin para Trazabilidad

**Contexto:** Requisitos de auditoria y trazabilidad completa de cambios en modelos criticos (inventario, formulas, clientes, pedidos) para cumplimiento ISO 27001 y COBIT DSS06.

**Decision:** Mixin abstracto Django que intercepta `save()` y `delete()` y genera automaticamente `AuditLog` con estado anterior/nuevo, usuario e IP.

**Alternativas descartadas:**

| Alternativa | Problema |
|-------------|----------|
| Django signals | Mas verboso; las signals no tienen acceso facil al estado previo |
| django-simple-history | Dependencia externa; menos control sobre el formato del log |
| Logging manual | Error-prone; facil de olvidar en nuevas vistas |

**Consecuencias:** Todo modelo que herede el mixin queda auditado automaticamente. El `AuditMiddleware` debe estar presente para capturar usuario e IP via thread-local. Los modelos con `requiere_justificacion_auditoria=True` exigen justificacion explicita en modificaciones.

---

### ADR-007: Servicios Satélites sin Acceso Directo a BD (API-First Internal)

**Contexto:** En versiones anteriores, scanning_service y reporting_excel se conectaban directamente a SQL Server vía SQLAlchemy + ODBC Driver. Esto creaba imágenes Docker pesadas y dependencias rígidas.

**Decisión:** Los servicios satélites solo hablan HTTP con Django, autenticados con JWT RS256. Ningún servicio satélite tiene credenciales de BD ni drivers ODBC.

**Consecuencias positivas:**
- Imagenes 60-70% mas livianas (sin ODBC Driver, sin SQLAlchemy)
- Si cambia el motor de BD, ningun servicio satélite requiere cambios
- La capa de datos es gestionada exclusivamente por Django ORM
- Menor superficie de ataque (credenciales de BD en un solo lugar)

**Consecuencias negativas:**
- Latencia adicional por la capa HTTP (mitigada por red Docker interna)
- El backend Django es un punto de acoplamiento critico

---

### ADR-008: Texto Vacío sin NULL (5-oct-2026)

**Contexto:** 32 campos de texto opcionales admitían `NULL` y `''` como vacío. La auditoría guardaba `None`, el frontend enviaba `null` en unos formularios y `''` en otros, y los filtros por `''` omitían las filas con `NULL`.

**Decisión:** los `CharField`/`TextField` opcionales son `blank=True, default=''` y la columna es `NOT NULL`. Las migraciones `gestion/0003_cadenas_vacias_sin_null` e `inventory/0002_cadenas_vacias_sin_null` convierten `NULL → ''` antes del `ALTER COLUMN`. La regla Ruff `DJ001` bloquea en el CI la reintroducción de texto nulo. Excepción: un campo `unique=True` opcional conserva `null=True` con su motivo (hoy no hay ninguno). Detalle completo: `docs/arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md`.

**Consecuencias positivas:**
- Una sola representación del vacío en filtros, reportes y frontend
- La API devuelve `""` de forma consistente

**Consecuencias negativas:**
- Un cliente que envíe `null` en esos campos recibe 400 (se corrigieron los formularios que lo hacían)
- La migración altera 32 columnas: hay que probarla sobre un respaldo con datos antes de desplegar (riesgo RD-05)

---

### ADR-009 a ADR-013

Las decisiones posteriores tienen su propio documento en `docs/arquitectura/ADR/`:

| ADR | Decision |
|-----|----------|
| [ADR-009](ADR/ADR_009_LOTE_CON_VARIOS_PRODUCTOS.md) | Un lote puede tener varios productos vendibles |
| [ADR-010](ADR/ADR_010_RENDIMIENTO_STOCK_Y_AUDITORIA.md) | Stock paginado y auditoria filtrable por indice |
| [ADR-011](ADR/ADR_011_EQUIVALENCIAS_EMPAQUE_SIN_CONSTANTE.md) | Equivalencias de empaque por sede, sin constante del sistema |
| [ADR-012](ADR/ADR_012_MRP_POR_SEDE.md) | MRP por sede: sugerencias de compra informativas y necesidad de produccion que alimenta el MTS |
| [ADR-013](ADR/ADR_013_PARO_AUTOMATICO_POR_ESTADO.md) | El cambio de estado de la maquina abre y cierra el paro que registra su detencion (historial de mantenimiento y Disponibilidad del OEE) |

---

## Apendice A: Variables de Entorno de Produccion

El unico archivo que se edita es `.env.prod` en el servidor; su plantilla es `.env.prod.example` y contiene exactamente las variables que interpola el compose (lo verifica `gestion/tests/test_despliegue_produccion.py`):

| Variable | Obligatoria | Uso |
|----------|-------------|-----|
| `CI_REGISTRY_IMAGE`, `TAG` | Si | Nombre y etiqueta de las imagenes (el CD las sobrescribe con el registro y el SHA) |
| `SECRET_KEY` | Si | Django |
| `FIELD_ENCRYPTION_KEYS`, `BLIND_INDEX_KEY` | Si | Cifrado de los datos personales en reposo y su indice ciego (RS-19). Sin ellas el backend no arranca; si se pierde la primera, los datos cifrados no se recuperan |
| `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` | Si | Host y origenes `https://` del servidor |
| `TRAZABILIDAD_BASE_URL` | Si | URL base del QR de los lotes |
| `DB_PASSWORD` | Si | Cuenta `sa` de SQL Server (backend y db) |
| `INTERNAL_JWT_PRIVATE_KEY`, `INTERNAL_JWT_PUBLIC_KEY` | Si | Par RSA del JWT entre servicios (privada solo en el backend) |
| `SCANNING_SERVICE_SECRET`, `REPORTING_SERVICE_SECRET` | Si | Credenciales que `register_services` registra para los satelites |
| `MSSQL_PID` | No (default `Developer`) | Edicion licenciada de SQL Server: en produccion, `Standard` o `Enterprise` |
| `DB_CPUS`, `DB_MEMORY_LIMIT_MB` | No (2 / 4096) | Recursos de `db`; la memoria fija tambien `MSSQL_MEMORY_LIMIT_MB` |
| `BACKEND_CPUS`, `BACKEND_MEMORY_LIMIT_MB`, `BACKEND_WORKERS` | No (2 / 2048 / 3) | Recursos y workers de Gunicorn (medido: 3 CPU, 3072 MB y 20 workers para 100 usuarios) |

El compose fija el resto: la conexion a la BD (`DB_HOST=db`, `DB_NAME=texcore_db`, `DB_USER=sa`, ODBC 18), `DEBUG=0`, las URL internas de los servicios (`http://printing:8001`, `http://reporting_excel:8002`, `http://backend:8000`), `SERVICE_NAME` de scanning, `AUDIT_DB_PATH` de los satelites y `NGINX_REDIRIGIR_HTTP=1`.

---

## Apendice B: Glosario

| Termino | Definicion |
|---------|-----------|
| **OP** | Orden de Produccion — documento que planifica la transformacion de materia prima en producto terminado |
| **Lote** | Unidad fisica de produccion resultante de una OP. Tiene un codigo de barras unico impreso en etiqueta Zebra |
| **Kardex** | Registro cronologico de todos los movimientos de un producto en una bodega. Es la fuente de verdad del inventario |
| **ZPL** | Zebra Programming Language — lenguaje de descripcion de etiquetas para impresoras Zebra |
| **RBAC** | Role-Based Access Control — control de acceso basado en grupos/roles de Django |
| **JWT RS256** | JSON Web Token firmado con RSA 2048 bits (algoritmo asimetrico) |
| **JWT HS256** | JSON Web Token firmado con HMAC-SHA256 (algoritmo simetrico, para usuarios) |
| **PBKDF2** | Password-Based Key Derivation Function 2 — algoritmo de hash usado para `ServiceCredential.secret_hash` |
| **SPA** | Single Page Application — la aplicacion React se carga una vez y maneja la navegacion internamente |
| **ADR** | Architecture Decision Record — documento que registra una decision arquitectonica importante |
| **ERP** | Enterprise Resource Planning — sistema de gestión de órdenes de producción |
| **MES** | Manufacturing Execution System — sistema de ejecucion de manufactura |
| **ACID** | Atomicity, Consistency, Isolation, Durability — propiedades de las transacciones de BD |
| **Sede** | Unidad organizacional (empresa) dentro de TexCore. Cada sede tiene sus propias bodegas, areas y usuarios |
| **Merma** | Perdida de material durante el proceso productivo. Se registra como `MovimientoInventario` tipo MERMA |
| **Bulto** | Unidad de empaque fisica (caja, funda, cono). Un lote puede tener multiples bultos |
| **Despacho incompleto** | Despacho donde la cantidad fisica escaneada no cubre el 100% de los pedidos seleccionados |
