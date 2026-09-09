# Análisis del Sistema de Despacho - TexCore

**Version:** 4.0 (arquitectura con Django Internal API + JWT RS256)
**Ultima revision:** 2026-06-05

---

## Resumen Ejecutivo

El sistema de despacho de TexCore es una solución de monolito Django con servicios satélite donde los componentes periféricos (scanning_service, reporting_excel) **no tienen acceso directo a la base de datos**. Toda la persistencia ocurre en Django, que actúa como único guardián de los datos. Los servicios satélite consumen una API interna autenticada con JWT RS256 (par de claves asimétricas). El módulo de despacho incorpora validación de completitud con confirmación de despachos parciales y trazabilidad completa de items no despachados.

---

## Arquitectura General

### Diagrama de Componentes

```
                            ┌──────────────────────────────────────────────────────┐
                            │                   RED DOCKER INTERNA                 │
                            │                                                      │
 ┌────────────┐   HTTPS     │  ┌────────────┐        ┌────────────────────────┐   │
 │  Browser   │────────────▶│  │   Nginx    │───────▶│  Backend (Django)      │   │
 │  (React)   │             │  │ API Gateway│        │  Puerto: 8000          │   │
 └────────────┘             │  └────────────┘        │  Gunicorn (interno)    │   │
                            │       │                └────────────┬───────────┘   │
                            │       │ proxy_pass                  │               │
                            │       │ /api/scanning/*             │ ORM           │
                            │       ▼                             ▼               │
                            │  ┌─────────────────┐    ┌──────────────────────┐   │
                            │  │ scanning_service │    │  SQL Server (MS SQL) │   │
                            │  │  FastAPI v3.0   │    │  expose: 1433        │   │
                            │  │  expose: 8000   │    │  (NO ports en prod)  │   │
                            │  └────────┬────────┘    └──────────────────────┘   │
                            │           │ HTTP + JWT RS256                        │
                            │           ▼                                         │
                            │  GET /api/internal/v1/lotes/{codigo}/validate/      │
                            │                                                     │
                            │  ┌───────────────────┐                             │
                            │  │ reporting_excel    │                             │
                            │  │  FastAPI           │                             │
                            │  │  expose: 8002      │                             │
                            │  └────────┬───────────┘                            │
                            │           │ HTTP + JWT RS256                        │
                            │           ▼                                         │
                            │  GET /api/internal/v1/reports/*                    │
                            │                                                     │
                            └──────────────────────────────────────────────────--┘

NOTA: "expose" = accesible solo dentro de la red Docker; "ports" = expuesto al host.
Solo Nginx expone ports al exterior (80:80, 443:443).
```

### Principio de Aislamiento de BD

```
ARQUITECTURA ANTERIOR (obsoleta):
  scanning_service ──pyodbc──▶ SQL Server   [ELIMINADO]

ARQUITECTURA ACTUAL:
  scanning_service ──HTTP+JWT──▶ Django Internal API ──ORM──▶ SQL Server
  reporting_excel  ──HTTP+JWT──▶ Django Internal API ──ORM──▶ SQL Server
```

Solo Django (backend) tiene credenciales de base de datos. Los servicios satélite autentican su identidad con un `SERVICE_NAME` + `SERVICE_SECRET` y reciben un JWT RS256 de corta duración.

---

## Autenticacion JWT RS256 entre Servicios

### Flujo de Autenticacion Inicial

```
Servicio Satélite                Django Backend
     │                                 │
     │  POST /api/internal/v1/auth/token/
     │  Body: { service_name, service_secret }
     │────────────────────────────────▶│
     │                                 │ 1. Busca ServiceCredential
     │                                 │    WHERE name = service_name
     │                                 │ 2. check_password(secret, secret_hash)
     │                                 │    (PBKDF2 hash)
     │                                 │ 3. Genera JWT RS256:
     │                                 │    - iss: "texcore"
     │                                 │    - sub: service_name
     │                                 │    - scope: ["lotes:read"]
     │                                 │    - type: "service_access"
     │                                 │    - exp: now + ACCESS_TTL
     │                                 │    - jti: uuid4()
     │◀────────────────────────────────│
     │  200 { access_token, refresh_token, expires_in }
     │                                 │
     │  (almacena token EN MEMORIA)    │
     │                                 │
```

### Flujo de Llamada Autenticada

```
Servicio Satélite                Django Backend
     │                                 │
     │  GET /api/internal/v1/lotes/{codigo}/validate/
     │  Header: Authorization: Bearer <JWT>
     │────────────────────────────────▶│
     │                                 │ JWTServiceAuthentication:
     │                                 │ 1. jwt.decode(token, PUBLIC_KEY, RS256)
     │                                 │ 2. Verifica exp, type == "service_access"
     │                                 │ 3. Crea ServicePrincipal(name, scopes)
     │                                 │
     │                                 │ IsInternalService:
     │                                 │ 4. isinstance(request.user, ServicePrincipal)
     │                                 │
     │                                 │ HasScope("lotes:read"):
     │                                 │ 5. "lotes:read" in principal.scopes
     │                                 │
     │                                 │ 6. Ejecuta logica de negocio
     │◀────────────────────────────────│
     │  200 { lote_id, codigo_lote, producto, ... }
     │                                 │
```

### Renovacion de Token (JWTTokenManager)

