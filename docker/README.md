# docker/

| Archivo | Propósito |
|---------|-----------|
| `Dockerfile.django-test` | Imagen `texcore-django-test` para correr las pruebas y los gates del backend (Ruff, mypy, Semgrep, detect-secrets, pip-audit) en un contenedor |

Los compose del sistema están en `infrastructure/docker/`:
- `docker-compose.yml` — desarrollo (incluye Redis, `celery_worker` y el frontend con Vite);
- `docker-compose.prod.yml` — producción (ver `docs/arquitectura/GUIA_DESPLIEGUE.md`).

En Windows se usan contenedores Linux con Docker Desktop (WSL 2); no hay variante de contenedores Windows.
