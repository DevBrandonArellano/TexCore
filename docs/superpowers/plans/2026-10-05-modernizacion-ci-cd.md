# Plan — Modernización del CI/CD de TexCore

> **Fecha:** 5-oct-2026 · **Estado:** Fases 0 y 1 **hechas**; Fase 2 **en curso** (gates de cobertura, SCA, Semgrep, mypy y Ruff etapas 1-3 hechos; Ruff etapas 4-5, ESLint y Tailwind 4 pendientes). Todo en `MES`, sin commitear; ver el CHANGELOG.
> **Plan hijo:** migración a Ruff, `2026-10-05-migracion-ruff.md`.
> **Alcance:** `.github/workflows/{ci,cd,security,rollback}.yml`, `.gitlab-ci.yml`, `.pre-commit-config.yaml`,
> Dockerfiles de los 5 servicios y `infrastructure/docker/docker-compose.prod.yml`.
> **Regla:** cero deuda técnica — cada fase se cierra con sus gates en verde, no con una lista de pendientes.

## 1. Principios de un buen pipeline (contra los que se evaluó)

| # | Principio | Qué exige en la práctica (estándar de la industria 2026) |
|---|---|---|
| P1 | **Una sola fuente de verdad** | Un único sistema de CI y una única definición por etapa. |
| P2 | **Los gates bloquean de verdad** | Si un control no puede fallar el pipeline, no es un control. Las excepciones se documentan con fecha de vencimiento. |
| P3 | **Feedback rápido y temprano (shift-left)** | Todas las ramas con trabajo corren CI; lint antes que tests; jobs con `timeout-minutes`. |
| P4 | **Lo que se verifica es lo que se despliega** | En el pipeline de `master` las imágenes se construyen desde cero y esa misma imagen, por **digest**, es la que se escanea, se prueba en el staging efímero y llega a producción. |
| P5 | **Dependencias inmutables** | Actions fijadas por SHA de commit; imágenes base por digest; actualizaciones automáticas (Dependabot o Renovate). |
| P6 | **Mínimo privilegio** | `permissions` por job; credenciales efímeras (OIDC) en lugar de llaves de larga vida. |
| P7 | **Cadena de suministro verificable** | SBOM, procedencia (SLSA nivel 2–3) y firma de imágenes (Sigstore/cosign) verificadas antes del deploy. |
| P8 | **Promoción entre entornos** | staging → producción con la misma imagen, smoke tests y aprobación en el *environment*. |
| P9 | **Despliegue y rollback seguros** | Migraciones *expand/contract*, respaldo previo, health checks y rollback probado. |
| P10 | **El pipeline también es código** | Lint del propio workflow (`actionlint`, `zizmor`), revisión con CODEOWNERS y métricas DORA. |

## 2. Inventario de tecnologías

| Capa | Tecnología actual |
|---|---|
| CI/CD | **GitHub Actions** (4 workflows, 1 339 líneas) **y GitLab CI** (`.gitlab-ci.yml`, 597 líneas) en paralelo |
| Backend | Python 3.12, Django + DRF, SQL Server 2022 (servicio `mssql/server:2022-latest` en CI), `manage.py test` + `coverage` (`fail_under = 90`) |
| Microservicios | FastAPI (`reporting_excel`, `printing_service`, `scanning_service`), pytest + `--cov-fail-under=80` |
| Frontend | React + TypeScript + Vite, Node 24, Vitest (umbrales 94/89/91/95), `tsc --noEmit`; sin ESLint operativo |
| Calidad estática | flake8 7.2, mypy 1.15 (informativo), pre-commit (flake8, bandit, detect-secrets) |
| Seguridad | bandit, detect-secrets, pip-audit, npm audit, Semgrep, **Trivy** (`trivy-action@master`, `aquasec/trivy:latest`) |
| Contenedores | Docker Buildx, GHCR, `provenance: true` y `sbom: true` en el build del CD |
| Despliegue | SSH (`appleboy/ssh-action`) a un servidor on-premise, `docker compose` con la imagen por SHA y un rollback manual |

