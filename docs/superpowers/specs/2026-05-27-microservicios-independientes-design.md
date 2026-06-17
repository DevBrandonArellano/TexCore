# Diseño: Microservicios Independientes — TexCore

**Fecha:** 2026-05-27  
**Autor:** Brandon Arellano  
**Estado:** Aprobado para implementación  
**Estándares:** ISO 27001, COBIT DSS05/DSS06, SOLID, RFC 5424  

---

## 1. Contexto y Problema

Los tres microservicios FastAPI (`scanning_service`, `printing_service`, `reporting_excel`) actualmente comparten la base de datos MS SQL Server `texcore_db` con el core Django. Esto viola:

- **ISO 27001 A.9** (Control de Acceso): múltiples servicios tienen credenciales SQL completas
- **ISO 27001 A.12.4** (Registro de Eventos): no hay audit trail por identidad de servicio
- **COBIT DSS05** (Gestión de Servicios de Seguridad): sin separación de responsabilidades
- **COBIT DSS06** (Controles de Proceso): sin trazabilidad de acceso a datos sensibles

## 2. Decisiones de Diseño

| Decisión | Elección | Razón |
|---|---|---|
| Patrón de independencia | API Gateway (HTTP calls) | Menos complejidad, alineado con ISO 27001 |
| Autenticación inter-servicios | JWT Service Tokens (RS256) | Audit trail granular, revocación por servicio |
| Estructura API interna | `/api/internal/v1/` namespace dedicado | Separación clara API pública vs interna |
| Encriptación JWT | RS256 (asimétrico) | Clave privada solo en Django; servicios solo verifican |
| Logging | RFC 5424 severity levels | Estándar de syslog para trazabilidad |

---

## 3. Arquitectura

### 3.1 Vista General

```
ANTES:
  scanning_service ──────────────────────► texcore_db (SQL Server)
  reporting_excel  ──────────────────────► texcore_db (SQL Server)
  Django Core      ──────────────────────► texcore_db (SQL Server)
  ❌ Tres puntos de acceso a BD  ❌ Sin audit trail  ❌ Sin identidad de servicio

DESPUÉS:
  scanning_service  ──[JWT RS256]──► /api/internal/v1/ ──► texcore_db
  reporting_excel   ──[JWT RS256]──► /api/internal/v1/ ──► texcore_db
  printing_service  (sin cambios — ya es independiente)
  Django Core       ───────────────────────────────────► texcore_db
  ✅ Un solo punto de acceso a BD  ✅ Audit trail completo  ✅ Identidad por servicio
```

### 3.2 Nuevo Componente: `internal_api` (App Django)

Nueva app Django con responsabilidad exclusiva de atender comunicación servicio-a-servicio:

```
gestion/
inventory/
internal_api/           ← NUEVA APP
  ├── models.py         ← ServiceCredential (identidades de servicio)
  ├── authentication.py ← JWTServiceAuthentication (DRF auth backend)
  ├── permissions.py    ← IsInternalService (DRF permission)
  ├── serializers.py    ← Serializers para respuestas internas
  ├── views/
  │   ├── auth_views.py         ← POST /auth/token/ y /auth/refresh/
  │   ├── scanning_views.py     ← GET /lotes/{codigo}/validate/
  │   └── reporting_views.py    ← 18 endpoints de reportes
  ├── urls.py
  ├── audit.py          ← AuditLogger (RFC 5424)
  └── tests/
      ├── test_auth.py
      ├── test_scanning.py
      └── test_reporting.py
```

---

## 4. Autenticación JWT Service Tokens

### 4.1 Flujo Completo

