# Roadmap del Proyecto TexCore

Este documento describe los próximos pasos y futuras mejoras planificadas para el sistema TexCore. La base actual del proyecto es estable, con una gestión de datos dinámica para los módulos principales. Las siguientes fases se centran en expandir la funcionalidad, mejorar la experiencia de usuario y preparar el sistema para producción.

---

### Fase 1: Completar la Integración de Datos y Mejorar la UI (A corto plazo)

El objetivo de esta fase es reemplazar todos los datos de prueba restantes y mejorar la robustez de los componentes de gestión actuales.

-   **[✓] Eliminar Datos de Prueba (`mockData`):**
    -   **Completado:** El panel de administración (`AdminSistemasDashboard`) ya no utiliza datos quemados. Toda la información (Productos, Químicos, Bodegas, Órdenes de Producción, etc.) se carga ahora desde la API.

-   **[✓] Corregir Persistencia de Datos y Refactorizar Estado:**
    -   **Completado:** Se refactorizó el CRUD de usuarios para asegurar que los datos se guarden en el backend y persistan entre sesiones. La lógica de estado se centralizó en `AdminSistemasDashboard` para una única fuente de verdad.

-   **[✓] Crear Componentes de Gestión Dedicados:**
    -   **Completado:** Se han creado componentes con funcionalidad CRUD completa para `Productos`, `Químicos`, `Fórmulas`, `Clientes` y `Bodegas`.

-   **[✓] Mejorar la Experiencia de Usuario (UX) en las Tablas de Gestión:**
    -   **Búsqueda y Filtrado:** Se añadieron campos de búsqueda en todas las tablas de gestión.
    -   **Paginación:** Se implementó paginación en todas las tablas de gestión.
    -   **Feedback Visual:** Se añadieron indicadores de carga (esqueletos) mientras se obtienen los datos iniciales.

-   **[✓] Configurar Sistema de Logs en Backend:**
    -   **Completado:** Se ha configurado un sistema de logging en Django que captura los errores del servidor en un archivo `logs/backend.log` para facilitar la depuración.

---

### Fase 2: Lógica de Negocio Principal y Módulo Logístico (A mediano plazo)

Esta fase se centra en desarrollar los flujos de trabajo que son el corazón del sistema, con un nuevo enfoque en la gestión logística avanzada.

-   **[✓] Módulo Logístico Avanzado - Refactorización de Inventario:**
    -   **Completado:** Se ha refactorizado por completo el sistema de inventario, reemplazando los modelos anteriores por una estructura robusta (`StockBodega`, `MovimientoInventario`) que permite una trazabilidad precisa.
    -   **Completado:** Se implementó una API transaccional (`/api/inventory/transferencias/`) para mover stock entre bodegas de forma atómica, garantizando la integridad de los datos.

-   **[✓] Refactorización Arquitectónica del Inventario:**
    -   **Completado:** Se unificó el modelo `Chemical` dentro del modelo `Producto` (con un tipo "quimico"). Este cambio crucial permite que el inventario de químicos sea gestionado con las mismas reglas que el resto de productos, habilitando el control de stock y el consumo automático.

-   **[✓] Flujo de Órdenes de Producción:**
    -   **Completado:** Se ha desarrollado la interfaz para el CRUD de `Ordenes de Producción` y el cambio de estados (`pendiente` -> `en_proceso` -> `finalizada`).
    -   **[✓] Implementar la lógica para asociar `Lotes de Producción` a una orden existente.**
        -   **Completado:** Se implementó una API (`/api/ordenes-produccion/<id>/registrar-lote/`) y una interfaz en el panel del Jefe de Planta para registrar lotes. Esta acción descuenta automáticamente del inventario tanto el producto base (ej. hilo crudo) como los químicos de la fórmula asociada, garantizando la consistencia del stock en tiempo real.


-   **[ ] Flujo de Ventas:**
    -   Desarrollar la interfaz para la creación y gestión de `Pedidos de Venta`.
    -   Implementar la lógica para asociar `Detalles de Pedido` a un pedido.
    -   Integrar el despacho de pedidos con el descuento de inventario del `StockBodega`.

---

### Fase 3: Paneles de Control (Dashboards) y Reportería (A largo plazo)

Con los flujos de negocio en funcionamiento, el siguiente paso es proporcionar herramientas para el análisis y la toma de decisiones.

-   **[ ] Dashboards Dinámicos y por Rol:**
    -   Crear paneles de control visuales con KPIs (Indicadores Clave de Rendimiento) relevantes para cada rol.
    -   **Ejemplos:**
        -   **Jefe de Planta:** Visualización del estado de las órdenes de producción, eficiencia de máquinas.
        -   **Jefe de Logística:** Niveles de stock por bodega, alertas de stock bajo.
        -   **Ejecutivo:** Gráficos de ventas, valorización de inventario.

-   **[ ] Módulo de Reportería Avanzada:**
    -   **[✓] API de Reporte Kardex:** Se ha implementado el endpoint `/api/bodegas/{id}/kardex/?producto_id={id}` que sirve como base para cualquier reporte de trazabilidad.
    -   **[ ] Interfaz de Usuario para Reportes:** Desarrollar una sección en el frontend para generar y visualizar reportes (Kardex, Resumen de Inventario, etc.) en PDF o Excel.

---

### Fase 4: Pruebas y Despliegue a Producción

La fase final para asegurar la calidad y estabilidad del sistema.

-   **[ ] Pruebas Unitarias y de Integración (Backend):**
    -   Escribir pruebas con `pytest` para todos los endpoints de la API y la lógica de negocio en Django, especialmente para el módulo de inventario.

-   **[ ] Pruebas de Componentes y End-to-End (Frontend):**
    -   Utilizar herramientas como `Jest` y `React Testing Library` para probar los componentes de React.
    -   Implementar pruebas E2E con `Cypress` o `Playwright` para validar los flujos de usuario completos (ej. una transferencia).

-   **[ ] Documentación para Despliegue:**
    -   Crear una guía detallada para desplegar el proyecto en un entorno de producción.
    -   Incluir configuraciones recomendadas para `Docker`, `Gunicorn`, `Nginx` y la gestión de variables de entorno.

---

### Fase 5: Mantenimiento y Optimizaciones Futuras

Mejoras continuas y nuevas funcionalidades para expandir las capacidades del sistema.

-   **[✓] Alertas de Stock:**
    -   **Completado:** Se ha implementado un endpoint (`/api/inventory/alertas-stock/`) que lista los productos por debajo de su nivel de stock mínimo definido.

-   **[ ] Optimización de Consultas:**
    -   Analizar y optimizar las consultas a la base de datos que presenten cuellos de botella a medida que el volumen de datos crezca.

-   **[ ] Roles y Permisos Avanzados:**
    -   Refinar los permisos para un control más granular (ej. permisos por bodega o por tipo de producto).