## 3. Diagnóstico — estado actual

### 3.1 Hallazgos críticos (el pipeline no protege lo que dice proteger)

| ID | Hallazgo | Evidencia | Principio |
|---|---|---|---|
| C-1 | **El CD nunca se ha disparado desde un merge.** `cd.yml` espera un `workflow_run` del CI en `master`, pero el CI no corre en `push` a `master` (solo en PRs, cuyo `head_branch` es `staging`). | API de Actions: 0 corridas del CI con `head_branch = master`; las 6 corridas del CD (abril) fallaron. | P4, P8 |
| C-2 | **El CI no valida el push a `master`**, que es justo el evento que debe disparar el CD (ver C-1). Las ramas de trabajo quedan **fuera del CI por decisión del usuario** (§6): son temporales y se validan al hacer merge a `staging`. La última corrida del CI fue el 9-sep-2026: todo lo posterior está en `MES`, sin integrar. | `on.push.branches: [staging]` | P3 |
| C-3 | **El escaneo semanal nunca corre.** Los `schedule` de GitHub solo se ejecutan desde la rama por defecto, y `main` (último commit 16-oct-2025) no tiene workflows. | `default_branch = main`; Security Scan solo registra corridas por `push` a `master`. | P2, P3 |
| C-4 | **Actions en referencias mutables.** `trivy-action@master` en 3 pasos y el resto en tags mayores (`@v4`, `@v5`…). Es justo el vector del ataque a Trivy de marzo 2026 (CVE-2026-33634): se reescribieron 75 tags de `trivy-action` para robar secretos de CI. TexCore **no estuvo expuesto**: sus workflows se crearon el 8-abr-2026. Pero la configuración actual repetiría el riesgo. | `security.yml:125`, `cd.yml:187,196`; GitLab `aquasec/trivy:latest`, que el atacante también reasignó. | P5, P7 |
| C-5 | **El umbral de cobertura del backend no bloquea.** El paso de `coverage report` tiene `continue-on-error: true`; con 89 % el pipeline sigue verde. | `ci.yml:225-230` | P2 |
| C-6 | **Tasa de fallo del CI del 82 %** (58 de 71 corridas). Un pipeline que casi siempre está rojo deja de mirarse. | API de Actions | P2 |

### 3.2 Hallazgos altos

| ID | Hallazgo | Principio |
|---|---|---|
| A-1 | **Dos pipelines divergentes.** GitLab usa Node 20 y GitHub Node 24; GitLab escanea los 3 microservicios y GitHub no. El README declara ambos. | P1 |
| A-2 | **No se construye una sola vez.** El CI valida el build sin publicarlo; el CD reconstruye después. Lo probado y lo desplegado son artefactos distintos. | P4 |
| A-3 | **El CD solo escanea `backend` y `nginx`**; los 3 microservicios llegan a producción sin escanear. | P7 |
| A-4 | **Controles informativos disfrazados de gates:** mypy (`\|\| true`), pip-audit y npm audit (`continue-on-error`), Semgrep (`\|\| true`), Trivy semanal (`exit-code: 0`). | P2 |
| A-5 | **No hay actualización automática de dependencias** (no existe `dependabot.yml` ni `renovate.json`). Las actions van de 2 a 3 versiones mayores atrás (por ejemplo `checkout@v4` frente a v7.0.1, `build-push-action@v6` frente a v7.4.0). | P5 |
| A-6 | **No se firman ni verifican imágenes.** Hay SBOM y procedencia, pero nadie los verifica antes del deploy. | P7 |
| A-7 | **El deploy no está desacoplado de las migraciones.** `entrypoint.sh` ejecuta `migrate` al arrancar el contenedor: un rollback de imagen no deshace el esquema y no se respalda la base antes. | P9 |
| A-8 | **No hay entorno de staging desplegado.** Producción es el primer lugar donde corren juntas las 5 imágenes. | P8 |
| A-9 | **Llave SSH de larga vida** con acceso al servidor; el deploy hace `git checkout` en el servidor y escribe `.env` con todos los secretos. | P6 |