```
[Microservicio arranca]
        │
        ▼
POST /api/internal/v1/auth/token/
  Body: { "service_name": "scanning_service", "service_secret": "<secret>" }
        │
        ▼
Django valida credenciales → ServiceCredential.objects.get(name=..., is_active=True)
        │
        ▼
Retorna: { "access_token": "<JWT RS256>", "refresh_token": "...", "expires_in": 900 }
        │
        ▼
[Servicio almacena token EN MEMORIA — nunca en disco]
        │
        ▼
GET /api/internal/v1/lotes/{codigo}/validate/
  Header: Authorization: Bearer <access_token>
        │
        ▼
Django: JWTServiceAuthentication.authenticate() → extrae service_id del payload
Django: AuditLogger.log(service="scanning_service", action="validate_lote", ...)
Django: retorna datos solicitados
        │
        ▼
[Token expira en 15 min → JWTTokenManager.refresh() automático]
```

### 4.2 Modelo `ServiceCredential` (Django)

```python
class ServiceCredential(models.Model):
    """Identidad de un microservicio autorizado. ISO 27001 A.9.2"""
    name = models.CharField(max_length=100, unique=True)   # "scanning_service"
    secret_hash = models.CharField(max_length=255)          # bcrypt hash
    is_active = models.BooleanField(default=True)
    allowed_scopes = models.JSONField(default=list)         # ["lotes:read"]
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True)
    
    class Meta:
        db_table = "internal_service_credential"
```

### 4.3 Seguridad JWT (ISO 27001 A.10 — Criptografía)

- **Algoritmo:** RS256 (RSA + SHA-256 asimétrico)
- **Clave privada:** Solo en Django (`INTERNAL_JWT_PRIVATE_KEY` env var)
- **Clave pública:** Distribuida a microservicios para verificación local
- **Access token expiry:** 15 minutos
- **Refresh token expiry:** 24 horas
- **Payload mínimo:** `{ "sub": "scanning_service", "scope": ["lotes:read"], "jti": "<uuid>", "iat": ..., "exp": ... }`
- **Transport:** HTTPS obligatorio (TLS 1.2+)

---

## 5. Django Internal API — Endpoints

### 5.1 Autenticación

```
POST /api/internal/v1/auth/token/
POST /api/internal/v1/auth/refresh/
```

### 5.2 Para `scanning_service`

```
GET /api/internal/v1/lotes/{codigo_barras}/validate/
  Scope requerido: lotes:read
  Respuesta: { lote_id, producto, peso_kg, bodega, sede, estado, orden_produccion }
```

### 5.3 Para `reporting_excel` (18 endpoints)

```
# Inventario
GET /api/internal/v1/reports/kardex/?bodega_id=&fecha_desde=&fecha_hasta=
GET /api/internal/v1/reports/productos/?sede_id=
GET /api/internal/v1/reports/usuarios/?sede_id=
GET /api/internal/v1/reports/stock-actual/?bodega_id=
GET /api/internal/v1/reports/valorizacion/?bodega_id=
GET /api/internal/v1/reports/aging/?bodega_id=
GET /api/internal/v1/reports/rotacion/?bodega_id=&periodo=
GET /api/internal/v1/reports/stock-cero/?bodega_id=
GET /api/internal/v1/reports/resumen-movimientos/?fecha_desde=&fecha_hasta=

# Por vendedor
GET /api/internal/v1/vendedores/{id}/ventas/?fecha_desde=&fecha_hasta=
GET /api/internal/v1/vendedores/{id}/top-clientes/
GET /api/internal/v1/vendedores/{id}/deudores/

# Gerencial
GET /api/internal/v1/gerencial/ventas/?fecha_desde=&fecha_hasta=
GET /api/internal/v1/gerencial/top-clientes/
GET /api/internal/v1/gerencial/deudores/

# Producción
GET /api/internal/v1/produccion/ordenes/?fecha_desde=&fecha_hasta=
GET /api/internal/v1/produccion/lotes/?fecha_desde=&fecha_hasta=
GET /api/internal/v1/produccion/tendencia/?periodo=
```

Todos requieren `scope: reports:read`.

---

## 6. Cambios en `scanning_service`

### 6.1 Patrón: Adapter (nuevo) + Repository existente

