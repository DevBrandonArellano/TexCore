#!/bin/sh
# Este script usa finales de línea estilo Unix (LF). Si se edita en Windows,
# asegúrese de que su editor guarde con finales de línea LF para evitar
# errores de 'archivo no encontrado' en Linux.

# Termina el script inmediatamente si un comando falla.
set -e

echo "Backend entrypoint script started."

# La BD ya está healthy gracias al healthcheck + depends_on en docker-compose.
# Desarrollo prepara la base en cada arranque. Producción fija MIGRAR_AL_INICIAR=0:
# las migraciones corren una vez por despliegue, después del respaldo, para que un
# rollback de imagen no arranque sobre un esquema migrado a medias.
if [ "${MIGRAR_AL_INICIAR:-1}" != "0" ]; then
    sh infrastructure/docker/preparar_bd.sh
else
    echo "MIGRAR_AL_INICIAR=0: la base se prepara en el despliegue, no al arrancar."
fi

# Ejecuta el comando principal del contenedor (el que se pasa en 'command' de docker-compose.yml)
exec "$@"
