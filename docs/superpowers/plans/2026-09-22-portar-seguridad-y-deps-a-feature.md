# Plan: Portar el trabajo de seguridad/dependencias del 22-sep-2026 de `refactorizacion` a `feature`

## ⚠️ Contexto crítico — leer antes de hacer nada

Este trabajo se hizo por error en la rama `refactorizacion`, que está **desactualizada** (76 commits detrás de `feature`, que es la rama vigente con el trabajo de la semana del 15-19 de septiembre de 2026). `feature` es la rama correcta para todo desarrollo nuevo.

**No borrar la rama `refactorizacion` (ni local ni remota) hasta que todo lo de este documento esté aplicado y verificado en `feature`.** El commit `91a0f94` en `origin/refactorizacion` contiene el 100% del trabajo descrito aquí — si se borra la rama antes de portar el trabajo, ese commit puede quedar inalcanzable y perderse en el próximo garbage collection de Git/GitHub.

- Commit con todo el trabajo: **`91a0f94`** en `origin/refactorizacion` — `fix: seguridad de printing_service, actualización de dependencias con CVE y ampliación de cobertura CI/Trivy`
- Commit menor adicional (junio 2026, probablemente ya obsoleto): `b71494f` — `fix: CI modulo de jwt`, solo toca `inventory/tests/test_reporting_proxy.py` y `scanning_service/tests/test_jwt_token_manager.py`. **Verificar primero si `feature` ya tiene una versión equivalente o mejor de esos 2 archivos de test antes de portarlo** — se detectó que el contenido diverge bastante del que tiene `feature` hoy (mocks de `httpx.Client.get` vs `.post`, distinto patrón de autenticación en el test), así que un cherry-pick directo probablemente genere conflictos que hay que resolver leyendo ambas versiones, no aplicar a ciegas.

## Bloqueo de infraestructura encontrado hoy (aplica a cualquier sesión futura en esta máquina)

`frontend/dist/assets/` y `logs/` quedaron con dueño `root` (de un build de Docker que montó el repo como volumen y escribió como root dentro del contenedor). Esto bloquea `git merge`/`git pull`/`git stash -u` en esta máquina hasta que se libere. Antes de intentar el merge, correr (el usuario, no el agente, ya que requiere password de sudo):
```bash
sudo chown -R desarrollo:desarrollo frontend/dist logs
```

## Cómo aplicar este trabajo a `feature`

### Opción A — Cherry-pick directo (probar primero)
```bash
git checkout feature
git pull origin feature
git cherry-pick 91a0f94
```
Dado que `feature` tiene 76 commits que `refactorizacion` no tiene, es probable que haya conflictos en archivos que ambas ramas tocaron independientemente (candidatos más probables, por ser archivos "calientes" del proyecto: `gestion/utils.py`, `inventory/views.py`, `gestion/management/commands/stress_test_data.py`, `.gitlab-ci.yml`, `requirements.txt`). Si el cherry-pick tiene demasiados conflictos para resolver con confianza, usar la Opción B.

### Opción B — Reaplicar manualmente cambio por cambio
Si el cherry-pick es inviable, usar `git show 91a0f94 -- <archivo>` para ver el diff exacto de cada archivo y decidir cómo fusionarlo con el estado actual de `feature`. A continuación el detalle completo de qué cambió y por qué, organizado por tema.

---

## 1. Autenticación JWT en `printing_service` (el fix de seguridad principal)

**Problema:** `printing_service` no tenía ninguna autenticación — a diferencia de `scanning_service` y `reporting_excel`, que ya exigían JWT RS256. Cualquier actor con acceso a la red interna de Docker podía generar PDFs de notas de venta (datos de clientes, montos) y etiquetas ZPL arbitrarias sin credenciales.

**Verificar primero:** ¿`feature` ya tiene este fix? (buscar `verify_jwt_service_token` en `printing_service/src/main.py`). Si no, aplicar:

