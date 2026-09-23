# TexCore — Registro de Riesgos

> Versión 1.0 | 2026-03-27
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
| RS-12 | **Sin escaneo Trivy de los 3 microservicios satélite en CI** — el job `scan:images` solo cubría `backend`/`nginx`; `printing_service`, `scanning_service` y `reporting_excel` nunca se escaneaban, a pesar de haberse encontrado CVEs CRITICAL en ellos el 2026-09-22 | 3 | 3 | 9 🟡 | ✅ Mitigado (2026-09-22) | Nuevo job `scan:images-satellites` en `.gitlab-ci.yml` (stage `scan`), con `needs` en los 3 jobs `build:*` existentes y gate en `deploy`. Usa `--ignore-unfixed` (bloquea solo CVEs con parche disponible — ver justificación en RS-11) |

---

## Riesgos de Disponibilidad

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RD-01 | **Health checks superficiales** — `/health` retorna ok sin verificar BD real | 3 | 4 | 12 🟠 | ⚠️ Parcial (Sprint 7) | `scanning_service` verifica BD real; `printing_service` verifica templates; `reporting_excel` pendiente de BD real |
| RD-02 | **Sin circuit breaker** entre backend y servicios satélite — fallo en cascada | 2 | 5 | 10 🟡 | ✅ Mitigado (Sprint 5) | `reporting_proxy.py` usa `httpx.Client(timeout=60.0)` con `httpx.RequestError` |
| RD-03 | **Sin réplica de BD** en producción — SQL Server único punto de fallo | 2 | 5 | 10 🟡 | 🔄 Pendiente | Evaluar Always On Availability Groups |
| RD-04 | **Logs solo en archivo** — perdida de logs si el contenedor es eliminado | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | Logging a stdout (JSON) + archivo rotativo |

---

## Riesgos de Calidad de Código

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RC-01 | **N+1 queries no detectadas** — degradación de rendimiento en producción | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 2) | `select_related` + `annotate` en `reporte_eficiencia` |
| RC-02 | **Excepciones silenciadas** — errores perdidos, dificultan diagnóstico | 4 | 3 | 12 🟠 | ✅ Mitigado (Sprint 2) | Bare excepts reemplazados por logging específico |
| RC-03 | **Cobertura de tests insuficiente** — regresiones no detectadas en CI | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 3) | `coverage.py` con umbral 75% en CI |
| RC-04 | **Tests sin técnica ISTQB** — baja efectividad en detección de defectos | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 3) | Convención de nombres + EP/BVA/STT aplicados |
| RC-05 | **Sin validación de tipos en Python** (mypy ausente) | 2 | 2 | 4 🔵 | 🔄 Pendiente | Evaluar mypy con `--ignore-missing-imports` |

---

## Riesgos de Gobierno (COBIT)

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RG-01 | **Sin CI/CD** — despliegues manuales con riesgo de error humano | 4 | 4 | 16 🟠 | ✅ Mitigado (Sprint 4) | `.github/workflows/ci.yml` con quality gate |
| RG-02 | **Sin pre-commit hooks** — código de baja calidad puede entrar al repositorio | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | `.pre-commit-config.yaml` con flake8 + bandit + detect-secrets |
| RG-03 | **Sin estándares documentados** — inconsistencia entre desarrolladores | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | `docs/DEVELOPMENT_STANDARDS.md` creado |
| RG-04 | **Sin registro de riesgos** — gestión reactiva en lugar de proactiva | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | Este documento |
| RG-05 | **Sin documentación de API** — integración de terceros compleja | 3 | 3 | 9 🟡 | ✅ Mitigado (Sprint 4) | OpenAPI 3.1 en `/api/docs/` vía drf-spectacular |

---

## Seguimiento de Riesgos

### Resumen de Exposición Total

| Estado | Cantidad | Exposición Promedio |
|--------|----------|-------------------|
| ✅ Mitigado | 25 | — |
| ⚠️ Parcial | 1 | 12 (🟠 Alto) |
| 🔄 Pendiente | 2 | 9.5 (🟡 Medio) |

### Próxima revisión

**Fecha:** 2026-04-27
**Responsable:** Tech Lead / Auditor de Calidad
**Criterio de cierre de riesgos pendientes:** Implementación verificada en rama `staging` con CI verde.

### Riesgos Pendientes — Próximo Sprint

| ID | Acción inmediata |
|----|-----------------|
| RD-01 | Health check real en `reporting_excel` (verificar conexión a SQL Server) |
| RD-03 | Tarea de infraestructura — fuera del alcance del equipo de desarrollo |
| RC-05 | Evaluar mypy con `--ignore-missing-imports` en siguiente sprint de calidad |
