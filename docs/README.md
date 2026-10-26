# TexCore — Índice de Documentación

> Base de conocimiento técnico y funcional del sistema de gestión de órdenes de producción para la industria textil.

---

## Manuales de Usuario

| Documento | Descripción |
|-----------|-------------|
| [Índice de Manuales de Usuario](manuales-usuario/README.md) | Guía paso a paso por rol, lista para entregar a los usuarios finales del sistema |

---

## Historias de Usuarios

| Documento | Descripción |
|-----------|-------------|
| [Roles y Permisos](historias-usuarios/ROLES_Y_PERMISOS.md) | Matriz de roles RBAC: permisos por módulo y sede |
| [HU Módulo Ventas](historias-usuarios/HU_MODULO_VENTAS.md) | Historias de usuario — flujos del rol Vendedor |
| [HU Módulo Producción](historias-usuarios/HU_MODULO_PRODUCCION.md) | Historias de usuario — flujos de producción y operarios |

---

## Requerimientos

| Documento | Descripción |
|-----------|-------------|
| [Plan de Pruebas](requerimientos/PLAN_PRUEBAS.md) | Estrategia de testing: unitario, integración, E2E |
| [Registro de Riesgos](requerimientos/REGISTRO_RIESGOS.md) | Riesgos del proyecto con impacto, probabilidad y mitigación |
| [Auditoría de Calidad](requerimientos/AUDITORIA_CALIDAD.md) | Resultados de auditoría ISO/IEC 25010 |
| [Plan de Mejora](requerimientos/PLAN_MEJORA.md) | Hoja de ruta de mejoras priorizadas |
| [Evidencia de Rendimiento y Usabilidad](requerimientos/EVIDENCIA_RENDIMIENTO_USABILIDAD.md) | RNF-03 y RNF-05 contrastados con la tesis: Locust con 100 y 250 usuarios sobre 3 años de datos |
| [Evidencia por Sprint](gestion-proyecto/evidencia/EVIDENCIA_POR_SPRINT.md) | Pruebas automatizadas de cada historia, por sprint, sobre SQL Server 2022 (generado) |
| [Contraste de la Tesis](gestion-proyecto/evidencia/CHECKLIST_EVIDENCIA_MANUAL.md) | Veredicto por compromiso de la tesis: DoD, RNF, despliegue y puesta en marcha |
| [Correcciones a la Tesis](gestion-proyecto/evidencia/CORRECCIONES_TESIS.md) | Afirmaciones del texto que no coinciden con el sistema entregado |

---

## Diagramas UML

| Documento | Descripción |
|-----------|-------------|
| [Diagramas de Secuencia](diagramas-uml/DIAGRAMAS_SECUENCIA.md) | Flujos por rol: vendedor, bodeguero, encargado de despacho, etc. |

---

## Arquitectura del Proyecto

