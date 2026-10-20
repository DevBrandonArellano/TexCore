# TexCore — Registro de Riesgos

> Versión 1.0 | 2026-03-27 · Actualizado: 2026-10-08 (RD-06 mitigado y medido; 2026-10-06: RD-05 parcial; antes 2026-10-05: RD-05, RC-03 y RC-05 a RC-08, RG-02 y RG-03)
> Marco de referencia: COBIT 2019 (APO12) — Gestión del Riesgo
> Escala: Probabilidad 1-5 × Impacto 1-5 = Exposición 1-25

---

## Matriz de Riesgos

### Leyenda de Severidad

| Exposición | Nivel | Acción |
|-----------|-------|--------|
| 20-25 | 🔴 Crítico | Mitigar inmediatamente |
| 12-19 | 🟠 Alto | Mitigar en el sprint actual |
| 6-11 | 🟡 Medio | Planificar mitigación |
| 1-5 | 🔵 Bajo | Monitorear |

---

## Riesgos de Seguridad

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RS-01 | **Path Traversal en reporting proxy** — acceso a archivos arbitrarios del servidor | 3 | 5 | 15 🟠 | ✅ Mitigado (Sprint 1) | Regex whitelist en `_validate_report_path()` |
| RS-02 | **Secrets hardcodeados con defaults** — `REPORTING_INTERNAL_KEY` expuesto en imagen Docker | 4 | 5 | 20 🔴 | ✅ Mitigado (Sprint 1) | `_get_required_env()` + eliminación de `:-` en docker-compose |
| RS-03 | **IP Spoofing** — manipulación de `X-Forwarded-For` para bypass de controles por IP | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 1) | Validación contra `_TRUSTED_PROXY_NETWORKS` |
| RS-04 | **JWT sin revocación** — tokens válidos post-logout (Session Fixation) | 4 | 4 | 16 🟠 | ✅ Mitigado (Sprint 1) | JWT Blacklist activada (`token.blacklist()`) |
| RS-05 | **CORS abierto** en servicio satélite de reportes (`allow_origins=["*"]`) | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 1) | CORS restringido a `http://backend:8000` |
| RS-06 | **Rate limiting ausente** en endpoints de autenticación — susceptible a brute force | 4 | 4 | 16 🟠 | ✅ Mitigado (Sprint 1) | Nginx: 5 req/min en `/api/token/` |
| RS-07 | **Secrets en secrets.baseline ausente** — detect-secrets no inicializado | 2 | 3 | 6 🟡 | ✅ Mitigado (Sprint 5) | `.secrets.baseline` creado y commiteado |
| RS-08 | **Dependencias sin versiones fijadas** (printing_service/requirements.txt) | 3 | 3 | 9 🟡 | ✅ Mitigado (verificado 2026-09-22) | Todas las líneas de `printing_service/requirements.txt` y `scanning_service/requirements.txt` fijadas con `==` |
| RS-09 | **`printing_service` sin autenticación** — cualquier actor con acceso a la red interna de Docker podía generar PDFs de notas de venta (datos de clientes, montos) y etiquetas ZPL arbitrarias sin credenciales, a diferencia de `scanning_service`/`reporting_excel` (ya usaban JWT RS256) | 4 | 5 | 20 🔴 | ✅ Mitigado (2026-09-22) | Middleware `verify_jwt_service_token` (JWT Bearer RS256, mismo esquema que `reporting_excel`) en `printing_service/src/main.py`; Django firma el token vía `JWTServiceAuthentication.generate_token()` en `gestion/utils.py`; verificado end-to-end (sin token → 401, token forjado → 401, llamada real → 200); 9 tests nuevos en `printing_service/tests/test_auth_middleware.py` |
| RS-10 | **Llave privada TLS embebida en la imagen del backend** — `Dockerfile.prod` usa `COPY . .` con el repo como contexto y `.dockerignore` no excluía `nginx/certs/`; cualquiera con acceso a la imagen `backend` (registry, capa Docker) podía extraer `nginx-selfsigned.key`. Detectado por escaneo Trivy (`trivy image --scanners secret`) el 2026-09-22 | 3 | 4 | 12 🟠 | ✅ Mitigado (2026-09-22) | Agregado `nginx/certs/` a `.dockerignore`; verificado con rebuild + re-escaneo Trivy: 0 coincidencias de `nginx-selfsigned` en la imagen |
| RS-11 | **Dependencias con CVE conocidos en imágenes de producción** — Django 5.2.7 (CVE-2025-64459 CRITICAL, inyección SQL), PyJWT 2.10.1 (CVE-2026-48526, bypass de autenticación), cryptography 42.0.8 (múltiples CVE), sqlparse 0.5.3 (CVE-2026-54284, DoS) | 3 | 4 | 12 🟠 | ✅ Mitigado (2026-09-22) | Django → 5.2.17, PyJWT → 2.14.0, cryptography → 50.0.1 (`requirements.txt` de los 4 servicios Python), sqlparse → 0.6.0 (backend). Rebuild `--pull --no-cache` de las 5 imágenes de producción; re-escaneo Trivy confirmó 0 CVEs en Django/PyJWT/cryptography/sqlparse en las 4 imágenes. Suite completa sin regresiones (backend 333 tests, `scanning_service` 35, `reporting_excel` 27, `printing_service` 38) y flujo end-to-end Django→`printing_service` verificado tras cada rebuild. CVEs CRITICAL restantes (`libxml2` CVE-2026-6653, `linux-libc-dev` CVE-2026-43185) son de paquetes base Debian **sin parche publicado todavía** (columna "Fixed Version" vacía en Trivy) — no corregibles por el equipo hoy, quedan en monitoreo (ver `scan:images-satellites` en `.gitlab-ci.yml`, que usa `--ignore-unfixed` para no bloquear el pipeline por esto). |
| RS-12 | **Sin escaneo Trivy de los 3 microservicios satélite en CI** — el job `scan:images` solo cubría `backend`/`nginx`; `printing_service`, `scanning_service` y `reporting_excel` nunca se escaneaban, a pesar de haberse encontrado CVEs CRITICAL en ellos el 2026-09-22 | 3 | 3 | 9 🟡 | ✅ Mitigado (2026-10-05) | El job de 2026-09-22 vivía en `.gitlab-ci.yml`, pipeline que no se ejecutaba, así que la mitigación no era efectiva. Desde el 2026-10-05 la matriz de escaneo del CD cubre los satélites; desde el 2026-10-13 vive en el job `scan` de `.github/workflows/release.yml` y escanea las **6** imágenes por digest; los 3 satélites con `ignore-unfixed` (bloquea solo CVEs con parche disponible — ver justificación en RS-11) |
| RS-13 | **Actions de CI en referencias mutables** — `aquasecurity/trivy-action@master`, tags mayores (`@v4`) y `aquasec/trivy:latest`: es el vector del compromiso de Trivy del 19 al 23 de marzo de 2026 (CVE-2026-33634 / GHSA-69fq-xp46-6x23), en el que se reescribieron 75 tags para robar secretos de CI. TexCore no estuvo expuesto (workflows creados el 2026-04-08) | 3 | 5 | 15 🟠 | ✅ Mitigado (2026-10-05) | Todas las actions fijadas por SHA de commit, binario de Trivy fijado (v0.75.0), Dependabot para actualizarlas, `actionlint` + `zizmor` como gate del CI y `persist-credentials: false` en cada checkout |
| RS-14 | **El CD podía desplegar código de un fork** — `workflow_run` con `branches: [master]` filtra por el nombre de la rama de origen; un PR desde un fork con una rama llamada `master` cumplía el filtro y, con el CI en verde, habría construido y desplegado ese código con los secretos de producción | 2 | 5 | 10 🟡 | ✅ Mitigado (2026-10-05) | La guardia `ci-guard` exigía además `event == 'push'` y que el repositorio de origen fuera el propio. **Eliminado de raíz el 2026-10-13:** `cd.yml` se borró y `release.yml` corre en el `push` a `master` del propio repositorio, sin `workflow_run`; el deploy va en un runner propio dentro del environment `production` con aprobación, y verifica la firma cosign de cada imagen antes de desplegar |
| RS-15 | **Inyección de comandos en el rollback** — el «motivo» que escribe quien lanza el rollback se interpolaba directamente en el script de notificación | 2 | 4 | 8 🟡 | ✅ Mitigado (2026-10-05) | Los valores llegan por `env` y el JSON se arma con `jq`; zizmor lo verifica en cada PR |
| RS-16 | **Credenciales en claro por el puerto 80** — nginx servía todo el sitio por HTTP sin redirigir; un login por `http://` en producción viajaba sin cifrar (RNF-01) | 3 | 5 | 15 🟠 | ✅ Mitigado (2026-10-13) | `NGINX_REDIRIGIR_HTTP=1` en `docker-compose.prod.yml`: el puerto 80 responde 301 hacia HTTPS (TLS 1.2/1.3 con HSTS). Las cookies de sesión, CSRF y JWT llevan `Secure`. `gestion/tests/test_nginx_redireccion_https.py`, `gestion/tests/test_cookies_seguras_produccion.py` y `docs/gestion-proyecto/evidencia/sprint-0/2026-10-13_nginx-https.txt` |
| RS-17 | **El gate de detect-secrets no bloqueaba** — complementa RS-07: el paso del CI (`detect-secrets scan --baseline`) solo reescribía la línea base y siempre terminaba en 0 | 3 | 4 | 12 🟠 | ✅ Mitigado (2026-10-12) | `detect-secrets-hook` sobre `git ls-files` y la línea base auditada por completo, ambos bloqueantes en `ci.yml`. Exclusiones (JUnit, resultados de Locust, graphify-out, lockfiles) en los filtros de la línea base |
| RS-18 | **SQL Server en edición Developer en el compose de producción** — `MSSQL_PID=Developer` estaba fijo; esa edición no está licenciada para producción | 2 | 4 | 8 🟡 | ✅ Mitigado en configuración (2026-10-12) | `MSSQL_PID` se toma del `.env`. `.env.prod.example` indica la edición licenciada (Standard), ver `docs/arquitectura/REQUISITOS_INFRAESTRUCTURA.md` |
| RS-19 | **Datos personales sin cifrado en reposo** — `Cliente.ruc_cedula` (cédula o RUC) y la fecha de nacimiento del usuario se guardaban en claro. La tesis afirma «privacidad desde el diseño» con las medidas técnicas de la LOPDP (2021) y los principios de la ISO/IEC 27001, así que el texto afirmaba más de lo que el sistema hacía. Era el defecto `SEC-08` de la auditoría de abril, diferido y nunca retomado | 2 | 4 | 8 🟡 | ✅ Mitigado (2026-10-19) | Se tomó la opción **(a) cifrado a nivel de campo**, descartando TDE como *única* medida (depende de la edición licenciada, ver RS-18) y complementándola con la corrección de la redacción de la tesis, que ahora describe con precisión lo que existe. Fernet (AES-128-CBC + HMAC) en `gestion/crypto.py` y `gestion/model_fields.py`; la unicidad `(RUC, sede)` y la búsqueda por identificación pasan a un **índice ciego** HMAC-SHA256 (`Cliente.ruc_cedula_hash`), porque el texto cifrado de un mismo valor cambia en cada escritura. Dos claves nuevas *fail-fast*: `FIELD_ENCRYPTION_KEYS` (rotable, `MultiFernet`) y `BLIND_INDEX_KEY` (estable), ninguna derivada de `SECRET_KEY`. Migración `gestion/0010_cifrar_datos_personales` (cifra lo existente en lotes de 500) y `manage.py cifrar_datos_personales` para verificar, reparar y reindexar. La fecha de nacimiento se audita por su HMAC, no en claro, porque `AuditLog` no está cifrado. 34 pruebas en `gestion/tests/test_cifrado_datos_personales.py`. Detalle en `docs/arquitectura/CIFRADO_DATOS_PERSONALES.md`; contraste en `AUDITORIA_CALIDAD.md` §I.5 |
| RS-20 | **Escaneo de despacho sin autenticación de usuario** — nginx reenviaba `/api/scanning/*` directo al `scanning_service`, que no autentica usuarios: sin iniciar sesión se podía consultar por código si un lote existía y, con stock vendible, su producto, peso y bodega, de cualquier sede; la documentación OpenAPI del servicio también era pública. Contradecía API1/API2 y el RNF-02 | 3 | 4 | 12 🟠 | ✅ Mitigado (2026-10-20) | nginx verifica la sesión con Django (`auth_request` a `/api/auth/verificar-sesion/`) antes de pasar la petición, y le envía al servicio la sede del usuario en cabeceras que reemplaza; el servicio responde 401 sin ellas y reenvía la sede a la `internal_api`, que acota lote y stock. Solo se publica `/api/scanning/validate`. Pruebas: `gestion/tests/test_profile_views.py`, `scanning_service/tests/integration/test_validate_endpoint.py`, `internal_api/tests/test_scanning_views.py`; verificado en el stack (sin sesión 401, otra sede «no encontrado», documentación 404) |
| RS-21 | **Autorización por objeto incompleta** — `SedeViewSet` mostraba todas las sedes con sus conteos a cualquier usuario; la validación de lote de Django distinguía un lote de otra sede de uno inexistente y daba 500 con un código repetido entre sedes; el panel ejecutivo (KPI, resumen, tendencia y producción por producto) no exigía rol | 2 | 3 | 6 🟢 | ✅ Mitigado (2026-10-20) | Sedes acotadas a la propia salvo para quien ve todas; validación de lote con `filtrar_lotes_por_sede`; `IsPanelEjecutivo` (Ejecutivo y administradores) en los indicadores. Control permanente: `gestion/tests/test_acceso_no_autorizado_global.py` recorre todas las rutas de objeto con los 9 roles acotados a una sede |
| RS-22 | **Escrituras con la cookie JWT sin token CSRF y relay de logs sin límites** — la cookie viaja sola en cualquier petición del navegador y solo `SameSite=Lax` frenaba una escritura desde otra página; el relay público `/api/logs/` creaba un logger por cada `msgid` distinto (memoria que Python no libera), aceptaba saltos de línea que falsifican entradas del log y no tenía límite de tasa | 2 | 3 | 6 🟢 | ✅ Mitigado (2026-10-20) | `CookieJWTAuthentication` valida el token CSRF en métodos no seguros y Django emite la cookie `csrftoken` en el login y el perfil; axios la reenvía en `X-CSRFToken`. El relay acota `msgid`, mensaje y `sd`, quita los saltos de línea y limita a 120 peticiones por minuto por IP. Pruebas: `gestion/tests/test_cookie_jwt_auth.py`, `gestion/tests/test_system_views.py`, `frontend/src/lib/axios.test.ts` |
| RS-23 | **GitLab autoalojado como punto único de falla del CI/CD** — el servidor de GitLab (código, pipeline y Container Registry) corre en el mismo equipo que el staging; si cae o se pierde su volumen, no hay pipeline ni registro de imágenes. El espejo en GitHub conserva el código pero no las imágenes ni la configuración de GitLab | 3 | 4 | 12 🟠 | 🟡 Mitigado en diseño (2026-10-20) | Respaldo diario (`gitlab-backup` y `backup-etc`, 7 días) con copia a otro equipo (`GUIA_GITLAB.md` §10), versión y digest fijos, espejo del código en GitHub y la guía de reinstalación. Las imágenes de producción por digest quedan en el registro de la VM tras cada despliegue (`:backup`). **Pendiente:** probar una restauración del respaldo |
| RS-24 | **Certificado propio y claves de firma como secretos de la cadena de suministro** — el certificado de GitLab que confían git, docker y cosign, y el par de claves de cosign (sin firma keyless, la clave privada es lo único que impide firmar imágenes falsas) | 2 | 5 | 10 🟡 | 🟡 Mitigado en diseño (2026-10-20) | La clave privada y su contraseña son variables de CI protegidas y enmascaradas (solo ramas protegidas), `cosign.pub` en el repositorio con `CODEOWNERS`, certificado de 825 días con aviso de renovación y rotación trimestral en `SECURITY.md`. **Pendiente:** cargar las variables en GitLab y borrar `infrastructure/gitlab/secretos/` |
| RS-25 | **Agotamiento de memoria por carga compartida** — GitLab, el stack `texcore-prod`, los jobs del pipeline (SQL Server de pruebas, Vitest) y el escritorio comparten un equipo de 16 GB **sin swap**. El 20-oct el kernel activó el OOM killer y cerró el navegador y el escritorio; un pico mayor pudo alcanzar a GitLab o al stack | 3 | 4 | 12 🟠 | 🟡 Mitigado parcialmente (2026-10-20) | Runner a 1 job, tope de 4 GB por job y 3 GB por servicio, `MSSQL_MEMORY_LIMIT_MB=2048` y heap de Node acotado (`GUIA_GITLAB.md` §1). **Pendiente:** crear swap o zram (requiere `sudo`) y, cuando exista la VM de producción, mover el runner de CI fuera de este equipo |

