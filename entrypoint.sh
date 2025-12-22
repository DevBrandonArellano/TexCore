#!/bin/sh

# Termina el script inmediatamente si un comando falla.
set -e

echo "Backend entrypoint script started."

# Esperar a que la base de datos esté lista
# Usamos el script wait-for-it.sh que ya tienes
echo "Waiting for database connection..."
/app/wait-for-it.sh db:1433 --timeout=60

echo "Database is ready."

# Aplicar las migraciones de la base de datos
echo "Applying database migrations..."
python manage.py migrate

echo "Database migrations applied successfully."

# Ejecuta el comando principal del contenedor (el que se pasa en 'command' de docker-compose.yml)
exec "$@"
