# Guía de GitLab CE autoalojado — TexCore

> **Fecha:** 20-oct-2026 · **Decisión:** `docs/arquitectura/ADR/ADR_014_GITLAB_CI_AUTOALOJADO.md`
> GitLab es la plataforma principal del CI/CD y del registro de imágenes (§5.3 de la tesis); GitHub es solo un espejo.
> Todo corre en el equipo de staging, dentro de la red de Interfibra (192.168.1.55 en desarrollo).

## 1. Qué se instala

| Pieza | Dónde | Puerto |
|---|---|---|
| GitLab CE (web, API, Git por HTTPS) | contenedor `gitlab` | 8929 |
| GitLab Container Registry | contenedor `gitlab` | 5050 |
| Git por SSH | contenedor `gitlab` | 2224 |
| `texcore-ci` | contenedor `runner-ci` | — |
| `texcore-staging` | contenedor `runner-staging` | — |
| `texcore-produccion` | la VM de producción (Hyper-V, ejecutor shell) | — |

Los puertos 80 y 443 son del stack de TexCore y no se tocan. El archivo es `infrastructure/gitlab/docker-compose.gitlab.yml`, con versión y digest fijos.

**Memoria.** El equipo tiene 16 GB y **no tiene swap**. GitLab queda limitado a 6 GB (usa ~3,8) y el stack de TexCore usa unos 3 GB, así que el staging es **efímero** (`scripts/staging_efimero.sh`): se levanta, se prueba y se baja dentro del pipeline. El 20-oct el OOM killer cerró el navegador y el escritorio al coincidir un pipeline con ambos; por eso:

- `texcore-ci` corre **1 job a la vez** y cada job tiene un tope de 4 GB (`memory = "4g"` y `service_memory = "3g"` en `[runners.docker]` del `config.toml` del runner). Un exceso hace fallar ese job, no el equipo.
- El SQL Server de las pruebas lleva `MSSQL_MEMORY_LIMIT_MB=2048` (en `.gitlab-ci.yml` y en `scripts/run_backend_tests.sh`): sin tope, reserva hasta el 80 % de la memoria.
- `test:frontend` acota el heap de Node a 2 GB.
- **Crea swap** (necesita `sudo`; protege al escritorio de los picos): `sudo fallocate -l 8G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab`; o zram con `systemd-zram-generator`.
- Mientras corre un pipeline evita abrir muchas pestañas; el pipeline completo dura unos 15 minutos.

## 0. Estado de la instalación (20-oct-2026)

