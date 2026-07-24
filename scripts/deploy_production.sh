#!/bin/bash
# =============================================================================
# TEXCORE PRODUCTION LAUNCH SCRIPT (LINUX / BASH)
# Lanzamiento limpio desde cero: Contenedores + Database Baseline + DDL SQL Server 2022
# =============================================================================
set -e

echo "====================================================================="
echo "   TEXCORE - DESPLIEGUE A PRODUCCIÓN Y BASAL DE BASE DE DATOS        "
echo "====================================================================="

COMPOSE_FILE="infrastructure/docker/docker-compose.prod.yml"
ENV_FILE=".env.prod"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: No se encontró el archivo $ENV_FILE. Por favor copia .env.prod.example a .env.prod y configura las variables."
    exit 1
fi

echo "[1/5] Construyendo imágenes Docker de producción..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache

echo "[2/5] Iniciando base de datos SQL Server 2022 y Redis..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d db redis

echo "[3/5] Esperando disponibilidad de SQL Server 2022..."
until docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T db /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${DB_PASSWORD}" -C -N -Q "SELECT 1" > /dev/null 2>&1; do
    echo "  Esperando conexión con SQL Server..."
    sleep 3
done
echo "  SQL Server 2022 está listo."

# Migraciones (baseline 0001_initial) y optimizaciones DDL/stored procedures
# (database/V2_*.sql, V3_*.sql) ya NO se aplican a mano aquí: el entrypoint
# del contenedor 'web' (infrastructure/docker/entrypoint.sh) las ejecuta
# automáticamente en cada arranque, vía `manage.py migrate` +
# `manage.py apply_sql_optimizations` (este último lee los .sql con la propia
# conexión Django/pyodbc — no depende de que sqlcmd/los archivos .sql existan
# dentro del contenedor 'db', que es donde antes fallaban).
echo "[4/5] Levantando aplicación Web Django y Microservicios (migraciones y optimizaciones DDL se aplican automáticamente en el arranque)..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d web scanning_service reporting_excel printing_service nginx

echo "  Esperando a que el contenedor 'web' termine su arranque (migrate + optimizaciones DDL)..."
until docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py migrate --check > /dev/null 2>&1; do
    echo "  Esperando arranque de 'web'..."
    sleep 3
done
echo "  Contenedor 'web' listo."

echo "[5/5] Sembrando datos maestros iniciales (Grupos RBAC, superusuario)..."
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py seed_production_masters

echo "====================================================================="
echo "   DESPLIEGUE A PRODUCCIÓN FINALIZADO EXITOSAMENTE                 "
echo "   TexCore está operando en: https://${ALLOWED_HOSTS%%,*}           "
echo "====================================================================="