- **`printing_service/src/main.py`**: agregar middleware `verify_jwt_service_token` — copia exacta del patrón ya usado en `reporting_excel/src/main.py` (`jwt.decode` con `INTERNAL_JWT_PUBLIC_KEY`, valida `iss=texcore` y `type=service_access`, exime solo `/health`). Fail-fast si falta `INTERNAL_JWT_PUBLIC_KEY` en el entorno.
- **`printing_service/requirements.txt`**: agregar `PyJWT` y `cryptography` (cryptography es obligatorio para que PyJWT soporte RS256 — sin él falla con "Algorithm not supported").
- **`gestion/utils.py`** (`PrintingService`): agregar función `_printing_auth_headers()` que firma un JWT de 60s con `JWTServiceAuthentication.generate_token()` (ya existe en `internal_api/authentication.py`, reutilizar sin duplicar) y enviarlo como `Authorization: Bearer` en `generate_nota_venta_pdf()` y `generate_zpl_label()`.
- **`infrastructure/docker/docker-compose.yml` y `docker-compose.prod.yml`**: agregar `INTERNAL_JWT_PUBLIC_KEY=${INTERNAL_JWT_PUBLIC_KEY}` al servicio `printing`.
- **Tests nuevos**: `printing_service/tests/conftest.py` (fixture `bypass_jwt` que mockea `jwt.decode`, mismo patrón que `reporting_excel/tests/conftest.py`) y `printing_service/tests/test_auth_middleware.py` (9 tests: sin header, header sin Bearer, token expirado, tipo incorrecto, emisor no reconocido, `/health` exento).
- **Si `feature` ya tiene `printing_service/tests/unit/test_printing_endpoints.py`** con tests que llaman a los endpoints directamente vía `TestClient` sin header de auth: esos tests van a empezar a fallar con 401 en cuanto se agregue el middleware — hay que agregarles `headers={"Authorization": "Bearer test-token"}` a cada `client.post(...)` (ver commit `91a0f94` para el diff exacto de ese archivo).
- **`.gitlab-ci.yml`**: el job `test:printing-service` debe instalar `PyJWT` y correr `pytest tests/` completo (no solo `test_nota_venta_calculos.py`).

**Verificación:** `pytest printing_service/tests/ -v` (esperar 38+ tests, todos pasando), y prueba end-to-end real: levantar el stack, llamar `PrintingService.generate_zpl_label(...)` desde `manage.py shell` y confirmar que retorna contenido (no `None`), y que una petición HTTP directa a `printing_service` sin token retorna 401.

---

## 2. Actualización de dependencias con CVE conocido (4 `requirements.txt`)

Encontrado con `trivy image --severity CRITICAL,HIGH` contra las imágenes de producción construidas localmente.

| Paquete | Antes | Después | CVE que cierra |
|---|---|---|---|
| `Django` (solo raíz/backend) | 5.2.7 | **5.2.17** | CVE-2025-64459 (CRITICAL, inyección SQL) + varios HIGH publicados desde 5.2.8 |
| `PyJWT` (los 4 `requirements.txt`) | 2.10.1 | **2.14.0** | CVE-2026-48526 (bypass de autenticación) |
| `cryptography` (los 4 `requirements.txt`) | 42.0.8 | **50.0.1** | múltiples CVE, incluyendo OpenSSL embebido vulnerable |
| `sqlparse` (solo raíz/backend) | 0.5.3 | **0.6.0** | CVE-2026-54284 (DoS) |

**Verificar primero:** comparar las versiones actuales en `feature` de estos 4 paquetes — es posible que `feature` (al ser más reciente) ya tenga versiones iguales o más nuevas. Si `feature` tiene versiones MÁS VIEJAS que las de esta tabla, aplicar el bump. Revisar también si hay versiones aún más nuevas disponibles en PyPI al momento de retomar esto (`pip index versions <paquete>`) — se priorizó la última versión estable dentro de líneas seguras, no solo la mínima con fix.

**Verificación tras el bump:** rebuild de las imágenes con `--pull --no-cache` (para traer también paquetes de sistema operativo frescos, no solo las libs de Python), correr la suite completa de cada servicio, y re-escanear con Trivy para confirmar 0 CVEs en estos 4 paquetes. Ver también sección 4 (CI) para el mecanismo de detección automática futura.

---

## 3. Llave privada TLS embebida en la imagen del backend

**Problema:** `Dockerfile.prod` usa `COPY . .` con el repo completo como contexto de build. `.dockerignore` no excluía `nginx/certs/`, así que `nginx-selfsigned.key` terminaba embebida dentro de la imagen `backend` — extraíble por cualquiera con acceso a esa imagen (registry, capa Docker).