### 3.3 Hallazgos medios y bajos

- **A-3 resuelto (5-oct):** la matriz de Trivy del CD ya cubre las 5 imágenes.
- **M-1** ESLint inexistente: el job dice «ESLint», pero no hay paso; `package.json` arrastra `eslintConfig: react-app` (de CRA, sin dependencias instaladas).
- **M-2** Ningún job tiene `timeout-minutes` (por defecto 6 h).
- **M-3** `permissions` global con `pull-requests: write` que ningún job usa.
- **M-4** `reporting_excel` y `printing_service` corren como **root**; `printing_service` usa Python 3.11 y el resto 3.12; las imágenes base no están fijadas por digest.
- **M-5** El health check usa `secrets.ALLOWED_HOSTS` y el *environment* usa `vars.ALLOWED_HOSTS`, fuentes distintas para el mismo dato.
- **M-6** El rollback solo respalda `backend` y `nginx` como `:backup`.
- **M-7** No hay `actionlint`, CODEOWNERS ni reglas de protección de rama visibles; el `quality-gate` es un script bash en vez de *required checks*.
- **M-8** La auditoría de rutas (`scripts/auditar_rutas_frontend.py`) queda **fuera del CI** (decisión del 1-oct, ratificada el 5-oct): fue una herramienta de limpieza puntual.
- **M-9** No hay pruebas E2E ni smoke tests contra el stack levantado; tampoco DAST.
- **M-10** El servicio `mssql/server:2022-latest` del CI es mutable.
- **M-11** `frontend/dist/` está versionado en git (9 archivos) aunque `.gitignore` lo excluye: artefactos de build en el repo. Hay que sacarlo del índice (`git rm --cached`).
- **M-12** El README declara GitLab CI y cifras viejas (umbral 89 %, 998 pruebas del frontend).

### 3.4 Lo que ya está bien (se conserva)

`concurrency` con `cancel-in-progress`; matrix por servicio; SQL Server real en CI (paridad con producción); imágenes etiquetadas por SHA; `provenance` y `sbom` en el build; rollback con confirmación y auditoría; inputs del rollback pasados por `env` (evita inyección); `fail-fast: false` en los escaneos; pre-commit con bandit y detect-secrets.

## 4. Arquitectura objetivo

Flujo del usuario: rama de trabajo (p. ej. `MES`) → **PR a `staging`** → **PR de `staging` a `master`** → producción.
`master` es producción; `staging` es integración y pruebas; las ramas de trabajo son temporales y no llevan CI propio.

```
 PR hacia staging / push a staging / PR hacia master        (ci.yml)
   └─ actionlint + zizmor → lint (Ruff, ESLint) → tests backend (SQL Server) · 3 microservicios · frontend
      → SCA bloqueante con excepciones vencibles → build de validación de las 5 imágenes (sin push)
      └─ quality-gate = required check de la protección de rama

 push a master (merge del PR staging → master)              (release.yml)
   └─ CI completo sobre el commit de master
      → build DESDE CERO de las 5 imágenes (sin caché) → push a GHCR por digest
      → Trivy (5 imágenes) → SBOM + procedencia → firma cosign keyless
      → staging efímero en el runner: compose con esos digests + SQL Server desechable → migraciones → smoke tests
      → aprobación del environment "production"
      → [runner propio en el servidor] respaldo de BD → migraciones → deploy por digest verificando la firma
      → health check → registro del deployment (DORA)

 semanal (desde master, rama por defecto) → Trivy + pip-audit + npm audit + Semgrep + OpenSSF Scorecard
```

