# =============================================================================
# TEXCORE — DESPLIEGUE EN PRODUCCIÓN (WINDOWS / POWERSHELL)
# Se ejecuta desde la raíz del repositorio. Guía: docs/arquitectura/GUIA_DESPLIEGUE.md
# Sirve para la primera instalación y para cada actualización.
# =============================================================================

$ErrorActionPreference = "Stop"

$PROYECTO = "texcore-prod"  # nombre fijo: contenedores texcore-prod-<servicio>-1
$COMPOSE_FILE = "infrastructure/docker/docker-compose.prod.yml"
$ENV_FILE = ".env.prod"
# Tiempo máximo para que los contenedores queden sanos.
$ESPERA_SEGUNDOS = 900
$DESTINO_RESPALDOS = if ($env:DESTINO_RESPALDOS) { $env:DESTINO_RESPALDOS } else { "C:\respaldos\texcore" }

function Invoke-Compose {
    docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $($args -join ' ') terminó con código $LASTEXITCODE" }
}

# Mismo procedimiento que scripts/respaldar_bd.sh: si texcore_db existe, la respalda dentro
# del contenedor db (con su MSSQL_SA_PASSWORD) y copia el .bak al host.
function Invoke-RespaldarBD {
    $sqlcmd = '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -C -N -b -h -1 -W -Q "$0"'
    $existe = (Invoke-Compose exec -T db bash -c $sqlcmd "SET NOCOUNT ON; SELECT ISNULL(DB_ID(N'texcore_db'), 0)" | Out-String).Trim()
    if ($existe -eq "0") { Write-Host "texcore_db no existe todavía: no hay nada que respaldar."; return }
    $archivo = "texcore_$(Get-Date -Format 'yyyyMMdd_HHmmss').bak"
    Invoke-Compose exec -T db bash -c $sqlcmd "BACKUP DATABASE [texcore_db] TO DISK = N'/var/opt/mssql/backup/$archivo' WITH COMPRESSION, CHECKSUM, INIT"
    New-Item -ItemType Directory -Force -Path $DESTINO_RESPALDOS | Out-Null
    Invoke-Compose cp "db:/var/opt/mssql/backup/$archivo" "$DESTINO_RESPALDOS\"
    Invoke-Compose exec -T db rm -f "/var/opt/mssql/backup/$archivo"
    Write-Host "Respaldo listo: $DESTINO_RESPALDOS\$archivo"
}

if (-not (Test-Path $ENV_FILE)) {
    Write-Error "Falta $ENV_FILE. Copia .env.prod.example a $ENV_FILE y completa sus valores."
    exit 1
}

Write-Host "[1/5] Construyendo las imágenes de producción..." -ForegroundColor Yellow
Invoke-Compose build --pull

Write-Host "[2/5] Levantando SQL Server y respaldando la base actual (si existe)..." -ForegroundColor Yellow
docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE up -d --wait db
if ($LASTEXITCODE -ne 0) { throw "SQL Server no quedó sano. Revisa: docker compose logs db" }
Invoke-RespaldarBD

# En producción el backend no migra al arrancar (MIGRAR_AL_INICIAR=0): la base se prepara
# aquí, una vez, con la imagen nueva.
Write-Host "[3/5] Preparando la base con la versión nueva (migraciones y optimizaciones)..." -ForegroundColor Yellow
docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE run --rm --no-deps backend sh infrastructure/docker/preparar_bd.sh
if ($LASTEXITCODE -ne 0) { throw "preparar_bd.sh falló: la versión anterior sigue en ejecución y el respaldo está en $DESTINO_RESPALDOS" }

# printing y reporting_excel corren sin privilegios (UID 10001). Sus volúmenes de auditoría
# creados antes del 13-oct-2026 son de root: se ajusta el dueño (idempotente).
docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE run --rm --no-deps --user 0 --entrypoint chown printing -R 10001:10001 /data
docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE run --rm --no-deps --user 0 --entrypoint chown reporting_excel -R 10001:10001 /data

Write-Host "[4/5] Levantando los servicios y esperando a que estén sanos (hasta $ESPERA_SEGUNDOS s)..." -ForegroundColor Yellow
docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE up -d --wait --wait-timeout $ESPERA_SEGUNDOS
if ($LASTEXITCODE -ne 0) { throw "Los servicios no quedaron sanos a tiempo. Revisa: docker compose logs" }

Write-Host "[5/5] Sembrando los datos maestros iniciales (grupos RBAC y cuenta admin)..." -ForegroundColor Yellow
docker compose -p $PROYECTO -f $COMPOSE_FILE --env-file $ENV_FILE exec -T backend python manage.py seed_production_masters
if ($LASTEXITCODE -ne 0) { throw "seed_production_masters falló" }

Invoke-Compose ps
Write-Host "Despliegue terminado. Verifica la salud con: curl -k https://<host>/api/health/" -ForegroundColor Green