**Fix:** agregar a `.dockerignore`:
```
# Certificados TLS — Dockerfile.prod usa COPY . . con el repo como contexto;
# sin esto, la llave privada autofirmada de nginx (nginx/certs/*.key) quedaba
# embebida dentro de la imagen del backend (detectado por Trivy 2026-09-22).
nginx/certs/
```

**Verificar primero:** ¿ya existe esta exclusión en el `.dockerignore` de `feature`? Si no, agregarla. **Verificación:** rebuild del backend y re-escaneo Trivy con `--scanners secret` — debe dar 0 coincidencias de `nginx-selfsigned`.

---

## 4. Cobertura Trivy para los 3 microservicios satélite en CI

**Problema:** el job `scan:images` en `.gitlab-ci.yml` solo escaneaba `backend` y `nginx`. Los 3 microservicios satélite (`printing_service`, `scanning_service`, `reporting_excel`) nunca se escaneaban, a pesar de tener CVEs CRITICAL reales.

**Fix:** nuevo job `scan:images-satellites` (mismo stage `scan`), con `needs` en `build:printing-service`, `build:scanning-service`, `build:reporting-excel`. Usa `--ignore-unfixed` (a diferencia del job de `backend`/`nginx`, que NO lo usa) — esto bloquea solo CVEs CRITICAL/HIGH que **ya tienen parche publicado** (los de aplicación, que el equipo controla), sin dejar el pipeline permanentemente en rojo por CVEs de paquetes base de Debian sin parche todavía disponible (`libxml2`, `linux-libc-dev` al momento de este trabajo). El job `deploy` debe depender también de `scan:images-satellites` además de `scan:images`.

**Ver commit `91a0f94` para el YAML exacto** (incluye comentario explicando por qué `--ignore-unfixed` no es una relajación arbitraria del gate).

**Verificar primero:** revisar si `feature` ya tiene algún job de escaneo para los satélites (puede haber evolucionado independientemente en los últimos commits).

---

## 5. Bugs reales encontrados y corregidos durante la validación (no relacionados con seguridad, pero reales)

Estos se encontraron porque el trabajo de seguridad requirió levantar el stack completo y correr el stress test — no son hipotéticos, se reprodujeron y verificaron.

### 5.1 `gestion/management/commands/stress_test_data.py` — drift de esquema
El comando usaba campos `producto`/`bodega` que ya no existen en `OrdenProduccion` (el modelo real usa `producto_entrada`/`producto_salida`/`bodega_entrada`/`bodega_salida`). Además:
- Los `LoteProduccion` sembrados no tenían `StockBodega` asociado (nada era escaneable/despachable).
- El usuario demo `user_despacho` no tenía bodegas asignadas (`bodegas_all=True` faltante en su `ensure_user(...)`).

**Verificar primero:** `feature` es más reciente, es posible que ya no tenga este bug si el modelo cambió de forma diferente ahí, o que tenga un bug distinto. Correr `python manage.py stress_test_data` en `feature` y ver si falla con `TypeError: OrdenProduccion() got unexpected keyword arguments`. Si sí, aplicar el mismo fix (ver diff exacto en el commit).

### 5.2 `scanning_service` — mismatch `producto_salida` entre dominio y servicio
`scanning_service/src/domain/models.py` tenía el modelo de dominio `OrdenProduccion.producto` (campo viejo), pero `services/validation_service.py` ya esperaba `producto_salida` — esto causaba **HTTP 500 en cada escaneo real** contra el backend (bug 100% reproducible, no edge case). Corregido renombrando el campo en `domain/models.py` y en `infrastructure/django_client.py` (que construye el objeto de dominio).

**Verificar primero:** si `feature` tiene una versión distinta de `scanning_service`, revisar si ya tiene esta consistencia o si el bug persiste ahí también.

### 5.3 `inventory/views.py` — `ProtectedError` al revertir despacho
`HistorialDespachoViewSet.destroy()` y `.revertir()` hacían `historial.delete()` directo, pero `DetalleHistorialDespachoPedido.historial` es una FK `PROTECT` que nunca se limpiaba antes del delete — **cualquier reversión de despacho con pedidos asociados fallaba con 500** (bug real de producción, no solo del stress test). Fix: `DetalleHistorialDespachoPedido.objects.filter(historial=historial).delete()` antes de `historial.delete()`, en ambos métodos.

