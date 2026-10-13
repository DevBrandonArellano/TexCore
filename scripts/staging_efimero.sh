#!/bin/bash
# =============================================================================
# TEXCORE — STAGING EFÍMERO
# Levanta las 6 imágenes de un release con el compose de producción y un SQL Server
# desechable, prepara la base desde cero, siembra los usuarios demo por rol y corre las
# pruebas de humo (scripts/smoke_test.py). Al terminar, borra contenedores, volúmenes y
# secretos: no queda nada.
#
# Uso, desde la raíz del repositorio:
#   bash scripts/staging_efimero.sh <imagenes.env>
# <imagenes.env> tiene una línea por servicio del compose: servicio=referencia, p. ej.
#   backend=ghcr.io/org/texcore/backend@sha256:...
# Lo ejecuta el job `staging` de .github/workflows/release.yml; también corre en cualquier
# equipo con Docker (usa los puertos 8080 y 8443).
# =============================================================================
set -euo pipefail

IMAGENES="${1:?Uso: bash scripts/staging_efimero.sh <imagenes.env>}"
PROYECTO="texcore-staging"
BASE_COMPOSE="infrastructure/docker/docker-compose.prod.yml"
PUERTO_HTTP="${PUERTO_HTTP:-8080}"
PUERTO_HTTPS="${PUERTO_HTTPS:-8443}"
TMP="$(mktemp -d)"

compose() {
    docker compose -p "$PROYECTO" -f "$BASE_COMPOSE" -f "$TMP/override.yml" --env-file "$TMP/staging.env" "$@"
}
limpiar() {
    compose down -v --remove-orphans >/dev/null 2>&1 || true
    rm -rf "$TMP"
}
trap limpiar EXIT

echo "[1/6] Generando secretos y certificado desechables..."
aleatorio() { openssl rand -hex "$1"; }
openssl genrsa -out "$TMP/jwt.key" 2048 2>/dev/null
openssl rsa -in "$TMP/jwt.key" -pubout -out "$TMP/jwt.pub" 2>/dev/null
una_linea() { awk 'BEGIN { ORS = "\\n" } { print }' "$1"; }  # PEM en una línea con \n literales
mkdir -p "$TMP/certs"
openssl req -x509 -nodes -newkey rsa:2048 -days 1 -subj "/CN=localhost" \
    -keyout "$TMP/certs/nginx-selfsigned.key" -out "$TMP/certs/nginx-selfsigned.crt" 2>/dev/null
chmod 644 "$TMP/certs/nginx-selfsigned.key"
cat > "$TMP/staging.env" <<EOF
CI_REGISTRY_IMAGE=texcore-staging
TAG=staging
SECRET_KEY=$(aleatorio 32)
ALLOWED_HOSTS=localhost
CSRF_TRUSTED_ORIGINS=https://localhost:$PUERTO_HTTPS
CORS_ALLOWED_ORIGINS=https://localhost:$PUERTO_HTTPS
TRAZABILIDAD_BASE_URL=https://localhost:$PUERTO_HTTPS/trazabilidad
DB_PASSWORD=Stg-$(aleatorio 12)-Aa1!
MSSQL_PID=Developer
INTERNAL_JWT_PRIVATE_KEY=$(una_linea "$TMP/jwt.key")
INTERNAL_JWT_PUBLIC_KEY=$(una_linea "$TMP/jwt.pub")
SCANNING_SERVICE_SECRET=$(aleatorio 24)
REPORTING_SERVICE_SECRET=$(aleatorio 24)
DB_CPUS=2
DB_MEMORY_LIMIT_MB=2048
BACKEND_CPUS=2
BACKEND_MEMORY_LIMIT_MB=2048
BACKEND_WORKERS=4
EOF

# Imágenes del release; nginx además con puertos que no chocan con otra instalación y
# el certificado desechable.
declare -A REFERENCIA
while IFS='=' read -r servicio referencia; do
    [ -n "$servicio" ] && REFERENCIA[$servicio]="$referencia"
done < "$IMAGENES"
{
    echo "services:"
    for servicio in "${!REFERENCIA[@]}"; do
        printf '  %s:\n    image: %s\n' "$servicio" "${REFERENCIA[$servicio]}"
        if [ "$servicio" = "nginx" ]; then
            printf '    ports: !override\n      - "%s:80"\n      - "%s:443"\n' "$PUERTO_HTTP" "$PUERTO_HTTPS"
            printf '    volumes: !override\n      - %s:/etc/nginx/certs:ro\n      - prod_django_static:/var/www/django_static:ro\n' "$TMP/certs"
        fi
    done
} > "$TMP/override.yml"

echo "[2/6] Levantando SQL Server desechable..."
compose up -d --wait db

echo "[3/6] Preparando la base desde cero (todas las migraciones)..."
compose run --rm --no-deps backend sh infrastructure/docker/preparar_bd.sh

echo "[4/6] Levantando los 6 servicios..."
compose up -d --wait --wait-timeout 900

echo "[5/6] Sembrando maestros y usuarios demo por rol..."
compose exec -T backend python manage.py seed_production_masters
compose exec -T backend python manage.py seed_data

echo "[6/6] Pruebas de humo..."
python3 scripts/smoke_test.py "https://localhost:$PUERTO_HTTPS" --http "http://localhost:$PUERTO_HTTP"
