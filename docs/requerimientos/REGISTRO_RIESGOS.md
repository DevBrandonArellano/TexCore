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
| RS-12 | **Sin escaneo Trivy de los 3 microservicios satélite en CI** — el job `scan:images` solo cubría `backend`/`nginx`; `printing_service`, `scanning_service` y `reporting_excel` nunca se escaneaban, a pesar de haberse encontrado CVEs CRITICAL en ellos el 2026-09-22 | 3 | 3 | 9 🟡 | ✅ Mitigado (2026-10-05) | El job de 2026-09-22 vivía en `.gitlab-ci.yml`, pipeline que no se ejecutaba, así que la mitigación no era efectiva. Desde el 2026-10-05 la matriz `scan-images` de `.github/workflows/cd.yml` escanea las 5 imágenes; los 3 satélites con `ignore-unfixed` (bloquea solo CVEs con parche disponible — ver justificación en RS-11) |
| RS-13 | **Actions de CI en referencias mutables** — `aquasecurity/trivy-action@master`, tags mayores (`@v4`) y `aquasec/trivy:latest`: es el vector del compromiso de Trivy del 19 al 23 de marzo de 2026 (CVE-2026-33634 / GHSA-69fq-xp46-6x23), en el que se reescribieron 75 tags para robar secretos de CI. TexCore no estuvo expuesto (workflows creados el 2026-04-08) | 3 | 5 | 15 🟠 | ✅ Mitigado (2026-10-05) | Todas las actions fijadas por SHA de commit, binario de Trivy fijado (v0.75.0), Dependabot para actualizarlas, `actionlint` + `zizmor` como gate del CI y `persist-credentials: false` en cada checkout |
| RS-14 | **El CD podía desplegar código de un fork** — `workflow_run` con `branches: [master]` filtra por el nombre de la rama de origen; un PR desde un fork con una rama llamada `master` cumplía el filtro y, con el CI en verde, habría construido y desplegado ese código con los secretos de producción | 2 | 5 | 10 🟡 | ✅ Mitigado (2026-10-05) | La guardia `ci-guard` exige además `event == 'push'` y que el repositorio de origen sea el propio. `cd.yml` se reemplaza por `release.yml` en la Fase 3 del plan de CI/CD |
| RS-15 | **Inyección de comandos en el rollback** — el «motivo» que escribe quien lanza el rollback se interpolaba directamente en el script de notificación | 2 | 4 | 8 🟡 | ✅ Mitigado (2026-10-05) | Los valores llegan por `env` y el JSON se arma con `jq`; zizmor lo verifica en cada PR |

---

## Riesgos de Disponibilidad

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RD-01 | **Health checks superficiales** — `/health` retorna ok sin verificar BD real | 3 | 4 | 12 🟠 | ⚠️ Parcial (Sprint 7) | `scanning_service` verifica BD real; `printing_service` verifica templates; `reporting_excel` pendiente de BD real |
| RD-02 | **Sin circuit breaker** entre backend y servicios satélite — fallo en cascada | 2 | 5 | 10 🟡 | ✅ Mitigado (Sprint 5) | `reporting_proxy.py` usa `httpx.Client(timeout=60.0)` con `httpx.RequestError` |
| RD-03 | **Sin réplica de BD** en producción — SQL Server único punto de fallo | 2 | 5 | 10 🟡 | 🔄 Pendiente | Evaluar Always On Availability Groups |
| RD-04 | **Logs solo en archivo** — perdida de logs si el contenedor es eliminado | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | Logging a stdout (JSON) + archivo rotativo |
| RD-05 | **Migración `NULL → NOT NULL` sobre datos reales** (`gestion/0003` e `inventory/0002`, regla DJ001): el CI la prueba en SQL Server 2022 con la BD vacía; en producción convierte los `NULL` y altera 32 columnas, incluida `documento_ref` de la tabla de movimientos (la más grande, con índice) | 2 | 4 | 8 🟡 | ⚠️ Parcial (2026-10-06) | Antes de desplegar, aplicar la migración sobre un respaldo de producción y verificar 0 `NULL`, el índice de `documento_ref` y el tiempo de ejecución (`docs/arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md` §5). **6-oct:** verificada sobre una copia de la base de desarrollo en SQL Server 2022 (76 000 `NULL`, 88 405 auditorías): ~8 s, 32 columnas `NOT NULL`, mismas filas, 373 índices y 51 CHECK. Falta repetirla sobre el respaldo de producción |

