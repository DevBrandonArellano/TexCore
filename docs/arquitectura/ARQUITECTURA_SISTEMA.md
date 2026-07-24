# TexCore — Arquitectura del Sistema
## Referencia Técnica Definitiva

> **Version:** 1.0 | **Fecha:** 2026-06-05
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

TexCore es un sistema **Sistema de gestión de órdenes de producción** (Enterprise Resource Planning / Manufacturing Execution System) diseñado para la industria textil. Gestiona el ciclo completo de operaciones de cuatro empresas textiles (Interfibra, Ribel, Hiltexpoy, Jaltextiles) bajo una unica plataforma multi-sede.

### 1.2 Capacidades Principales

| Dominio | Descripcion |
|---------|-------------|
| **Produccion** | Ordenes de produccion, lotes, control de maquinaria y operarios, mermas |
| **Inventario** | Kardex en tiempo real, transferencias, alertas de stock minimo, trazabilidad por lote |
| **Despacho** | Escaneo de lotes, validacion de pedidos, despacho con incompletos, historial |
| **Ventas** | Pedidos de venta, clientes con credito, facturacion, reportes por vendedor |
| **Tintoreria** | Formulas de color, fases de receta, descarga automatica de quimicos |
| **Empaquetado** | Configuracion de bultos, etiquetas ZPL para impresoras Zebra |
| **Reportes** | Excel y PDF: Kardex, stock, valorizacion, ventas, deudores, tendencias |
| **Auditoria** | Trazabilidad completa de cambios con AuditLog polimórfico |

### 1.3 Caracteristicas Tecnicas Clave

- **Usuarios simultaneos objetivo:** ~50
- **Multi-sede:** Una instancia por sede, segregacion de datos por `sede_id`
- **Trazabilidad completa:** Cada cambio en modelos criticos genera un `AuditLog`
- **Arquitectura híbrida:** Monolito Django para lógica core + servicios satélites FastAPI para operaciones especializadas
- **Sin acceso directo a BD desde servicios satélites:** Toda comunicación pasa por la API interna con JWT RS256

### 1.4 Stack Tecnologico

| Capa | Tecnologia | Version |
|------|-----------|---------|
| Backend core | Python + Django + Django REST Framework | 3.12 / 5.x |
| Servicios Satélites | FastAPI + Uvicorn | 0.109.x |
| Frontend | React + TypeScript + Vite | 18.x |
| Base de datos | Microsoft SQL Server | 2022 |
| Proxy inverso | Nginx Alpine | Latest |
| Contenedores | Docker + Docker Compose | Latest |
| Cache/Queue | Redis + Celery | 6-alpine |
| Autenticacion usuarios | SimpleJWT (HS256) con cookies httpOnly | |
| Autenticacion servicios | JWT RS256 (PyJWT) con claves RSA 2048 | |
| Generacion reportes | Pandas + openpyxl / WeasyPrint | |
| Etiquetas ZPL | Jinja2 templates para impresoras Zebra | |

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
║                         RED DOCKER: texcore_network                             ║
║                                                                                  ║
║  ┌─────────────────────────────────────────────────────────────────────────┐    ║
║  │  CLIENTE (Browser)                                                       │    ║
║  │  React SPA (compilado, servido por Nginx)                                │    ║
║  └───────────────────────────┬─────────────────────────────────────────────┘    ║
║                              │ HTTPS :443 / HTTP :80                            ║
║  ┌───────────────────────────▼─────────────────────────────────────────────┐    ║
║  │  NGINX (Alpine)  — Puertos: 80, 443                                      │    ║
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
║         │             │ JWT RS256 + HTTP                                          ║
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
║  [REDIS :6379] ← Celery broker (dev, base para produccion futura)                ║
║  [CELERY WORKER] ← mismo codigo que backend, tareas asincronas                   ║
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
║  │ · EmpaqueService │  │ · OrdenCompra     │  │                  │ ║
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

| Path | Destino | Rate Limit |
|------|---------|-----------|
| `POST /api/token/` | `backend:8000` | 5 req/min, burst 3 |
| `POST /api/token/refresh/` | `backend:8000` | 10 req/min, burst 5 |
| `/api/scanning/*` | `scanning:8000` (path rewritten) | Sin limite especifico |
| `/api/*` | `backend:8000` | 100 req/s, burst 200 |
| `/static/*` | Volumen `prod_django_static` (alias) | Sin limite |
| `/` | SPA React (`/usr/share/nginx/html`) | Sin limite |

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
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'` (React requiere unsafe-eval) |
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

