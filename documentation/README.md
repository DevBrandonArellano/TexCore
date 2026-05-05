# Documentación Técnica de TexCore

Bienvenido a la base de conocimiento de TexCore. Aquí encontrarás guías detalladas sobre la arquitectura, despliegue, mantenimiento y procesos de negocio del sistema.

## 📚 Índice de Contenidos

### 1. Arquitectura y Datos
*   [**Arquitectura y Desarrollo**](arquitectura_y_desarrollo.md): Visión de alto nivel sobre la infraestructura, microservicios y filosofía de desarrollo del sistema.
*   [**Modelo de Datos y Procesos**](modelo_datos_proceso.md): Fuente de verdad sobre el esquema de base de datos (SQL Server), diagramas de flujo de negocio (Crédito, Ventas) y lógica logística (Kardex).
*   [**Recursos Algorítmicos**](recursos_algoritmicos.md): Explicación técnica sobre optimizaciones de rendimiento, índices de base de datos y solución al problema N+1 en querysets.

### 2. Infraestructura y Docker
*   [**Configuración de Docker**](docker_setup.md): Explicación detallada de la arquitectura de contenedores, volúmenes, redes y scripts de inicio (`deploy.sh`/`deploy.ps1`). Incluye sección de solución de problemas comunes.

### 3. Guías de Despliegue (Deployment)
*   [**Comandos de Producción**](comandos_produccion.md): Referencia rápida ("Cheatsheet") para operaciones comunes en servidores vivos (logs, reinicios, backups).
*   [**Despliegue en Ubuntu/Hyper-V**](guia_detallada_ubuntu_hyperv.md): Guía paso a paso para desplegar el sistema desde cero en un servidor Ubuntu virtualizado.

### 4. Seguridad y Autenticación
*   [**Troubleshooting de Autenticación**](authentication_troubleshooting.md): Guía para resolver problemas relacionados con JWT, Cookies HttpOnly y políticas CORS.

### 5. Análisis de Negocio y Roles
*   [**Manual de Roles y Permisos**](GUIA_ROLES_SISTEMA.md): Detalle de qué puede hacer cada usuario (Vendedor, Operario, Jefe de Planta, etc.) en el sistema.
*   [**Análisis Estratégico**](analisis_estrategico.md): Diagramas FODA y Causa-Raíz (Ishikawa) sobre el contexto del sector textil.

### 6. Arquitectura Frontend
*   [**Navegación Híbrida (URL State)**](../docs/IMPLEMENTACION_NAVEGACION_HIBRIDA.md): Detalles sobre la sincronización del estado de UI (paginación, filtros) con la URL en componentes React.
*   [**Decisión Arquitectónica (ADR)**](../docs/ADR_NAVEGACION_HIBRIDA.md): Explicación del porqué de la adopción del modelo híbrido para el sistema ERP.

### 7. Calidad y Aseguramiento (QA)
*   [**Plan de Pruebas Técnico (ISTQB)**](plan_pruebas_texcore.md): Documento comprehensivo con escenarios de prueba, lógica de negocio y casos de caja negra/blanca. Incluye 11 casos ISTQB para CU-EJ-07 (Sprint 6).
*   [**Walkthrough de Correcciones QA**](walkthrough_correcciones_qa.md): Detalle técnico de las correcciones implementadas tras la auditoría de QA (D-01 a D-06) y resultados de validación.

---

> **[Sprint 6 — 2026-04-10]**

### 8. Dashboard Ejecutivo y Reportes Gerenciales (Sprint 6)

Componentes nuevos implementados en el Sprint 6:

| Artefacto | Tipo | Descripción |
|-----------|------|-------------|
| `gestion/services/produccion_kpi_service.py` | Service Layer | `ProduccionKPIService` con Value Objects frozen (`ProduccionKPIs`, `OpsEstado`, `TendenciaDia`) |
| `inventory/services/executive_kpi_service.py` | Service Layer | `ExecutiveKPIService` con Value Objects frozen (`ExecutiveKPIs`, `MRPKPIs`, `StockKPIs`, `CarteraKPIs`) |
| `gestion/views.py` | Django Views | 3 nuevas vistas: `KpiEjecutivoView`, `ProduccionResumenView`, `ProduccionTendenciaView` |
| `gestion/urls.py` | Routing | 3 nuevos endpoints: `/kpi-ejecutivo/`, `/produccion/resumen/`, `/produccion/tendencia/` |
| `inventory/migrations/0020_produccion_reporting_sps.py` | BD | 3 Stored Procedures SQL Server para reportes gerenciales de producción |
| `reporting_excel/src/routers/produccion.py` | FastAPI | Router con 3 endpoints: `/ordenes`, `/lotes`, `/tendencia` |
| `frontend/…/EjecutivosDashboard.tsx` | React | Tab Reportes (CU-EJ-07): 6 exports Excel, validación fechas, loading state |
| `frontend/…/EjecutivosDashboard.reportes.test.tsx` | Tests | 11 tests ISTQB (EP + BVA + Transición de Estado) — todos pasan ✅ |

Documentación relacionada:
*   [**Datos para Dashboard Ejecutivo**](../docs/DATOS_PARA_DASHBOARD_EJECUTIVO.md): Endpoints, interfaces TypeScript y parámetros de los 6 reportes.
*   [**Diagramas de Secuencia — Ejecutivo**](../docs/diagramas_secuencia_usuarios.md): Flujos CU-EJ-01 y CU-EJ-07.
*   [**Guía de Roles**](GUIA_ROLES_SISTEMA.md): Sección actualizada del rol Ejecutivo con todos los CU implementados.
*   [**Modelo de Datos**](modelo_datos_proceso.md): Stored Procedures y flujos de datos Service Layer → SQL Server → Excel.
*   [**Arquitectura**](arquitectura_y_desarrollo.md): Service Layer diagram y componentes del microservicio `reporting_excel`.

---

## 💡 ¿Por dónde empezar?

- **Para desarrolladores nuevos:** Lee [Configuración de Docker](docker_setup.md) y [Modelo de Datos](modelo_datos_proceso.md).
- **Para DevOps/SysAdmin:** Revisa [Comandos de Producción](comandos_produccion.md) y la [Guía de Despliegue](guia_detallada_ubuntu_hyperv.md).
- **Para entender el negocio:** Consulta los diagramas en [Modelo de Datos y Procesos](modelo_datos_proceso.md).
- **Para el módulo ejecutivo:** Lee [Datos para Dashboard Ejecutivo](../docs/DATOS_PARA_DASHBOARD_EJECUTIVO.md) y la sección §8 de este índice.
