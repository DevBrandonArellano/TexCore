# Contraste de la tesis con el sistema — evidencia no automatizada

> **Versión evaluada:** rama `MES`, migraciones hasta `gestion/0010` · **Fecha:** 26-oct-2026
> (La evidencia de infraestructura del Sprint 0 se capturó el 13-oct, sobre `gestion/0008`; nada de lo añadido después la altera.)
> **Propósito:** respaldar el paso a producción, contrastando cada compromiso de la tesis con el sistema.
> **Entorno:** la configuración de despliegue de producción (`infrastructure/docker/docker-compose.prod.yml`) con 3 años de operación simulada.
> **Fuente de la tesis:** `docs/Anteproyecto_Capstone_Final_Version.pdf`: RNF (Tablas 6 a 10), Definición de Hecho (§5.1), sprints (Tabla 14), despliegue (§5.3) y puesta en marcha (§5.4).

Este documento complementa a `EVIDENCIA_POR_SPRINT.md`, que reúne las pruebas automatizadas de cada historia. Las correcciones al texto de la tesis están en `CORRECCIONES_TESIS.md`.

**Veredicto:** ✅ cumple · ❌ no cumple como está redactado · ⏳ pendiente · 📅 planificado para la puesta en marcha.

---

## 1. Sprint 0 — Infraestructura (Tabla 14)

DoD de la tesis: «Contenedores levantan sin errores; pipeline ejecuta build y lint; backlog estimado y priorizado».

| Criterio | Evidencia | Veredicto |
|---|---|---|
| Contenedores levantan sin errores (TEX-01 CA-1) | Los 6 contenedores en `healthy`, cada imagen con su `HEALTHCHECK`: `sprint-0/2026-10-13_docker-compose-ps.txt` | ✅ |
| Arranque sin reinicios ni errores (TEX-01 CA-2) | `RestartCount=0` en los 6 y log de arranque sin errores: `sprint-0/2026-10-08_reinicios.txt` | ✅ |
| Persistencia en volumen nombrado (TEX-01 CA-3) | Registro creado, `down` + `up` y registro recuperado: `sprint-0/2026-10-08_persistencia-volumen.txt` | ✅ |
| Comunicación por nombre en la red interna (TEX-02 CA-1) | Resolución DNS entre servicios y redes `dmz_net`/`internal_net`: `sprint-0/2026-10-08_red-interna.txt` | ✅ |
| Puerto de la BD no accesible desde fuera (TEX-02 CA-2) | 1433 sin publicar y conexión rechazada: `sprint-0/2026-10-08_puerto-bd.txt` | ✅ |
| Nginx enruta `/api/` y sirve React (TEX-03 CA-1/2) | `curl` por HTTPS a `/api/health/` y a `/`: `sprint-0/2026-10-13_nginx-https.txt` | ✅ |
| IP real del cliente en la auditoría (TEX-03 CA-3) | `gestion/tests/test_system_views.py` (`_extract_client_ip`) | ✅ |
| Pipeline ejecuta build y lint (TEX-04) | Pipeline #6 del `.gitlab-ci.yml` en GitLab CI (20-oct-2026): los 12 jobs de integración (`lint:*`, `test:*`, `audit:*`) en verde, cobertura media 95,8 %. El build de imágenes y el release se ejecutan al fusionar en `master`. La configuración de los jobs cambió el 26-oct (topes de memoria): la corrida con la configuración actual está pendiente de subir | ✅ integración · ⏳ release y corrida actual |
| Estructura base del repositorio y estándares (TEX-05) | `docs/arquitectura/ESTANDARES_DESARROLLO.md` y convención ISTQB de nombres de prueba | ✅ |
| Backlog estimado y priorizado | `docs/gestion-proyecto/PRODUCT_BACKLOG.md`: 54 historias, 288 puntos, 9 épicas | ✅ |

## 2. Sprints 1 a 8 — Definición de Hecho por sprint (Tabla 14)

Las pruebas de cada historia se ejecutan sobre SQL Server 2022 y se detallan en `EVIDENCIA_POR_SPRINT.md`, en la sección del sprint: 0 fallidas y 0 omitidas en todos los sprints.

| Sprint | DoD de la tesis | Evidencia | Veredicto |
|---|---|---|---|
| 1 | Acceso restringido por rol verificado; pruebas de acceso no autorizado superadas; auditoría activa | TEX-06 a TEX-10 (53 pruebas) | ✅ |
| 2 | OP transita estados correctamente; registro de lote atómico; cobertura ≥ 75 % | TEX-11 a TEX-17 (444 pruebas); cobertura del núcleo de 92,5 % | ✅ |
| 3 | Movimientos reflejan saldo correcto; cada operación auditada; sin saldos inconsistentes | TEX-18 a TEX-23 (151 pruebas); stock = kárdex en 51 994 combinaciones tras la carga concurrente (`docs/requerimientos/EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §3.3) | ✅ |
| 4 | MRP genera órdenes de compra sugeridas; alertas correctas; pruebas de borde superadas | TEX-24 a TEX-29 (209 pruebas) | ✅ |
| 5 | Validación de crédito bloquea pedidos fuera de cupo; FIFO aplica cronológicamente; reversión auditada | TEX-30 a TEX-36 (80 pruebas) | ✅ |
| 6 | Dosificación calcula gramos exactos; etiqueta ZPL impresa con tara; recetas versionadas | TEX-37 a TEX-43 (268 pruebas) | ✅ |
| 7 | Escaneo valida lote contra pedido; despacho atómico sin descargas parciales; KPIs en tiempo real | TEX-44 a TEX-48 (199 pruebas); escaneo < 2500 ms bajo carga (`EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §3) | ✅ |
| 8 | Roles administrativos operan según su alcance; navegación persistente | TEX-49 a TEX-53 | ✅ |
| 8 | Congelamiento de código aplicado; sistema completo en staging (TEX-54) | Etiqueta de versión, protección de ramas, despliegue en staging y ejecución del job `rollback:produccion` | ⏳ |