| Documento | Descripción |
|-----------|-------------|
| [**Arquitectura del Sistema**](arquitectura/ARQUITECTURA_SISTEMA.md) | Referencia técnica definitiva — C4, ERD, APIs, flujos, ADRs |
| [Monolito con Servicios Satélites vs Monolito Puro](arquitectura/MICROSERVICIOS.md) | Análisis comparativo y decisión arquitectónica |
| [Servicio Satélite de Impresión](arquitectura/MICROSERVICIO_IMPRESION.md) | Detalle técnico del printing_service (ZPL, Zebra) |
| [Docker Setup](arquitectura/DOCKER_SETUP.md) | Configuración de contenedores para dev y producción |
| [Guía de Despliegue y Operación](arquitectura/GUIA_DESPLIEGUE.md) | Servidor Ubuntu/Hyper-V, `.env.prod`, certificados, despliegue con `scripts/deploy_production.sh`, operación, respaldos y rollback |
| [Requisitos de Infraestructura](arquitectura/REQUISITOS_INFRAESTRUCTURA.md) | CPU/RAM/workers por contenedor y tamaño de la VM para 100 y 250 usuarios concurrentes, medidos con 3 años de datos (Locust, 8-oct-2026) |
| [Estándares de Desarrollo](arquitectura/ESTANDARES_DESARROLLO.md) | Convenciones de código, ramas git, commits |
| [Grafo de Conocimiento (Graphify)](arquitectura/GRAFO_CONOCIMIENTO.md) | Configuración, automatización y consultas del grafo de dependencias |
| [ADR-001 Navegación Híbrida](arquitectura/ADR/ADR_001_NAVEGACION_HIBRIDA.md) | Decision Record: useSearchParams para estado de UI |
| [ADR-008 Texto vacío sin NULL](arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md) | Cadenas vacías en vez de `NULL` en campos de texto |
| [ADR-009 Lote con varios productos](arquitectura/ADR/ADR_009_LOTE_CON_VARIOS_PRODUCTOS.md) | Un lote de producción puede tener varios productos vendibles |
| [ADR-010 Rendimiento de stock y auditoría](arquitectura/ADR/ADR_010_RENDIMIENTO_STOCK_Y_AUDITORIA.md) | Stock paginado y auditoría filtrable por índice |
| [ADR-011 Equivalencias de empaque](arquitectura/ADR/ADR_011_EQUIVALENCIAS_EMPAQUE_SIN_CONSTANTE.md) | Equivalencias configurables por sede, sin constantes |
| [ADR-012 MRP por sede](arquitectura/ADR/ADR_012_MRP_POR_SEDE.md) | Cálculo de necesidades por sede, sugerencias de compra informativas |

---

## Arquitectura de Base de Datos

| Documento | Descripción |
|-----------|-------------|
| [Modelo de Datos](arquitectura-bd/MODELO_DATOS.md) | ERD completo y descripción de entidades |
| [Diccionario de Eliminación](arquitectura-bd/DICCIONARIO_ELIMINACION.md) | Reglas de eliminación en cascada y soft-delete |
| [Performance](arquitectura-bd/PERFORMANCE.md) | Reporte de rendimiento de queries críticos |
| [Optimizaciones de Queries](arquitectura-bd/OPTIMIZACIONES_QUERIES.md) | Índices, select_related, prefetch_related aplicados |

---

## Módulos del Sistema

| Documento | Descripción |
|-----------|-------------|
| [Análisis Sistema Despacho](modulos/ANALISIS_SISTEMA_DESPACHO.md) | Análisis completo del módulo de despacho — flujos, API interna, modelos |
| [Implementación Despacho](modulos/DESPACHO_IMPLEMENTACION.md) | Detalle de implementación técnica del módulo de despacho |
| [Reversión de Despacho](modulos/REVERSION_DESPACHO.md) | Flujo de reversión de despachos con auditoría |
| [Dashboard Ejecutivo](modulos/DASHBOARD_EJECUTIVO.md) | KPIs y datos expuestos en el dashboard ejecutivo |
| [Navegación Híbrida](modulos/NAVEGACION_HIBRIDA.md) | Implementación de navegación con useSearchParams |
| [Descarga de Químicos](modulos/DESCARGA_QUIMICOS.md) | Módulo de tintorería — descarga automática de químicos |
| [Reversión de Pagos](modulos/REVERSION_PAGOS.md) | Flujo de reversión de pagos de clientes |
| [Gestión de Etiquetas](modulos/GESTION_ETIQUETAS.md) | Reetiquetado, reimpresión gobernada, búsqueda por fechas e impresión real (Zebra/PDF) |
| [Auditoría y Mejoras del Rol Jefe de Área](modulos/AUDITORIA_JEFE_AREA.md) | Comparativa con la industria (ISA-95, OEE, ISO 9001, TPM); KPIs reales (Yield/FPY), rechazo con motivo y fix RBAC de reetiquetado |

---

## 📊 Análisis, Normas y Trazabilidad

| Documento | Descripción |
|-----------|-------------|
| [Auditoría de Cumplimiento ANSI/ISA/VDI](analisis_y_reportes/auditoria_cumplimiento_ANSI_ISA_VDI.md) | Verificación de estándares internacionales (ANSI/ISA-95, ISA-88, VDI 5600, ISO 22400) |
| [Matriz de Trazabilidad de Pruebas](matriz_trazabilidad_pruebas.md) | Mapeo entre requerimientos de negocio, historias de usuario y casos de prueba |

