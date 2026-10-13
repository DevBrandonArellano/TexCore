#!/bin/bash
# =============================================================================
# TEXCORE — ENTORNO DE DESARROLLO (LINUX / MACOS / WSL)
# Levanta el compose de desarrollo (incluye Redis y celery_worker). Producción:
# scripts/deploy_production.sh y docs/arquitectura/GUIA_DESPLIEGUE.md.
# =============================================================================
set -euo pipefail

COMPOSE_FILE="infrastructure/docker/docker-compose.yml"

if [ ! -f .env ]; then
    echo "Creando .env desde .env.example (revisa sus valores)..."
    cp .env.example .env
fi

docker compose -f "$COMPOSE_FILE" --env-file .env up -d --build
docker compose -f "$COMPOSE_FILE" --env-file .env ps
echo "Entorno de desarrollo levantado."
