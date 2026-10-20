#!/bin/sh
# Prepara la base de datos para la versión de la imagen: crea texcore_db si no existe,
# aplica las migraciones y las optimizaciones de SQL Server (database/V2, V4, V5 y V6) y
# registra las credenciales de los servicios satélite. Todo es idempotente.
#
# Desarrollo lo ejecuta en cada arranque (entrypoint.sh). Producción lo ejecuta una sola
# vez por despliegue, después del respaldo y antes de levantar la versión nueva
# (scripts/deploy_production.sh, .gitlab-ci.yml).
set -e

echo "Ensuring database exists..."
python scripts/create_db.py

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Applying SQL Server DDL optimizations..."
python manage.py apply_sql_optimizations

echo "Registering service credentials..."
python manage.py register_services

echo "Database ready."
