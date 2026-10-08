# Evidencia manual por sprint — TexCore

Complemento de `EVIDENCIA_POR_SPRINT.md` (pruebas automatizadas). Aquí está lo que **no**
se demuestra con una prueba unitaria: infraestructura, pipeline, mediciones, usabilidad,
staging y las ceremonias de Scrum.

**Convención:**
- cada evidencia se guarda en `docs/gestion-proyecto/evidencia/<sprint>/` con fecha en el nombre (`2026-10-08_docker-ps.png`);
- en la tesis se cita esa ruta.

**Equipo:** **🖥️ SQL** = equipo con Docker y SQL Server · **💻** = este equipo (sin Docker) · **🌐** = GitHub.

**Estado:** ✅ ya existe · ⏳ por generar · 🚧 requiere trabajo antes de poder demostrarlo.

---

## Sprint 0 — Infraestructura y DevOps

| Historia / CA | Qué mostrar | Cómo generarla | Equipo | Estado |
|---|---|---|---|---|
| TEX-01 CA-1 | Los 9 contenedores en `healthy` | `docker compose -f infrastructure/docker/docker-compose.yml up -d` y luego `docker compose ps` (captura) | 🖥️ SQL | 🚧 Hoy solo `db` tiene `healthcheck` (M-3, Fase 9) |
| TEX-01 CA-2 | Arranque sin reinicios ni errores | `docker compose ps` (columna STATUS) + `docker compose logs --no-color > arranque.log` | 🖥️ SQL | ⏳ |
| TEX-01 CA-3 | Persistencia en volumen nombrado | Crear un registro, `docker compose down` + `up`, consultarlo; `docker volume ls` | 🖥️ SQL | ⏳ |
| TEX-02 CA-1 | Comunicación por nombre en red interna | `docker compose exec backend python -c "import socket;print(socket.gethostbyname('scanning'))"` | 🖥️ SQL | ⏳ |
| TEX-02 CA-2 | Puerto de BD no accesible desde fuera | Desde otro equipo: `Test-NetConnection <ip> -Port 1433` → falla (en dev está ligado a `127.0.0.1`; en prod usa `expose`) | 🖥️ SQL | ⏳ |
| TEX-03 CA-1/2 | Nginx enruta `/api/` y sirve React | `curl -i http://localhost/api/health/` y `curl -i http://localhost/` (capturas) | 🖥️ SQL | ⏳ |
| TEX-03 CA-3 | IP real en la auditoría | Prueba `gestion/tests/test_system_views.py` (`_extract_client_ip`) + registro de auditoría con la IP del cliente | 💻 | ✅ prueba |
| TEX-04 CA-1/2/3 | Pipeline con quality gate y SQL Server efímero | Captura de una ejecución de `ci.yml` en GitHub Actions con todos los jobs en verde y del job `quality-gate` | 🌐 | 🚧 Requiere push de los cambios sin commitear |
| TEX-05 CA-1/2 | Estructura y estándares | Árbol del repositorio (`tree /F /A` filtrado) + `CLAUDE.md` / docs de estándares (convención ISTQB) | 💻 | ⏳ |

## Definición de Hecho transversal (§5.1 de la tesis)

| Criterio de la DoD | Qué mostrar | Cómo generarla | Estado |
|---|---|---|---|
| Integrado en la rama principal vía CI/CD | Historial de PRs `staging` → `master` con checks verdes | GitHub → Pull requests (captura) | 🚧 El trabajo de octubre está sin commitear |
| Análisis estáticos | Ruff, mypy, Semgrep, detect-secrets, pip-audit y npm audit en verde; **ESLint** en el frontend | Job `backend-lint` y `frontend-test` en Actions; localmente: `ruff check .`, `npx eslint .` | ✅ local / 🚧 Actions |
| Cobertura ≥ 75 % (hoy el gate es 90 %) | Reporte de cobertura del backend (≥ 90 %), microservicios (85/95/90) y frontend (95.5/90/93.9/96.6) | Artefactos `coverage` del CI; local frontend `npx vitest run --coverage` | ✅ frontend (7-oct) / ⏳ backend con SQL Server |
| Auditoría en operaciones críticas | Pruebas de TEX-09 y TEX-10 | `EVIDENCIA_POR_SPRINT.md`, Sprint 1 | ✅ |
| Desplegado en staging | Ejecución de `cd.yml` / despliegue en staging + sistema operando | Fase 9 del plan | 🚧 |

> **Corregir en la tesis:** la DoD nombra `flake8` y `bandit`. Ruff los reemplazó (ADR-008 y TEX-04 actualizado el 7-oct). El texto debe decir «Ruff (reglas de estilo y de seguridad `S`), mypy, Semgrep, detect-secrets y pip-audit».

