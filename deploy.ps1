<#
.SYNOPSIS
Este script de PowerShell es un orquestador multiplataforma para iniciar la aplicación TexCore con Docker Compose.

.DESCRIPTION
Detecta si el sistema operativo anfitrión es Windows o Linux y ejecuta el comando 'docker compose'
apuntando al archivo de configuración correspondiente ('docker-compose.windows.yml' o 'docker-compose.yml').

Esto permite un único punto de entrada para levantar el entorno de desarrollo o producción.
#>

# --- Inicio del script ---

# Limpiar la consola para una salida clara
Clear-Host

Write-Host "Iniciando script de despliegue de TexCore..." -ForegroundColor Green

# Variable para almacenar el archivo de Docker Compose a utilizar
$composeFile = ""

# 1. Detectar el sistema operativo
if ($IsWindows) {
    Write-Host "Sistema operativo Windows detectado."
    $composeFile = "docker-compose.windows.yml"
}
elseif ($IsLinux) {
    Write-Host "Sistema operativo Linux detectado."
    $composeFile = "docker-compose.yml"
}
else {
    Write-Error "Error: Sistema operativo no compatible. Este script solo funciona en Windows y Linux."
    # Salir del script con un código de error
    exit 1
}

Write-Host "Se utilizará el archivo de configuración: '$composeFile'" -ForegroundColor Cyan

# 2. Verificar que el archivo .env existe
if (-not (Test-Path ".env")) {
    Write-Host "El archivo '.env' no se encuentra. Creándolo desde '.env.example'..."
    Copy-Item .env.example -Destination .env
    Write-Host "Archivo '.env' creado. Por favor, revísalo si necesitas cambiar alguna configuración."
}

# 3. Construir y levantar los contenedores
Write-Host "Levantando el entorno con Docker Compose... (Esto puede tardar varios minutos la primera vez)"
try {
    # Se utiliza --env-file para asegurar que las variables se carguen correctamente
    # Se utiliza -d para modo 'detached' (segundo plano)
    # Se utiliza --build para forzar la reconstrucción de las imágenes si hay cambios
    docker compose -f $composeFile --env-file .env up -d --build

    Write-Host ""
    Write-Host "¡Entorno desplegado con éxito!" -ForegroundColor Green
    Write-Host "Puedes ver los logs con el comando: 'docker compose -f $($composeFile) logs -f'"
}
catch {
    Write-Error "Ocurrió un error durante la ejecución de 'docker compose'. Por favor, revisa los mensajes de error anteriores."
    exit 1
}
