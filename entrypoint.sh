#!/bin/sh
# Termina el script inmediatamente si un comando falla.
set -e

echo "Backend entrypoint script started."

# Crear directorio de logs
echo "Creating log directory..."
mkdir -p /app/logs

# Esperar a que la base de datos esté lista
echo "Waiting for database connection..."
./wait-for-it.sh db:1433 --timeout=60 --strict -- echo "Database is ready."

# Asegurarse de que la base de datos exista antes de aplicar migraciones
echo "Ensuring database exists..."
python create_db.py

# Aplicar las migraciones de la base de datos
echo "Applying database migrations..."
python manage.py migrate
echo "Database migrations applied successfully."

# Inicia el servidor de Django
echo "Starting Django server..."
exec python manage.py runserver 0.0.0.0:8000