**Variables de entorno obligatorias:**

| Variable | Descripcion |
|----------|-------------|
| `SECRET_KEY` | Django secret key (produccion) |
| `DB_ENGINE` | `mssql` |
| `DB_NAME` | `texcore_db` |
| `DB_USER` / `DB_PASSWORD` | Credenciales SQL Server |
| `DB_HOST` / `DB_PORT` | `db` / `1433` |
| `DB_DRIVER` | `ODBC Driver 18 for SQL Server` |
| `ALLOWED_HOSTS` | Dominio(s) separados por coma |
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

**Flujo de datos:** El backend Django actua como intermediario — genera un JWT de servicio para el reporting_excel, que usa ese token para llamar de regreso a Django y obtener los datos via `GET /api/internal/v1/reports/*`.

**Variables de entorno:**

| Variable | Descripcion |
|----------|-------------|
| `DJANGO_INTERNAL_URL` | `http://backend:8000` |
| `SERVICE_NAME` | `reporting_excel` |
| `SERVICE_SECRET` | Secret para autenticarse con Django |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave publica RSA |
| `CORS_ALLOWED_ORIGINS` | `http://backend:8000` |

**Reportes disponibles:**

```
reporting_excel/src/
├── routers/
│   ├── kardex.py          → GET /kardex/
│   ├── stock.py           → GET /stock-actual/, /valorizacion/, /stock-cero/
│   ├── ventas.py          → GET /ventas/gerencial/, /ventas/vendedor/{id}/
│   ├── produccion.py      → GET /produccion/ordenes/, /produccion/lotes/
│   └── clientes.py        → GET /deudores/, /top-clientes/, /aging/
├── services/
│   └── report_factory.py  → Genera xlsx/pdf desde DataFrame
└── repositories/
    └── django_report_repository.py  → GET datos via JWT a Django
```

---

### 3.5 Printing Service (FastAPI)

**Puerto:** `expose:8001`
**Tecnologia:** FastAPI + Uvicorn + WeasyPrint (PDF) + Jinja2 (ZPL)
**Acceso a BD:** Ninguno. Recibe datos completos en el payload del request.

**Endpoints:**

| Endpoint | Descripcion |
|----------|-------------|
| `POST /zpl/etiqueta` | Genera etiqueta ZPL para impresora Zebra a partir de datos del lote |
| `POST /pdf/nota-venta` | Genera PDF de nota de venta con WeasyPrint |
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

**Imagen:** Custom (`database/Dockerfile`) — imagen base Microsoft + scripts de inicializacion
**Acceso:** Solo la red Docker interna (`expose:1433`, sin `ports:`)
**Volumen:** `mssql_data` (persistente entre reinicios)

**Conexion Django:**

```python
DATABASES = {
    'default': {
        'ENGINE': 'mssql',     # mssql-django
        'OPTIONS': {
            'driver': 'ODBC Driver 18 for SQL Server',
            'extra_params': 'Encrypt=yes;TrustServerCertificate=yes'
        }
    }
}
```

**Healthcheck:**

```yaml
test: ["/opt/mssql-tools18/bin/sqlcmd", "-S", "localhost", "-U", "sa",
       "-P", "${DB_PASSWORD}", "-C", "-N", "-Q", "SELECT 1"]
interval: 10s
timeout: 5s
retries: 5
start_period: 120s
```

El backend espera a que el healthcheck sea exitoso antes de arrancar (`condition: service_healthy`).

---

### 3.7 Redis y Celery

**Estado actual:** Redis (`redis:6-alpine`) esta definido en el compose y disponible, pero Celery esta configurado como base para tareas asincronas futuras (notificaciones, reportes en background).

**Celery Worker:** Usa el mismo codigo fuente que el backend Django, con el comando de arranque `celery -A TexCore worker`.

---

### 3.8 Frontend (React SPA)

**Tecnologia:** React 18 + TypeScript + Vite + TanStack Query + Tailwind CSS + shadcn/ui

**Compilado:** El build de produccion (`npm run build`) genera `dist/` que es copiado a Nginx en la imagen multi-stage.

**Estructura de dashboards por rol:**

