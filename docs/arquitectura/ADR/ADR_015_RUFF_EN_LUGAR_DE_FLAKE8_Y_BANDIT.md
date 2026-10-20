# ADR-015 — Ruff como analizador estático único de Python, en lugar de flake8 y bandit (TexCore)

> Numeración continua con ADR-014 (`ADR_014_GITLAB_CI_AUTOALOJADO.md`).
**Tema:** Herramienta de análisis estático (estilo, errores y seguridad) del código Python
**Fecha:** 5-oct-2026 (decisión y migración), registrado el 20-oct-2026 · **Estado:** Aceptada · **Origen:** plan de modernización del CI/CD, Fase 2

## 1. Contexto

La tesis (§5.1, p. 65, y §5.3, p. 68–69) define como análisis estáticos del pipeline **flake8** (sintaxis y formato), **bandit** (vulnerabilidades) y **detect-secrets** (secretos expuestos). Al medir el estado real antes de cambiar nada (Ruff 0.16.10 sobre los 378 archivos `.py` del repositorio, sin `migrations/`):

- **El lint no cubría todo el código.** El CI corría flake8 solo sobre los 4 paquetes del núcleo (`gestion/`, `inventory/`, `TexCore/`, `internal_api/`). Sobre los 3 microservicios y `scripts/`, flake8 daba **48 violaciones** que nadie veía.
- **Dos herramientas con dos configuraciones.** flake8 y bandit se configuraban por separado, y la del CI no coincidía con la del pre-commit.
- **flake8 solo mira estilo y errores de sintaxis.** Defectos reales del código pasaban sin aviso. Ejemplos medidos:
  - una clave duplicada en un diccionario (`F601`);
  - 30 `raise` sin `from` que pierden la causa original;
  - 22 `logger.error` dentro de un `except`, que dejan el log sin la traza;
  - `os.path` bloqueante dentro de funciones `async` de los 3 microservicios;
  - `datetime.date.today()` en el cálculo de la cartera vencida, que con UTC−5 cambia de día a las 19:00;
  - 9 funciones con complejidad ciclomática mayor que 15.

## 2. Decisión

**Ruff es el analizador estático único de Python.** Se configura una sola vez en `pyproject.toml`, y la misma configuración corre en el pipeline y en el pre-commit:

| Lo que hacía | Lo hace ahora |
|---|---|
| flake8 (pycodestyle + pyflakes) | Ruff, reglas `E`, `W` y `F` |
| bandit | Ruff, reglas `S` (las mismas comprobaciones de bandit) |
| — | Ruff, reglas que detectan defectos: `B` (bugbear), `DJ` (Django), `DTZ` (fechas sin zona), `BLE`, `TRY400`, `ASYNC`/`FAST`, `PERF`, `SIM`, `RET`, `C4`, `PTH`, `PIE` y `C901` (complejidad ≤ 15) |
| — | `ruff format`, el formateador, como gate (`ruff format --check`) |
| detect-secrets | Se queda: Ruff no busca secretos |
| — | mypy (tipos) y Semgrep (SAST) se suman como gates, porque Ruff no verifica tipos ni flujos de datos |

Condiciones de la migración, todas cumplidas:

1. **Sin regresión:** todo lo que flake8 rechazaba, Ruff lo sigue rechazando. Se verificó corriendo las dos herramientas sobre el mismo árbol, ambas en 0.
2. **Cada regla nueva entró con 0 violaciones:** las existentes se corrigieron en la misma etapa, sin una «línea base» que escondiera deuda.
3. **Cada regla descartada está justificada** en `pyproject.toml`. Ejemplo: `RUF012` es un falso positivo con los atributos de clase de Django y DRF.

## 3. Por qué es mejor opción

1. **Una herramienta en lugar de dos.** Cubre lo de flake8 y lo de bandit, más el orden de imports y el formateo. Una sola configuración y una sola versión que mantener.
2. **Cubre todo el código.** Revisa el 100 % del Python del repositorio con las mismas reglas: núcleo, 3 microservicios y scripts. Con flake8 quedaban fuera los microservicios y los scripts.
3. **Detecta defectos, no solo estilo.** Las reglas adicionales encontraron y permitieron corregir defectos reales:
   - una fecha de pedido que salía mal porque usaba `timezone.utc`, eliminado en Django 5.0;
   - una vista que respondía 500 ante una cantidad no numérica;
   - el detalle interno de las excepciones expuesto en los errores 500 del `printing_service` (CWE-209).
4. **Rápido.** Está escrito en Rust y revisa unos 400 archivos en segundos, así que el gate no alarga el pipeline.
5. **Mantenido y estándar.** Es la herramienta de lint de Python más adoptada hoy, con publicaciones frecuentes. Reemplaza a una cadena de complementos de flake8 que había que alinear entre sí.

## 4. Consecuencias

- **Texto de la tesis.** §5.1 (DoD) y §5.3 (fase de análisis estático) nombran flake8 y bandit. Hay que cambiarlos por «Ruff (estilo, errores y reglas de seguridad), mypy, Semgrep y detect-secrets». El objetivo que describe la tesis, una barrera de estilo, seguridad y secretos en el pipeline, se mantiene y queda ampliado. Texto propuesto en `docs/gestion-proyecto/evidencia/CORRECCIONES_TESIS.md` §5.
- **Marcadores de excepción.** Los `# nosec` de bandit pasaron a `# noqa: Sxxx`, con el motivo en el mismo comentario.
- **Formateo masivo.** El reformateo de `ruff format` (389 archivos, 14-oct-2026) es solo de forma, sin cambio de comportamiento. Se registra en `.git-blame-ignore-revs` para que `git blame` lo salte.