```python
# scanning_service/src/infrastructure/jwt_token_manager.py
REFRESH_BUFFER_SECONDS = 30

def get_valid_token(self) -> str:
    # Refresca si el token expira en los proximos 30 segundos
    if self._access_token is None or self._is_expiring(self._access_token):
        self._access_token = self._fetch_token()
    return self._access_token
```

El token se almacena solo en memoria del proceso (nunca en disco ni logs), cumpliendo ISO 27001 A.10.

### Estructura del JWT de Servicio

```json
{
  "iss": "texcore",
  "sub": "scanning_service",
  "type": "service_access",
  "scope": ["lotes:read"],
  "iat": 1748823600,
  "exp": 1748823900,
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

Firmado con clave RSA 2048 bits. La clave privada reside exclusivamente en Django (`INTERNAL_JWT_PRIVATE_KEY`). Los servicios satélite solo tienen la clave publica (`INTERNAL_JWT_PUBLIC_KEY`) para verificar.

---

## Servicio Satélite: scanning_service

### Estructura Interna

```
scanning_service/
├── src/
│   ├── main.py                        # App factory, singletons, fail-fast env check
│   ├── domain/
│   │   └── models.py                  # Dataclasses puros: Producto, OrdenProduccion,
│   │                                  #   LoteProduccion, Bodega, StockBodega
│   ├── schemas/
│   │   └── validate.py                # Pydantic: ValidateRequest, LoteInfo, ValidateResponse
│   ├── repositories/
│   │   └── base.py                    # Protocol ILoteRepository (interfaz)
│   ├── services/
│   │   └── validation_service.py      # LoteValidationService (logica de negocio)
│   ├── routers/
│   │   ├── validate.py                # POST /validate
│   │   └── health.py                  # GET /health
│   └── infrastructure/
│       ├── django_client.py           # DjangoApiClient (implementa ILoteRepository)
│       └── jwt_token_manager.py       # JWTTokenManager
└── tests/
    ├── unit/test_validation_service.py
    ├── integration/test_validate_endpoint.py
    └── test_django_client.py
```

### Capas de la Arquitectura

```
        ┌─────────────────────────────────────────────┐
        │  Capa HTTP (routers/)                        │
        │  FastAPI: valida request Pydantic, llama svc │
        └──────────────────────┬──────────────────────┘
                               │ LoteValidationService(repo)
        ┌──────────────────────▼──────────────────────┐
        │  Capa de Servicio (services/)                │
        │  LoteValidationService: reglas de negocio    │
        │  SRP: no conoce HTTP, no conoce HTTP client  │
        └──────────────────────┬──────────────────────┘
                               │ ILoteRepository (Protocol)
        ┌──────────────────────▼──────────────────────┐
        │  Capa de Repositorio (repositories/)         │
        │  ILoteRepository: Protocolo/Interfaz         │
        │  (runtime_checkable Protocol — LSP + DIP)    │
        └──────────────────────┬──────────────────────┘
                               │ implementa
        ┌──────────────────────▼──────────────────────┐
        │  Capa de Infraestructura (infrastructure/)   │
        │  DjangoApiClient: hace llamada HTTP a Django │
        │  JWTTokenManager: ciclo de vida del token    │
        └─────────────────────────────────────────────┘
```

### Variables de Entorno

| Variable | Descripcion | Ejemplo |
|---|---|---|
| `DJANGO_INTERNAL_URL` | URL base del backend Django | `http://backend:8000` |
| `SERVICE_NAME` | Nombre del servicio (debe coincidir con ServiceCredential.name) | `scanning_service` |
| `SERVICE_SECRET` | Secreto plano (se compara con hash PBKDF2 en BD) | `<secret>` |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave publica RSA 2048 en PEM (newlines como `\n`) | `-----BEGIN PUBLIC KEY-----\n...` |

Fail-fast: `main.py` lanza `RuntimeError` al inicio si alguna variable falta, evitando arrancar en estado inconsistente.

### Circuit Breaker en DjangoApiClient

```python
_CIRCUIT_THRESHOLD = 3

# Despues de 3 timeouts consecutivos:
raise RuntimeError("Django Internal API no responde (circuit breaker activo).")
```

Cada respuesta exitosa resetea el contador a 0.

### Endpoints del scanning_service

#### GET /health

Verifica conectividad con Django Internal API.

```
Request:  GET /health
Response (saludable):
  200 { "status": "healthy", "django_api": "connected" }

Response (Django no responde):
  503 { "detail": "Django API unreachable: ..." }
```

#### POST /validate

Valida un codigo de lote escaneado (QR o codigo de barras).

```
Request:
  POST /validate
  Content-Type: application/json
  { "code": "LOT-2026-001" }

Response (lote valido con stock):
  200 {
    "valid": true,
    "lote": {
      "codigo": "LOT-2026-001",
      "producto_id": 123,
      "producto_nombre": "Hilo Nylon 40/2",
      "peso": "150.500",
      "bodega_id": 5,
      "bodega_nombre": "Bodega Principal"
    }
  }

Response (lote no encontrado):
  200 { "valid": false, "reason": "Lote no encontrado en el sistema" }

Response (sin stock):
  200 { "valid": false, "reason": "Lote existe pero no tiene stock disponible (0 kg)" }

Response (sin orden/producto):
  200 { "valid": false, "reason": "Lote no tiene orden de produccion o producto asociado" }
```

**Nota:** Las respuestas invalidas son siempre HTTP 200 con `valid: false`. Los errores HTTP 503/500 indican falla en la infraestructura (Django no responde, circuit breaker, etc.).

### Flujo Interno de DjangoApiClient (patron cache de request)