| Dashboard | Rol(es) |
|-----------|---------|
| `AdminSistemasDashboard` | admin_sistemas |
| `BodegeroDashboard` | bodeguero |
| `OperarioDashboard` | operario |
| `JefeAreaDashboard` | jefe_area |
| `JefePlantaDashboard` | jefe_planta |
| `EjecutivosDashboard` | ejecutivo |
| `VendedorDashboard` | vendedor |
| `DespachoDashboard` | encargado_despacho |
| `HistorialDespachoDashboard` | encargado_despacho, jefe_planta |
| `EmpaquetadoDashboard` | operario, jefe_area |

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
    'AUTH_COOKIE_SECURE': True,  # Solo HTTPS en produccion
    'AUTH_COOKIE_SAMESITE': 'Lax',
}
```

**Logout:** El refresh token es agregado a la JWT Blacklist (`rest_framework_simplejwt.token_blacklist`) para invalidarlo inmediatamente. Requiere que la tabla de blacklist exista en BD (`migrate`).

### 4.2 Roles y Permisos (RBAC via Django Groups)

| Grupo | Permisos principales |
|-------|---------------------|
| `admin_sistemas` | Acceso total al sistema, gestion de usuarios y sedes |
| `bodeguero` | CRUD de stock, movimientos, transferencias, Kardex |
| `operario` | Crear lotes de produccion, ver sus OPs asignadas |
| `jefe_area` | Aprobar OPs, gestionar formulas, ver KPIs de area |
| `jefe_planta` | Vision de toda la planta, reportes de produccion |
| `ejecutivo` | Reportes gerenciales, KPIs globales, sin operacion |
| `vendedor` | Crear pedidos de venta, ver sus clientes y comisiones |
| `encargado_despacho` | Proceso de despacho, escaneo de lotes, historial |

Los permisos DRF se generan con `make_group_permission()` (factory interna) para evitar duplicacion de clases.

### 4.3 Capa 2: Autenticacion Servicio-a-Servicio (JWT RS256)

**Proposito:** Permite que los servicios satélite (scanning, reporting) llamen a la API interna de Django con identidad verificada criptograficamente, sin compartir contraseñas de usuarios.

**Generacion de claves:**

```bash
# scripts/generate_rsa_keys.py
openssl genrsa -out internal_jwt_private.pem 2048
openssl rsa -in internal_jwt_private.pem -pubout -out internal_jwt_public.pem
```

**Distribucion de claves:**

| Clave | Ubicacion |
|-------|----------|
| Privada (firma tokens) | Solo en backend Django (`INTERNAL_JWT_PRIVATE_KEY`) |
| Publica (verifica tokens) | Backend + scanning + reporting_excel (`INTERNAL_JWT_PUBLIC_KEY`) |

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
 ├── tipo: hilo|tela|subproducto|quimico|insumo|materia_prima
 └── unidad_medida: kg|gr|lb|l|ml|gl|metros|yardas|unidades

OrdenProduccion
 ├── codigo CharField
 ├── producto_entrada FK → Producto
 ├── producto_salida FK → Producto
 ├── formula_color FK → FormulaColor (nullable)
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
 ├── presentacion: baño|funda|cono
 ├── clasificacion_calidad: primera|segunda|saldo
 ├── operario FK → CustomUser
 ├── maquina FK → Maquina
 └── turno CharField

FormulaColor
 ├── codigo CharField
 ├── nombre_color CharField
 ├── tipo_sustrato: algodon|poliester|nylon|mixto
 ├── version PositiveInteger
 ├── estado: en_pruebas|aprobada
 └── sede FK → Sede

FaseReceta (fase de FormulaColor)
 ├── formula FK → FormulaColor
 ├── nombre: pre_tratamiento|tintura|lavado|suavizado|auxiliares
 ├── orden PositiveInteger
 ├── temperatura Integer (°C)
 └── tiempo Integer (minutos)

DetalleFormula (quimico por fase)
 ├── fase FK → FaseReceta
 ├── producto FK → Producto (quimico)
 ├── tipo_calculo: gr_l|pct
 └── concentracion/porcentaje Decimal

Cliente
 ├── nombre_razon_social CharField
 ├── ruc CharField (unique)
 ├── limite_credito Decimal
 ├── cartera_vencida Decimal
 ├── nivel_precio: 1|2|3
 └── plazo_credito_dias Integer

PedidoVenta
 ├── cliente FK → Cliente
 ├── vendedor_asignado FK → CustomUser
 ├── guia_remision CharField
 ├── estado: pendiente|despachado|facturado
 ├── esta_pagado Boolean
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
 └── total_con_iva Decimal (desnormalizado: subtotal × 1.15 si iva)

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

### 5.2 Diagrama ERD — App `inventory`

```
StockBodega
 ├── bodega FK → Bodega
 ├── producto FK → Producto
 ├── lote FK → LoteProduccion (nullable)
 ├── cantidad Decimal(12,2)
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
 ├── cantidad Decimal(12,2)  [CHECK: >= 0]
 ├── saldo_resultante Decimal(12,2)  [CHECK: >= 0]
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
 ├── total_peso Decimal(12,2)
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
 ├── peso Decimal(12,2)
 └── es_devolucion Boolean

