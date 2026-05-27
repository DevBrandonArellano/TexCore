#!/bin/sh
# Este script usa finales de línea estilo Unix (LF). Si se edita en Windows,
# asegúrese de que su editor guarde con finales de línea LF para evitar
# errores de 'archivo no encontrado' en Linux.


# Termina el script inmediatamente si un comando falla.
set -e

echo "Backend entrypoint script started."

# Esperar a que la base de datos esté lista
# Usamos el script wait-for-it.sh que ya tienes
echo "Waiting for database connection..."
./wait-for-it.sh

echo "Database is ready."

# Crear la base de datos si no existe
echo "Ensuring database exists..."
python create_db.py
echo "Database check complete."

# Aplicar las migraciones de la base de datos
echo "Applying database migrations..."
python manage.py migrate

echo "Database migrations applied successfully."

# Crear credenciales de servicio para microservicios (idempotente — no falla si ya existen)
echo "Seeding service credentials..."
python manage.py seed_service_credentials
echo "Service credentials ready."

# Ejecuta el comando principal del contenedor (el que se pasa en 'command' de docker-compose.yml)
exec "$@"