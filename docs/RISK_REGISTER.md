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
| RS-05 | **CORS abierto** en microservicio de reportes (`allow_origins=["*"]`) | 3 | 4 | 12 🟠 | ✅ Mitigado (Sprint 1) | CORS restringido a `http://backend:8000` |
| RS-06 | **Rate limiting ausente** en endpoints de autenticación — susceptible a brute force | 4 | 4 | 16 🟠 | ✅ Mitigado (Sprint 1) | Nginx: 5 req/min en `/api/token/` |
| RS-07 | **Secrets en secrets.baseline ausente** — detect-secrets no inicializado | 2 | 3 | 6 🟡 | 🔄 Pendiente | Ejecutar `detect-secrets scan > .secrets.baseline` |
| RS-08 | **Dependencias sin versiones fijadas** (printing_service/requirements.txt) | 3 | 3 | 9 🟡 | 🔄 Pendiente | Fijar versiones en todos los requirements.txt |

---

## Riesgos de Disponibilidad

| ID | Riesgo | Prob | Impacto | Exposición | Estado | Plan de Mitigación |
|----|--------|------|---------|-----------|--------|--------------------|
| RD-01 | **Health checks superficiales** — `/health` retorna ok sin verificar BD real | 3 | 4 | 12 🟠 | 🔄 Pendiente | Verificar conexión a BD en cada health check |
| RD-02 | **Sin circuit breaker** entre backend y microservicios — fallo en cascada | 2 | 5 | 10 🟡 | 🔄 Pendiente | Implementar timeout + retry con backoff |
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
| ✅ Mitigado | 17 | — |
| 🔄 Pendiente | 6 | 7.5 (🟡 Medio) |

### Próxima revisión

**Fecha:** 2026-04-27
**Responsable:** Tech Lead / Auditor de Calidad
**Criterio de cierre de riesgos pendientes:** Implementación verificada en rama `staging` con CI verde.

### Riesgos Pendientes — Próximo Sprint

| ID | Acción inmediata |
|----|-----------------|
| RS-07 | `detect-secrets scan > .secrets.baseline && git add .secrets.baseline` |
| RS-08 | Fijar versiones en `printing_service/requirements.txt` y `scanning_service/requirements.txt` |
| RD-01 | Health checks reales en `printing_service` (verificar templates) y `scanning_service` (ya implementado) |
| RD-02 | Añadir `timeout=10` en todas las llamadas `httpx` del reporting_proxy |
| RD-03 | Tarea de infraestructura — fuera del alcance del equipo de desarrollo |
| RC-05 | Evaluar en siguiente sprint de calidad |
