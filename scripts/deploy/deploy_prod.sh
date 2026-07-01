#!/bin/bash
# --- Script de Despliegue Automatizado para Producción (Unix/Linux) ---
# Este script levanta el entorno de producción, genera certificados si faltan,
# y ejecuta todos los comandos de inicialización de Django.
set -e

# Colores para la salida
print_green() { echo -e "\e[32m$1\e[0m"; }
print_cyan() { echo -e "\e[36m$1\e[0m"; }
print_yellow() { echo -e "\e[33m$1\e[0m"; }
print_error() { echo -e "\e[31m$1\e[0m"; }

clear
print_green "======================================================================"
print_green " Iniciando Despliegue Automatizado de TexCore en Producción (Linux) "
print_green "======================================================================"

COMPOSE_FILE="infrastructure/docker/docker-compose.prod.yml"

# 1. Verificar archivo .env
if [ ! -f ".env" ]; then
    print_yellow "El archivo .env de producción no existe."
    if [ -f ".env.example" ]; then
        print_cyan "Creando .env a partir de .env.example..."
        cp .env.example .env
        print_yellow "¡ATENCIÓN!: Se ha creado un archivo .env base. Por favor edítalo con tus claves y contraseñas reales antes de continuar."
        exit 1
    else
        print_error "Error: No se encontró .env ni .env.example."
        exit 1
    fi
fi

# 2. Verificar o Generar Certificados SSL autofirmados de respaldo
mkdir -p nginx/certs
if [ ! -f "nginx/certs/nginx-selfsigned.crt" ] || [ ! -f "nginx/certs/nginx-selfsigned.key" ]; then
    print_yellow "Certificados SSL no detectados en nginx/certs/."
    print_cyan "Generando certificado autofirmado de respaldo..."
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
      -keyout nginx/certs/nginx-selfsigned.key \
      -out    nginx/certs/nginx-selfsigned.crt \
      -subj "/CN=localhost"
    chmod 600 nginx/certs/nginx-selfsigned.key
    print_green "Certificado de respaldo generado con éxito."
fi

# 3. Construir y levantar contenedores de producción
print_cyan "Construyendo y levantando contenedores de producción en segundo plano..."
docker compose -f "$COMPOSE_FILE" --env-file .env up -d --build

# 4. Esperar a que el backend esté listo y saludable (usando healthcheck)
print_cyan "Esperando a que el backend de producción esté saludable..."
counter=0
max_wait=24
backend_healthy=false

while [ $counter -lt $max_wait ]; do
    status=$(docker inspect --format="{{.State.Health.Status}}" docker-backend-1 2>/dev/null || echo "starting")
    if [ "$status" = "healthy" ]; then
        backend_healthy=true
        break
    fi
    echo -n "."
    sleep 5
    counter=$((counter+1))
done

echo "" # Salto de línea

if [ "$backend_healthy" = false ]; then
    print_error "Error: El backend no se reportó saludable en el tiempo esperado."
    docker compose -f "$COMPOSE_FILE" logs --tail=50 backend
    exit 1
fi

print_green "Backend listo y saludable."

# 5. Inicializar configuraciones internas de Django en producción
print_cyan "Configurando permisos y roles (setup_permissions)..."
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py setup_permissions

print_cyan "Creando superusuario de administración (create_admin)..."
docker compose -f "$COMPOSE_FILE" exec -T backend python manage.py create_admin

print_green "======================================================================"
print_green " ¡El Despliegue de Producción se ha completado con éxito! "
print_green "======================================================================"
print_cyan "Servicios en línea en:"
echo " - Sitio Principal: https://localhost"
echo " - API Docs:        https://localhost/api/docs/"
print_cyan "Credenciales de superusuario creadas:"
echo " - Usuario:    sistemas"
echo " - Contraseña: Sistemas2026* (Por favor cambiar en producción real)"
print_green "======================================================================"