```
get_lote_by_codigo(codigo)
  │
  │── GET /api/internal/v1/lotes/{quote(codigo, safe='')}/validate/
  │   Authorization: Bearer <JWT>
  │
  ├── 404 → return None
  ├── 200 → parsea JSON:
  │         - Construye LoteProduccion(id, codigo_lote, orden_produccion)
  │         - Almacena StockBodega en _stock_cache[lote_id]
  │         - return LoteProduccion
  │
  ▼
get_stock_activo_por_lote(lote_id)
  │── return _stock_cache.pop(lote_id, None)
  │   (pop: limpia cache tras uso, una sola llamada HTTP por validacion)
```

> **Fix 2026-08-25 — inyección de path sin codificar:** `codigo` viene tal cual del escáner físico.
> Si el operario apunta por error al QR de trazabilidad de la etiqueta (una URL completa, con `/`)
> en vez del código de barras, ese valor interpolado sin codificar en el f-string de la URL
> corrompía el path de la request — Django no lograba enrutarla al endpoint de validación y caía
> en el catch-all SPA (`TemplateDoesNotExist: index.html` → 500 en vez de un 404 limpio). Corregido
> envolviendo `codigo` con `urllib.parse.quote(codigo, safe='')` antes de interpolarlo: cualquier
> valor con caracteres especiales llega como un único segmento de path y simplemente no encuentra
> el lote (`404` → `None` → `{"valid": false}`), sin importar qué símbolo se haya escaneado. Ver
> `scanning_service/tests/test_django_client.py::test_get_lote_by_codigo_dado_codigo_con_barras_...`.

---

## Servicio Satélite: reporting_excel

### Patron DjangoReportRepository

`reporting_excel` no usa pyodbc ni credenciales de BD. En su lugar, `DjangoReportRepository.execute_sp()` mapea nombres de stored procedures a endpoints de la Django Internal API.

```python
# Mapeo SP → endpoint REST
_SP_MAPPING = {
    "sp_GetKardexBodega":        ("/api/internal/v1/reports/kardex/", [...]),
    "sp_GetProductosCatalogo":   ("/api/internal/v1/reports/productos/", []),
    "sp_GetStockActualBodega":   ("/api/internal/v1/reports/stock-actual/", [...]),
    "sp_GetValorizacionInventario": ("/api/internal/v1/reports/valorizacion/", [...]),
    "sp_GetVentasPorVendedor":   ("/api/internal/v1/vendedores/{vendedor_id}/ventas/", [...]),
    "sp_GetVentasGerencial":     ("/api/internal/v1/gerencial/ventas/", [...]),
    # ... 18 SPs en total
}

def execute_sp(self, sp_name: str, params: dict) -> pd.DataFrame:
    endpoint, param_names = _SP_MAPPING[sp_name]
    url = self._base_url + endpoint.format(**params)
    response = httpx.get(url, params=query_params, headers=self._headers())
    return pd.DataFrame(response.json())
```

### Variables de Entorno

| Variable | Descripcion |
|---|---|
| `DJANGO_INTERNAL_URL` | URL base del backend Django |
| `SERVICE_NAME` | `reporting_excel` |
| `SERVICE_SECRET` | Secreto del servicio |
| `INTERNAL_JWT_PUBLIC_KEY` | Clave publica RSA para verificar tokens |
| `CORS_ALLOWED_ORIGINS` | Origenes permitidos (ej: `http://backend:8000`) |

Scope requerido para `reporting_excel`: `reports:read`

---

## Django Internal API (/api/internal/v1/)

### Autenticacion y Permisos

Todas las views de la API interna declaran:

```python
authentication_classes = [JWTServiceAuthentication]
permission_classes = [IsInternalService, HasScope("lotes:read")]  # o "reports:read"
```

- `JWTServiceAuthentication`: decodifica el JWT RS256, verifica `exp`, `type == "service_access"`, crea `ServicePrincipal(service_name, scopes)`.
- `IsInternalService`: verifica que `request.user` sea instancia de `ServicePrincipal`.
- `HasScope(scope)`: verifica que el scope requerido este en `principal.scopes`.

Si el header `Authorization` no esta presente, `JWTServiceAuthentication` retorna `None` (permite que otros backends continuen). Si el token es invalido o expirado, lanza `AuthenticationFailed`.

### Tabla de Endpoints Internos

