# Plan detallado — Migración de flake8 a Ruff

> **Fecha:** 5-oct-2026 · **Estado:** Etapas 1 a 4 **hechas** el 5-oct-2026 (Ruff en 0 con todas sus reglas, incluidas Django y complejidad ≤ 15; bandit retirado). Etapa 5 (formateador) pendiente hasta el merge de `MES` a `staging` · **Rama:** `MES`.
> Es parte del plan de CI/CD (`2026-10-05-modernizacion-ci-cd.md`, Fase 2).
> **Medición:** Ruff 0.16.10 sobre los 378 archivos `.py` del repositorio (sin `migrations/`), en un entorno virtual
> aislado. Todas las cifras de este documento salen de esa corrida, no de estimaciones.

## 1. Objetivo

Reemplazar flake8 y bandit por **Ruff** como linter único de Python y aprovechar sus reglas para detectar defectos
reales, no solo estilo. Condiciones:

- **Sin regresión:** todo lo que flake8 rechaza hoy, Ruff lo sigue rechazando.
- **Cada regla nueva entra con 0 violaciones.** Se corrigen las existentes en la misma etapa; nada de «línea base» que
  esconda deuda.
- **Cada regla descartada queda justificada** en este documento y en el `pyproject.toml`.

## 2. Qué se toca (inventario completo)

| # | Archivo | Cambio |
|---|---|---|
| 1 | `pyproject.toml` (nuevo, en la raíz) | `[tool.ruff]` con `line-length = 120`, `target-version = "py312"`, `extend-exclude = ["**/migrations"]`, reglas y `per-file-ignores`. Es la única configuración de lint del repo. |
| 2 | `printing_service/pyproject.toml` (nuevo) | `extend = "../pyproject.toml"` con `target-version = "py311"`, mientras ese servicio siga en Python 3.11 (CI/CD Fase 5 lo sube a 3.12; entonces se borra). |
| 3 | `.pre-commit-config.yaml` | Se reemplazan los hooks `flake8` y `bandit` por `astral-sh/ruff-pre-commit` (`ruff-check --fix`). `pre-commit-hooks` sube de v4.6.0 a la versión vigente. `detect-secrets` se queda. |
| 4 | `.github/workflows/ci.yml`, job `backend-lint` | Se quitan `flake8` y `bandit` del `pip install` y sus dos pasos. Entra `ruff check --output-format=github .`, que anota cada violación en la línea del PR. Se suma un reporte SARIF para la pestaña Security. `detect-secrets` y `mypy` se quedan: Ruff no verifica tipos. |
| 5 | Código Python | 3 marcadores `# nosec` pasan a `# noqa: Sxxx`, porque Ruff no lee `nosec`: `gestion/views/sales_views.py:486,567` (B104 → S104) y `printing_service/src/routers/zpl.py:18` (B701 → S701). Los 17 `# noqa` existentes (E402, F401, F403) siguen siendo válidos; RUF100 avisará si alguno sobra. |
| 6 | Documentación vigente | `docs/arquitectura/ESTANDARES_DESARROLLO.md` §148 (gate de flake8), `README.md` (fila «Pruebas y Calidad», que además tiene cifras viejas: umbral 89 % y 998 pruebas), `docs/matriz_trazabilidad_pruebas.md` y la memoria `cero-deuda-tecnica`, que cita los flags de flake8. Las entradas antiguas del CHANGELOG, los planes y las specs conservan el nombre de su época. |
| 7 | `.gitlab-ci.yml` | No se toca: se elimina en la Fase 0 del plan de CI/CD. |
| 8 | Dependencias | Ruff no entra a `requirements.txt` (no es de runtime). La versión se fija en la `rev` de pre-commit y en el `pip install ruff==X` del CI; Dependabot actualiza ambas. |

**No se toca:** `setup.cfg` (solo tiene pytest), `.coveragerc`, `mypy`, `detect-secrets` ni Semgrep.

### Hallazgo de alcance: hoy el lint no cubre todo el código
- El CI corre flake8 solo sobre `gestion/ inventory/ TexCore/ internal_api/`.
- El pre-commit también incluye los 3 microservicios. Pero sobre ellos y sobre `scripts/` flake8 reporta **48 violaciones**, así que **nadie está corriendo el pre-commit**.
- Con Ruff, el CI pasa a lintar **todo** el Python del repo con una sola configuración, y el pre-commit deja de divergir.

