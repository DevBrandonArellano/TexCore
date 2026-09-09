# Endurecimiento de internal_api Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline, misma sesión — no subagent-driven-development, no `git commit` de Claude, ver Constraints).

**Goal:** Cerrar las 4 brechas confirmadas en `internal_api` (exposición pública vía nginx, ausencia de throttling en el handshake de servicio, red Docker plana, parámetro de URL sin validar) sin romper el flujo legítimo servicio-a-servicio (`scanning_service`/`reporting_excel` → `backend:8000` directo por DNS de Docker).

**Architecture:** Defensa en profundidad en 4 capas independientes: (1) nginx deja de reenviar `/api/internal/*` — el catch-all `location /api/` seguía sirviéndolo; (2) throttle DRF + validación de IP privada en `ServiceTokenView`/`ServiceTokenRefreshView`, capa Django que protege también el camino directo `backend:8000` que nginx no toca; (3) `re_path` con regex estricta para `codigo_barras`; (4) segmentación de red en `docker-compose.prod.yml` (`dmz_net`: nginx+backend+scanning — nginx proxea a ambos directo; `internal_net` con `internal: true`: backend+db+printing+reporting_excel).

**Tech Stack:** Django REST Framework (`AnonRateThrottle`), nginx, Docker Compose networks, `ipaddress` stdlib.

**Spec:** Análisis de seguridad "agy" pegado por el usuario en la conversación (sin archivo — hallazgos verificados línea por línea contra `nginx/nginx.conf`, `internal_api/views/auth_views.py`, `internal_api/urls.py`, `internal_api/views/scanning_views.py`, `infrastructure/docker/docker-compose.prod.yml` antes de escribir este plan).

## Global Constraints

- No ejecutar `git add`/`git commit`/`git push` — Brandon hace todos los commits (ver memoria `git-workflow-preference`).
- No hay Docker local disponible en esta máquina — Task 4 (redes Docker) se escribe pero **Brandon debe validarla** con el stack real (`docker compose config`, arranque completo, healthcheck de `db`). Ver nota de riesgo en Task 4.
- No hay SQL Server local; los tests de este plan corren con `TexCore.settings_test_local` (SQLite en memoria) cuando sea posible. Si un test requiere una migración con T-SQL nativo (no es el caso de los archivos tocados aquí), Brandon corre la suite completa después.
- Convención de nombres de test ya usada en `internal_api/tests/`: `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`, con comentario `# EP:`/`# STT:`/`# BVA:` arriba de cada test (ISTQB CTFL v4.0, ver `CLAUDE.md`).
- No introducir Redis: `AnonRateThrottle` usará el cache default (`LocMemCache`, no configurado explícitamente en `settings.py`) — dejar una nota explícita de que el throttle es por-worker-gunicorn, no global, hasta que se configure un cache compartido (fuera de alcance de este plan, YAGNI).

---

### Task 1: Bloquear `/api/internal/` en nginx

**Files:**
- Modify: `nginx/nginx.conf` (server HTTP :80, ~línea 34-98; server HTTPS :443, ~línea 150-241)

**Interfaces:**
- No consume nada de otras tasks.
- Produce: los microservicios (`scanning_service`, `reporting_excel`) siguen llamando `http://backend:8000/api/internal/v1/...` vía DNS interno de Docker — **no pasan por nginx**, así que este bloqueo no los afecta. Task 4 no depende de esto.

- [x] **Step 1: Añadir el bloqueo en el server HTTP (:80)**

Insertar, inmediatamente antes de `location /api/ { ... }` en el bloque `server { listen 80; ... }` (nginx elige por prefijo más largo, pero `^~` lo hace explícito y evita que una regex futura lo intercepte):

```nginx
    # BLOQUEO TOTAL: la API interna JAMÁS debe responder a través del proxy
    # público. Los microservicios la llaman directo por DNS de Docker
    # (http://backend:8000/api/internal/v1/...), sin pasar por nginx — este
    # bloqueo no los afecta.
    location ^~ /api/internal/ {
        return 404;
    }

```

