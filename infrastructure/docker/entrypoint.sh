#!/bin/sh
# Este script usa finales de línea estilo Unix (LF). Si se edita en Windows,
# asegúrese de que su editor guarde con finales de línea LF para evitar
# errores de 'archivo no encontrado' en Linux.


# Termina el script inmediatamente si un comando falla.
set -e

echo "Backend entrypoint script started."

# La BD ya está healthy gracias al healthcheck + depends_on en docker-compose
# Crear la base de datos si no existe
echo "Ensuring database exists..."
python scripts/create_db.py
echo "Database check complete."

# Aplicar las migraciones de la base de datos
echo "Applying database migrations..."
python manage.py migrate

echo "Database migrations applied successfully."

# Registrar credenciales de servicio para microservicios (idempotente)
echo "Registering service credentials..."
python manage.py register_services
echo "Service credentials ready."

# Ejecuta el comando principal del contenedor (el que se pasa en 'command' de docker-compose.yml)
exec "$@"