## 3. Medición: violaciones por familia de reglas

Las cifras son todo el código sin `migrations/`. El autofix es seguro (`--fix`), sin `--unsafe-fixes`.

| Familia | Qué detecta | Total | Autofix | Producción* |
|---|---|---:|---:|---:|
| **E, W, F** (paridad flake8) | estilo PEP 8 y errores de pyflakes | 40 | 29 | — |
| **I** (isort) | orden de imports | 268 | 268 | 129 |
| **UP** (pyupgrade) | sintaxis moderna de 3.12 (`X \| None`, `list[int]`, `datetime.UTC`) | 144 | 138 | 138 |
| **B** (bugbear) | bugs probables | 60 | 0 | 49 |
| **S** (bandit) | seguridad | 551 | 0 | 5 tras las excepciones de §4 |
| **DTZ** | fechas sin zona horaria | 88 | 0 | 2 |
| **BLE** | `except Exception` sin reraise | 47 | 0 | 42 |
| **ASYNC / FAST** | bloqueos en `async` y FastAPI | 26 | 0 | 23 |
| **DJ** | Django | 54 | 0 | 54 |
| **G / LOG** | logging | 88 | 0 | 88 |
| **TRY400** | `logger.error` en un `except` (pierde la traza) | 22 | 0 | 22 |
| **T20** | `print` | 34 | 0 | 18 |
| **SIM, RET, C4, PERF, PIE** | simplificaciones | 43 | 16 | 33 |
| **PTH** | `os.path` → `pathlib` | 32 | 0 | 26 |
| **ERA** | código comentado | 6 | 0 | 2 |
| **RUF** (100, 059, 010, 005, 022, 013) | `noqa` sin uso, f-strings, variables desempaquetadas sin uso, `Optional` implícito | 52 | 32 | 27 + RUF100 |
| **C901** (complejidad > 15) | funciones demasiado complejas | 9 | 0 | 9 |

\* Producción = sin `tests/`, `test_*.py` ni `conftest.py`.

### Defectos reales que Ruff ya encontró y flake8 no
1. **F601 — clave duplicada** en `gestion/management/commands/stress_test_data.py:441` y `:450`: `'area': area` aparece dos veces en el mismo `defaults`. pyflakes solo lo reporta si los valores difieren; Ruff lo reporta siempre.
2. **B904 (30 casos)** — `raise` dentro de un `except` sin `from`: se pierde la causa original en la traza.
3. **TRY400 (22)** — `logger.error(...)` dentro de un `except`: el log no incluye el *stack trace*; `logger.exception` sí lo incluye.
4. **BLE001 (42)** — `except Exception` que no relanza: hay que revisar cuáles ocultan errores. Algunos son legítimos, como los handlers de último nivel.
5. **ASYNC240 (3)** — `os.path` bloqueante dentro de una función `async` en el `engine.py` de los 3 microservicios: bloquea el *event loop* de FastAPI.
6. **DTZ011 (2)** — `datetime.date.today()` en `gestion/serializers/sales_serializers.py:332` y `:380` (cartera vencida y fecha de vencimiento). Usa la fecha del sistema operativo y no la de Django (`timezone.localdate()`). Con `TIME_ZONE = 'UTC'` hoy coinciden, pero en Ecuador (UTC−5), a partir de las 19:00 hora local, «hoy» ya es el día siguiente. **Requiere una decisión de negocio** (§6).
7. **S701 — `printing_service/src/routers/zpl.py:18`**: Jinja sin autoescape. **Corrección (Etapa 3):** la inyección ZPL ya estaba mitigada y probada — `ZplOutputStrategy.render` pasa el contexto por `zpl_sanitizer`, que elimina `^` y `~` (`tests/unit/test_zpl_sanitizer.py`). Este plan lo había marcado como riesgo por mirar solo el router; queda como `noqa: S701` con el motivo.
8. **C901 — 9 funciones con complejidad > 15**: `registrar_operacion` (47, `gestion/services/ejecucion_produccion.py`), `registrar_lote` (29), `resolve_report` (23), `reporting_proxy.get` (23), `despacho_views._procesar` (23), `transform_view.post` (21), `production_lote_views.get_queryset` (18), `core._get_object_sede_id` (17) y `stress_test_data.handle` (91, un comando de carga).