| Metodo | Path | Scope | Descripcion |
|---|---|---|---|
| POST | `/api/internal/v1/auth/token/` | - | Emite JWT access+refresh para un servicio |
| POST | `/api/internal/v1/auth/refresh/` | - | Renueva access token con refresh token |
| GET | `/api/internal/v1/lotes/{codigo_barras}/validate/` | `lotes:read` | Datos de lote + stock para scanning_service |
| GET | `/api/internal/v1/reports/kardex/` | `reports:read` | Kardex de bodega |
| GET | `/api/internal/v1/reports/productos/` | `reports:read` | Catalogo de productos |
| GET | `/api/internal/v1/reports/usuarios/` | `reports:read` | Usuarios del sistema |
| GET | `/api/internal/v1/reports/stock-actual/` | `reports:read` | Stock actual por bodega |
| GET | `/api/internal/v1/reports/valorizacion/` | `reports:read` | Valorizacion de inventario |
| GET | `/api/internal/v1/reports/aging/` | `reports:read` | Aging de inventario |
| GET | `/api/internal/v1/reports/rotacion/` | `reports:read` | Rotacion de inventario |
| GET | `/api/internal/v1/reports/stock-cero/` | `reports:read` | Productos sin stock |
| GET | `/api/internal/v1/reports/resumen-movimientos/` | `reports:read` | Resumen de movimientos |
| GET | `/api/internal/v1/vendedores/{id}/ventas/` | `reports:read` | Ventas por vendedor |
| GET | `/api/internal/v1/vendedores/{id}/top-clientes/` | `reports:read` | Top clientes por vendedor |
| GET | `/api/internal/v1/vendedores/{id}/deudores/` | `reports:read` | Deudores por vendedor |
| GET | `/api/internal/v1/gerencial/ventas/` | `reports:read` | Ventas gerenciales |
| GET | `/api/internal/v1/gerencial/top-clientes/` | `reports:read` | Top clientes gerenciales |
| GET | `/api/internal/v1/gerencial/deudores/` | `reports:read` | Deudores gerenciales |
| GET | `/api/internal/v1/produccion/ordenes/` | `reports:read` | Ordenes de produccion |
| GET | `/api/internal/v1/produccion/lotes/` | `reports:read` | Lotes de produccion |
| GET | `/api/internal/v1/produccion/tendencia/` | `reports:read` | Tendencia de produccion |

### Contrato del Endpoint de Validacion de Lote

```
GET /api/internal/v1/lotes/{codigo_barras}/validate/
Authorization: Bearer <JWT RS256>

Response 200:
{
  "lote_id": 42,
  "codigo_lote": "LOT-2026-001",
  "producto": {
    "id": 123,
    "descripcion": "Hilo Nylon 40/2"
  },
  "estado": "terminada",
  "orden_produccion_id": 17,
  "stock_id": 88,
  "peso_kg": "150.500",
  "bodega": {
    "id": 5,
    "nombre": "Bodega Principal"
  }
}

Response 404 (lote no existe o sin orden/producto):
{ "detail": "Lote no encontrado." }
```

Si no hay stock (`cantidad = 0`), los campos `stock_id`, `peso_kg` y `bodega` son `null`.

### Contrato del Endpoint de Emision de Token

```
POST /api/internal/v1/auth/token/
Content-Type: application/json

{
  "service_name": "scanning_service",
  "service_secret": "<plain text secret>"
}

Response 200:
{
  "access_token": "<JWT RS256>",
  "refresh_token": "<JWT RS256>",
  "expires_in": 300
}

Response 401: { "detail": "Credenciales invalidas." }
Response 403: { "detail": "Servicio deshabilitado." }
```

### Contrato del Endpoint de Renovacion

```
POST /api/internal/v1/auth/refresh/
Content-Type: application/json

{ "refresh_token": "<JWT RS256 con type=service_refresh>" }

Response 200:
{
  "access_token": "<nuevo JWT RS256>",
  "refresh_token": "<nuevo JWT RS256>",
  "expires_in": 300
}

Response 401: { "detail": "Refresh token expirado." }
```

---

## Modelo ServiceCredential

```python
# internal_api/models.py
class ServiceCredential(models.Model):
    name          = CharField(max_length=100, unique=True)
    secret_hash   = CharField(max_length=255)    # PBKDF2 via make_password()
    is_active     = BooleanField(default=True)
    allowed_scopes = JSONField(default=list)      # Ej: ["lotes:read"]
    created_at    = DateTimeField(auto_now_add=True)
    last_used_at  = DateTimeField(null=True)

    class Meta:
        db_table = "internal_service_credential"
```

#### Tabla en BD

| Campo | Tipo SQL | Descripcion |
|---|---|---|
| `id` | INT (PK) | Identificador autoincremental |
| `name` | NVARCHAR(100) UNIQUE | Nombre del servicio (ej: `scanning_service`) |
| `secret_hash` | NVARCHAR(255) | Hash PBKDF2 del secreto |
| `is_active` | BIT | Si 0, el servicio no puede autenticarse |
| `allowed_scopes` | NVARCHAR(MAX) JSON | Lista de scopes permitidos |
| `created_at` | DATETIME2 | Timestamp de creacion |
| `last_used_at` | DATETIME2 NULL | Timestamp de ultimo uso |

---

## Modelos de Inventario para Despacho

### HistorialDespacho (actualizado)

```python
# inventory/models.py
class HistorialDespacho(models.Model):
    fecha_despacho       = DateTimeField(auto_now_add=True)
    usuario              = ForeignKey(AUTH_USER_MODEL, on_delete=SET_NULL, null=True)
    pedidos              = ManyToManyField('gestion.PedidoVenta',
                               through='DetalleHistorialDespachoPedido')
    total_bultos         = IntegerField()
    total_peso           = DecimalField(max_digits=12, decimal_places=2)
    observaciones        = TextField(blank=True, null=True)
    items_no_despachados = JSONField(default=dict, blank=True)
    # Ejemplo de items_no_despachados:
    # {
    #   "Hilo Nylon 40/2": {
    #     "requerido": 200.0,
    #     "escaneado": 150.0,
    #     "faltante": 50.0
    #   }
    # }
```

`items_no_despachados` es un campo `JSONField` introducido en la migracion `0028`. Si el despacho es completo el campo queda como `{}`.

### DetalleHistorialDespachoPedido (tabla M2M through)

```python
class DetalleHistorialDespachoPedido(models.Model):
    historial           = ForeignKey(HistorialDespacho, on_delete=PROTECT)
    pedido              = ForeignKey('gestion.PedidoVenta', on_delete=PROTECT)
    cantidad_despachada = DecimalField(max_digits=12, decimal_places=3, default=0.000)
```

