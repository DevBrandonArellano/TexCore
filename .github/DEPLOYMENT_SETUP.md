# TexCore — Configuración CI/CD con GitHub Actions

## Flujo de ramas

```
feature/mi-cambio
        │
        │  push
        ▼
    staging  ◄──── CI corre automáticamente (lint, tests, auditoría)
        │
        │  cuando todos los checks pasan → crear PR manualmente
        ▼
  PR: staging → master
        │
        │  CI re-corre en el PR (última barrera)
        │  Revisión y aprobación manual del PR
        ▼
      master  ◄──── CD despliega automáticamente a producción
        │
        │  si algo falla → ejecutar Rollback (workflow manual)
        ▼
   Producción
```

## Workflows disponibles

| Workflow | Archivo | Cuándo corre |
|----------|---------|--------------|
| TexCore CI | `ci.yml` | Push a `staging`, PRs hacia `staging` o `master` |
| TexCore CD | `cd.yml` | CI verde en `master` (automático tras merge) |
| TexCore Rollback | `rollback.yml` | Manual — solo en emergencias |
| TexCore Security Scan | `security.yml` | Lunes 06:00 UTC + push a `master` |

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
| `REPORTING_INTERNAL_KEY` | Clave interna entre backend y microservicio reporting |

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
