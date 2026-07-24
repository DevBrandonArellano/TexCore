# entrypoint.ps1 - Script de PowerShell para inicializar el backend de Django en un contenedor de Windows.

# --- Función para esperar a la base de datos ---
function Wait-For-DB {
    param(
        [string]$Host,
        [int]$Port,
        [int]$Timeout = 60,
        [int]$RetryInterval = 5
    )

    Write-Host "Esperando a que la base de datos en '$($Host):$($Port)' esté disponible..."
    $ stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

    while ($stopwatch.Elapsed.TotalSeconds -lt $Timeout) {
        try {
            # Intenta establecer una conexión TCP con el host y puerto de la DB
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $tcpClient.Connect($Host, $Port)

            if ($tcpClient.Connected) {
                Write-Host "¡La conexión con la base de datos se ha establecido correctamente!"
                $tcpClient.Close()
                return $true
            }
        }
        catch {
            # La conexión falló, se reintentará
            Write-Host "La base de datos aún no está lista. Reintentando en $RetryInterval segundos..."
            Start-Sleep -Seconds $RetryInterval
        }
        finally {
            if ($tcpClient) {
                $tcpClient.Dispose()
            }
        }
    }

    Write-Error "No se pudo conectar a la base de datos después de $Timeout segundos."
    return $false
}

# --- Inicio del script principal ---

Write-Host "Iniciando script de entrada del backend (PowerShell)..."

# Termina el script inmediatamente si un comando falla.
$ErrorActionPreference = "Stop"

# Esperar a que la base de datos esté lista
# Lee las variables de entorno para la conexión
$db_host = $env:DB_HOST
$db_port = $env:DB_PORT

if (Wait-For-DB -Host $db_host -Port $db_port) {
    # La base de datos está lista, continuar con la inicialización.

    # 1. Asegurarse de que la base de datos exista
    Write-Host "Asegurando que la base de datos exista..."
    python create_db.py
    Write-Host "Verificación de la base de datos completa."

    # 2. Aplicar las migraciones de Django
    Write-Host "Aplicando migraciones de la base de datos..."
    python manage.py migrate
    Write-Host "Migraciones aplicadas con éxito."

    # 3. Ejecutar el comando principal pasado al contenedor (CMD en Dockerfile)
    Write-Host "Iniciando el proceso principal: $Args"
    & $Args
}
else {
    Write-Error "El script de entrada falló porque la base de datos no estuvo disponible a tiempo."
    exit 1
}
