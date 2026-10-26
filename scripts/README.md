# Scripts de Utilidad

Scripts de soporte para operaciones de desarrollo, despliegue y mantenimiento.

| Script | Propósito |
|--------|-----------|
| `generate_rsa_keys.py` | Genera par de claves RSA 2048 para JWT RS256. Produce salida compatible con `.env` (una línea con `\n`) |
| `create_db.py` | Crea la base de datos SQL Server si no existe. Útil para inicialización en entorno limpio |
| `ver-cambios-frontend.ps1` | Muestra cambios recientes en el frontend — útil para revisiones rápidas en Windows |
| `deploy_production.sh` / `.ps1` | Único despliegue a **producción**: construye, levanta con `up --wait` y siembra los maestros (ver `docs/arquitectura/GUIA_DESPLIEGUE.md`) |
| `run_backend_tests.sh` | Levanta SQL Server 2022 en Docker y ejecuta la suite completa de tests Django con cobertura |

## Subdirectorios

| Carpeta | Descripción |
|---------|-------------|
| `deploy/` | Levantan el entorno de **desarrollo** (`infrastructure/docker/docker-compose.yml`): `deploy.sh` (Linux/macOS/WSL) y `deploy.ps1` (Windows, Docker Desktop) |
| `tests/` | Scripts de smoke test y verificación manual de componentes (ver `tests/README.md`) |

## Uso frecuente

```bash
# Generar claves RSA para producción
python scripts/generate_rsa_keys.py

# Crear BD en entorno nuevo
python scripts/create_db.py

# Ejecutar suite completa de tests backend (Docker — recomendado)
./scripts/run_backend_tests.sh

# Entorno de desarrollo (Linux/macOS/WSL o Windows con Docker Desktop)
./scripts/deploy/deploy.sh
./scripts/deploy/deploy.ps1

# Producción (servidor con .env.prod; ver docs/arquitectura/GUIA_DESPLIEGUE.md)
bash scripts/deploy_production.sh
```

## Notas de configuración de entorno

- **`.env` es requerido** en la raíz del proyecto para desarrollo local. `manage.py` lo carga con prioridad sobre `.env.test`.
- Si `.env` no existe, `deploy.sh`/`deploy.ps1` copian `.env.example` como base automáticamente.
- El frontend Vite corre en `:5173` — las variables `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` deben incluir `http://localhost:5173`.
- En Windows se usan contenedores Linux (Docker Desktop con WSL 2); no hay variante de contenedores Windows.
