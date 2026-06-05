# Scripts de Utilidad

Scripts de soporte para operaciones de desarrollo, despliegue y mantenimiento.

| Script | Propósito |
|--------|-----------|
| `generate_rsa_keys.py` | Genera par de claves RSA 2048 para JWT RS256. Produce salida compatible con `.env` (una línea con `\n`) |
| `create_db.py` | Crea la base de datos SQL Server si no existe. Útil para inicialización en entorno limpio |
| `reset_db_identities.sql` | Resetea los contadores de identidad en SQL Server (útil tras truncar tablas en desarrollo) |
| `ver-cambios-frontend.ps1` | Muestra cambios recientes en el frontend — útil para revisiones rápidas en Windows |

## Subdirectorios

| Carpeta | Descripción |
|---------|-------------|
| `tests/` | Scripts de smoke test y verificación manual de componentes (ver `tests/README.md`) |

## Uso frecuente

```bash
# Generar claves RSA para producción
python scripts/generate_rsa_keys.py

# Crear BD en entorno nuevo
python scripts/create_db.py
```
