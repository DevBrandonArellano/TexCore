# =============================================================================
# TEXCORE PRODUCTION LAUNCH SCRIPT (WINDOWS / POWERSHELL)
# Lanzamiento limpio desde cero: Contenedores + Database Baseline + DDL SQL Server 2022
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "   TEXCORE - DESPLIEGUE A PRODUCCIÓN Y BASAL DE BASE DE DATOS        " -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

$COMPOSE_FILE = "infrastructure/docker/docker-compose.prod.yml"
$ENV_FILE = ".env.prod"

if (-not (Test-Path $ENV_FILE)) {
    Write-Error "ERROR: No se encontró el archivo $ENV_FILE. Copia .env.prod.example a .env.prod y configura las variables de entorno."
    exit 1
}

Write-Host "[1/5] Construyendo imágenes Docker de producción..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE build --no-cache

Write-Host "[2/5] Iniciando base de datos SQL Server 2022 y Redis..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d db redis

Write-Host "[3/5] Esperando disponibilidad de SQL Server 2022..." -ForegroundColor Yellow
$dbReady = $false
while (-not $dbReady) {
    try {
        $result = docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T db /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P $env:DB_PASSWORD -C -N -Q "SELECT 1" 2>$null
        if ($result -like "*1*") {
            $dbReady = $true
        }
    } catch {
        Write-Host "  Esperando a SQL Server 2022..."
        Start-Sleep -Seconds 3
    }
}
Write-Host "  SQL Server 2022 listo para recibir conexiones." -ForegroundColor Green

# Migraciones (baseline 0001_initial) y optimizaciones DDL/stored procedures
# (database/V2_*.sql, V3_*.sql) ya NO se aplican a mano aquí: el entrypoint
# del contenedor 'web' (infrastructure/docker/entrypoint.sh) las ejecuta
# automáticamente en cada arranque, vía `manage.py migrate` +
# `manage.py apply_sql_optimizations` (este último lee los .sql con la propia
# conexión Django/pyodbc — no depende de que sqlcmd/los archivos .sql existan
# dentro del contenedor 'db', que es donde antes fallaban).
Write-Host "[4/5] Levantando aplicación Web Django y Microservicios (migraciones y optimizaciones DDL se aplican automáticamente en el arranque)..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE up -d web scanning_service reporting_excel printing_service nginx

Write-Host "  Esperando a que el contenedor 'web' termine su arranque (migrate + optimizaciones DDL)..." -ForegroundColor Yellow
$webReady = $false
while (-not $webReady) {
    docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py migrate --check *> $null
    if ($LASTEXITCODE -eq 0) {
        $webReady = $true
    } else {
        Write-Host "  Esperando arranque de 'web'..."
        Start-Sleep -Seconds 3
    }
}
Write-Host "  Contenedor 'web' listo." -ForegroundColor Green

Write-Host "[5/5] Sembrando datos maestros iniciales (Grupos RBAC, superusuario)..." -ForegroundColor Yellow
docker compose -f $COMPOSE_FILE --env-file $ENV_FILE exec -T web python manage.py seed_production_masters

Write-Host "=====================================================================" -ForegroundColor Green
Write-Host "   DESPLIEGUE A PRODUCCIÓN FINALIZADO EXITOSAMENTE                 " -ForegroundColor Green
Write-Host "=====================================================================" -ForegroundColor Green