- [x] **Step 2: Añadir el mismo bloqueo en el server HTTPS (:443)**

Mismo bloque, insertado antes de `location /api/ { ... }` en `server { listen 443 ssl; ... }`.

- [x] **Step 3: Verificar sintaxis nginx si hay binario disponible**

Run: `nginx -t -c "$(pwd)/nginx/nginx.conf"` (si nginx no está instalado localmente, omitir — Brandon valida al levantar el stack).
Expected: `syntax is ok` / `test is successful`, o confirmación manual de que el bloque `location ^~ /api/internal/` aparece antes de `location /api/` en ambos server blocks.

- [x] **Step 4: Confirmar manualmente que no hay overlap con otras locations**

Revisar que `/api/internal/` no coincide con ninguna `location ~ regex` existente (solo existe `location ~ ^/api/scanning/(.*)$`, que no matchea `/api/internal/...`).

---

### Task 2: Throttling + validación de IP privada en el handshake de servicio

**Files:**
- Modify: `internal_api/views/auth_views.py`
- Test: `internal_api/tests/test_auth_views.py` (nuevos tests), `internal_api/tests/test_auth_views_refresh.py` (nuevos tests)

**Interfaces:**
- Consumes: nada de otras tasks.
- Produces: clase `ServiceAuthThrottle(AnonRateThrottle)` con `rate = '10/minute'`, reutilizada por `ServiceTokenView` y `ServiceTokenRefreshView`. Función `_is_internal_ip(remote_addr: str) -> bool` en el mismo módulo, reutilizada por ambas vistas.

- [x] **Step 1: Escribir los tests que fallan (throttle)**

Añadir a `internal_api/tests/test_auth_views.py`:

```python
from django.core.cache import cache


class TestServiceTokenViewThrottle(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/internal/v1/auth/token/"
        cache.clear()

    def tearDown(self):
        cache.clear()

    # STT: 11na petición en el mismo minuto desde la misma IP → 429
    def test_token_dado_mas_de_10_intentos_por_minuto_cuando_solicita_entonces_retorna_429(self):
        _create_credential()
        for _ in range(10):
            resp = self.client.post(
                self.url,
                {"service_name": "scanning_service", "service_secret": "wrong"},
                format="json",
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)
```

Añadir a `internal_api/tests/test_auth_views_refresh.py` (mismo patrón, usando la URL `/api/internal/v1/auth/refresh/` y un `refresh_token` inválido de relleno — no importa que la petición sea inválida, el throttle cuenta antes de validar el payload).

- [x] **Step 2: Ejecutar y confirmar que fallan**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest internal_api/tests/test_auth_views.py::TestServiceTokenViewThrottle -q`
Expected: FAIL (no hay throttle todavía, la petición 11 también da 401, no 429).

- [x] **Step 3: Implementar `ServiceAuthThrottle` y aplicarla a ambas vistas**

En `internal_api/views/auth_views.py`, añadir después de los imports existentes:

```python
import ipaddress

from rest_framework.throttling import AnonRateThrottle


class ServiceAuthThrottle(AnonRateThrottle):
    """Un microservicio renueva su token cada `INTERNAL_JWT_ACCESS_TTL_SECONDS`
    (minutos, no segundos) — 10/min es holgado para uso legítimo y corta
    fuerza bruta contra `service_secret`. Cache por-proceso (ver Constraints):
    con gunicorn multi-worker el límite real es 10 * BACKEND_WORKERS/min
    hasta que haya un cache compartido (Redis)."""

    rate = "10/minute"


def _is_internal_request(remote_addr: str) -> bool:
    """True si `remote_addr` es una IP privada/loopback (RFC 1918 o ::1/127.0.0.1).

    Defensa en profundidad: el bloqueo de nginx (Task 1) es la barrera
    principal contra tráfico externo; esta función protege además el camino
    directo `backend:8000` que nginx nunca toca (llamado real de los
    microservicios, y cualquier contenedor comprometido en la red plana).
    No reemplaza el bloqueo de nginx — si nginx reenvía una petición externa
    por error de configuración, `REMOTE_ADDR` que Django ve es la IP de nginx
    (también privada), así que esta función no la detectaría; ver limitación
    documentada en el plan.
    """
    try:
        ip_obj = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return ip_obj.is_private or ip_obj.is_loopback
