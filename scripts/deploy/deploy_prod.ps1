# --- Script de Despliegue Automatizado para Producción (Windows PowerShell) ---
Clear-Host
Write-Host "======================================================================" -ForegroundColor Green
Write-Host " Iniciando Despliegue Automatizado de TexCore en Producción (Windows) " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green

$composeFile = "infrastructure/docker/docker-compose.prod.yml"

# 1. Verificar archivo .env
if (-not (Test-Path ".env")) {
    Write-Host "El archivo .env de producción no existe." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "Creando .env a partir de .env.example..." -ForegroundColor Cyan
        Copy-Item .env.example -Destination .env
        Write-Host "¡ATENCIÓN!: Se ha creado un archivo .env base. Por favor edítalo con tus claves y contraseñas reales antes de continuar." -ForegroundColor Yellow
        exit 1
    } else {
        Write-Error "Error: No se encontró .env ni .env.example."
        exit 1
    }
}

# 2. Verificar o Generar Certificados SSL autofirmados de respaldo
if (-not (Test-Path "nginx/certs")) {
    New-Item -ItemType Directory -Force -Path "nginx/certs" | Out-Null
}

if (-not (Test-Path "nginx/certs/nginx-selfsigned.crt") -or -not (Test-Path "nginx/certs/nginx-selfsigned.key")) {
    Write-Host "Certificados SSL no detectados en nginx/certs/." -ForegroundColor Yellow
    Write-Host "Generando certificado autofirmado de respaldo..." -ForegroundColor Cyan
    
    # Intentamos usar openssl si está disponible localmente o mediante el contenedor
    # En producción o local, podemos levantarlo y usar el comando exec en docker.
    # Pero primero levantamos la base con docker-compose y luego ejecutamos el openssl interno.
}

# 3. Construir y levantar contenedores de producción
Write-Host "Construyendo y levantando contenedores de producción en segundo plano..." -ForegroundColor Cyan
docker compose -f $composeFile --env-file .env up -d --build

if ($LASTEXITCODE -ne 0) {
    Write-Error "Error al levantar los contenedores con Docker Compose."
    exit 1
}

# Generar certificados autofirmados si no existen a través del backend levantado
if (-not (Test-Path "nginx/certs/nginx-selfsigned.crt") -or -not (Test-Path "nginx/certs/nginx-selfsigned.key")) {
    Write-Host "Generando certificados SSL dentro del contenedor..." -ForegroundColor Cyan
    docker exec docker-backend-1 openssl req -x509 -nodes -newkey rsa:2048 -days 365 -keyout /app/nginx/certs/nginx-selfsigned.key -out /app/nginx/certs/nginx-selfsigned.crt -subj "/CN=localhost"
    
    # Reiniciar Nginx para que cargue los certificados
    Write-Host "Reiniciando Nginx con los nuevos certificados..." -ForegroundColor Cyan
    docker compose -f $composeFile restart nginx
}

# 4. Esperar a que el backend esté listo y saludable (usando healthcheck)
Write-Host "Esperando a que el backend de producción esté saludable..." -ForegroundColor Cyan
$counter = 0
$maxWait = 24
$backendHealthy = $false

while ($counter -lt $maxWait) {
    $status = docker inspect --format="{{.State.Health.Status}}" docker-backend-1 2>$null
    if ($status -eq "healthy") {
        $backendHealthy = $true
        break
    }
    Write-Host -NoNewline "."
    Start-Sleep -Seconds 5
    $counter++
}

Write-Host "" # Salto de línea

if (-not $backendHealthy) {
    Write-Error "Error: El backend no se reportó saludable en el tiempo esperado."
    docker compose -f $composeFile logs --tail=50 backend
    exit 1
}

Write-Host "Backend listo y saludable." -ForegroundColor Green

# 5. Inicializar configuraciones internas de Django en producción
Write-Host "Configurando permisos y roles (setup_permissions)..." -ForegroundColor Cyan
docker compose -f $composeFile exec -T backend python manage.py setup_permissions

Write-Host "Creando superusuario de administración (create_admin)..." -ForegroundColor Cyan
docker compose -f $composeFile exec -T backend python manage.py create_admin

Write-Host "======================================================================" -ForegroundColor Green
Write-Host " ¡El Despliegue de Producción se ha completado con éxito! " -ForegroundColor Green
Write-Host "======================================================================" -ForegroundColor Green
Write-Host "Servicios en línea en:" -ForegroundColor Cyan
Write-Host " - Sitio Principal: https://localhost"
Write-Host " - API Docs:        https://localhost/api/docs/"
Write-Host "Credenciales de superusuario creadas:" -ForegroundColor Cyan
Write-Host " - Usuario:    sistemas"
Write-Host " - Contraseña: Sistemas2026* (Por favor cambiar en producción real)"
Write-Host "======================================================================" -ForegroundColor Green