Esta es la tabla intermedia de la relacion M2M entre `HistorialDespacho` y `PedidoVenta`. **No es un TextField con IDs separados por coma** (eso era la arquitectura anterior).

### DetalleHistorialDespacho (detalle por lote)

```python
class DetalleHistorialDespacho(models.Model):
    historial    = ForeignKey(HistorialDespacho, related_name='detalles', on_delete=CASCADE)
    lote         = ForeignKey(LoteProduccion, on_delete=SET_NULL, null=True)
    producto     = ForeignKey(Producto, on_delete=SET_NULL, null=True)
    peso         = DecimalField(max_digits=12, decimal_places=2)
    es_devolucion = BooleanField(default=False)
```

### Diagrama de Relaciones

```
HistorialDespacho (1)
    │
    ├──through DetalleHistorialDespachoPedido──▶ (N) PedidoVenta
    │
    ├──related_name="detalles"──▶ (N) DetalleHistorialDespacho
    │                                       │
    │                                       ├──▶ (1) LoteProduccion
    │                                       └──▶ (1) Producto
    │
    └──▶ (1) CustomUser (usuario)
```

### Esquema de Tablas en BD

#### `inventory_historialdespacho`

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | INT PK | Identificador autoincremental |
| `fecha_despacho` | DATETIME2 | Timestamp automatico al crear |
| `usuario_id` | INT FK | Usuario que proceso el despacho |
| `total_bultos` | INT | Cantidad de lotes procesados |
| `total_peso` | DECIMAL(12,2) | Peso total despachado en kg |
| `observaciones` | NVARCHAR(MAX) NULL | Notas opcionales |
| `items_no_despachados` | NVARCHAR(MAX) JSON | Productos con faltantes (puede ser `{}`) |

#### `inventory_detallehistorialdespachopedido`

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | INT PK | Identificador autoincremental |
| `historial_id` | INT FK | Referencia al HistorialDespacho |
| `pedido_id` | INT FK | Referencia al PedidoVenta |
| `cantidad_despachada` | DECIMAL(12,3) | Cantidad efectivamente despachada |

#### `inventory_detallehistorialdespacho`

| Campo | Tipo | Descripcion |
|---|---|---|
| `id` | INT PK | Identificador autoincremental |
| `historial_id` | INT FK | Referencia al HistorialDespacho |
| `lote_id` | INT FK NULL | Lote despachado |
| `producto_id` | INT FK NULL | Producto del lote |
| `peso` | DECIMAL(12,2) | Peso del lote en kg |
| `es_devolucion` | BIT | Flag para devoluciones futuras |

---

## ProcessDespachoAPIView

**Endpoint:** `POST /api/inventory/process-despacho/`
**Permisos:** `IsDespachoWriter`

### Request

```json
{
  "pedidos": [1, 2, 3],
  "lotes": ["LOT-2026-001", "LOT-2026-002"],
  "observaciones": "Despacho urgente cliente X",
  "confirmar_incompleto": false
}
```

`confirmar_incompleto` es opcional, por defecto `false`.

### Logica de Validacion de Completitud (_calcular_incompletos)

Antes de iniciar la transaccion, se invoca el metodo estatico:

```python
@staticmethod
def _calcular_incompletos(pedidos_ids: list, lotes_codes: list) -> dict:
    """
    1. Calcula requeridos: suma det.peso por producto para cada pedido.
    2. Calcula escaneados: suma stock.cantidad por producto para cada lote.
    3. Retorna {} si todo esta cubierto.
    4. Retorna dict con faltantes si hay discrepancias.
    """
```

Estructura del resultado cuando hay faltantes:

```json
{
  "Hilo Nylon 40/2": {
    "requerido": 200.0,
    "escaneado": 150.0,
    "faltante": 50.0
  },
  "Algodon Crudo": {
    "requerido": 80.0,
    "escaneado": 0.0,
    "faltante": 80.0
  }
}
```

### Diagrama de Flujo de la Vista

