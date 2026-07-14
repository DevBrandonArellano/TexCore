# TexCore — Sistema Integral de Gestión para la Industria Textil

Sistema de gestión de órdenes de producción para la industria textil que gestiona el ciclo completo de operaciones: producción, inventario, ventas y despacho. Arquitectura de monolito con servicios satélites contenerizados con trazabilidad total desde la orden de venta hasta el despacho de producto terminado.

---

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Backend** | Python 3.12 + Django 5 + Django REST Framework |
| **Frontend** | React + TypeScript + Vite + TailwindCSS + Shadcn/UI |
| **Base de datos** | Microsoft SQL Server 2022 |
| **Servicios Satélites** | FastAPI — scanning, reporting_excel, printing_service |
| **Auth servicio-a-servicio** | JWT RS256 via `internal_api` Django app |
| **Tareas asíncronas** | Celery + Redis |
| **Gateway** | Nginx (reverse proxy + rate limiting + cabeceras de seguridad) |
| **Servidor de producción** | Gunicorn |
| **CI/CD** | GitHub Actions + GitLab CI |

---

## Inicio Rápido

```bash
# Linux / macOS / WSL2
./scripts/deploy/deploy.sh

# Windows (PowerShell)
./scripts/deploy/deploy.ps1

# Docker Compose Manual (Dev)
docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up -d

# Windows con contenedores Windows
docker compose -f docker/docker-compose.windows.yml up -d
```

### Acceso

| Servicio | URL |
|----------|-----|
| Frontend | http://localhost:5173 |
| API + Swagger | http://localhost:8000/api/docs/ |
| Scanning service | http://localhost:8001 (vía Nginx) |
| Reporting service | http://localhost:8002 (interno) |

### Datos de prueba

```bash
docker exec texcore-backend-1 python manage.py seed_data
```

Todos los usuarios de prueba usan la contraseña `password123`.

---

## Estructura del Proyecto

```
TexCore/
├── frontend/              # React SPA
├── gestion/               # Django app — producción, ventas, clientes, fórmulas
├── inventory/             # Django app — kardex, stock, despacho, MRP
├── internal_api/          # Django app — API interna JWT RS256 para servicios satélites
├── TexCore/               # Configuración Django (settings, urls, wsgi)
├── scanning_service/      # FastAPI — validación de lotes escaneados
├── reporting_excel/       # FastAPI — exportación a Excel via stored procedures
├── printing_service/      # FastAPI — generación de etiquetas ZPL y PDFs
├── nginx/                 # Configuración de Nginx
├── database/              # Dockerfiles y scripts de inicialización de SQL Server
├── scripts/               # Utilidades de desarrollo y despliegue
│   ├── generate_rsa_keys.py
│   ├── create_db.py
│   └── tests/             # Smoke tests y verificaciones manuales
├── docker/                # Docker para Windows (compose + dockerfile)
├── docs/                  # Documentación técnica y funcional
└── .github/               # GitHub Actions workflows
```

---

## Testing

```bash
# Suite completa backend con SQL Server (via Docker — recomendado)
./scripts/run_backend_tests.sh

# Suite principal Django (lógica de negocio + inventario)
docker exec texcore-backend-1 python manage.py test gestion.tests_integrados

# Tests de inventario y despacho
docker exec texcore-backend-1 python manage.py test inventory.tests

# Tests locales sin SQL Server (SQLite, requiere --no-migrations)
python manage.py test --settings=TexCore.settings_test_local gestion.tests --no-migrations

# Tests del servicio satélite reporting_excel
docker compose run --rm -e PYTHONPATH=/app reporting_excel pytest -v tests/
```

---

## Documentación

**[Índice completo de documentación](docs/README.md)**

| Documento | Descripción |
|-----------|-------------|
| [Arquitectura del Sistema](docs/arquitectura/ARQUITECTURA_SISTEMA.md) | Referencia técnica definitiva — C4, ERD, APIs, flujos |
| [Guía de Despliegue](docs/arquitectura/GUIA_DESPLIEGUE.md) | Despliegue en producción paso a paso |
| [Docker Setup](docs/arquitectura/DOCKER_SETUP.md) | Infraestructura de contenedores |
| [Comandos de Operación](docs/arquitectura/COMANDOS_OPERACION.md) | Cheatsheet para sysadmins |
| [Modelo de Datos](docs/arquitectura-bd/MODELO_DATOS.md) | Esquemas SQL y relaciones del dominio |
| [Roadmap](ROADMAP.md) | Hitos y visión a futuro |
| [Changelog](CHANGELOG.md) | Registro de cambios |

---

## Contribución

1. Finales de línea en **LF** — configura `git config core.autocrlf false`.
2. Actualiza `gestion/tests_integrados.py` al modificar reglas de negocio.
3. Documenta cambios en `CHANGELOG.md` siguiendo el formato existente.
4. No commitear archivos `.pem`, `.env` ni logs.
