# Docker — Configuración específica por plataforma

Esta carpeta contiene archivos Docker para plataformas no-Linux (Windows). La configuración principal para Linux/Mac está en la raíz del proyecto.

| Archivo | Propósito |
|---------|-----------|
| `dockerfile.windows` | Dockerfile del backend adaptado para contenedores Windows |
| `docker-compose.windows.yml` | Compose para entorno Windows (SQL Server en contenedor Windows) |

## Uso en Windows

```powershell
# Desde la raíz del proyecto
docker compose -f docker/docker-compose.windows.yml up -d
```

> **Nota:** Los paths en `docker-compose.windows.yml` usan `..` para referenciar la raíz del proyecto desde esta subcarpeta.

## Configuración principal

Para Linux/Mac/WSL2 usa los archivos en la carpeta de infraestructura:
- `infrastructure/docker/docker-compose.yml` — Entorno de desarrollo
- `infrastructure/docker/docker-compose.prod.yml` — Entorno de producción
