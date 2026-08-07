# TexCore — Sistema Integral de Gestión para la Industria Textil

TexCore es una plataforma integral de gestión industrial y trazabilidad para la industria textil que cubre todo el ciclo operativo: planificación de producción, transformación máquina a máquina, control de mermas, formulación química de tintura, gestión de inventarios (Kardex, MRP, atómico con `select_for_update()`), empaquetado/reetiquetado gobernado, ventas y logística de despacho con validación por escaneo de código de barras.

Arquitectura de **monolito modular (Django 5 + SQL Server 2022)** complementado con **servicios satélite autónomos (FastAPI)** comunicados mediante autenticación inter-servicio basada en **JWT RS256** (`internal_api`).

---

## 🚀 Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| **Backend Core** | Python 3.12 + Django 5.2 + Django REST Framework 3.16 |
| **Frontend UI** | React 18 + TypeScript 5 + Vite 7 + Tailwind CSS + Shadcn/UI + Radix UI |
| **Base de Datos** | Microsoft SQL Server 2022 (Nivel de aislamiento RCSI + Stored Procedures T-SQL) |
| **Servicios Satélite** | FastAPI + SQLAlchemy 2.0 (aiosqlite) — `scanning_service`, `reporting_excel`, `printing_service` |
| **Autenticación Inter-Servicio** | JWT RS256 vía `internal_api` (ISO 27001 A.10 / Criptografía RSA 2048) |
| **Pruebas y Calidad** | Pytest + Coverage (umbral ≥89%) + Vitest (998 tests frontend) + flake8 + bandit |
| **Gateway & Proxy** | Nginx (Reverse proxy + rate limiting + cabeceras de seguridad) |
| **CI / CD** | GitHub Actions (`.github/workflows/ci.yml`, `cd.yml`, `security.yml`, `rollback.yml`) y GitLab CI (`.gitlab-ci.yml`) |

---

## ⚡ Inicio Rápido

### Despliegue con Docker Compose (Desarrollo)

```bash
# 1. Clonar el repositorio y copiar configuración de entorno
cp .env.example .env

# 2. Desplegar servicios con Docker Compose
docker compose -f infrastructure/docker/docker-compose.yml --env-file .env up -d

# 3. Inicializar roles RBAC, permisos y cuenta administrador inicial
docker exec -it texcore-backend-1 python manage.py seed_production_masters
```

### URLs de Acceso

| Servicio / Interfaz | URL | Descripción |
|---------------------|-----|-------------|
| **Frontend Web** | `http://localhost:5173` | Aplicación React SPA (Vite Dev Server) |
| **API REST Backend & Docs** | `http://localhost:8000/api/docs/` | Documentación Swagger / OpenAPI 3 (drf-spectacular) |
| **Scanning Service** | `http://localhost:8000` | Microservicio satélite de validación por escaneo |
| **Printing Service** | `http://localhost:8001` | Microservicio satélite de generación de etiquetas ZPL / PDF |
| **Reporting Excel Service** | `http://localhost:8002` | Microservicio satélite de reportes gerenciales en Excel |

---

## 👥 Roles de Usuario y RBAC (11 Grupos)

El sistema implementa Control de Acceso Basado en Roles (RBAC) con 11 grupos predefinidos inicializados por `seed_production_masters`:

| Rol Slug | Nombre legible | Ámbito de Operación | Workflow de Agente |
|----------|----------------|---------------------|--------------------|
| `admin_sistemas` | Administrador de Sistemas | Configuración global, Sedes, Áreas, Bodegas, Usuarios y RBAC | [.agent/workflows/admin-sistemas.md](.agent/workflows/admin-sistemas.md) |
| `admin_sede` | Administrador de Sede | Gestión local de la sede, aprobaciones de inventario y personal local | [.agent/workflows/admin-sede.md](.agent/workflows/admin-sede.md) |
| `jefe_planta` | Jefe de Planta | Planificación de OPs, seguimiento de avance y transferencias interárea | [.agent/workflows/jefe-planta.md](.agent/workflows/jefe-planta.md) |
| `jefe_area` | Jefe de Área | Maquinaria, OEE, paros de máquina (Seis Pérdidas), mermas y líneas | [.agent/workflows/jefe-area.md](.agent/workflows/jefe-area.md) |
| `operario` | Operario de Planta | Registro de avance por lote, pesos y transformaciones en máquina | [.agent/workflows/operario.md](.agent/workflows/operario.md) |
| `tintorero` | Tintorero / Laboratorio | Formulación de color por sustrato, dosificación y exportación Infotint | [.agent/workflows/tintorero.md](.agent/workflows/tintorero.md) |
| `empaquetado` | Empaquetador | Registro de bultos, pesaje con tolerancia, impresión y supervisor override | [.agent/workflows/empaquetado.md](.agent/workflows/empaquetado.md) |
| `despacho` | Personal de Despacho | Validación de salida por escaneo de código de barras e historial | [.agent/workflows/despacho.md](.agent/workflows/despacho.md) |
| `bodeguero` | Bodeguero | Control de stock, transferencias entre bodegas, mermas y auditoría | [.agent/workflows/bodeguero.md](.agent/workflows/bodeguero.md) |
| `vendedor` | Vendedor Comercial | Gestión de clientes, límite de crédito, pedidos de venta y notas en PDF | [.agent/workflows/vendedor.md](.agent/workflows/vendedor.md) |
| `ejecutivo` | Ejecutivo / Gerencia | Dashboard de KPIs gerenciales y drill-down multi-bodega (solo lectura) | [.agent/workflows/ejecutivo.md](.agent/workflows/ejecutivo.md) |

