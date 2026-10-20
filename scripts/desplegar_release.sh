#!/bin/bash
# =============================================================================
# TEXCORE — DESPLIEGUE DE UN RELEASE (runner propio del servidor)
# Lo ejecuta el job `deploy:produccion` de .gitlab-ci.yml en el runner `texcore-produccion`,
# con las imágenes ya firmadas y verificadas. No usa SSH ni hace `git checkout` en el
# servidor: corre desde el workspace del runner y toma del servidor solo .env.prod,
# los certificados y el directorio de respaldos.
#
# Uso, desde la raíz del repositorio:
#   TEXCORE_DIR=/opt/texcore IMAGE_BASE=192.168.1.55:5050/grupo/texcore bash scripts/desplegar_release.sh <imagenes.env>
# <imagenes.env>: una línea por servicio del compose, servicio=imagen@sha256:...
# =============================================================================
set -euo pipefail

IMAGENES="${1:?Uso: bash scripts/desplegar_release.sh <imagenes.env>}"
TEXCORE_DIR="${TEXCORE_DIR:?Falta TEXCORE_DIR (directorio del servidor con .env.prod y nginx/certs)}"
IMAGE_BASE="${IMAGE_BASE:?Falta IMAGE_BASE (registro de las imágenes)}"
export PROYECTO="texcore-prod"
export COMPOSE_FILE="infrastructure/docker/docker-compose.prod.yml"
export ENV_FILE="$TEXCORE_DIR/.env.prod"
ESPERA_SEGUNDOS=900
OVERRIDE="$(mktemp --suffix=.yml)"
trap 'rm -f "$OVERRIDE"' EXIT

[ -f "$ENV_FILE" ] || { echo "Falta $ENV_FILE (docs/arquitectura/GUIA_DESPLIEGUE.md §3.2)."; exit 1; }

# Imágenes por digest y certificados del servidor (la ruta relativa del compose apuntaría
# al workspace del runner).
declare -A REFERENCIA
while IFS='=' read -r servicio referencia; do
    [ -n "$servicio" ] && REFERENCIA[$servicio]="$referencia"
done < "$IMAGENES"
{
    echo "services:"
    for servicio in "${!REFERENCIA[@]}"; do
        printf '  %s:\n    image: %s\n' "$servicio" "${REFERENCIA[$servicio]}"
        if [ "$servicio" = "nginx" ]; then
            printf '    volumes: !override\n      - %s/nginx/certs:/etc/nginx/certs:ro\n      - prod_django_static:/var/www/django_static:ro\n' "$TEXCORE_DIR"
        fi
    done
} > "$OVERRIDE"

compose() { docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" -f "$OVERRIDE" --env-file "$ENV_FILE" "$@"; }

echo "[1/6] Respaldando como :backup las imágenes en ejecución (para rollback:produccion)..."
# servicio del compose:nombre de su imagen
for par in db:db backend:backend nginx:nginx printing:printing_service scanning:scanning_service reporting_excel:reporting_excel; do
    servicio="${par%%:*}"; imagen="${par#*:}"
    actual=$(docker inspect --format '{{.Config.Image}}' "texcore-prod-${servicio}-1" 2>/dev/null || true)
    if [ -n "$actual" ]; then
        docker tag "$actual" "${IMAGE_BASE}/${imagen}:backup"
    fi
done

echo "[2/6] Descargando las imágenes del release..."
compose pull --quiet

echo "[3/6] Respaldando la base de datos..."
# Si SQL Server ya corre se respalda tal cual (no se recrea con la imagen nueva antes del respaldo).
compose up --no-recreate -d --wait db
bash scripts/respaldar_bd.sh "$TEXCORE_DIR/respaldos"

echo "[4/6] Ajustando el dueño de los volúmenes de auditoría (UID 10001)..."
compose run --rm --no-deps --user 0 --entrypoint chown printing -R 10001:10001 /data
compose run --rm --no-deps --user 0 --entrypoint chown reporting_excel -R 10001:10001 /data

echo "[5/6] Preparando la base con la versión nueva (migraciones y optimizaciones)..."
compose run --rm --no-deps backend sh infrastructure/docker/preparar_bd.sh

echo "[6/6] Actualizando los servicios y esperando a que estén sanos..."
compose up -d --wait --wait-timeout "$ESPERA_SEGUNDOS" --remove-orphans
compose ps
