#!/bin/bash
# =============================================================================
# TEXCORE — RESPALDO DE LA BASE DE DATOS (texcore_db)
# Uso, desde la raíz del repositorio:  bash scripts/respaldar_bd.sh [directorio_destino]
# Lo usan el despliegue (antes de migrar), el release y el cron diario de la guía
# (docs/arquitectura/GUIA_DESPLIEGUE.md §4.3).
# Variables opcionales: PROYECTO, COMPOSE_FILE, ENV_FILE, RETENCION_DIAS.
# =============================================================================
set -euo pipefail

PROYECTO="${PROYECTO:-texcore-prod}"
COMPOSE_FILE="${COMPOSE_FILE:-infrastructure/docker/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.prod}"
DESTINO="${1:-/var/backups/texcore}"
RETENCION_DIAS="${RETENCION_DIAS:-7}"

compose() { docker compose -p "$PROYECTO" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }
# La contraseña se lee dentro del contenedor db (MSSQL_SA_PASSWORD): no pasa por este script.
# Por eso va entre comillas simples: se expande en el contenedor, no aquí.
sqlcmd() {
    # shellcheck disable=SC2016
    compose exec -T db bash -c '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -N -b -h -1 -W -Q "$0"' "$1"
}

# Primera instalación: todavía no hay base que respaldar.
existe=$(sqlcmd "SET NOCOUNT ON; SELECT ISNULL(DB_ID(N'texcore_db'), 0)" | tr -d '[:space:]')
if [ "$existe" = "0" ]; then
    echo "texcore_db no existe todavía: no hay nada que respaldar."
    exit 0
fi

archivo="texcore_$(date +%Y%m%d_%H%M%S).bak"
echo "Respaldando texcore_db en $DESTINO/$archivo ..."
sqlcmd "BACKUP DATABASE [texcore_db] TO DISK = N'/var/opt/mssql/backup/$archivo' WITH COMPRESSION, CHECKSUM, INIT"
mkdir -p "$DESTINO"
compose cp "db:/var/opt/mssql/backup/$archivo" "$DESTINO/"
compose exec -T db rm -f "/var/opt/mssql/backup/$archivo"
find "$DESTINO" -name 'texcore_*.bak' -mtime +"$RETENCION_DIAS" -delete
echo "Respaldo listo: $DESTINO/$archivo"
