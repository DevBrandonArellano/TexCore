# Script para ver cambios del frontend en TexCore
# Ejecutar desde: c:\Users\Sistemas\Desktop\Texcore\TexCore

Write-Host "=== Reconstruyendo frontend (nginx) ===" -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache nginx 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error en build. Ejecuta manualmente: docker compose -f docker-compose.yml -f docker-compose.prod.yml build --no-cache nginx" -ForegroundColor Red
    exit 1
}

Write-Host "=== Reiniciando nginx ===" -ForegroundColor Cyan
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --force-recreate nginx

Write-Host "`nListo. Abre http://localhost o https://localhost y haz Ctrl+Shift+R (recarga forzada) para evitar cache del navegador." -ForegroundColor Green
Write-Host "`nAlternativa rapida: usa http://localhost:5173 con el frontend en modo desarrollo (cambios al instante):" -ForegroundColor Yellow
Write-Host "  docker compose up -d frontend backend db" -ForegroundColor Gray