| RD-06 | **Degradación con años de operación** — en la prueba de carga del 6-oct-2026 (3 años, 4 empresas) `/api/inventory/stock/` sin paginar mataba workers por memoria y el `COUNT` de `/audit-logs/` era el 75 % de la CPU de SQL Server: con 100 usuarios, 3 % de fallos; con 250, 10,6 % | 2 | 4 | 8 🟡 | ✅ Mitigado (2026-10-08) | Stock paginado + resumen por bodega y auditoría filtrable (`ADR_010_RENDIMIENTO_STOCK_Y_AUDITORIA.md`). **8-oct, medido sobre la base cargada:** la `0005` rellenó ~1 M de auditorías en 37 s; el `COUNT` seguía en el 40,7 % de la CPU con los índices de la `0004` y se corrigió con el índice cubriente `gestion/0008` (10 356 → 299 lecturas). Locust: 100 usuarios, 0,09 % de fallos (solo de negocio) y p95 de 270 ms con 3 CPU; 250 usuarios, 0,31 % y p95 de 410 ms con la BD en 6 CPU. Recursos recomendados en `EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §8 |
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
| RC-08 | **Dos representaciones del texto vacío** (`NULL` y `''`) en 32 campos — filtros y reportes que omiten filas | 3 | 2 | 6 🟡 | ✅ Mitigado (2026-10-05) | `blank=True, default=''` con migración de datos y regla Ruff `DJ001` como gate (`ADR_008_TEXTO_VACIO_SIN_NULL.md`); el despliegue depende de RD-05 |

---

## Riesgos de Gobierno (COBIT)

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RG-01 | **Sin CI/CD** — despliegues manuales con riesgo de error humano | 4 | 4 | 16 🟠 | ✅ Mitigado (Sprint 4) | `.github/workflows/ci.yml` con quality gate |
| RG-02 | **Sin pre-commit hooks** — código de baja calidad puede entrar al repositorio | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | `.pre-commit-config.yaml` con Ruff (reemplaza a flake8 y bandit desde el 2026-10-05) + detect-secrets, las mismas reglas que el CI |
| RG-03 | **Sin estándares documentados** — inconsistencia entre desarrolladores | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | `docs/arquitectura/ESTANDARES_DESARROLLO.md` (actualizado el 2026-10-05) |
| RG-04 | **Sin registro de riesgos** — gestión reactiva en lugar de proactiva | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | Este documento |
| RG-05 | **Sin documentación de API** — integración de terceros compleja | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | OpenAPI 3.1 en `/api/docs/` vía drf-spectacular |

---

## Seguimiento de Riesgos

### Resumen de Exposición Total

| Estado | Cantidad | Exposición Promedio |
|--------|----------|-------------------|
| ✅ Mitigado | 30 | — |
| ⚠️ Parcial | 3 | 11 (🟡 Medio) |
| 🔄 Pendiente | 1 | 10 (🟡 Medio) |

### Próxima revisión

**Fecha:** 2026-04-27
**Responsable:** Tech Lead / Auditor de Calidad
**Criterio de cierre de riesgos pendientes:** Implementación verificada en rama `staging` con CI verde.

### Riesgos Pendientes — Próximo Sprint

| ID | Acción inmediata |
|----|-----------------|
| RD-01 | Health check real en `reporting_excel` (verificar conexión a SQL Server) |
| RD-03 | Tarea de infraestructura — fuera del alcance del equipo de desarrollo |
| RD-05 | Probar las migraciones DJ001 sobre un respaldo de producción en SQL Server antes del despliegue de `MES` |
| RD-06 | ✅ Cerrado el 8-oct (ver `EVIDENCIA_RENDIMIENTO_USABILIDAD.md`). Al desplegar, dimensionar la BD según la concurrencia esperada (§8) |