---

## 📁 Estructura del Proyecto

```
TexCore/
├── frontend/                  # React SPA (TypeScript, Vite, TailwindCSS, Vitest)
├── gestion/                   # App Django — Producción, OPs, transformaciones, mermas, clientes, formulas
├── inventory/                 # App Django — StockBodega, MovimientoInventario, kardex, MRP, despacho
├── internal_api/              # App Django — Generación y validación de tokens JWT RS256 para microservicios
├── TexCore/                   # Configuración global Django (settings, settings_test, urls, wsgi, asgi)
├── scanning_service/          # Microservicio FastAPI — Validación de lotes escaneados por código de barras
├── reporting_excel/           # Microservicio FastAPI — Generación de reportes gerenciales en Excel
├── printing_service/          # Microservicio FastAPI — Generación de etiquetas de bulto ZPL y comprobantes PDF
├── database/                  # Dockerfiles y scripts T-SQL (V2 optimización SQL Server 2022, V3 Stored Procedures)
├── infrastructure/docker/     # Configuraciones docker-compose de desarrollo y producción (docker-compose.prod.yml)
├── nginx/                     # Reverse proxy Nginx con SSL/TLS, rate-limiting y proxy a servicios
├── docs/                      # Documentación técnica, manuales de arquitectura, base de datos y despliegue
├── .agent/workflows/          # Workflows operativos de agentes por rol (11 archivos .md)
├── .agents/rules/             # Reglas estandarizadas de calidad, pruebas y grafo de conocimiento (graphify)
├── .github/workflows/         # Pipeline CI/CD de GitHub Actions (ci.yml, cd.yml, security.yml, rollback.yml)
├── manage.py                  # CLI de administración Django
├── setup.cfg                  # Configuración unificada de pytest, coverage (fail_under = 89) y linters
├── package.json               # Scripts unificados del monorepo
└── requirements.txt           # Dependencias fijadas del backend principal
```

---

## 🧪 Pruebas y Verificación de Calidad

De acuerdo con los estándares del proyecto (ISTQB CTFL v4.0 e ISO/IEC 25010), ejecuta los siguientes comandos de verificación:

### 1. Pruebas Backend (Django DRF)
```bash
# Ejecución con Pytest
pytest gestion/ inventory/ internal_api/

# Ejecución con runner nativo Django y settings de prueba
python manage.py test --settings=TexCore.settings_test
```

### 2. Pruebas de Servicios Satélite (FastAPI)
```bash
(cd scanning_service && PYTHONPATH=. pytest tests)
(cd reporting_excel && PYTHONPATH=. pytest tests)
(cd printing_service && PYTHONPATH=. pytest tests)
```

### 3. Pruebas Frontend (React / TypeScript / Vitest)
```bash
# Verificación de tipos estáticos TypeScript
cd frontend && npx tsc --noEmit

# Pruebas unitarias e integración con Vitest (998+ tests)
npm test
```

---

## 📚 Documentación Adicional

- **[Índice Completo de Documentación](docs/README.md)**
- **[Arquitectura del Sistema](docs/arquitectura/ARQUITECTURA_SISTEMA.md)**: Vista C4, diagramas de secuencia, ERD y seguridad.
- **[Estándares de Desarrollo](docs/arquitectura/ESTANDARES_DESARROLLO.md)**: Convenciones de código, nombres de prueba ISTQB y principios SOLID.
- **[Guía de Despliegue en Producción](docs/arquitectura/GUIA_DESPLIEGUE.md)**: Procedimiento paso a paso para entorno on-premise / cloud.
- **[Gestión de Etiquetas y Reetiquetado](docs/modulos/GESTION_ETIQUETAS.md)**: Especificación de `EventoEtiqueta` y override supervisor in-situ.
- **[Changelog de Cambios](CHANGELOG.md)**: Registro histórico de versiones y características.