RequerimientoMaterial
 ├── producto_requerido FK → Producto
 ├── cantidad_necesaria Decimal(12,3)
 ├── sede FK → Sede
 ├── origen_tipo: PEDIDO|OP
 ├── origen_id PositiveInteger
 └── fecha_requerida Date

OrdenCompraSugerida
 ├── producto FK → Producto
 ├── sede FK → Sede
 ├── cantidad_sugerida Decimal(12,3)
 ├── estado: PENDIENTE|APROBADA|RECHAZADA
 └── UNIQUE: (producto, sede, estado)  ← Solo 1 sugerencia pendiente por prod/sede
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
| `GET/POST` | `/api/inventory/movimientos/` | Kardex global / crear movimiento manual |
| `POST` | `/api/inventory/transferencias/` | Transferencia entre bodegas |
| `POST` | `/api/inventory/transformaciones/` | Transformacion de producto |
| `GET` | `/api/inventory/bodegas/{id}/kardex/` | Kardex filtrado por bodega |
| `GET` | `/api/inventory/alertas-stock/` | Productos bajo stock minimo |
| `POST` | `/api/inventory/process-despacho/` | Procesar despacho (ver flujo §7.2) |
| `GET/POST` | `/api/inventory/historial-despachos/` | Historial de despachos |
| `GET` | `/api/inventory/audit-logs/` | Registros de auditoria |
| `GET/POST` | `/api/inventory/requerimientos-material/` | Requerimientos de compra |
| `GET/POST` | `/api/inventory/sugerencias-compra/` | Ordenes de compra sugeridas |

#### Gestion (`/api/`)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `GET/POST` | `/api/ordenes-produccion/` | CRUD de OPs |
| `GET/POST` | `/api/lotes-produccion/` | CRUD de lotes |
| `GET/POST` | `/api/pedidos-venta/` | CRUD de pedidos |
| `GET/POST` | `/api/clientes/` | CRUD de clientes |
| `GET/POST` | `/api/formulas-color/` | Formulas de tintura |
| `GET/POST` | `/api/maquinas/` | Maquinaria |
| `GET/POST` | `/api/bodegas/` | Bodegas |
| `GET/POST` | `/api/sedes/` | Sedes |
| `GET` | `/api/kpis/` | KPIs por rol |