## 3. Definición de Hecho transversal (§5.1)

| Criterio de la tesis | Evidencia | Veredicto |
|---|---|---|
| Código integrado en la rama principal a través del pipeline de CI/CD | PR `MES` → `staging` → `master` con los checks en verde | ⏳ |
| Superación de los análisis estáticos (flake8, bandit, detect-secrets) | Gates bloqueantes del `.gitlab-ci.yml`, todos en 0. Job `lint:backend`: Ruff (estilo y reglas de seguridad `S`, que reemplazan a flake8 y bandit; ADR-015), mypy y detect-secrets (ningún secreto nuevo y línea base auditada por completo). Job `sast:semgrep`: Semgrep. Job `test:frontend`: ESLint y `tsc`. Job `lint:istqb`: convención ISTQB | ✅ |
| Cobertura de pruebas automatizadas ≥ 75 % en el núcleo | 92,5 % del backend sobre SQL Server (1944 pruebas), con un gate de 90 % en el CI (`.coveragerc`). Microservicios con gates de 95 % (`printing_service`: 98,6 %), 90 % (`reporting_excel`: 98,3 %) y 90 % (`scanning_service`: 94,0 %). Frontend (1981 pruebas) con 95,4 % de sentencias, 90,2 % de ramas, 93,7 % de funciones y 96,5 % de líneas | ✅ |
| Registro de auditoría en las operaciones críticas | TEX-09 (auditoría inmutable) y TEX-10 (justificación obligatoria), en `EVIDENCIA_POR_SPRINT.md` Sprint 1 | ✅ |
| Despliegue verificado en el ambiente de staging | Despliegue en staging con la suite en verde | ⏳ |

## 4. Requerimientos no funcionales (Tablas 6 a 10)

