#!/bin/bash
# --- Inicio del script de despliegue para Unix ---

# Función para imprimir con colores
print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_cyan() {
    echo -e "\e[36m$1\e[0m"
}

print_error() {
    echo -e "\e[31m$1\e[0m"
}

clear
print_green "Iniciando script de despliegue de TexCore (Unix)..."

COMPOSE_FILE=""

# 1. Detectar el sistema operativo
# En bash, generalmente asumimos un entorno tipo Unix/Linux si se está ejecutando este script.
# Sin embargo, comprobamos si es WSL o Linux nativo / macOS para logging.
OS_NAME=$(uname)

if [[ "$OS_NAME" == "Linux" ]] || [[ "$OS_NAME" == "Darwin" ]]; then
    echo "Sistema operativo compatible detectado: $OS_NAME"
    COMPOSE_FILE="docker-compose.yml"
else
    # Fallback por si acaso, aunque raro en bash
    echo "Sistema operativo detectado: $OS_NAME. Asumiendo configuración estándar."
    COMPOSE_FILE="docker-compose.yml"
fi

print_cyan "Se utilizará el archivo de configuración: '$COMPOSE_FILE'"

# 2. Verificar archivo .env
if [ ! -f ".env" ]; then
    echo "Creando archivo .env desde .env.example..."
    cp .env.example .env
fi

# 3. Construir y levantar
echo "Levantando entorno con Docker..."

# Preferimos 'docker compose' (v2), si falla intentamos 'docker-compose' (v1)
if docker compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker compose"
elif docker-compose version >/dev/null 2>&1; then
    DOCKER_CMD="docker-compose"
else
    print_error "Error: No se encontró 'docker compose' ni 'docker-compose'. Por favor instale Docker."
    exit 1
fi

$DOCKER_CMD -f "$COMPOSE_FILE" --env-file .env up -d --build

if [ $? -ne 0 ]; then
    print_error "Error al ejecutar Docker Compose."
    exit 1
fi

print_green "¡Entorno desplegado con éxito!"