#### Escaneo (via Nginx → scanning_service)

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/api/scanning/validate/{codigo}` | Validar lote por codigo de barras |

### 6.3 Endpoints Internos (Servicios)

> Acceso exclusivo con `Authorization: Bearer <JWT RS256>`. Nginx NO enruta estos endpoints al exterior.

| Metodo | Endpoint | Scope requerido | Descripcion |
|--------|----------|----------------|-------------|
| `POST` | `/api/internal/auth/token/` | - | Obtener JWT de servicio |
| `POST` | `/api/internal/auth/refresh/` | - | Renovar JWT de servicio |
| `GET` | `/api/internal/v1/lotes/{codigo}/validate/` | `lotes:read` | Datos de lote para escaneo |
| `GET` | `/api/internal/v1/reports/kardex/` | `reports:read` | Datos Kardex |
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
│  3. (Opcional) TINTORERIA descarga quimicos automaticamente          │
│     Sistema calcula: cantidad = (formula.concentracion × volumen)    │
│     MovimientoInventario CONSUMO creado automaticamente              │
│     StockBodega de quimicos decrementado                             │
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
│  6. Sistema envia a printing_service                                 │
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
│  3. Django (reporting_proxy.py):                                     │
│     a. Valida permisos del usuario (rol ejecutivo/bodeguero)         │
│     b. Genera JWT RS256 para reporting_excel service (5 min)         │
│     c. HTTP POST a reporting_excel:8002/kardex/                      │
│        Authorization: Bearer <JWT interno>                           │
│        Body: {params del filtro}                                     │
│                                                                      │
│  4. reporting_excel recibe request:                                  │
│     a. jwt.decode(token, public_key, algorithms=["RS256"])           │
│     b. Verifica scope "reports:read"                                 │
│     c. DjangoReportRepository:                                       │
│        GET /api/internal/v1/reports/kardex/ + params                 │
│        Authorization: Bearer <mismo token>                           │
│                                                                      │
│  5. Django responde a reporting_excel con datos crudos (JSON)        │
│     → reporting_excel convierte a DataFrame de Pandas                │
│     → ReportFactory.generate_xlsx() → bytes del archivo              │
│                                                                      │
│  6. reporting_excel retorna blob xlsx al backend Django              │
│                                                                      │
│  7. Backend Django retorna blob al frontend con:                     │
│     Content-Type: application/vnd.openxmlformats-officedocument...   │
│     Content-Disposition: attachment; filename="kardex_2026.xlsx"     │
│                                                                      │
│  8. Browser descarga el archivo Excel automaticamente                │
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
redis (independiente)
celery_worker (independiente)
```

**Volumenes:**

| Volumen | Descripcion | Montaje |
|---------|-------------|---------|
| `mssql_data` | Datos SQL Server | `/var/opt/mssql` (db) |
| `prod_django_static` | Archivos estaticos Django | `/home/appuser/app/staticfiles` (backend) + `/var/www/django_static:ro` (nginx) |
| `./nginx/certs` | Certificados SSL | `/etc/nginx/certs:ro` (nginx) |

**Politica de reinicio:** `restart: always` en todos los servicios.

### 8.2 Estrategia de Imagenes Docker

| Servicio | Registro | Tag |
|----------|----------|-----|
| backend | `ghcr.io/<owner>/texcore/backend:<SHA>` | SHA commit |
| nginx | `ghcr.io/<owner>/texcore/nginx:<SHA>` | SHA commit |
| scanning | `ghcr.io/<owner>/texcore/scanning_service:<SHA>` | SHA commit |
| reporting_excel | `ghcr.io/<owner>/texcore/reporting_excel:<SHA>` | SHA commit |
| printing | `ghcr.io/<owner>/texcore/printing_service:<SHA>` | SHA commit |

Las imagenes son **inmutables por SHA** — el mismo SHA siempre corresponde al mismo binario. El tag `latest` apunta al ultimo deploy exitoso.

### 8.3 CI/CD — GitHub Actions

**Flujo de ramas:**

```
feature/* ─── push ──► staging ─── (CI pasa) ──► PR staging → master
                         CI                              CI re-corre
                                                          │
                                                    merge a master
                                                          │
                                                     CD despliega
```

**Archivo `ci.yml` — Jobs y dependencias:**

```
backend-lint ────────────────────────────────────────────────┐
backend-test (needs: backend-lint) ──────────────────────────┤
reporting-excel-test ────────────────────────────────────────┤
printing-service-test ───────────────────────────────────────┤→ quality-gate
scanning-service-test ───────────────────────────────────────┤
dependency-audit ────────────────────────────────────────────┤
frontend-test ───────────────────────────────────────────────┤
docker-build-validation (solo en push o PR a master) ────────┘
```

**Herramientas de analisis estatico:**

| Herramienta | Proposito | Bloquea merge? |
|-------------|-----------|----------------|
| `flake8` | Estilo PEP 8 | Si |
| `bandit` | SAST Python (vulnerabilidades) | Si (medium+) |
| `detect-secrets` | Credenciales expuestas | Si |
| `mypy` | Tipos estaticos Python | No (informativo) |
| `pip-audit` | CVEs en dependencias | No (warning) |
| `npm audit` | CVEs en dependencias JS | No (warning) |

**Archivo `cd.yml` — Etapas:**