## 4. Reglas descartadas (y por qué)

| Regla | Total | Motivo |
|---|---:|---|
| `Q`, `COM` (comillas, comas finales) | 17 259 | Son formato, no lint: si se adopta `ruff format` (§6), el formateador las resuelve. |
| `D` (docstrings) | 4 558 | Exigir docstrings en todo, incluidas las pruebas, es ruido. Se reconsidera para la API pública de los servicios. |
| `PT009`, `PT027` | 2 905 | Las pruebas de Django usan `TestCase` (`self.assertEqual`). La regla es para pytest puro y no aplica. |
| `RUF012` | 288 | Falso positivo en Django y DRF: `fields = [...]`, `permission_classes = [...]` y `Meta` son atributos de clase por diseño. |
| `ARG001`, `ARG002` | 180 | Las firmas de DRF y Django exigen `request`, `*args` y `**kwargs` aunque no se usen. |
| `PLC0415` (import local) | 261 | Se usa a propósito para evitar imports circulares entre apps de Django. |
| `PLR2004` (números mágicos) | 130 | Mucho ruido en reglas de negocio (porcentajes, 100 %, tolerancias). |
| `TRY003`, `EM101`, `EM102` | 264 | Estilo de mensajes de excepción; poco valor con mensajes en español para el usuario. |
| `FBT`, `TID252`, `N` | 146 | Convenciones existentes y consistentes (imports relativos en los servicios, nombres de clases en las pruebas). |
| `PLR0911-0917` | 79 | Las cubre `C901`, con un solo umbral más claro. |
| `S311` en comandos de carga y scripts | 179 | `random` para generar datos de prueba no es criptografía. Se ignora solo en `management/commands/stress_*`, `load_million.py` y `scripts/loadtest/`. |
| `S101`, `S105`, `S106` en pruebas | ~350 | `assert` y contraseñas de fixture son normales en pruebas: se ignoran en `**/tests/**`. |

## 5. Ejecución por etapas

Cada etapa es un commit propio en `MES`, con el CI en verde y las suites completas en verde (backend con
`settings_test_local` y los 3 microservicios). Ninguna etapa cambia comportamiento salvo la 3, que lleva pruebas
nuevas antes del cambio.

### Resultado de las Etapas 1-3 (5-oct-2026)
- **Etapa 1:** paridad con flake8 (reglas *preview* de pycodestyle listadas explícitamente), Ruff en CI y pre-commit sobre todo el repo.
- **Etapa 2:** `I`, `UP`, `RUF100`, `RUF010`, `RUF022` — 427 correcciones automáticas; migraciones sin cambios, suites en verde.
- **Etapa 3:** `B`, `S`, `BLE`, `DTZ`, `ASYNC`, `FAST`, `TRY400`, `LOG`, `G`, `T20`, `RUF059` en 0. **Bandit retirado** del CI y del pre-commit (lo cubren las reglas `S`).
  - Defecto real: `_fecha_pedido_to_iso_utc` usaba `timezone.utc`, eliminado en Django 5.0; el error quedaba tragado y la fecha del pedido salía en el formato de respaldo. Corregido con 6 pruebas.
  - Prueba que no probaba nada: «fallo intermedio» de la reversión de despacho usaba un detalle sin lote, que la reversión salta sin fallar. Reescrita con un fallo real y comprobación del rollback.
  - CWE-209 en `printing_service`: los 8 endpoints devolvían `str(exc)` en el 500. Ahora responden un mensaje genérico; el detalle queda en la auditoría. Con prueba.
  - Código muerto eliminado: `reporting_excel/src/services/excel_generator.py` (duplicado de `ExcelFormatter`) con su prueba, y `scripts/tests/test_pd.py`.
  - Excepciones acotadas: auditoría de microservicios → `SQLAlchemyError`; formateadores → `ValueError`/`TypeError`; JWT → `PyJWTError`; `chmod` del SQLite fuera del event loop (`asyncio.to_thread`).
  - **`ERA` descartada:** sus 6 hallazgos eran comentarios explicativos (`# BVA: severity = 3`), no código muerto.
  - Incidente del proceso (corregido y verificado): un script propio de conversión G004 calculó posiciones en bytes UTF-8 y dañó llamadas de log en 22 archivos; se reconstruyeron desde `HEAD` y se verificó que ningún mensaje cambió. Un `ruff --fix --select RUF100` acotado borró `noqa` legítimos —incluido el `import gestion.signals` de `apps.py`, que el siguiente `--fix` eliminó—; se restauraron todos contra `HEAD`.