## Requisitos medibles (RNF-03 y usabilidad)

| Historia / CA | Umbral | Evidencia | Estado |
|---|---|---|---|
| TEX-44 CA-3 escaneo | < 2500 ms | Locust: `scripts/loadtest/resultados/carga_100_2026-09-29_*.csv` (12 195 peticiones, mediana 22 ms, p95 100 ms, máx. 541 ms; **coincide con la Tabla 47 de la tesis**) | ✅ Repetir tras los cambios de octubre |
| TEX-17 CA-3 panel de planta | < 3 s | Prueba `PanelJefePlantaRendimientoTest` + nueva corrida de Locust | ✅ prueba / ⏳ Locust 🖥️ SQL |
| TEX-22 CA-3 kárdex | < 3 s | Prueba `KardexBodegaRendimientoTestCase` + nueva corrida de Locust | ✅ prueba / ⏳ Locust 🖥️ SQL |
| TEX-12 CA-5 registro de lote | ≤ 3 pasos | Grabación (GIF o video) del Operario registrando un lote, numerando cada clic | ⏳ |
| TEX-41 CA-3 pesaje | ≤ 3 pasos | Grabación del Empaquetado pesando y emitiendo la etiqueta | ⏳ |
| TEX-46 CA-4 panel responsivo | Legible en móvil, tableta y escritorio | Capturas del panel ejecutivo a 375, 768 y 1366 px | ⏳ |
| Capacitación ≤ 2 h por grupo | — | Se ejecuta en la puesta en marcha (marzo 2027, §5.4). **No se puede demostrar antes:** declararlo como actividad planificada | — |

Entregable: `docs/requerimientos/EVIDENCIA_RENDIMIENTO_USABILIDAD.md` (Fase 7).

## Sprint 8 — TEX-54 Congelamiento y staging

| CA | Qué mostrar | Cómo | Estado |
|---|---|---|---|
| CA-1 congelamiento | Etiqueta de versión y regla de solo correcciones | `git tag -a v1.0.0-rc1` + protección de rama `master`/`staging` en GitHub (captura de los ajustes) | 🚧 Fase 9 |
| CA-2 staging en verde | Sistema completo en staging con la suite en verde y la cobertura sobre el umbral | Ejecución de `cd.yml` + capturas de los 11 paneles en staging | 🚧 Fase 9 |
| CA-3 reversión en un paso | Ejecución de `rollback.yml` (`workflow_dispatch`, confirmación `ROLLBACK`) | Captura de la ejecución en Actions | 🚧 Fase 9 |

Mientras TEX-54 no esté hecho, la tesis **no** debe marcarlo como «Completada» (hoy figura así en el resumen de historias y en la Sprint Review del Sprint 8).

## Ceremonias de Scrum (§5.1 y §7.2.3)

La tesis afirma Sprint Planning, Review y Retrospective en cada sprint. Evidencia aceptable:

- [ ] Backlog cargado en Jira (`texcore_jira_import.csv`): captura del tablero y del burndown por sprint.
- [ ] Actas breves de cada Sprint Review: fecha, asistentes, incremento mostrado y acuerdos. Conviene la firma o el correo de confirmación de Interfibra.
- [ ] Retrospectivas: qué mejorar y qué se aplicó (el CHANGELOG sirve de respaldo de los cambios).
- [ ] Commits por sprint: `git log --since=<inicio> --until=<fin> --oneline` para cada rango de fechas de la Tabla 14.

> Redactar en la tesis solo las reuniones que efectivamente ocurrieron, y como ocurrieron. Si una revisión fue interna, decirlo así.

## Afirmaciones del documento (6-oct) que hay que corregir o respaldar

| Afirmación | Situación real | Acción |
|---|---|---|
| «Réplica equivalente en GitLab CI» | GitLab CI se retiró (commit `a65ff02`) | Quitar la mención o justificar el retiro |
| DoD con `flake8`, `bandit` | Reemplazados por Ruff | Actualizar 5.1, 5.3, 7.2.3 y la tabla de herramientas |
| «La auditoría de dependencias se reporta como advertencia» | Ahora es **bloqueante** | Actualizar 7.2.13 |
| TEX-54 «Completada» / Sprint 8 en staging | Pendiente (Fase 9) | Completar la Fase 9 o corregir el texto |
| 331 commits; tamaño del código | 368 commits al 7-oct, y crecerá | Actualizar las cifras al cierre |
| Tabla 46 (resultados de pruebas) | Anterior al 7-oct | Actualizar con `EVIDENCIA_POR_SPRINT.md` y la cobertura final |
| Pipeline (Figura 49) | Ahora incluye ESLint y el typecheck de pruebas del frontend | Actualizar la figura y el texto |