---

## Riesgos de Disponibilidad

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RD-01 | **Health checks superficiales** — `/health` retorna ok sin verificar BD real | 3 | 4 | 12 🟠 | ⚠️ Parcial (Sprint 7) | `scanning_service` verifica BD real; `printing_service` verifica templates; `reporting_excel` pendiente de BD real |
| RD-02 | **Sin circuit breaker** entre backend y servicios satélite — fallo en cascada | 2 | 5 | 10 🟡 | ✅ Mitigado (Sprint 5) | `reporting_proxy.py` usa `httpx.Client(timeout=60.0)` con `httpx.RequestError` |
| RD-03 | **Sin réplica de BD** en producción — SQL Server único punto de fallo | 2 | 5 | 10 🟡 | 🔄 Pendiente | Evaluar Always On Availability Groups |
| RD-04 | **Logs solo en archivo** — perdida de logs si el contenedor es eliminado | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | Logging a stdout (JSON) + archivo rotativo |
| RD-05 | **Migración `NULL → NOT NULL` sobre datos reales** (`gestion/0003` e `inventory/0002`, regla DJ001): el CI la prueba en SQL Server 2022 con la BD vacía; en producción convierte los `NULL` y altera 32 columnas, incluida `documento_ref` de la tabla de movimientos (la más grande, con índice) | 2 | 4 | 8 🟡 | ⚠️ Parcial (2026-10-06) | Antes de desplegar, aplicar la migración sobre un respaldo de producción y verificar 0 `NULL`, el índice de `documento_ref` y el tiempo de ejecución (`docs/arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md` §5). **6-oct:** verificada sobre una copia de la base de desarrollo en SQL Server 2022 (76 000 `NULL`, 88 405 auditorías): ~8 s, 32 columnas `NOT NULL`, mismas filas, 373 índices y 51 CHECK. Falta repetirla sobre el respaldo de producción |