Se introduce `DjangoApiClient` que implementa la interfaz `ILoteRepository` ya existente. El `LoteService` no cambia — solo cambia el repositorio inyectado.

```
ANTES: LoteService → SqlAlchemyLoteRepository → DB
DESPUÉS: LoteService → DjangoApiClient (Adapter) → Django REST API → DB
```

### 6.2 Nuevos archivos

```
scanning_service/src/
  ├── infrastructure/
  │   ├── django_client.py      ← DjangoApiClient: ILoteRepository
  │   └── jwt_token_manager.py  ← JWTTokenManager (SRP)
  ├── config.py                 ← agrega DJANGO_INTERNAL_URL, SERVICE_NAME, SERVICE_SECRET
```

### 6.3 Archivos eliminados

```
scanning_service/src/
  ├── database.py       ← ELIMINAR (SQLAlchemy engine)
  └── repository.py     ← ELIMINAR (SqlAlchemyLoteRepository)
```

### 6.4 `docker-compose.yml` — scanning_service

```yaml
# ELIMINAR:
  - DB_ENGINE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_DRIVER

# AGREGAR:
  - DJANGO_INTERNAL_URL=http://backend:8000
  - SERVICE_NAME=scanning_service
  - SERVICE_SECRET=${SCANNING_SERVICE_SECRET}
  - INTERNAL_JWT_PUBLIC_KEY=${INTERNAL_JWT_PUBLIC_KEY}
```

---

## 7. Cambios en `reporting_excel`

### 7.1 Patrón: Repository reemplazado (mismo patrón existente)

`DjangoReportRepository` implementa `IReportRepository` existente. `ReportFactory` y `OutputFormatter` no cambian.

```
ANTES: ReportFactory → ReportService → SqlRepository (pyodbc) → DB SPs
DESPUÉS: ReportFactory → ReportService → DjangoReportRepository → Django REST API → DB
```

### 7.2 Nuevos archivos

```
reporting_excel/src/
  ├── infrastructure/
  │   ├── django_client.py       ← DjangoReportRepository: IReportRepository
  │   └── jwt_token_manager.py   ← JWTTokenManager (SRP, idéntico al de scanning)
  ├── config.py                  ← agrega DJANGO_INTERNAL_URL, SERVICE_NAME, SERVICE_SECRET
```

### 7.3 Archivos eliminados

```
reporting_excel/src/
  ├── database.py    ← ELIMINAR (pyodbc connection)
  └── repositories/sql_repository.py ← ELIMINAR (18 SPs directos)
```

---

## 8. Componente Compartido: `JWTTokenManager`

Clase reutilizable en ambos microservicios (copia idéntica, no dependencia compartida — servicios son independientes).

```python
class JWTTokenManager:
    """SRP: responsabilidad única de gestionar el ciclo de vida del JWT.
    ISO 27001 A.10: tokens en memoria, nunca en disco."""
    
    def __init__(self, django_url: str, service_name: str, service_secret: str): ...
    async def get_valid_token(self) -> str: ...      # refresca si expira
    async def _fetch_token(self) -> TokenPair: ...
    async def _refresh_token(self) -> TokenPair: ...
    def _is_expired(self, token: str) -> bool: ...   # verifica exp del payload
```

---

## 9. Manejo de Errores — RFC 5424

Se usa la escala de severidad RFC 5424 en todos los logs estructurados:

| Nivel | Código | Cuándo usarlo en TexCore |
|---|---|---|
| EMERGENCY | 0 | DB inaccesible, sistema completo caído |
| ALERT | 1 | Token de servicio revocado, intrusión detectada |
| CRITICAL | 2 | Django Internal API no responde tras 3 reintentos |
| ERROR | 3 | Validación de lote fallida, endpoint 500 |
| WARNING | 4 | Token próximo a expirar, rate limit cercano |
| NOTICE | 5 | Servicio iniciado, token renovado |
| INFO | 6 | Request completado, reporte generado |
| DEBUG | 7 | Payload JWT decodificado, query ejecutada |