**Por qué se reconstruye en `master`:** `staging` puede acumular muchos cambios y `master` estar atrasada. Construir desde cero sobre el commit exacto de `master` garantiza que la imagen corresponde a lo que se va a producción, sin capas en caché de otra rama (decisión del usuario). Dentro del pipeline de `master`, esa imagen se construye **una sola vez** y es la misma que se escanea, se prueba y se despliega.

## 5. Plan por fases

Cada fase es un PR independiente y no empieza hasta que la anterior está en verde.

### Fase 0 — Contención de seguridad (½ día) — ✅ hecha 5-oct-2026
1. **Fijar todas las actions por SHA de commit**, con la versión en un comentario (`uses: actions/checkout@<sha> # v7.0.1`), y subirlas a su versión mayor vigente.
2. **Trivy:** `aquasecurity/trivy-action` v0.36.0 (`ed142fd0673e97e23eac54620cfb913e5ce36c25`) con `version:` explícita de Trivy (v0.75.0); en GitLab, mientras exista, `aquasec/trivy:0.75.0` por digest.
3. **`.github/dependabot.yml`** semanal para `github-actions`, `pip` (backend y 3 servicios), `npm` y `docker`, agrupando los parches y los minors.
4. **`permissions: {}`** a nivel de workflow, permisos por job y `timeout-minutes` en todos (M-2, M-3).
5. Agregar **`actionlint`** y **`zizmor`** (auditor de seguridad de workflows) como primer job del CI.
6. **Eliminar `.gitlab-ci.yml`** y quitarlo del README (A-1, M-12). Sacar `frontend/dist/` del índice de git (M-11).

*Criterio de salida:* `grep -E "uses: .+@(v[0-9]+|master|main)$"` sobre `.github/` devuelve 0 líneas; `zizmor` sin hallazgos altos.

### Fase 1 — Que el CI corra donde importa (½ día) — ✅ hecha en el código; faltan los ajustes de GitHub del usuario (§6)
1. Disparadores: `pull_request` hacia `staging` y `master` y `push` a `staging`, con `concurrency` por ref. Las ramas de trabajo no llevan CI propio: se validan en el PR hacia `staging` (decisión del usuario). **El push a `master` no se agrega todavía:** activaría el `cd.yml` actual, que nunca se ha disparado y se reemplaza en la Fase 3; ahí `release.yml` corre el CI completo sobre `master`.
2. **Rama por defecto = `master`** (decidido): Settings → Branches. Así corren el `schedule` y Dependabot (C-3). `main` solo tiene el «Initial commit»; se borra después de cambiar la rama por defecto.
3. **Protección de rama** (rulesets) que hace cumplir el flujo:
   - `master` solo acepta PR **desde `staging`**;
   - `staging` solo acepta PR;
   - `quality-gate` es *required check*;
   - sin *force-push* ni borrado.

   CODEOWNERS para `.github/`, `infrastructure/` y `database/`.