### Resultado de la Etapa 4 (5-oct-2026)
- **Reglas activas:** `DJ`, `SIM`, `RET`, `C4`, `PERF`, `PTH`, `PIE` y `C901` (`max-complexity = 15`). Ruff en 0.
- **DJ012:** miembros de 7 archivos de modelos reordenados por bloques (verificado: mismas líneas, `makemigrations --check` sin cambios).
- **DJ001:** los 32 `CharField`/`TextField` con `null=True` pasan a `blank=True, default=''`. Ninguno era `unique`, así que no hubo excepciones. Migraciones `gestion/0003_cadenas_vacias_sin_null` e `inventory/0002_cadenas_vacias_sin_null`: primero convierten los `NULL` en `''` y después alteran la columna. Ningún índice nativo (V2/V4/V5) usa esas columnas.
  - Escritores que mandaban `None` corregidos: auditoría (`AuditLog.justificacion` en el mixin y las señales), `registro_lote` (`tipo_merma`), `transferencia_views` (`documento_ref`), `load_million`, y el frontend (`|| null` → `|| ''` en productos, químicos y líneas), con sus pruebas.
  - **Pendiente de verificar en SQL Server:** el CI la ejecuta sobre SQL Server 2022 al crear la BD de pruebas. Falta probarla sobre una base con datos (un respaldo de producción) antes del despliegue.
- **C901 — 10 funciones refactorizadas**, cada una cubierta antes con pruebas de caracterización y verificada contra `HEAD`:
  - `registrar_operacion` (47) y `registrar_lote` (29): un paso por fase. `registrar_lote` ahora corre la sincronización MES en su propio *savepoint*. Antes, un error de BD dentro de ese bloque *best-effort* dejaba la transacción del lote inservible; la prueba nueva falla contra `HEAD`.
  - `stress_test_data.handle` (91): dividido en pasos. Una huella determinista (`random.seed`) dio resultados idénticos antes y después. Después se quitó un `random.random()` sin uso y la rama `DEVOLUCION`, que nunca se elegía. Tiene una prueba de humo permanente.
  - `transform_view.post`: una `cantidad` no numérica caía en el `except` genérico y respondía **500**; ahora responde 400 (con prueba).
  - `generar_docx.convertir`: el `.docx` sale idéntico byte a byte. Había un bucle infinito latente con una línea `| x` sin separador de tabla; quedó corregido.
  - `resolve_report` (tabla de despacho), `reporting_proxy.get`, `despacho_views._procesar` (más pruebas de sus ramas de error), `production_lote_views.get_queryset` y `core._get_object_sede_id` (tabla de relaciones).
- Quedan 11 funciones entre 11 y 15 de complejidad. Bajar el umbral a 10 es una mejora opcional, no una deuda del plan.
- Decisión documentada en **ADR-008** (`docs/arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md`). Riesgo de despliegue RD-05 en `docs/requerimientos/REGISTRO_RIESGOS.md`.

### Etapa 1 — Paridad y cambio de herramienta (½ día)
1. Crear `pyproject.toml` solo con `E`, `W`, `F` y `line-length = 120`.
2. Corregir las 40 violaciones: 29 con `--fix`; las demás (E501, E402 y la F601) a mano.
3. Pre-commit y CI con Ruff; se quitan flake8 y bandit; los 3 `nosec` pasan a `noqa`.
4. **Verificación de paridad:** correr flake8 y Ruff sobre el mismo árbol; ambos deben dar 0.