| RD-06 | **Degradación con años de operación** — en la prueba de carga del 6-oct-2026 (3 años, 4 empresas) `/api/inventory/stock/` sin paginar mataba workers por memoria y el `COUNT` de `/audit-logs/` era el 75 % de la CPU de SQL Server: con 100 usuarios, 3 % de fallos; con 250, 10,6 % | 2 | 4 | 8 🟡 | ✅ Mitigado (2026-10-08) | Stock paginado + resumen por bodega y auditoría filtrable (`ADR_010_RENDIMIENTO_STOCK_Y_AUDITORIA.md`). **8-oct, medido sobre la base cargada:** la `0005` rellenó ~1 M de auditorías en 37 s; el `COUNT` seguía en el 40,7 % de la CPU con los índices de la `0004` y se corrigió con el índice cubriente `gestion/0008` (10 356 → 299 lecturas). Locust: 100 usuarios, 0,09 % de fallos (solo de negocio) y p95 de 270 ms con 3 CPU; 250 usuarios, 0,31 % y p95 de 410 ms con la BD en 6 CPU. Recursos recomendados en `EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §5 |
---

## Riesgos de Calidad de Código

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RC-01 | **N+1 queries no detectadas** — degradación de rendimiento en producción | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 2) | `select_related` + `annotate` en `reporte_eficiencia` |
| RC-02 | **Excepciones silenciadas** — errores perdidos, dificultan diagnóstico | 4 | 3 | 12 🟠 | ✅ Mitigado (Sprint 2) | Bare excepts reemplazados por logging específico |
| RC-03 | **Cobertura de tests insuficiente** — regresiones no detectadas en CI | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 3; endurecido 2026-10-05) | `coverage.py` con `fail_under = 90` en `.coveragerc`, bloqueante en el CI desde el 2026-10-05 (91,8 %); microservicios con su umbral en cada `pytest.ini` (85/95/90 %) |
| RC-04 | **Tests sin técnica ISTQB** — baja efectividad en detección de defectos | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 3) | Convención de nombres + EP/BVA/STT aplicados |
| RC-05 | **Sin validación de tipos en Python** (mypy ausente) | 2 | 2 | 4 🔵 | ✅ Mitigado (2026-10-05) | mypy con los plugins de Django y DRF como gate del CI, en 0 sobre 268 archivos (configuración en `pyproject.toml`) |
| RC-06 | **Funciones demasiado complejas en el núcleo de producción** — `registrar_operacion` (complejidad 47), `registrar_lote` (29) y otras 8 por encima de 15: difíciles de probar y de modificar sin regresiones | 3 | 3 | 9 🟡 | ✅ Mitigado (2026-10-05) | Ruff `C901` con `max-complexity = 15` como gate; las 10 funciones divididas en pasos, con pruebas de caracterización verificadas contra el código anterior |
| RC-07 | **Paso *best-effort* sin savepoint dentro de la transacción del lote** — un error de BD en la sincronización MES de `registrar_lote` se atrapaba, pero dejaba la corrida a medio crear y la transacción expuesta | 2 | 4 | 8 🟡 | ✅ Mitigado (2026-10-05) | La sincronización corre en su propio `transaction.atomic()`; prueba de regresión que falla contra el código anterior. Regla en `ESTANDARES_DESARROLLO.md` §4 |
| RC-09 | **Esquema OpenAPI incompleto** — ningún endpoint usa `@extend_schema`, así que `manage.py spectacular` emite **124 avisos**: autenticador propio sin extensión registrada, parámetros de ruta sin tipo, `SerializerMethodField` sin anotación y acciones cuya respuesta no es el serializer del ViewSet (entre ellas `/api/paros-maquina/historial/`, que devuelve un objeto compuesto). El esquema publicado describe de menos lo que la API hace | 2 | 3 | 6 🟡 | ⚠️ Abierto (detectado 2026-10-14) | Pendiente de decisión del usuario: registrar una `OpenApiAuthenticationExtension` para `CookieJWTAuthentication` (quita la mayoría de los avisos de una vez), tipar los `SerializerMethodField` —los nuevos ya van anotados— y anotar con `@extend_schema` las acciones cuya respuesta no es su serializer. Es un barrido propio, no se mezcla con una funcionalidad |
| RC-10 | **Un cambio de estado de máquina fuera de la API no genera su paro** — `ParoPorEstadoService` vive en `MaquinaViewSet.perform_update` (ADR-013), así que un `UPDATE` directo en la base o una edición desde el admin de Django dejan el historial sin el intervalo | 1 | 3 | 3 🔵 | ⚠️ Aceptado (2026-10-14) | La API es el único camino de la aplicación y el admin de Django solo lo usa el administrador de sistemas. Si el admin pasa a usarse para esto, la sincronización se mueve a una señal `post_save` con la misma prueba de la tabla de decisión. Documentado en el ADR-013 §3 |
| RC-08 | **Dos representaciones del texto vacío** (`NULL` y `''`) en 32 campos — filtros y reportes que omiten filas | 3 | 2 | 6 🟡 | ✅ Mitigado (2026-10-05) | `blank=True, default=''` con migración de datos y regla Ruff `DJ001` como gate (`ADR_008_TEXTO_VACIO_SIN_NULL.md`); el despliegue depende de RD-05 |

---

## Riesgos de Gobierno (COBIT)

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RG-01 | **Sin CI/CD** — despliegues manuales con riesgo de error humano | 4 | 4 | 16 🟠 | ✅ Mitigado (Sprint 4) | `.gitlab-ci.yml` con los gates de calidad (antes, `.github/workflows/ci.yml`) |
| RG-02 | **Sin pre-commit hooks** — código de baja calidad puede entrar al repositorio | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | `.pre-commit-config.yaml` con Ruff (reemplaza a flake8 y bandit desde el 2026-10-05) + detect-secrets, las mismas reglas que el CI |
| RG-03 | **Sin estándares documentados** — inconsistencia entre desarrolladores | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | `docs/arquitectura/ESTANDARES_DESARROLLO.md` (actualizado el 2026-10-05) |
| RG-04 | **Sin registro de riesgos** — gestión reactiva en lugar de proactiva | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | Este documento |
| RG-05 | **Sin documentación de API** — integración de terceros compleja | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | OpenAPI 3.1 en `/api/docs/` vía drf-spectacular |

---

## Seguimiento de Riesgos

### Resumen de Exposición Total

| Estado | Cantidad | Exposición Promedio |
|--------|----------|-------------------|
| ✅ Mitigado | 31 | — |
| ⚠️ Parcial | 3 | 11 (🟡 Medio) |
| 🔄 Pendiente | 1 | 10 (🟡 Medio) |
| ⚠️ Abierto / Aceptado (19-oct-2026) | 2 | 4,5 (🟡 Medio) — RC-09 esquema OpenAPI, RC-10 estado de máquina fuera de la API |

### Próxima revisión

**Fecha:** al abrir el PR `MES → staging` (hoja de ruta del `CHANGELOG`, paso 13)
**Responsable:** Tech Lead / Auditor de Calidad
**Criterio de cierre de riesgos pendientes:** Implementación verificada en rama `staging` con CI verde.

### Riesgos Pendientes — Próximo Sprint

| ID | Acción inmediata |
|----|-----------------|
| RD-01 | Health check real en `reporting_excel` (verificar conexión a SQL Server) |
| RD-03 | Tarea de infraestructura — fuera del alcance del equipo de desarrollo |
| RD-05 | Probar las migraciones DJ001 sobre un respaldo de producción en SQL Server antes del despliegue de `MES` |
| RC-09 | Barrido del esquema OpenAPI: extensión del autenticador, tipos en los parámetros de ruta y `@extend_schema` en las acciones compuestas (plan propio, pendiente de decisión) |
| RD-06 | ✅ Cerrado el 8-oct (ver `EVIDENCIA_RENDIMIENTO_USABILIDAD.md`). Al desplegar, dimensionar la BD según la concurrencia esperada (§5) |