### Fase 2 — Gates que bloquean (1–2 días → 3–4 días por lo que destapó)
1. ✅ **Cobertura del backend bloqueante** (C-5): sin `continue-on-error`. Microservicios: umbral único en cada `pytest.ini` (85 / 95 / 90 %, medidos 88 / 98 / 94 %), suite completa en el CI (antes `printing_service` corría solo `tests/unit` y le faltaba PyJWT).
2. ✅ **SCA bloqueante**: `pip-audit` en los 4 servicios y `npm audit` de producción desde moderada. Se actualizaron las dependencias con CVE (DRF 3.17.2, PyJWT 2.15.0, requests 2.33.0, python-multipart 0.0.31, python-dotenv 1.2.2, WeasyPrint 70.0, axios y cadena vía `npm audit fix`, React Router 7.18.4, Vitest 4.1.11). Dependencias de desarrollo: bloquean CRITICAL; los HIGH restantes son la cadena de Tailwind 3 (punto 8).
3. ✅ **Semgrep** en el CI y en el escaneo semanal, bloqueante en `ERROR` (0 hallazgos); 5 falsos positivos anotados con `nosemgrep` y su motivo.
4. ✅ **mypy bloqueante** con los plugins de Django y DRF (antes corría sin ellos): de 598 errores a 0, **sin línea base**. Destapó y se corrigieron con TDD dos defectos reales (ver el CHANGELOG del 5-oct).
5. ⏳ **ESLint**: flat config instalada (ESLint 10, typescript-eslint, react-hooks 7, react-refresh) y `eslintConfig` de CRA eliminado. **No es gate todavía:** reporta 1146 hallazgos, entre ellos 201 `any` en código de producción (prohibido por el estándar del proyecto) y 51 `setState` dentro de efectos. Corregirlos es un refactor del frontend con sus pruebas.
6. ⏳ **Ruff**: Etapas 1-3 hechas (paridad con flake8, autofix, reglas de defectos y seguridad; bandit retirado, Ruff es el SAST de Python junto con Semgrep). Etapa 4 (Django, simplificaciones, complejidad — 134 hallazgos y 9 funciones > 15) y Etapa 5 (formateador) pendientes (`2026-10-05-migracion-ruff.md`).
7. ✅ El escaneo semanal (`security.yml`) usa los mismos gates y escanea las 5 imágenes.
8. ⏳ **Tailwind CSS 4**: elimina los HIGH de `braces`/`micromatch`/`chokidar` (solo build). Migración de configuración (CSS-first) y de `tailwindcss-animate` → `tw-animate-css`, con verificación visual.

### Fase 3 — Release en `master`: build desde cero, escaneo y firma (2 días)
1. Nuevo `release.yml` en `push` a `master`. Corre el CI completo y luego construye las 5 imágenes **desde cero** (`no-cache: true`, `pull: true` para traer las bases actualizadas) sobre el commit de `master`, y las publica en GHCR. Desde ahí todo usa el **digest** (`@sha256:`), no el tag.
2. **Trivy sobre las 5 imágenes** en matriz (A-3).
3. `actions/attest-build-provenance` y la atestación del SBOM (SLSA nivel 2–3); **firma keyless con cosign** (OIDC, sin llaves que custodiar).
4. Se reemplaza el disparador roto del CD (C-1): el deploy encadena con `needs:` dentro de `release.yml`, sin `workflow_run`. `cd.yml` se elimina.

### Fase 4 — Despliegue y rollback seguros (2–3 días)
1. **Staging efímero en el pipeline de `master`** (no hay servidor de staging):
   - en un runner de GitHub se levantan con `docker compose` las 5 imágenes recién construidas (por digest) y un SQL Server desechable;
   - se aplican **todas las migraciones desde cero** y `seed_production_masters`;
   - se corren los smoke tests: health de los 5 servicios, login y una consulta por rol.

   Si falla, no se pide aprobación ni se despliega. Más adelante se agrega E2E con Playwright (M-9). Si algún día hay un servidor de staging, el mismo job apunta a él sin cambiar las pruebas.
2. **Migraciones fuera del entrypoint:** job `migrate` previo al `up`, con respaldo de la base (`BACKUP DATABASE`) antes; política *expand/contract* para que la versión N-1 funcione con el esquema N (A-7).
3. **Verificar la firma antes del deploy** (`cosign verify` en el servidor) y desplegar por digest.
4. **Self-hosted runner en el servidor de producción** (decidido) en lugar de la llave SSH (A-9):
   - El runner abre la conexión hacia GitHub; el servidor no expone SSH a Internet ni guarda una llave en GitHub.
   - Corre como un usuario sin privilegios y con acceso solo a `docker compose`; es **efímero** (`--ephemeral`) y se limpia tras cada job.
   - Lo usa **únicamente** el job de deploy, con una etiqueta propia (`texcore-prod`), en el *environment* `production` con aprobación. **Nunca** corre código de un PR: los PR de forks podrían ejecutar código arbitrario en el servidor.
   - Los secretos se leen del *environment* y se escriben en `.env` con `chmod 600`, como hoy.
   - Se deja de hacer `git checkout` en el servidor: basta el `docker-compose.prod.yml` publicado junto a la imagen.
