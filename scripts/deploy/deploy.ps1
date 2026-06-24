# --- Inicio del script corregido ---
Clear-Host
Write-Host "Iniciando script de despliegue de TexCore..." -ForegroundColor Green

$composeFile = ""

# 1. Detectar el sistema operativo de forma universal
if ($PSVersionTable.PSVersion.Major -ge 6) {
    # Para PowerShell Core / 7+
    if ($IsWindows) { $os = "Windows" } else { $os = "Linux" }
} else {
    # Para PowerShell 5.1 (Windows Server 2019 nativo)
    $os = "Windows"
}

if ($os -eq "Windows") {
    Write-Host "Sistema operativo Windows detectado."
    $composeFile = "docker/docker-compose.windows.yml"
} else {
    Write-Host "Sistema operativo Linux detectado."
    $composeFile = "infrastructure/docker/docker-compose.yml"
}

Write-Host "Se utilizará el archivo de configuración: '$composeFile'" -ForegroundColor Cyan

# 2. Verificar archivo .env
if (-not (Test-Path ".env")) {
    Write-Host "Creando archivo .env desde .env.example..."
    Copy-Item .env.example -Destination .env
}

# 3. Construir y levantar — preferir 'docker compose' (v2); fallback a 'docker-compose' (v1)
Write-Host "Levantando entorno con Docker..."

function Test-DockerCmd($exe, $cmdArgs) {
    try { & $exe $cmdArgs *> $null; return ($LASTEXITCODE -eq 0) } catch { return $false }
}

if (Test-DockerCmd 'docker' @('compose', 'version')) {
    docker compose -f $composeFile --env-file .env up -d --build
} elseif (Test-DockerCmd 'docker-compose' @('version')) {
    docker-compose -f $composeFile --env-file .env up -d --build
} else {
    Write-Error "No se encontró 'docker compose' (v2) ni 'docker-compose' (v1). Instala Docker Desktop."
    exit 1
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Error al ejecutar Docker Compose."
    exit 1
}

Write-Host "¡Entorno desplegado con éxito!" -ForegroundColor Green