### Etapa 2 — Reglas con autofix seguro (½ día)
- `I` (268), `UP` (138 de 144; los 6 `UP035` restantes, a mano) y `RUF100`, `RUF010` y `RUF022`, con `ruff check --fix`. Es un cambio mecánico y grande en archivos tocados: va en un commit aparte para que la revisión sea solo de forma.
- Ese commit se registra en `.git-blame-ignore-revs` para que `git blame` lo salte.

### Etapa 3 — Reglas que detectan defectos (1–2 días)
`B`, `S` (con las excepciones de §4), `BLE`, `DTZ`, `ASYNC`, `FAST`, `TRY400`, `LOG`, `G`, `T20` (salvo `scripts/`), `ERA` y
`RUF059`. Cada corrección va con TDD cuando cambia comportamiento:
- **B008 / FAST002** en los routers de FastAPI: pasar a `Annotated[..., Depends(...)]`, el estándar actual de FastAPI. Se resuelven juntas.
- **B904:** `raise ... from exc`.
- **TRY400:** `logger.exception`.
- **G004:** logging con `%s` en lugar de f-strings, para que el logger RFC 5424 agrupe por mensaje.
- **ASYNC240:** mover el `os.path` fuera del `async` o usar `anyio.Path`.
- **BLE001:** revisar los 42 uno por uno: los legítimos llevan `# noqa: BLE001` con el motivo; el resto se acota a la excepción concreta.
- **S701 ZPL:** filtro de escape de `^` y `~` con su prueba de inyección.
- **DTZ011:** según la decisión de §6.

### Etapa 4 — Django, simplificaciones y complejidad (2–3 días)
- **`DJ012`** (orden de los miembros del modelo) y **`SIM`, `RET`, `C4`, `PERF`, `PTH`**.
- **`DJ001`** (32 `CharField` con `null=True`): corregirlo exige **migraciones** que cambian columnas en SQL Server. Va solo con decisión explícita (§6); si no se aprueba, se excluye en `pyproject.toml` con el motivo.
- **`C901` con `max-complexity = 15`:** refactorizar las 8 funciones de producción, extrayendo pasos a funciones o servicios (SRP) y cubriendo antes con pruebas de caracterización. `registrar_operacion` (47) y `registrar_lote` (29) son el núcleo de producción: cada una va en su propio commit. `stress_test_data.handle` es un comando de carga; se divide igual o se excluye con el motivo.

### Etapa 5 — Formateador (opcional, ver §6)
- `ruff format` sobre todo el repo, `ruff format --check` en el CI y el commit en `.git-blame-ignore-revs`.
- Conviene hacerlo **después** del merge de `MES` a `staging`, porque toca casi todos los archivos y generaría conflictos con el trabajo en curso.

## 6. Decisiones del usuario (5-oct-2026)

1. **DTZ011 — «hoy» se mantiene en UTC.** `TIME_ZONE = 'UTC'` no cambia. Los 2 `datetime.date.today()` de `sales_serializers.py` pasan a `timezone.now().date()` (fecha UTC de Django, no la del sistema operativo), con su prueba en la Etapa 3.
2. **DJ001 — se corrige con una migración propia:** los 32 `CharField` con `null=True` pasan a `blank=True, default=''`, con una migración de datos que convierte los `NULL` en `''` antes de cambiar la columna. Va en su propio commit y se verifica en SQL Server. **Excepción a revisar campo por campo:** un `CharField` `unique=True` y `null=True` admite varias filas con `NULL` pero no varias con `''`; esos campos conservan `null=True` con `# noqa: DJ001` y su motivo.
3. **Formateador — sí:** `ruff format` y `ruff format --check` en el CI, en la Etapa 5, después del merge de `MES` a `staging`.

## 7. Criterio de cierre

- `ruff check .` en 0, con las reglas de §5 activas, en el CI y en el pre-commit.
- `flake8` y `bandit` eliminados de `ci.yml`, `.pre-commit-config.yaml` y la documentación vigente.
- Suites completas en verde: backend (1478 o más), los 3 microservicios y el frontend sin cambios.
- Cada exclusión de regla está justificada en `pyproject.toml` con un comentario.