5. **Rollback:** respaldar las 5 imágenes, unificar `vars` y `secrets` del host (M-5) y probar el rollback en staging en cada release.

### Fase 5 — Contenedores endurecidos (1 día)
1. Usuario no root en `reporting_excel` y `printing_service`; `printing_service` a Python 3.12 (M-4).
2. Imágenes base fijadas por digest (Dependabot las actualiza) y `HEALTHCHECK` en cada Dockerfile.
3. `mssql/server` del CI fijado a un CU concreto (M-10).

### Fase 6 — Gobierno y mejora continua (½ día, luego recurrente)
1. **OpenSSF Scorecard** semanal (SARIF a Security) como termómetro de la cadena de suministro.
2. **Métricas DORA** (frecuencia de despliegue, lead time, tasa de fallos y MTTR) a partir de los GitHub Deployments.
3. `SECURITY.md` con la política de respuesta a vulnerabilidades y la rotación de secretos.
4. Revisión trimestral: versiones de actions y herramientas, excepciones vencidas y tiempo del pipeline.

## 6. Decisiones (5-oct-2026, todas tomadas)

| # | Decisión del usuario | Efecto en el plan |
|---|---|---|
| 1 | GitLab no se usa | Se elimina `.gitlab-ci.yml` en la Fase 0. |
| 2 | `master` es producción y rama por defecto; `staging` es integración; todo entra por PR a `staging` y de ahí a `master`; las ramas de trabajo son temporales | CI en PR y push de `staging` y PR hacia `master`; release en push a `master`; rulesets que obligan el flujo (Fase 1). |
| 3 | La auditoría de rutas no entra al CI | Se queda como script manual (M-8). |
| 4 | Deploy con runner propio | Self-hosted runner efímero en el servidor (Fase 4.4). |
| 5 | Migrar a Ruff, aprovechando al máximo sus reglas | Plan hijo `2026-10-05-migracion-ruff.md` (Fase 2.6). |
| 6 | Sin servidor de staging; `master` reconstruye las imágenes desde cero | Build sin caché en `release.yml` y staging efímero en ese pipeline (Fases 3 y 4.1). |

### Acciones en GitHub que hace el usuario (no se pueden hacer desde el código)
1. Settings → Branches: rama por defecto = `master`; luego borrar `main`.
2. Settings → Rules: rulesets de `master` y `staging` (Fase 1.3).
3. Settings → Environments: `production` con revisores obligatorios.
4. Settings → Actions → Runners: registrar el runner propio en el servidor (Fase 4.4, con las instrucciones que se entreguen).

### Estrategia con `MES`
Los cambios de CI que corren en un PR (Fases 0, 1, 2 y la migración a Ruff) se hacen **en `MES`**. GitHub ejecuta los workflows de un `pull_request` con la versión de la rama del PR, así que el PR `MES → staging` ya prueba el CI nuevo. Para tener feedback temprano sin integrar, conviene abrir ese PR **como borrador (draft)**: el CI corre en cada push a `MES` y el merge solo se hace cuando todo está en verde. Las Fases 3 a 5 (release, deploy, runner) solo se verifican de punta a punta en el primer merge a `master`.

## 7. Referencias

- GHSA-69fq-xp46-6x23 / CVE-2026-33634 — compromiso de `trivy`, `trivy-action` y `setup-trivy` (19–23 mar 2026).
- SLSA v1.0 (niveles de build), OpenSSF Scorecard, GitHub *Security hardening for GitHub Actions*.
- DORA — *Accelerate State of DevOps*.
