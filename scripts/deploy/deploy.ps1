# =============================================================================
# TEXCORE — ENTORNO DE DESARROLLO (WINDOWS / POWERSHELL, Docker Desktop)
# Levanta el compose de desarrollo (incluye Redis y celery_worker). Producción:
# scripts/deploy_production.ps1 y docs/arquitectura/GUIA_DESPLIEGUE.md.
# =============================================================================

$ErrorActionPreference = "Stop"

$COMPOSE_FILE = "infrastructure/docker/docker-compose.yml"

if (-not (Test-Path ".env")) {
    Write-Host "Creando .env desde .env.example (revisa sus valores)..."
    Copy-Item .env.example -Destination .env
}

docker compose -f $COMPOSE_FILE --env-file .env up -d --build
if ($LASTEXITCODE -ne 0) { throw "docker compose up terminó con código $LASTEXITCODE" }

docker compose -f $COMPOSE_FILE --env-file .env ps
Write-Host "Entorno de desarrollo levantado." -ForegroundColor Green
