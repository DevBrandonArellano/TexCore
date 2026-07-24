# Scripts de Utilidad

Scripts de soporte para operaciones de desarrollo, despliegue y mantenimiento.

| Script | Propósito |
|--------|-----------|
| `generate_rsa_keys.py` | Genera par de claves RSA 2048 para JWT RS256. Produce salida compatible con `.env` (una línea con `\n`) |
| `create_db.py` | Crea la base de datos SQL Server si no existe. Útil para inicialización en entorno limpio |
| `reset_db_identities.sql` | Resetea los contadores de identidad en SQL Server (útil tras truncar tablas en desarrollo) |
| `ver-cambios-frontend.ps1` | Muestra cambios recientes en el frontend — útil para revisiones rápidas en Windows |
| `run_backend_tests.sh` | Levanta SQL Server 2022 en Docker y ejecuta la suite completa de tests Django con cobertura |

## Subdirectorios

| Carpeta | Descripción |
|---------|-------------|
| `deploy/` | Scripts de despliegue para Linux (`deploy.sh`) y Windows PowerShell (`deploy.ps1`) |
| `tests/` | Scripts de smoke test y verificación manual de componentes (ver `tests/README.md`) |

## Uso frecuente

```bash
# Generar claves RSA para producción
python scripts/generate_rsa_keys.py

# Crear BD en entorno nuevo
python scripts/create_db.py

# Ejecutar suite completa de tests backend (Docker — recomendado)
./scripts/run_backend_tests.sh

# Despliegue Linux/WSL
./scripts/deploy/deploy.sh

# Despliegue Windows (PowerShell)
# Detecta automáticamente Docker Compose v1 (docker-compose) vs v2 (docker compose)
./scripts/deploy/deploy.ps1
```

## Notas de configuración de entorno

- **`.env` es requerido** en la raíz del proyecto para desarrollo local. `manage.py` lo carga con prioridad sobre `.env.test`.
- Si `.env` no existe, `deploy.sh`/`deploy.ps1` copian `.env.example` como base automáticamente.
- El frontend Vite corre en `:5173` — las variables `CORS_ALLOWED_ORIGINS` y `CSRF_TRUSTED_ORIGINS` deben incluir `http://localhost:5173`.
- Para Docker Windows, `docker/docker-compose.windows.yml` ya incluye las variables obligatorias del backend.