### 9.1 Formato de Log Estructurado

```json
{
  "timestamp": "2026-05-27T14:32:01Z",
  "severity": 6,
  "severity_name": "INFO",
  "service": "scanning_service",
  "action": "validate_lote",
  "codigo_barras": "LOT-2024-0451",
  "django_status": 200,
  "duration_ms": 34,
  "request_id": "uuid-v4"
}
```

### 9.2 Circuit Breaker

Si Django Internal API devuelve 3 errores consecutivos en < 30s, el microservicio entra en modo degradado y responde `503 Service Unavailable` con mensaje claro en lugar de reintentar indefinidamente.

---

## 10. Seguridad Adicional (ISO 27001)

| Medida | Implementación |
|---|---|
| Encriptación en tránsito | TLS 1.2+ obligatorio (Nginx ya configurado) |
| Rotación de secrets | `SERVICE_SECRET` rotable sin reiniciar servicios |
| Rate limiting | 100 req/min por servicio en nginx |
| Token blacklist | `jti` revocable en Redis (si un token es comprometido) |
| No logging de secrets | `SERVICE_SECRET` nunca aparece en logs |
| Headers de seguridad | `X-Content-Type-Options`, `X-Frame-Options` en respuestas internas |

---

## 11. Pruebas — TDD + ISTQB

### 11.1 Django `internal_api` tests

```python
# Técnicas: EP (Equivalencia), BVA (Valores Límite), STT (Transición Estado)
# Naming: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]

# EP:
test_jwt_auth_dado_credenciales_validas_cuando_solicita_token_entonces_retorna_200()
test_jwt_auth_dado_credenciales_invalidas_cuando_solicita_token_entonces_retorna_401()
test_jwt_auth_dado_servicio_inactivo_cuando_solicita_token_entonces_retorna_403()

# BVA:
test_token_dado_token_expirado_cuando_hace_request_entonces_retorna_401()
test_token_dado_token_con_1s_para_expirar_cuando_hace_request_entonces_renueva()

# STT:
test_service_credential_dado_activo_cuando_desactiva_entonces_acceso_revocado()

# Audit:
test_audit_log_dado_request_valido_cuando_accede_a_lote_entonces_registra_evento_rfc5424()
```

### 11.2 scanning_service tests (mock Django API)

```python
test_django_client_dado_api_disponible_cuando_valida_lote_entonces_retorna_info_lote()
test_django_client_dado_api_unavailable_cuando_valida_lote_entonces_circuit_breaker_activa()
test_jwt_manager_dado_token_expirado_cuando_get_valid_token_entonces_refresca_automaticamente()
```

### 11.3 reporting_excel tests (mock Django API)

```python
test_django_report_repo_dado_api_disponible_cuando_get_kardex_entonces_retorna_dataframe()
test_django_report_repo_dado_scope_incorrecto_cuando_accede_entonces_retorna_403()
```

---

## 12. Orden de Implementación

1. **`internal_api` app Django** — base de todo
   - `ServiceCredential` model + migración
   - `JWTServiceAuthentication` backend
   - Endpoint `POST /auth/token/` + `POST /auth/refresh/`
   - Tests auth
2. **Endpoints scanning** en Django + tests
3. **Migración `scanning_service`** — reemplazar repo por DjangoApiClient + tests
4. **Endpoints reporting** en Django (18 endpoints) + tests
5. **Migración `reporting_excel`** — reemplazar pyodbc por DjangoReportRepository + tests
6. **Docker Compose** — actualizar env vars
7. **Smoke test** end-to-end en Docker

---

## 13. Archivos No Modificados

- `printing_service/` — completo, ya es independiente ✅
- `gestion/` — sin cambios en modelos ni servicios existentes
- `inventory/` — sin cambios
- `frontend/` — sin cambios
- Nginx config — sin cambios (routing interno ya funciona)
