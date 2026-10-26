# Reconstruye la imagen de nginx (que incluye el frontend compilado) en el entorno de
# desarrollo para ver los cambios del frontend servidos por nginx. Ejecutar desde la raíz.

$COMPOSE_FILE = "infrastructure/docker/docker-compose.yml"

Write-Host "=== Reconstruyendo frontend (nginx) ===" -ForegroundColor Cyan
docker compose -f $COMPOSE_FILE build --no-cache nginx
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en build. Ejecuta manualmente: docker compose -f $COMPOSE_FILE build --no-cache nginx" -ForegroundColor Red
    exit 1
}

Write-Host "=== Reiniciando nginx ===" -ForegroundColor Cyan
docker compose -f $COMPOSE_FILE up -d --force-recreate nginx

Write-Host "`nListo. Abre https://localhost y haz Ctrl+Shift+R (recarga forzada) para evitar la caché del navegador." -ForegroundColor Green
Write-Host "`nAlternativa rápida: http://localhost:5173 con el frontend en modo desarrollo (cambios al instante):" -ForegroundColor Yellow
Write-Host "  docker compose -f $COMPOSE_FILE up -d frontend backend db" -ForegroundColor Gray