Ya hecho en este equipo: GitLab y el registro en marcha, grupo `interfibra` y proyecto `interfibra/texcore` (privado), ajustes del proyecto, `master` y `staging` protegidas, los dos runners registrados y en línea, la CA de confianza en Docker, las variables de CI de la tabla del §7 (salvo las marcadas como pendientes) y la programación semanal. Desde entonces el usuario hizo el primer push (pipeline #6 en verde), `master` es la rama por defecto y el MR #1 (`MES` → `staging`) está en curso. Lo que queda es del usuario: cerrar el push directo (§4), crear swap (§1), las variables `PRODUCCION_HOST` y `TEXCORE_DIR`, el espejo hacia GitHub y el runner de producción.

## 2. Instalación (una sola vez)

Desde la raíz del repositorio:

```bash
cp infrastructure/gitlab/.env.example infrastructure/gitlab/.env     # ajusta GITLAB_HOST si la IP cambia
bash infrastructure/gitlab/generar_certificado.sh 192.168.1.55       # certificado propio con SAN por IP
bash infrastructure/gitlab/construir_ci_tools.sh                     # imagen texcore/ci-tools:1 para los jobs de release
docker compose -f infrastructure/gitlab/docker-compose.gitlab.yml --env-file infrastructure/gitlab/.env up -d --wait
```

La primera vez, GitLab tarda varios minutos en estar sano (`start_period` de 5 minutos). La contraseña inicial de `root`:

```bash
docker compose -f infrastructure/gitlab/docker-compose.gitlab.yml exec gitlab cat /etc/gitlab/initial_root_password
```

Ese archivo se borra solo a las 24 horas: entra a `https://192.168.1.55:8929`, cambia la contraseña y crea una cuenta de administración propia. **Cierra el registro de usuarios** (Admin > Settings > General > Sign-up restrictions > desactivar «Sign-up enabled»): el ajuste `gitlab_signup_enabled` de `gitlab.rb` solo se aplica en el primer arranque y GitLab lo deja abierto. Las cuentas las crea el administrador. El 20-oct-2026 se cerró por consola y se comprobó que nadie se había registrado.

## 3. Confiar en el certificado propio

El certificado `infrastructure/gitlab/certs/gitlab.crt` es la CA que deben aceptar todos los clientes. Sin esto fallan `git`, `docker` y `cosign`.

| Cliente | Qué hacer |
|---|---|
| Docker de este equipo (push y pull del registro) | `sudo mkdir -p /etc/docker/certs.d/192.168.1.55:5050 && sudo cp infrastructure/gitlab/certs/gitlab.crt /etc/docker/certs.d/192.168.1.55:5050/ca.crt` |
| Docker de la VM de producción | Lo mismo, en la VM |
| `git` en cada equipo | `git config --global http.https://192.168.1.55:8929/.sslCAInfo /ruta/gitlab.crt` |
| Los jobs | Variable de archivo `GITLAB_CA_CRT` (§7); el pipeline la usa como `SSL_CERT_FILE` |
| Los runners | Ya la montan desde `infrastructure/gitlab/certs` |

El certificado dura 825 días: renovarlo antes y repetir esta tabla.

## 4. Proyecto, ramas y espejo

1. Crea el grupo y el proyecto `texcore` (privado).
2. Agrega el remoto y sube las ramas: `git remote add gitlab https://192.168.1.55:8929/<grupo>/texcore.git` y `git push gitlab master staging MES`. (Si prefieres, deja `gitlab` como `origin`.)
3. **Ramas protegidas** (Settings > Repository > Protected branches). Quedaron creadas con *push* de Maintainers para poder hacer la primera subida; **después del primer push** ciérralas:
   - `master`: push nadie; merge, Maintainers.
   - `staging`: push nadie; merge, Developers y Maintainers.
   - La aprobación obligatoria de Code Owners es una función de pago (Premium): en GitLab CE `.gitlab/CODEOWNERS` solo orienta a quien revisa. La política «a `master` solo desde `staging`» la hace cumplir el job `ramas:politica` y la de «el pipeline debe pasar» el ajuste del proyecto.
4. **Merge requests:** «Los pipelines deben tener éxito» y «Todos los hilos resueltos» ya están activados; la rama de origen se borra al fusionar. Tras el primer push, la rama por defecto debe ser `master` (Settings > Repository > Default branch); GitLab creó el proyecto con `main`.
5. **Espejo hacia GitHub** (Settings > Repository > Mirroring repositories): *Push*, URL `https://github.com/DevBrandonArellano/TexCore.git`, con un token de GitHub de solo escritura de contenido. GitHub no ejecuta nada: es una copia.
6. **Code Owners:** `.gitlab/CODEOWNERS` ya lista las rutas críticas (pipeline, infraestructura, migraciones).
7. El remoto `gitlab` ya está agregado a este repositorio con la CA configurada (`git config --local`); falta autenticarse con un token personal con `write_repository` al hacer el primer push.

## 5. Container Registry

El registro está en `192.168.1.55:5050`. Las imágenes se llaman `192.168.1.55:5050/<grupo>/texcore/<servicio>` y el pipeline las publica por SHA y por `latest`. Para entrar a mano:

```bash
docker login 192.168.1.55:5050     # usuario de GitLab y un token con write_registry / read_registry
```

Limpieza: Settings > Packages and registries > Container Registry > «Cleanup policies» (conservar las últimas 25 etiquetas, `latest`, `backup` y las de SHA).

## 6. Runners

Los tokens salen de GitLab (Admin > CI/CD > Runners > Nuevo runner de instancia; uno por cada runner).

```bash
TOKEN_CI=glrt-... TOKEN_STAGING=glrt-... bash infrastructure/gitlab/registrar_runners.sh
```

| Runner | Etiqueta | Opciones en GitLab | Para qué |
|---|---|---|---|
| `texcore-ci` | ninguna | «Ejecutar jobs sin etiqueta» activado; no protegido | lint, pruebas, auditorías, Semgrep, Trivy, Renovate |
| `texcore-staging` | `staging` | sin jobs sin etiqueta; **protegido** | construcción, firma y staging efímero. Los jobs reciben el socket del host y la red del host |
| `texcore-produccion` | `produccion` | sin jobs sin etiqueta; **protegido** | deploy y rollback en la VM |

**Runner de producción** (en la VM de Hyper-V, cuando exista; hasta entonces el job `deploy:produccion` queda esperando):

1. Instala Docker, `docker compose`, `cosign` (la versión de `infrastructure/gitlab/Dockerfile.ci-tools`), `jq` y `curl`.
2. Instala `gitlab-runner`, regístralo con ejecutor **shell** y confía en la CA (§3).
3. Prepara el directorio de `TEXCORE_DIR` con `.env.prod` y `nginx/certs`, como en `GUIA_DESPLIEGUE.md` §3.
4. Agrega al usuario del runner al grupo `docker`.

**Paralelismo.** `texcore-ci` corre 1 job a la vez (`concurrent = 1` en `/etc/gitlab-runner/config.toml` del contenedor, que vive en el volumen `runner_ci_config`); lo habíamos subido a 2 y provocó el OOM del 20-oct. Súbelo solo si hay swap y memoria libre, porque `test:backend` levanta un SQL Server. Antes de empujar, corre en local los mismos gates que `lint:backend` (`ruff`, `mypy`, `detect-secrets-hook`): son los que más fallan en el primer pipeline. Si `git ls-files -z | xargs -0 detect-secrets-hook --baseline .secrets.baseline` responde «The baseline file was updated», **no lo descartes**: hace `git add .secrets.baseline` y súbelo en el mismo commit (solo se movieron números de línea de secretos ya auditados); el CI falla mientras esa actualización no esté commiteada.

Un job de feature no puede usar el socket del host: los runners con socket son protegidos y el pipeline solo los pide en `master` y `staging`.

## 7. Variables de CI/CD

Settings > CI/CD > Variables. Las secretas, **protegidas** (solo ramas protegidas) y **enmascaradas** cuando el formato lo permite.

| Variable | Tipo | Valor |
|---|---|---|
| `COSIGN_PRIVATE_KEY` | Archivo, protegida | Contenido de `infrastructure/gitlab/secretos/cosign.key` |
| `COSIGN_PASSWORD` | Variable, protegida, enmascarada | Contenido de `infrastructure/gitlab/secretos/cosign.password` |
| `GITLAB_CA_CRT` | Archivo | Contenido de `infrastructure/gitlab/certs/gitlab.crt` |
| `PRODUCCION_HOST` | Variable, protegida | **Pendiente.** Nombre o IP de producción |
| `TEXCORE_DIR` | Variable, protegida | **Pendiente.** Directorio de la VM con `.env.prod` y `nginx/certs` |
| `GITLAB_TOKEN` | Variable, protegida, enmascarada | Token de proyecto `dora-lectura` (`read_api`, Reporter); vence el 19-oct-2027 |
| `RENOVATE_TOKEN` | Variable, protegida, enmascarada | Token de proyecto `renovate` (`api` y `write_repository`, Developer); vence el 19-oct-2027 |
| `DEPLOY_NOTIFY_WEBHOOK` | Variable, protegida, enmascarada | Opcional: webhook de aviso del despliegue |

**Claves de cosign.** El par se generó el 20-oct-2026: `cosign.pub` está en el repositorio y la privada, con su contraseña, en `infrastructure/gitlab/secretos/` (fuera de git). **Ya están cargadas en GitLab** como variables protegidas: guarda una copia en el gestor de secretos y borra esa carpeta del equipo. Si se pierde la privada, hay que generar otro par (`cosign generate-key-pair`), publicar el nuevo `cosign.pub` y volver a firmar. La rotación sigue `SECURITY.md`.

## 8. Pipelines programados

CI/CD > Programaciones. Ya existe una, en `master`, **cada lunes a las 06:00** (America/Guayaquil): todos los jobs con `rules: schedule` corren en ella.

| Job | Qué hace |
|---|---|
| `seguridad:dependencias`, `seguridad:npm` | `pip-audit` y `npm audit` |
| `seguridad:contenedores` | Trivy sobre las 6 imágenes `latest` del registro |
| `gobierno:dora` | Métricas DORA de 28 días (artefacto `metricas_dora.md`) |
| `dependencias:renovate` | Abre MR hacia `staging` con las actualizaciones |

Corre de verdad después del primer push, cuando exista `master`.

## 9. Flujo de trabajo

1. Trabajas en una rama (p. ej. `MES`) y abres un MR hacia `staging`: corren lint, pruebas, auditorías, Semgrep y el gate ISTQB.
2. Al fusionar en `staging`, `build:validacion` comprueba que el backend y nginx construyen.
3. MR de `staging` a `master` (la política lo exige). Al fusionar:
   `build:imagenes` (6 imágenes desde cero, firmadas) → `imagenes:unir` → `scan:trivy` → `staging:efimero`.
4. `deploy:produccion` queda en espera: un Maintainer lo lanza con un clic, y verifica las firmas, respalda, migra y comprueba la salud.
5. Si algo falla, `rollback:produccion` (manual): vacío vuelve a `:backup`; con `ROLLBACK_SHA` vuelve a esa versión verificando su firma. `ROLLBACK_MOTIVO` queda en el registro del job.

## 10. Respaldo, restauración y actualización de GitLab

```bash
# Respaldo (también diario por cron del contenedor)
docker compose -f infrastructure/gitlab/docker-compose.gitlab.yml exec gitlab gitlab-backup create
docker compose -f infrastructure/gitlab/docker-compose.gitlab.yml exec gitlab gitlab-ctl backup-etc    # gitlab.rb y secretos
```

Los respaldos quedan en el volumen `gitlab_data` (`/var/opt/gitlab/backups`, 7 días). Copia los `.tar` a otro equipo: el volumen y el servidor son el mismo punto de falla. La restauración exige la misma versión de GitLab (`gitlab-backup restore BACKUP=<id>`).

**Actualizar:** cambia la versión y el digest en `docker-compose.gitlab.yml` (la ruta de actualización de GitLab no admite saltar versiones mayores sin pasos intermedios), haz el respaldo y levanta de nuevo. Es una decisión, no un efecto de `latest`.

## 11. Verificación de la instalación

```bash
docker compose -f infrastructure/gitlab/docker-compose.gitlab.yml ps                 # gitlab, runner-ci, runner-staging sanos
curl -sk -o /dev/null -w '%{http_code}\n' https://192.168.1.55:8929/users/sign_in   # 200: la web responde
curl -sk -o /dev/null -w '%{http_code}\n' https://192.168.1.55:5050/v2/                 # 401: el registro pide autenticación (correcto)
docker login 192.168.1.55:5050                                                       # el registro acepta
free -h                                                                              # margen con texcore-prod encendido
```

Un MR de prueba debe correr `lint:*`, `test:*` y `audit:*` en verde; un push a `master`, construir y firmar las 6 imágenes y levantar el staging efímero.