| RNF | Métrica de la tesis | Evidencia | Veredicto |
|---|---|---|---|
| RNF-01 | Autenticación vía JWT | TEX-06: cookies `HttpOnly`, `SameSite=Lax` y `Secure` en producción (`Set-Cookie` del login en `sprint-0/2026-10-13_nginx-https.txt`) | ✅ |
| RNF-01 | Datos sensibles encriptados | **En tránsito:** TLS 1.2 y 1.3 con HSTS en el puerto 443 (TLS 1.0 y 1.1 rechazados), y el puerto 80 solo redirige (301) a HTTPS: `sprint-0/2026-10-13_nginx-https.txt`, `gestion/tests/test_nginx_redireccion_https.py`. Las cookies de sesión, CSRF y JWT solo viajan por HTTPS (`gestion/tests/test_cookies_seguras_produccion.py`). **Credenciales:** contraseñas con el hash de Django. El cifrado de la base en reposo (TDE) no forma parte de la configuración evaluada | ✅ |
| RNF-01 | RBAC aplicado al 100 % de los endpoints | `DEFAULT_PERMISSION_CLASSES = IsAuthenticated` y `gestion/tests/test_permisos_por_defecto.py`, que recorre todas las vistas y exige permisos declarados; `scripts/auditar_permisos_backend.py` lista cada ruta con su permiso (de clase o por acción) y su filtro de sede (`gestion/tests/test_auditoria_permisos_script.py`) | ✅ |
| RNF-02 | 100 % de funcionalidades con autenticación; autorización por rol en todas las operaciones; pruebas de acceso no autorizado | **Autenticación:** el anónimo recibe 401/403 en todas las rutas salvo las 6 públicas justificadas, y las escrituras con la cookie exigen el token CSRF. **Acceso no autorizado:** en cada ruta de objeto, los 9 roles acotados a una sede no acceden a objetos de otra sede (`gestion/tests/test_acceso_no_autorizado_global.py`). **Rol y sede por módulo:** TEX-07, TEX-08, TEX-23, TEX-49 y TEX-50, `gestion/tests/test_control_acceso_sede.py` e `inventory/tests/test_control_acceso_bodegas.py`. En el stack, el escaneo sin sesión responde 401 y el de otra sede, «no encontrado» | ✅ |
| RNF-03 | Microsoft SQL Server; consultas de inventario y producción < 3 s; escaneo QR < 2500 ms | SQL Server 2022; con 100 y 250 usuarios concurrentes, p95 del escaneo de 89 y 200 ms; panel de planta de 220 y 380 ms; kárdex de 610 y 390 ms (`EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §3) | ✅ |
| RNF-04 | Núcleo y tres módulos internos desplegables e independientes | El compose de producción despliega `scanning_service`, `printing_service` y `reporting_excel`, cada uno con su imagen, contenedor y `HEALTHCHECK` | ✅ |
| RNF-05 | Tareas frecuentes (registro de lote, escaneo) ≤ 3 pasos | Grabaciones numeradas del registro de lote, el escaneo y el pesaje (`EVIDENCIA_RENDIMIENTO_USABILIDAD.md` §4) | ⏳ |
| RNF-05 | Capacitación máxima de 2 horas para usuarios operativos | Se ejecuta en la puesta en marcha de marzo de 2027 (§5.4) | 📅 |

## 5. Plan de despliegue con enfoque CI (§5.3)

| Afirmación de la tesis | Situación del sistema | Veredicto |
|---|---|---|
| Pipeline configurado en GitLab CI; imágenes en GitLab Container Registry | `.gitlab-ci.yml` en un GitLab CE autoalojado con su Container Registry (`infrastructure/gitlab/`, `GUIA_GITLAB.md`, ADR-014). GitHub es solo un espejo y no ejecuta nada | ✅ en configuración · ⏳ primera ejecución en el servidor |
| Validación de sintaxis y formato con flake8 y detección de vulnerabilidades con bandit | Ruff con las reglas de estilo y de seguridad `S`, además de mypy y Semgrep (ADR-015) | ❌ como está redactado: única corrección de redacción del pipeline (`CORRECCIONES_TESIS.md` §5) |
| Escaneo de secretos con detect-secrets | Dos pasos bloqueantes en `lint:backend`: ningún secreto nuevo en los archivos versionados y línea base auditada | ✅ |
| Base de datos efímera para pruebas unitarias y de integración (Pytest y Django) | SQL Server 2022 como servicio del job `test:backend` | ✅ |
| Umbral de cobertura mínimo del 75 % para la mezcla | Gate del 90 % en el backend | ✅ |
| Imágenes de Backend, Frontend y microservicios | 6 imágenes: backend, nginx con el frontend, los 3 microservicios y la base de datos; el release las construye sin caché y las despliega por digest, firmadas con cosign | ✅ |
| Despliegue automático a staging | No hay servidor de staging permanente: `staging:efimero` levanta un **staging efímero** con las 6 imágenes del release y un SQL Server desechable, migra desde cero y corre las pruebas de humo de los 11 roles antes de habilitar el despliegue de producción | ✅ en configuración · ⏳ ejecución (primer merge a `master`) |
| Producción en Ubuntu Server (Hyper-V) con Gunicorn y Nginx | Compose de producción con Gunicorn (20 workers) detrás de Nginx; dimensionamiento en `docs/arquitectura/REQUISITOS_INFRAESTRUCTURA.md` | ✅ en configuración · ⏳ despliegue |
| Rollback manual con un solo clic | Job manual `rollback:produccion` (un clic; `ROLLBACK_SHA` y `ROLLBACK_MOTIVO` al lanzarlo) | ⏳ ejecución |

## 6. Puesta en marcha (§5.4)

| Afirmación de la tesis | Veredicto |
|---|---|
| Pruebas integrales y preparación de preproducción en febrero de 2027 | 📅 |
| Sincronización del servidor con las impresoras Zebra y el hardware óptico | 📅 |
| Talleres y capacitaciones de máximo 2 horas por grupo | 📅 |

## 7. Ceremonias de Scrum (§5.1)

| Ceremonia | Evidencia aceptable | Veredicto |
|---|---|---|
| Sprint Planning | Tablero y burndown por sprint en Jira (`docs/gestion-proyecto/texcore_jira_import.csv`) | ⏳ |
| Sprint Review | Acta breve por sprint: fecha, asistentes, incremento y acuerdos, con confirmación de Interfibra | ⏳ |
| Sprint Retrospective | Qué mejorar y qué se aplicó, con el CHANGELOG como respaldo | ⏳ |
| Trabajo por sprint | `git log --since=<inicio> --until=<fin> --oneline` para cada rango de la Tabla 14 | ⏳ |

## 8. Cómo completar lo pendiente

| Punto ⏳ | Qué generar | Dónde |
|---|---|---|
| TEX-04 y la integración por CI/CD | Captura de un pipeline de `.gitlab-ci.yml` con todos los jobs en verde | GitLab (CI/CD > Pipelines) |
| RNF-05 | Grabaciones del registro de lote (TEX-12), el escaneo y el pesaje (TEX-41), numerando cada paso; capturas del panel ejecutivo a 375, 768 y 1366 px (TEX-46) | Navegador contra el stack |
| TEX-54 y staging | `git tag -a v1.0.0-rc1`, protección de `master` y `staging`, despliegue en staging y ejecución de `rollback:produccion` | GitLab |
| Ceremonias | Actas, capturas de Jira y `git log` por sprint | — |