```

Modificar `ServiceTokenView`:

```python
class ServiceTokenView(APIView):
    """POST /api/internal/v1/auth/token/ — emite JWT para un microservicio."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ServiceAuthThrottle]

    def post(self, request):
        remote_addr = request.META.get("REMOTE_ADDR", "")
        if not _is_internal_request(remote_addr):
            logger.critical(
                "Intento de acceso a auth/token desde IP no privada: %s",
                remote_addr,
                extra={"sd": {"severity": 2, "remote_addr": remote_addr}},
            )
            return Response({"detail": "Acceso no autorizado."}, status=403)

        serializer = ServiceTokenRequestSerializer(data=request.data)
        # ... resto del método sin cambios
```

Aplicar el mismo `throttle_classes = [ServiceAuthThrottle]` y el mismo guard de `_is_internal_request` al inicio de `ServiceTokenRefreshView.post()`.

- [x] **Step 4: Ejecutar y confirmar que pasan**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest internal_api/tests/test_auth_views.py internal_api/tests/test_auth_views_refresh.py -q`
Expected: PASS — incluyendo los tests preexistentes (`test_token_dado_credenciales_validas_cuando_solicita_entonces_retorna_200`, etc.), que corren desde una IP de test (`127.0.0.1` con `APIClient`, por lo tanto privada — no deben empezar a fallar con 403).

- [x] **Step 5: Añadir test EP para el guard de IP**

```python
    # EP: request con REMOTE_ADDR público simulado → 403 antes de validar credenciales
    def test_token_dado_ip_publica_cuando_solicita_entonces_retorna_403(self):
        _create_credential()
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "test-secret"},
            format="json",
            REMOTE_ADDR="8.8.8.8",
        )
        self.assertEqual(resp.status_code, 403)
```

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest internal_api/tests/test_auth_views.py -q`
Expected: PASS.

---

### Task 3: Restringir `codigo_barras` en la URL a un patrón seguro

**Files:**
- Modify: `internal_api/urls.py`
- Test: `internal_api/tests/test_scanning_views.py` (nuevo test)

**Interfaces:**
- Consumes: nada de otras tasks.
- Produces: la URL `lotes/<codigo_barras>/validate/` ahora exige `^[a-zA-Z0-9_-]{1,50}$`; cualquier otro valor no matchea ninguna URL → Django devuelve 404 nativo antes de llegar a la vista.

- [x] **Step 1: Escribir el test que falla**

Añadir a `internal_api/tests/test_scanning_views.py`:

```python
    # EP: código con caracteres fuera del patrón permitido → 404 (no matchea URL)
    def test_validate_lote_dado_codigo_con_caracteres_invalidos_cuando_valida_entonces_retorna_404(self):
        resp = self.client.get("/api/internal/v1/lotes/../../etc/validate/")
        self.assertEqual(resp.status_code, 404)

    # BVA: código de 51 caracteres (límite+1) → 404 (no matchea URL)
    def test_validate_lote_dado_codigo_de_51_caracteres_cuando_valida_entonces_retorna_404(self):
        codigo_largo = "A" * 51
        resp = self.client.get(f"/api/internal/v1/lotes/{codigo_largo}/validate/")
        self.assertEqual(resp.status_code, 404)
```

- [x] **Step 2: Ejecutar y confirmar que fallan**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest internal_api/tests/test_scanning_views.py -q`
Expected: FAIL en el caso de 51 caracteres (hoy matchea y devuelve 404 por "no encontrado" desde la vista, no desde el router — mismo status code pero por la razón equivocada; el caso `../../etc/` probablemente ya da 404 porque Django normaliza el path, así que ese test puede pasar antes del fix — el objetivo real de este task es la razón del 404, verificable con el test de longitud).

- [x] **Step 3: Implementar el patrón restrictivo**

En `internal_api/urls.py`, reemplazar el import y la línea de la ruta:

```python
from django.urls import path, re_path
```

```python
    # ── Scanning ───────────────────────────────────────────────────────────
    # Solo alfanumérico y guiones, 1-50 caracteres (ej. LOT-2026-001) — evita
    # que basura/strings arbitrarios lleguen a la vista o al audit log.
    re_path(
        r"^lotes/(?P<codigo_barras>[a-zA-Z0-9_-]{1,50})/validate/$",
        ValidateLoteView.as_view(),
        name="validate_lote",
    ),
```

- [x] **Step 4: Ejecutar y confirmar que pasan**

Run: `DJANGO_SETTINGS_MODULE=TexCore.settings_test_local python -m pytest internal_api/tests/test_scanning_views.py -q`
Expected: PASS — incluyendo los tests preexistentes (`LOT-2026-001`, `NO-EXISTE` siguen matcheando el patrón).

---

### Task 3.1 (extensión, post-revisión con Brandon): cerrar la brecha del regex — validar `codigo_lote` en el punto de creación

**Contexto:** Brandon confirmó que `codigo_lote` sigue siempre `[A-Z0-9-]` en la práctica, pero al revisar `RegistrarLoteProduccionSerializer`/`LoteProduccion.clean()` no había ninguna validación de formato — la restricción de Task 3 era una convención asumida, no una garantía. Si algún día se registra un lote con "ñ"/tilde/espacio, `internal_api`'s `re_path` lo volvería imposible de escanear (404 real en planta). Brandon pidió cerrar la brecha en el punto de creación, no solo en la lectura.

**Files:**
- Modify: `gestion/models/produccion.py` — nueva constante compartida `CODIGO_LOTE_PATTERN`/`CODIGO_LOTE_REGEX` (única fuente de verdad), validación añadida a `LoteProduccion.clean()`.
- Modify: `gestion/serializers/production_serializers.py` — `RegistrarLoteProduccionSerializer.validate_codigo_lote()` (el punto realmente ejecutado antes de `RegistroLoteService.registrar_lote()`, confirmado leyendo `production_lote_views.py:711-723`).
- Modify: `internal_api/urls.py` — ahora importa `CODIGO_LOTE_PATTERN` de `gestion.models.produccion` en vez de duplicar el regex inline.
- Test: `gestion/tests/test_production_views.py` (`RegistrarLoteProduccionViewTestCase`) — 4 tests nuevos: 400 con "ñ" vía API, 201 con código manual válido, `ValidationError` en `LoteProduccion.save()` (que invoca `clean()` en cada guardado — confirmado leyendo `produccion.py:335-337`) con espacio.

**Nota de diseño:** se descartó reusar `ALPHANUMERIC_ACCENTS_REGEX` (`gestion/serializers/_common.py`, permite tildes/ñ/espacios) porque ese patrón es para texto legible (nombres/descripciones); `codigo_lote` es un identificador escaneable (QR/código de barras), no texto libre — coherente con que `generate_next_lote_codigo()` ya produce solo ASCII.

**Verificación:** `pytest gestion/ internal_api/ inventory/ -q --nomigrations` → 993 passed, 0 failed (incluye toda la suite, no solo los archivos tocados). `graphify update .` corrido tras los cambios.

---

### Task 4: Segmentación de red en `docker-compose.prod.yml`

**Files:**
- Modify: `infrastructure/docker/docker-compose.prod.yml`

**Interfaces:**
- Consumes: nada de otras tasks (independiente).
- Produces: dos redes Compose — `dmz_net` (nginx, backend, scanning) e `internal_net` con `internal: true` (backend, db, printing, reporting_excel). `backend` es el único servicio en ambas (puente intencional).

**Riesgo — requiere validación de Brandon con Docker real (no disponible en esta máquina):**
- `db` tiene `dns: [8.8.8.8]` sin comentario que explique el motivo; al quedar en `internal_net` (`internal: true`, sin ruta a internet) esa resolución DNS externa deja de funcionar. Si SQL Server la necesita para algo en el arranque (no debería, Developer edition no requiere activación online, pero no está verificado), el contenedor `db` podría fallar el healthcheck.
- Verificar con `docker compose -f infrastructure/docker/docker-compose.prod.yml config` que la definición es válida, y con un arranque completo que `db` pase `healthy`, que nginx sirva `/`, `/api/...` y `/api/scanning/...`, y que `scanning_service`/`reporting_excel` sigan autenticándose contra `backend:8000/api/internal/v1/auth/token/`.

- [x] **Step 1: Añadir la sección `networks` de nivel superior**

Al final de `infrastructure/docker/docker-compose.prod.yml`, después de la sección `volumes:` existente:

```yaml
networks:
  dmz_net:
    # nginx (único servicio con puertos publicados al host) + los dos
    # servicios a los que nginx proxea directo: backend (/api/) y
    # scanning (/api/scanning/). No internet-facing por sí sola — solo
    # nginx tiene "ports:"; los demás miembros no quedan expuestos al host
    # por estar en esta red.
    driver: bridge
  internal_net:
    # db, printing, reporting_excel: sin ruta de salida a internet
    # (internal: true) y sin ser alcanzables desde nginx/scanning — solo
    # backend, que también está en dmz_net, hace de puente.
    driver: bridge
    internal: true
```

- [x] **Step 2: Asignar cada servicio a su red**

Añadir `networks:` a cada servicio (reemplaza la ausencia actual de la clave, que hoy usa la red default de Compose):

```yaml
  db:
    # ... (sin cambios en el resto de la definición)
    networks:
      - internal_net

  backend:
    # ... (sin cambios en el resto de la definición)
    networks:
      - dmz_net
      - internal_net

  nginx:
    # ... (sin cambios en el resto de la definición)
    networks:
      - dmz_net

  printing:
    # ... (sin cambios en el resto de la definición)
    networks:
      - internal_net

  scanning:
    # ... (sin cambios en el resto de la definición)
    networks:
      - dmz_net

  reporting_excel:
    # ... (sin cambios en el resto de la definición)
    networks:
      - internal_net
```

- [x] **Step 3: Validar sintaxis (sin Docker, best-effort)**

Run: `python -c "import yaml; yaml.safe_load(open('infrastructure/docker/docker-compose.prod.yml'))"` para confirmar que el YAML es válido.
Expected: sin excepción.

- [x] **Step 4: Brandon valida con el stack real**

No ejecutable desde esta sesión (sin Docker local). Brandon corre:
```
docker compose -f infrastructure/docker/docker-compose.prod.yml config
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d
docker compose -f infrastructure/docker/docker-compose.prod.yml ps   # todos "healthy"/"running"
```
y confirma manualmente: `db` sano, login humano funciona (`/api/token/`), escaneo QR funciona (`/api/scanning/...` vía nginx), reportes Excel se generan (backend → reporting_excel → backend, sin pasar por nginx).

---

## Self-Review

- **Cobertura del análisis "agy":** Paso 1 → Task 1. Paso 2 → Task 2 (throttle + IP check, ambas vistas de auth, no solo `ServiceTokenView` como proponía el análisis original — `ServiceTokenRefreshView` tiene la misma superficie). Paso 3 → Task 3. Paso 4 → Task 4.
- **Placeholders:** ninguno — cada step tiene código completo o comando ejecutable.
- **Consistencia de tipos/nombres:** `ServiceAuthThrottle` y `_is_internal_request` se nombran igual en la descripción de Task 2 y en el código; `re_path` importado y usado con el mismo nombre de grupo `codigo_barras` que ya consume `ValidateLoteView.get(self, request, codigo_barras: str)` — sin cambios en la firma de la vista.
