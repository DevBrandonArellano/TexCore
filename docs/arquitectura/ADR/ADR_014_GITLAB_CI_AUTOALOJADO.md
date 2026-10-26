# ADR-014 — GitLab CI autoalojado como plataforma principal; GitHub como espejo (TexCore)

> Numeración continua con ADR-013 (`ADR_013_PARO_AUTOMATICO_POR_ESTADO.md`).
**Tema:** Dónde corre el pipeline de CI/CD y dónde se guardan las imágenes
**Fecha:** 20-oct-2026 · **Estado:** Aceptada (decisión del usuario) · **Origen:** cumplir lo que dice la tesis (§5.3) y dejar de explicarlo como una corrección

## 1. Contexto

La tesis define el despliegue con un pipeline «configurado a través de **GitLab CI**» (p. 46, §5.3 y p. 78), las imágenes en el «**GitLab Container Registry**», un ambiente de staging con despliegue automático y producción con rollback manual de un clic.

El historial del repositorio:

- Existió un `.gitlab-ci.yml` (7 stages: lint, test, build, scan, deploy, health-check, rollback).
- El 5-oct-2026 se retiró (commit `a65ff02`, «no se usaba y divergía») porque el proyecto vivía en GitHub y mantener dos pipelines producía divergencias medidas (A-1 del plan de modernización: versiones de Node distintas y solo GitLab escaneaba los satélites).
- Desde entonces el CI/CD corrió en GitHub Actions (`ci.yml`, `release.yml`, `rollback.yml`, `security.yml`, `gobierno.yml`).
- Resultado: la tesis y el sistema se contradecían, y la salida era corregir el texto de la tesis.

## 2. Decisión

**GitLab CE autoalojado es la plataforma principal del CI/CD y del registro de imágenes; GitHub queda como espejo de solo lectura del código.** No hay dos pipelines.

| Pieza | Decisión |
|---|---|
| Servidor | GitLab CE en el equipo de staging (192.168.1.55, red de Interfibra), con certificado propio. Puertos 8929 (web), 5050 (Container Registry) y 2224 (SSH) |
| Pipeline | `.gitlab-ci.yml` en la raíz: `lint → test → build → scan → staging → deploy → rollback` |
| Registro | GitLab Container Registry; las 6 imágenes por digest |
| Runners | `texcore-ci` (lint y pruebas, sin socket de Docker), `texcore-staging` (construcción y staging efímero, solo ramas protegidas) y `texcore-produccion` (VM de Hyper-V, solo `master`) |
| Producción | Job manual `deploy:produccion` y job manual `rollback:produccion` («un solo clic»), ambos en el runner propio, sin SSH |
| Firma | cosign con par de claves (`cosign.pub` en el repositorio; la privada, como variable protegida) |
| Dependencias | Renovate como pipeline programado, en lugar de Dependabot |
| Espejo | *Push mirror* de GitLab a GitHub |

## 3. Por qué no se repite la divergencia del 5-oct

1. **Un solo pipeline.** Los workflows de GitHub Actions y Dependabot se borraron en el mismo cambio. El espejo no ejecuta nada.
2. **Misma paridad que ya tenía Actions**, comprobada por pruebas (`gestion/tests/test_despliegue_produccion.py` lee `.gitlab-ci.yml`): 6 imágenes sin caché, firma y atestación, staging antes del deploy, deploy y rollback manuales en el runner propio, imágenes de los jobs fijadas por digest.
3. **Se conserva lo ganado desde el 5-oct:** Trivy por digest con bloqueo, escaneo de los 3 satélites, `pip-audit` y `npm audit` bloqueantes (en el GitLab antiguo eran `allow_failure`), SQL Server de pruebas por digest, Ruff como gate (ADR-015) y el gate ISTQB.

## 4. Consecuencias

- **Firma con clave en lugar de keyless.** La firma sin clave de Sigstore exige un emisor OIDC público; un GitLab interno no lo es. Se firma con un par de claves (`cosign sign --key`) y se verifica con `cosign.pub` en el deploy y el rollback, sin registro de transparencia público. La clave privada y su contraseña son variables protegidas y enmascaradas; hay que rotarlas según `SECURITY.md`.
- **OpenSSF Scorecard** y la atestación de procedencia de GitHub no existen en GitLab. La procedencia pasa a ser un predicado SLSA firmado con cosign; Scorecard queda fuera y se anota en `AUDITORIA_CALIDAD.md`.
- **Dependabot → Renovate.** El mismo alcance (Dockerfiles, compose, requirements, npm, el pipeline) y los MR hacia `staging`.
- **Métricas DORA** pasan a la API de GitLab (`scripts/metricas_dora.py`).
- **Un servidor más que mantener** en el equipo de staging: respaldo diario de GitLab, actualizaciones deliberadas (versión y digest fijos) y disponibilidad. Se registra en `REGISTRO_RIESGOS.md` (RS-23 y RS-24).
- **Memoria.** El equipo (16 GB) comparte GitLab (límite de 6 GB) con el stack de TexCore. Por eso el staging sigue siendo **efímero**: se levanta con las 6 imágenes, se prueba y se baja dentro del pipeline.
- **Texto de la tesis.** Las filas de `CORRECCIONES_TESIS.md` sobre GitLab CI y GitLab Container Registry pasan a «se cumple, sin corrección». Queda una sola corrección de redacción en el pipeline: flake8 y bandit por Ruff (ADR-015).