```
ci-guard (verifica que CI paso en master)
    │
build-images (construye y push a GHCR con SHA tag)
    │
scan-images (Trivy — CVEs en imagenes Docker)
    │
deploy (SSH al servidor: git checkout + docker compose up -d --no-build)
    │
health-check (verifica que todos los servicios responden)
    │
notify (webhook opcional Slack/Teams)
```

**Archivo `rollback.yml`:** Permite revertir manualmente a una imagen anterior especificando el SHA de commit anterior.

**Archivo `security.yml`:** Escaneo periodico de vulnerabilidades (schedule CRON) con Trivy y pip-audit.

**Secretos requeridos en GitHub:**

```
DEPLOY_SSH_HOST          # IP/hostname servidor produccion
DEPLOY_SSH_USER          # Usuario SSH
DEPLOY_SSH_KEY           # Clave privada SSH (PEM)
DEPLOY_SSH_PORT          # Puerto SSH (default: 22)
DEPLOY_PROJECT_PATH      # Ruta del proyecto en servidor
DB_PASSWORD              # Contraseña DB produccion
SECRET_KEY               # Django SECRET_KEY produccion
ALLOWED_HOSTS            # Dominio produccion
CORS_ALLOWED_ORIGINS     # Origins CORS
CSRF_TRUSTED_ORIGINS     # Origins CSRF
INTERNAL_JWT_PRIVATE_KEY # Clave privada RSA (backend)
INTERNAL_JWT_PUBLIC_KEY  # Clave publica RSA (todos)
SCANNING_SERVICE_SECRET  # Secret del scanning_service
REPORTING_SERVICE_SECRET # Secret del reporting_excel
DEPLOY_NOTIFY_WEBHOOK    # (Opcional) webhook notificaciones
```

### 8.4 GitLab CI

Paralelo a GitHub Actions, con las mismas etapas:

```
lint → test → build → scan → deploy → health-check → rollback
```

Usa GitLab Container Registry en lugar de GHCR.

### 8.5 Procedimiento de Deploy Manual (emergencia)

```bash
# En el servidor de produccion
cd /ruta/del/proyecto
git fetch origin master
git checkout master
git pull origin master

# Reconstruir solo la imagen que cambio
docker compose -f infrastructure/docker/docker-compose.prod.yml build backend

# Reiniciar sin downtime (graceful restart de Gunicorn)
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d --no-build backend

# Verificar estado
docker compose -f infrastructure/docker/docker-compose.prod.yml ps
docker compose -f infrastructure/docker/docker-compose.prod.yml logs backend --tail=50
```

### 8.6 Health Checks

| Servicio | Endpoint | Comando |
|----------|----------|---------|
| db | `SELECT 1` via sqlcmd | Definido en compose healthcheck |
| backend | `/api/health/` | Curl en CD workflow |
| scanning | `/health` | FastAPI endpoint |
| printing | `/health` | FastAPI endpoint |
| reporting_excel | `/health` | FastAPI endpoint |

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