```
POST /api/inventory/process-despacho/
         │
         │ 1. Leer pedidos[], lotes[], observaciones, confirmar_incompleto
         │
         ▼
┌─────────────────────────────────────────┐
│  _calcular_incompletos(pedidos, lotes)  │
│  (fuera de transaccion — sin efectos)   │
└──────────────────┬──────────────────────┘
                   │
          ┌────────▴────────┐
          │  hay faltantes? │
          └────────┬────────┘
                   │
        NO ────────┤──────── SI
        │          │         │
        │          │   confirmar_incompleto?
        │          │         │
        │          │    SI ──┤──NO
        │          │    │    │
        │          │    │    ▼
        │          │    │  HTTP 409
        │          │    │  {
        │          │    │    "error": "despacho_incompleto",
        │          │    │    "message": "Hay productos...",
        │          │    │    "items_incompletos": { ... }
        │          │    │  }
        │          │    │
        ▼          ▼    ▼
┌──────────────────────────────────────────────────────────────┐
│ transaction.atomic()                                         │
│                                                              │
│ 1. HistorialDespacho.objects.create(                         │
│      usuario, total_bultos, total_peso=0,                    │
│      observaciones, items_no_despachados=items_incompletos   │
│    )                                                         │
│                                                              │
│ 2. Para cada pedido_id:                                      │
│    DetalleHistorialDespachoPedido.objects.create(            │
│      historial, pedido_id, cantidad_despachada=0             │
│    )                                                         │
│                                                              │
│ 3. Para cada codigo de lote:                                 │
│    a. LoteProduccion.objects.get(codigo_lote=code)           │
│    b. StockBodega.objects.select_for_update()                │
│       .filter(lote=lote, cantidad__gt=0).first()             │
│    c. Si no hay stock → ValidationError (rollback)           │
│    d. MovimientoInventario.objects.create(                   │
│         tipo_movimiento='VENTA',                             │
│         producto, cantidad=stock.cantidad,                   │
│         bodega_origen=stock.bodega, lote,                    │
│         documento_ref=f"Despacho #{historial.id} (...)"      │
│       )                                                      │
│    e. DetalleHistorialDespacho.objects.create(               │
│         historial, lote, producto, peso=stock.cantidad       │
│       )                                                      │
│    f. stock.cantidad = 0; stock.save()                       │
│                                                              │
│ 4. historial.total_peso = sum(pesos); historial.save()       │
│                                                              │
│ 5. PedidoVenta.objects.filter(id__in=pedidos_ids)            │
│    .update(estado='despachado', fecha_despacho=today)        │
└──────────────────────────────────────────────────────────────┘
         │
         ▼
HTTP 200:
{
  "message": "Despacho procesado correctamente",
  "despacho_id": 42,
  "pedidos_actualizados": 3,
  "lotes_procesados": 2,
  "items_no_despachados": { ... }  // {} si fue completo
}
```

### Respuestas de la Vista

| HTTP | Situacion |
|---|---|
| 200 | Despacho procesado exitosamente |
| 400 | Faltan pedidos o lotes / lote invalido / sin stock en transaccion |
| 409 | Despacho incompleto y `confirmar_incompleto=false` |
| 500 | Error inesperado |

### Garantias Transaccionales

- **Atomicidad:** `transaction.atomic()` garantiza que si cualquier lote falla, se hace rollback de todo.
- **Concurrencia:** `select_for_update()` sobre `StockBodega` previene condiciones de carrera.
- **Auditoria:** Cada movimiento genera un registro en `MovimientoInventario` con `tipo_movimiento='VENTA'` y `documento_ref` que incluye el ID del historial y los pedidos.

---

## Flujo Completo de Despacho (end-to-end)

```
1. Usuario selecciona pedidos pendientes
   Frontend (DespachoDashboard — Modo Seleccion)
   │
   ├── GET /api/pedidos-venta/?estado=pendiente
   └── Checkbox multiple, validacion de mismo cliente

2. Usuario inicia despacho
   └── Modo Escaneo activado (DespachoDashboard — Modo Despacho)

3. Usuario escanea QR / codigo de barras
   │
   └── POST /api/scanning/validate          (Nginx → scanning_service)
       { "code": "LOT-2026-001" }
       │
       └── scanning_service:
           ├── JWTTokenManager.get_valid_token()
           │   └── Si token expira pronto:
           │       POST /api/internal/v1/auth/token/  → nuevo JWT
           │
           └── DjangoApiClient.get_lote_by_codigo(codigo)
               └── GET /api/internal/v1/lotes/{codigo}/validate/
                   Authorization: Bearer <JWT RS256>
                   │
                   └── Django: ValidateLoteView
                       ├── JWTServiceAuthentication verifica JWT
                       ├── HasScope("lotes:read") verifica scope
                       └── Consulta LoteProduccion + StockBodega
                           └── Retorna JSON con datos del lote

4. Frontend acumula lotes escaneados
   └── Lista visual con progreso por producto (requerido vs escaneado)

5. Usuario confirma despacho
   │
   └── POST /api/inventory/process-despacho/
       {
         "pedidos": [1, 2],
         "lotes": ["LOT-001", "LOT-002"],
         "observaciones": "...",
         "confirmar_incompleto": false
       }
       │
       ├── CASO A: Todo completo → HTTP 200 → despacho registrado
       │
       ├── CASO B: Faltantes detectados → HTTP 409
       │   └── Frontend muestra modal con tabla de faltantes
       │       └── Usuario confirma despacho parcial:
       │           POST con confirmar_incompleto=true
       │           └── HTTP 200 → despacho registrado con items_no_despachados
       │
       └── CASO C: Error de validacion → HTTP 400

6. Post-despacho
   ├── GET /api/pedidos-venta/{id}/download_pdf/  (abre PDF en nueva pestana)
   └── Reset al Modo Seleccion
```

---

## Seguridad

### Headers HTTP (Nginx)

Configurados en ambos bloques `server` (HTTP y HTTPS):

