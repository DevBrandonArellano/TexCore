# TexCore — Configuración CI/CD con GitHub Actions

## Flujo de ramas

`master` es producción y la rama por defecto; `staging` es integración y pruebas. Todo cambio entra por PR:

```
rama de trabajo (p. ej. MES, temporal)
        │  PR (abrirlo como draft da feedback del CI en cada push)
        ▼
    staging  ◄──── CI en el PR y en el push tras el merge
        │  PR staging → master (el CI rechaza PRs a master desde otra rama)
        ▼
     master  ◄──── CI en el PR; producción
        │
        ▼
   Producción  (si algo falla → workflow de Rollback)
```

Las ramas de trabajo no llevan CI propio: se validan en su PR hacia `staging`.

## Workflows disponibles

| Workflow | Archivo | Cuándo corre |
|----------|---------|--------------|
| TexCore CI | `ci.yml` | PRs hacia `staging` o `master`, push a `staging` |
| TexCore CD | `cd.yml` | CI verde tras un **push** a `master` del propio repo. Hoy el CI no corre en push a `master`, así que el CD no se dispara solo; `release.yml` lo reemplaza en la Fase 3 del plan de CI/CD |
| TexCore Rollback | `rollback.yml` | Manual — solo en emergencias |
| TexCore Security Scan | `security.yml` | Lunes 06:00 UTC (solo si `master` es la rama por defecto) + push a `master` |

Cadena de suministro: todas las actions están fijadas por SHA de commit (`@<sha> # vX.Y.Z`) y Dependabot
(`.github/dependabot.yml`) abre PRs semanales **hacia `staging`** para actualizarlas junto con pip, npm y las
imágenes base. El job `workflow-lint` (actionlint + zizmor) rechaza cualquier action sin fijar, inyección por
plantillas o permisos excesivos. Las excepciones de zizmor, con motivo y fecha de salida, están en `.github/zizmor.yml`.

## Configuración del repositorio en GitHub (una sola vez)

Estos ajustes no se pueden versionar en el código; los hace un administrador del repositorio.

1. **Rama por defecto** — Settings → General → Default branch → `master`. Sin esto no corren el escaneo semanal
   ni Dependabot. Después, borrar la rama `main` (solo tiene el «Initial commit»).
2. **Ruleset de `master`** — Settings → Rules → Rulesets → New branch ruleset, target `master`:
   - Restrict deletions y Block force pushes.
   - Require a pull request before merging (1 aprobación) + Require review from Code Owners.
   - Require status checks to pass: **Quality Gate · Barrera de Calidad**. Este check incluye la política
     "master solo acepta PRs desde staging".
3. **Ruleset de `staging`** — igual que el de `master`, sin la revisión de Code Owners obligatoria si el equipo
   lo prefiere; el status check **Quality Gate · Barrera de Calidad** sí es obligatorio.
4. **Environment `production`** — ver la sección de abajo.
5. **Artefactos de build fuera del repo** — `frontend/dist/` está versionado aunque `.gitignore` lo excluye:
   `git rm -r --cached frontend/dist` y commit.

## Secretos requeridos

Ve a **Settings → Secrets and variables → Actions → New repository secret**

### Deploy SSH

| Secreto | Descripción | Ejemplo |
|---------|-------------|---------|
| `DEPLOY_SSH_HOST` | IP o dominio del servidor de producción | `192.168.1.100` |
| `DEPLOY_SSH_USER` | Usuario SSH | `appuser` |
| `DEPLOY_SSH_KEY` | Clave privada SSH (PEM, sin passphrase) | `-----BEGIN RSA...` |
| `DEPLOY_SSH_PORT` | Puerto SSH (opcional, default: 22) | `22` |
| `DEPLOY_PROJECT_PATH` | Ruta del proyecto en el servidor | `/home/appuser/texcore` |

### Aplicación

| Secreto | Descripción |
|---------|-------------|
| `DB_PASSWORD` | Contraseña de SQL Server en producción |
| `SECRET_KEY` | Django SECRET_KEY (mínimo 50 caracteres, aleatorio) |
| `ALLOWED_HOSTS` | Dominio sin protocolo (ej: `texcore.miempresa.com`) |
| `CORS_ALLOWED_ORIGINS` | Origins CORS con protocolo (ej: `https://texcore.miempresa.com`) |
| `CSRF_TRUSTED_ORIGINS` | Origins CSRF con protocolo (igual que CORS) |
| `REPORTING_INTERNAL_KEY` | Clave interna entre backend y servicio satélite reporting |

### Opcionales

| Secreto | Descripción |
|---------|-------------|
| `DEPLOY_NOTIFY_WEBHOOK` | URL webhook para notificaciones de deploy (Slack/Teams/Discord) |

## Configuración del servidor de producción

El servidor necesita:

```bash
# 1. Docker y Docker Compose instalados
# 2. Usuario SSH en el grupo docker
sudo usermod -aG docker $DEPLOY_SSH_USER

# 3. Clonar el repositorio
git clone git@github.com:TU_ORG/texcore.git /home/appuser/texcore

# 4. Agregar la clave pública SSH del runner en el servidor
echo "ssh-rsa AAAA..." >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

## Environment "production" en GitHub

Crea el environment en **Settings → Environments → New environment → production**:

- **Required reviewers**: agrega usuarios que deben aprobar deploys a producción
  *(esto añade una aprobación manual extra sobre el PR ya aprobado)*
- **Wait timer**: 0-30 minutos antes de ejecutar el deploy
- **Deployment branches**: restricto a `master` únicamente

## Cómo ejecutar un rollback

1. Ve a **Actions → TexCore Rollback → Run workflow**
2. Selecciona la rama `master`
3. Campos:
   - **target_sha**: SHA del commit al que revertir (vacío = deploy anterior)
   - **confirm**: escribe exactamente `ROLLBACK`
   - **reason**: motivo (se registra en auditoría)
4. El workflow revierte, hace health check y notifica al equipo

## Cómo generar la clave SSH para el deploy

```bash
# En tu máquina local
ssh-keygen -t ed25519 -C "github-actions-texcore-deploy" -f texcore_deploy_key -N ""

# Agregar la clave pública al servidor
ssh-copy-id -i texcore_deploy_key.pub $DEPLOY_SSH_USER@$DEPLOY_SSH_HOST

# Copiar la clave privada como secreto en GitHub
cat texcore_deploy_key   # → pegar en DEPLOY_SSH_KEY
rm texcore_deploy_key texcore_deploy_key.pub
```
