#!/bin/bash
# =============================================================================
# TEXCORE — DESPLIEGUE EN PRODUCCIÓN (LINUX / BASH)
# Se ejecuta desde la raíz del repositorio. Guía: docs/arquitectura/GUIA_DESPLIEGUE.md
# Sirve para la primera instalación y para cada actualización.
# =============================================================================
set -euo pipefail

export PROYECTO="texcore-prod"  # nombre fijo: contenedores texcore-prod-<servicio>-1
export COMPOSE_FILE="infrastructure/docker/docker-compose.prod.yml"
export ENV_FILE=".env.prod"
# Tiempo máximo para que los contenedores queden sanos.
ESPERA_SEGUNDOS=900
DESTINO_RESPALDOS="${DESTINO_RESPALDOS:-/var/backups/texcore}"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: falta $ENV_FILE. Copia .env.prod.example a $ENV_FILE y completa sus valores."
    exit 1
fi

compose() { docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

echo "[1/5] Construyendo las imágenes de producción..."
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build --pull

echo "[2/5] Levantando SQL Server y respaldando la base actual (si existe)..."
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --wait db
bash scripts/respaldar_bd.sh "$DESTINO_RESPALDOS"

# En producción el backend no migra al arrancar (MIGRAR_AL_INICIAR=0): la base se prepara
# aquí, una vez, con la imagen nueva. preparar_bd.sh crea la base si no existe y aplica
# migraciones, database/V2-V6 y register_services.
echo "[3/5] Preparando la base con la versión nueva (migraciones y optimizaciones)..."
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --no-deps backend sh infrastructure/docker/preparar_bd.sh

# printing y reporting_excel corren sin privilegios (UID 10001). Sus volúmenes de auditoría
# creados antes del 13-oct-2026 son de root: se ajusta el dueño (idempotente).
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --no-deps --user 0 --entrypoint chown printing -R 10001:10001 /data
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" run --rm --no-deps --user 0 --entrypoint chown reporting_excel -R 10001:10001 /data

echo "[4/5] Levantando los servicios y esperando a que estén sanos (hasta ${ESPERA_SEGUNDOS} s)..."
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --wait --wait-timeout "$ESPERA_SEGUNDOS"

echo "[5/5] Sembrando los datos maestros iniciales (grupos RBAC y cuenta admin)..."
docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend python manage.py seed_production_masters

compose ps
echo "Despliegue terminado. Verifica la salud con: curl -k https://<host>/api/health/"