**Verificar primero:** si `inventory/views.py` cambió de estructura en `feature` (podría estar dividido en varios archivos, como pasó en la rama `MES`), ubicar el equivalente de `HistorialDespachoViewSet` y aplicar el mismo fix ahí.

---

## 6. Rediseño de `scripts/loadtest/locustfile.py` (prioridad baja — herramienta, no producto)

Se rediseñó el script de stress test de 100 usuarios para que simule los **11 roles RBAC reales** (uno por grupo de Django: `admin_sistemas`, `admin_sede`, `bodeguero`, `despacho`, `ejecutivo`, `empaquetado`, `jefe_area`, `jefe_planta`, `operario`, `tintorero`, `vendedor`) en vez de tareas de actividad inventadas. Incluye la validación del umbral de negocio de **<1s por escaneo durante el despacho**, verificada end-to-end contra el stack de producción real (gunicorn, `DEBUG=False`): 96 escaneos, 0 fallos, p95=270ms, máximo 323ms, bajo 100 usuarios concurrentes.

Esto es una herramienta de desarrollo (no afecta el producto), así que tiene prioridad más baja para portar. Si se retoma:
- Copiar `scripts/loadtest/locustfile.py` y `scripts/loadtest/README.md` completos desde el commit `91a0f94` (son archivos nuevos, no deberían generar conflicto salvo que `feature` ya tenga su propio `locustfile.py`).
- Requiere que los usuarios demo (`user_admin_sistemas`, `user_despacho`, etc.) existan — los crea `gestion/management/commands/stress_test_data.py` (ver sección 5.1).
- **Usar `docker-compose.prod.yml` (gunicorn, `DEBUG=False`) para medir, nunca `docker-compose.yml`** (dev, `runserver`+`DEBUG=True`) — se confirmó que este último da tiempos de respuesta de hasta 32 segundos bajo 100 usuarios, totalmente irreales, por el logging SQL verboso y el servidor mono-proceso.

---

## 7. Verificación final recomendada al terminar de portar

1. `git diff feature..91a0f94 -- <cada archivo de la lista> ` para confirmar que no queda nada suelto.
2. Rebuild `--pull --no-cache` de las 5 imágenes de producción.
3. Suite completa de cada servicio (backend Django, `scanning_service`, `reporting_excel`, `printing_service`, frontend) — 0 regresiones nuevas (comparar contra el baseline de `feature` antes de portar, ya que `feature` puede tener sus propios fallos preexistentes distintos a los de `refactorizacion`).
4. Re-escaneo Trivy de las 5 imágenes — confirmar 0 CVEs en Django/PyJWT/cryptography/sqlparse.
5. Verificación end-to-end manual: `PrintingService.generate_zpl_label(...)` desde `manage.py shell` debe retornar contenido; una petición HTTP sin token a `printing_service` debe dar 401.
6. Solo después de todo esto: considerar el borrado de la rama `refactorizacion` (local y remota), y solo si el usuario lo confirma explícitamente en ese momento.

---

## 8. Documentación ya escrita (evaluar si portar tal cual o adaptar)

Estos documentos ya fueron actualizados en `refactorizacion` con el contenido correcto — probablemente se puedan copiar casi literal a `feature`, ajustando solo referencias a rutas/archivos que hayan cambiado de ubicación:
- `docs/arquitectura/MICROSERVICIO_IMPRESION.md` (sección "Seguridad — Autenticación JWT")
- `docs/arquitectura/MICROSERVICIOS.md` (nota en §5 sobre `printing_service`)
- `docs/requerimientos/REGISTRO_RIESGOS.md` (entradas RS-09, RS-10, RS-11, RS-12 — **revisar numeración**, `feature` puede tener sus propias entradas RS-09+ por trabajo independiente, en cuyo caso hay que renumerar para evitar colisión de IDs)
- `CHANGELOG.md` (las 4 entradas del 22 de septiembre — revisar que no dupliquen contenido que `feature` ya tenga documentado de otra forma)