| Suite | Framework | Cantidad | Cobertura minima |
|-------|-----------|----------|-----------------|
| Backend (gestion + inventory) | pytest + Django test client | 64 tests | 75% |
| scanning_service | pytest + httpx | 33 tests | 80% |
| reporting_excel | pytest + httpx | 27 tests | 80% |
| printing_service | pytest + httpx | - | 80% |
| Frontend | Vitest + Testing Library | 42 archivos | - |

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
source = gestion, inventory
omit = */migrations/*, */tests/*

[report]
fail_under = 75
```

### 9.5 Entorno de Test CI

```yaml
# Configuracion del servicio SQL Server en GitHub Actions CI
services:
  sqlserver:
    image: mcr.microsoft.com/mssql/server:2022-latest
    env:
      MSSQL_SA_PASSWORD: "CI_Pass1234!"
      MSSQL_PID: "Developer"
    ports:
      - 1433:1433

# Settings especificos para CI
DJANGO_SETTINGS_MODULE: TexCore.settings_test
DB_ENGINE: mssql
DB_NAME: texcore_ci
```

El CI instala `ODBC Driver 18 for SQL Server` en el runner de Ubuntu antes de ejecutar los tests.

### 9.6 Estandares de Calidad

| Estandar | Aplicacion |
|----------|-----------|
| **ISO/IEC 25010** | Cobertura minima 75%, analisis de tipos (mypy) |
| **ISO/IEC 27001 A.14.2.1** | SAST con Bandit en cada CI |
| **OWASP DevSecOps** | Shift-left security: Bandit, detect-secrets, pip-audit, Trivy |
| **Conventional Commits** | Trazabilidad de cambios en commits y PRs |
| **PEP 8** | flake8 con max-line-length=120, excluye migrations |

---

## 10. Decisiones de Arquitectura (ADRs)

### ADR-001: Arquitectura de Monolito con Servicios Satélites

**Contexto:** Sistema de gestión de órdenes de producción textil con dominios de naturaleza muy diferente: lógica relacional compleja, operaciones en tiempo real de baja latencia, y procesamiento pesado de CPU/IO.

**Decisión:** Monolito Django para el core + servicios satélites FastAPI para los extremos especializados.

**Justificación:**

| Alternativa | Problema |
|-------------|----------|
| Monolito puro | Pandas y WeasyPrint bloquean workers Gunicorn → timeouts en operaciones críticas |
| Microservicios completos | Complejidad operativa excesiva para 50 usuarios; modelo de datos relacional no se fragmenta bien |
| Monolito con Servicios Satélites (elegida) | Aislamiento de carga pesada sin fragmentar el core |

**Consecuencias:** Los servicios satélites no acceden a la BD directamente. Toda comunicación pasa por la API interna de Django. Esto simplifica la seguridad y la consistencia de datos.

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

**Contexto:** La empresa ya usaba SQL Server en sus sistemas legacy. El equipo tiene experiencia con T-SQL y stored procedures para reportes.

**Decision:** SQL Server 2022 con `mssql-django` (backend ORM) y `ODBC Driver 18`.

**Alternativas descartadas:**

| Alternativa | Problema |
|-------------|----------|
| PostgreSQL | Migracion de datos legacy compleja; perdida de SPs existentes |
| MySQL | Menor compatibilidad con tipos de datos y SPs de SQL Server |

**Consecuencias:** Los reportes complejos pueden usar Stored Procedures ejecutados directamente desde reporting_excel via la API interna. La imagen Docker base de SQL Server es mas pesada que PostgreSQL.

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

**Decisión:** Los servicios satélites solo hablan HTTP con Django vía JWT RS256. Ningún servicio satélite tiene credenciales de BD ni drivers ODBC.

**Consecuencias positivas:**
- Imagenes 60-70% mas livianas (sin ODBC Driver, sin SQLAlchemy)
- Si cambia el motor de BD, ningun servicio satélite requiere cambios
- La capa de datos es gestionada exclusivamente por Django ORM
- Menor superficie de ataque (credenciales de BD en un solo lugar)

**Consecuencias negativas:**
- Latencia adicional por la capa HTTP (mitigada por red Docker interna)
- El backend Django es un punto de acoplamiento critico

---

## Apendice A: Variables de Entorno de Produccion

```bash
# Backend Django
SECRET_KEY=<256-bit-random-string>
DEBUG=0
DB_ENGINE=mssql
DB_NAME=texcore_db
DB_USER=sa
DB_PASSWORD=<strong-password>
DB_HOST=db
DB_PORT=1433
DB_DRIVER=ODBC Driver 18 for SQL Server
ALLOWED_HOSTS=texcore.ejemplo.com
CORS_ALLOWED_ORIGINS=https://texcore.ejemplo.com
CSRF_TRUSTED_ORIGINS=https://texcore.ejemplo.com
STATIC_ROOT=/home/appuser/app/staticfiles
REPORTING_SERVICE_URL=http://reporting_excel:8002
INTERNAL_JWT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...
INTERNAL_JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...
SCANNING_SERVICE_SECRET=<random-256-bit>
REPORTING_SERVICE_SECRET=<random-256-bit>

# Scanning Service
DJANGO_INTERNAL_URL=http://backend:8000
SERVICE_NAME=scanning_service
SERVICE_SECRET=<mismo que SCANNING_SERVICE_SECRET>
INTERNAL_JWT_PUBLIC_KEY=<mismo que backend>

# Reporting Excel
DJANGO_INTERNAL_URL=http://backend:8000
SERVICE_NAME=reporting_excel
SERVICE_SECRET=<mismo que REPORTING_SERVICE_SECRET>
INTERNAL_JWT_PUBLIC_KEY=<mismo que backend>
CORS_ALLOWED_ORIGINS=http://backend:8000
```

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