| Header | Valor |
|---|---|
| `server_tokens` | `off` (oculta version de Nginx) |
| `X-Frame-Options` | `SAMEORIGIN` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; ...` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (solo en bloque HTTPS 443) |

### Rate Limiting (Nginx)

```nginx
limit_req_zone $binary_remote_addr zone=login_zone:10m   rate=5r/m;
limit_req_zone $binary_remote_addr zone=refresh_zone:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=api_zone:10m     rate=100r/s;
```

| Zona | Rate | Burst | Aplica a |
|---|---|---|---|
| `login_zone` | 5 req/min | 3 | `/api/token/` |
| `refresh_zone` | 10 req/min | 5 | `/api/token/refresh/` |
| `api_zone` | 100 req/s | 200 | `/api/*` (resto) |

### Aislamiento de Red Docker

```yaml
# infrastructure/docker/docker-compose.prod.yml

db:
  expose: ["1433"]   # Solo accesible dentro de la red Docker
  # NO tiene "ports" — el puerto 1433 NUNCA se expone al host en produccion

scanning:
  expose: ["8000"]   # Solo accesible desde Nginx dentro de la red Docker

reporting_excel:
  expose: ["8002"]   # Solo accesible desde el backend Django

nginx:
  ports:
    - "80:80"
    - "443:443"  # Unico punto de entrada externo
```

### Credenciales de Servicios Satélite

Las credenciales (`ServiceCredential`) se almacenan con hash PBKDF2 (via `make_password` de Django). El secreto plano nunca se almacena en BD ni en logs.

```python
@staticmethod
def hash_secret(plain_secret: str) -> str:
    return make_password(plain_secret)  # PBKDF2-SHA256 por defecto en Django
```

### SSL/TLS

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers off;
ssl_ciphers "EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH";
ssl_ecdh_curve secp384r1;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;
```

---

## Docker Compose (produccion)

### Configuracion de Servicios

```yaml
services:
  db:
    expose: ["1433"]                    # Puerto NO expuesto al host
    healthcheck: sqlcmd SELECT 1 ...

  backend:
    environment:
      DB_HOST: db
      DB_PORT: 1433
      INTERNAL_JWT_PRIVATE_KEY: ${INTERNAL_JWT_PRIVATE_KEY}   # Solo backend tiene clave privada
      INTERNAL_JWT_PUBLIC_KEY: ${INTERNAL_JWT_PUBLIC_KEY}
      SCANNING_SERVICE_SECRET: ${SCANNING_SERVICE_SECRET}     # Para register_services
      REPORTING_SERVICE_SECRET: ${REPORTING_SERVICE_SECRET}
    depends_on:
      db: { condition: service_healthy }

  scanning:
    expose: ["8000"]
    environment:
      DJANGO_INTERNAL_URL: http://backend:8000
      SERVICE_NAME: scanning_service
      SERVICE_SECRET: ${SCANNING_SERVICE_SECRET}
      INTERNAL_JWT_PUBLIC_KEY: ${INTERNAL_JWT_PUBLIC_KEY}     # Solo clave publica
    depends_on:
      backend: { condition: service_started }

  reporting_excel:
    expose: ["8002"]
    environment:
      DJANGO_INTERNAL_URL: http://backend:8000
      SERVICE_NAME: reporting_excel
      SERVICE_SECRET: ${REPORTING_SERVICE_SECRET}
      INTERNAL_JWT_PUBLIC_KEY: ${INTERNAL_JWT_PUBLIC_KEY}     # Solo clave publica
    depends_on:
      backend: { condition: service_started }
    # NOTA: backend NO depende de reporting_excel (dependencia circular eliminada)

  nginx:
    ports: ["80:80", "443:443"]
    depends_on: [backend]
```

### Dependencias entre Servicios

```
db ──(service_healthy)──▶ backend ──(service_started)──▶ scanning
                      └──(service_started)──▶ reporting_excel
nginx ──(service_started)──▶ backend
```

`reporting_excel` ya NO esta en el `depends_on` del `backend`. La dependencia circular fue eliminada.

---

## Scripts y Comandos de Gestion

### Generar Par de Claves RSA

```bash
python scripts/generate_rsa_keys.py
```

Genera clave RSA 2048 bits. Salida: dos lineas para agregar al `.env`:
- `INTERNAL_JWT_PRIVATE_KEY="..."` (solo para `backend`)
- `INTERNAL_JWT_PUBLIC_KEY="..."` (para `backend`, `scanning`, `reporting_excel`)

Las newlines del PEM se codifican como `\n` para ser compatibles con variables de entorno.

### Registrar Credenciales de Servicios Satélite

```bash
# Primer despliegue (crea las credenciales en BD)
docker compose -f infrastructure/docker/docker-compose.prod.yml exec backend \
  python manage.py register_services

# Rotar secrets (actualiza los hashes en BD)
docker compose -f infrastructure/docker/docker-compose.prod.yml exec backend \
  python manage.py register_services --force
```

Lee `SCANNING_SERVICE_SECRET` y `REPORTING_SERVICE_SECRET` del entorno y crea/actualiza los registros `ServiceCredential` con hashes PBKDF2.

### Migraciones

```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml exec backend \
  python manage.py migrate
```

La migracion `inventory/migrations/0028_...` agrego el campo `items_no_despachados` (JSONField) a `HistorialDespacho`.

### Comandos de Diagnostico

```bash
# Logs del scanning service
docker compose -f infrastructure/docker/docker-compose.prod.yml logs -f scanning

# Verificar health del scanning service
docker compose -f infrastructure/docker/docker-compose.prod.yml exec scanning \
  curl http://localhost:8000/health

# Verificar conectividad interna Django ↔ scanning
docker compose -f infrastructure/docker/docker-compose.prod.yml exec scanning \
  curl http://backend:8000/api/health/

# Ver credenciales registradas (sin mostrar hashes)
docker compose -f infrastructure/docker/docker-compose.prod.yml exec backend \
  python manage.py shell -c \
  "from internal_api.models import ServiceCredential; [print(c) for c in ServiceCredential.objects.all()]"
```

---

## Trazabilidad y Auditoria

### AuditLogger (ISO 27001 A.12.4)

Cada acceso a la API interna registra:

```python
AuditLogger.log(
    service="scanning_service",
    action="validate_lote",
    resource="LOT-2026-001",
    status_code=200,
)
```

Emite log estructurado RFC 5424 con campos: `service`, `action`, `resource`, `status_code`, `rfc5424_severity`.

### Logs Estructurados (RFC 5424)

Todos los servicios (scanning_service, reporting_excel, Django) emiten logs en formato RFC 5424 con Structured Data (SD). En `scanning_service`:

```
facility=18 (local2), app_name="texcore-scanning"
```

Si `/dev/log` esta disponible, tambien envia a syslog del host para integracion con herramientas de monitoreo.

### Cadena de Trazabilidad de un Despacho

```
HistorialDespacho.id = 42
  │
  ├── DetalleHistorialDespachoPedido: pedido_id=1, pedido_id=2
  │
  ├── DetalleHistorialDespacho: lote="LOT-001", peso=150.5 kg
  │                             lote="LOT-002", peso=80.0 kg
  │
  └── MovimientoInventario (tipo=VENTA):
        documento_ref = "Despacho #42 (Pedidos: 1,2)"
        bodega_origen = Bodega Principal
        producto = Hilo Nylon 40/2
        cantidad = 150.5 kg
        saldo_resultante = 0.00
```

---

## Checklist de Funcionalidades

### Implementado

- [x] scanning_service sin acceso a BD — consume Django Internal API con JWT RS256
- [x] reporting_excel sin acceso a BD — DjangoReportRepository.execute_sp() via API interna
- [x] JWTServiceAuthentication + IsInternalService + HasScope en Django
- [x] ServiceCredential con hash PBKDF2 (nunca secreto plano en BD)
- [x] JWTTokenManager con renovacion automatica 30s antes de expirar
- [x] Circuit breaker en DjangoApiClient (3 errores → RuntimeError)
- [x] Fail-fast en main.py de scanning_service (variables de entorno obligatorias)
- [x] ProcessDespachoAPIView con validacion de items incompletos (HTTP 409)
- [x] Campo `items_no_despachados` en HistorialDespacho (JSONField, migracion 0028)
- [x] Modal de confirmacion en frontend para despachos parciales (`confirmar_incompleto`)
- [x] Relacion M2M via DetalleHistorialDespachoPedido (reemplaza pedidos_ids como TextField)
- [x] Security headers HTTP en Nginx (X-Frame-Options, X-Content-Type-Options, etc.)
- [x] HSTS en bloque HTTPS (`max-age=31536000; includeSubDomains`)
- [x] Rate limiting en Nginx (login, refresh, api)
- [x] `server_tokens off` en Nginx
- [x] Aislamiento de red Docker: DB con `expose` no `ports` en produccion
- [x] `backend` no depende de `reporting_excel` (dependencia circular eliminada)
- [x] `register_services` management command
- [x] `scripts/generate_rsa_keys.py`
- [x] AuditLogger RFC 5424 en todos los endpoints de la API interna
- [x] Logs estructurados RFC 5424 en scanning_service con handler syslog
- [x] Trazabilidad completa: MovimientoInventario vinculado a cada despacho
- [x] `select_for_update()` en StockBodega para prevenir condiciones de carrera
- [x] Reversion de despacho con justificacion obligatoria (DespachoReversionService)
- [x] GUIA_DESPLIEGUE_PRODUCCION.md actualizada

### Pendiente

- [ ] Dashboard de metricas de despacho (tasa de completitud, tiempo promedio, etc.)
- [ ] Generacion de PDF del documento de despacho (guia de despacho imprimible)
- [ ] Monitoreo con Prometheus + Grafana (metricas de latencia, errores, circuit breaker)
- [ ] Tests de integracion E2E del flujo completo con Docker Compose
- [ ] Funcionalidad de devoluciones (reversion parcial por lote especifico)
- [ ] Caché Redis para validaciones frecuentes en scanning_service

---

## Archivos Clave de Referencia

| Archivo | Descripcion |
|---|---|
| `scanning_service/src/main.py` | App factory, singletons, fail-fast |
| `scanning_service/src/infrastructure/django_client.py` | Adapter HTTP → ILoteRepository |
| `scanning_service/src/infrastructure/jwt_token_manager.py` | Ciclo de vida del JWT |
| `scanning_service/src/services/validation_service.py` | Logica de negocio de validacion |
| `internal_api/authentication.py` | JWTServiceAuthentication + ServicePrincipal |
| `internal_api/permissions.py` | IsInternalService, HasScope |
| `internal_api/views/auth_views.py` | ServiceTokenView, ServiceTokenRefreshView |
| `internal_api/views/scanning_views.py` | ValidateLoteView |
| `internal_api/views/reporting_views.py` | 18 endpoints de reporting |
| `internal_api/models.py` | ServiceCredential |
| `internal_api/audit.py` | AuditLogger RFC 5424 |
| `internal_api/urls.py` | URLconf de la API interna |
| `inventory/models.py` | HistorialDespacho, DetalleHistorialDespachoPedido, DetalleHistorialDespacho |
| `inventory/views.py` | ProcessDespachoAPIView, HistorialDespachoViewSet |
| `reporting_excel/src/infrastructure/django_client.py` | DjangoReportRepository |
| `nginx/nginx.conf` | Rate limiting, security headers, routing |
| `infrastructure/docker/docker-compose.prod.yml` | Configuracion de produccion con aislamiento de red |
| `scripts/generate_rsa_keys.py` | Generador de par de claves RSA 2048 |
| `gestion/management/commands/register_services.py` | Registro de credenciales de servicios satélite |
