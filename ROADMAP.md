# Roadmap del Proyecto TexCore

Este documento describe los próximos pasos y futuras mejoras planificadas para el sistema TexCore. La base actual del proyecto es estable, con una gestión de datos dinámica para los módulos principales. Las siguientes fases se centran en expandir la funcionalidad, mejorar la experiencia de usuario y preparar el sistema para producción.

---

### Fase 1: Completar la Integración de Datos y Mejorar la UI (A corto plazo)

El objetivo de esta fase es reemplazar todos los datos de prueba restantes y mejorar la robustez de los componentes de gestión actuales.

-   **[✓] Eliminar Datos de Prueba (`mockData`):**
    -   **Completado:** El panel de administración (`AdminSistemasDashboard`) ya no utiliza datos quemados. Toda la información (Productos, Químicos, Bodegas, Órdenes de Producción, etc.) se carga ahora desde la API.

-   **[✓] Corregir Persistencia de Datos y Refactorizar Estado:**
    -   **Completado:** Se refactorizó el CRUD de usuarios para asegurar que los datos se guarden en el backend y persistan entre sesiones. La lógica de estado se centralizó en `AdminSistemasDashboard` para una única fuente de verdad.

-   **[ ] Crear Componentes de Gestión Dedicados:**
    -   Actualmente, los datos de `Productos`, `Químicos`, `Fórmulas`, etc., solo se visualizan. El siguiente paso es crear componentes de gestión (CRUD) para cada uno, similar a como funcionan `ManageUsers`, `ManageSedes` y `ManageAreas`.
    -   **Componentes a crear:**
        -   `ManageProductos`
        -   `ManageQuimicos`
        -   `ManageFormulas`
        -   `ManageClientes`
        -   `ManageBodegas`

-   **[ ] Mejorar la Experiencia de Usuario (UX) en las Tablas de Gestión:**
    -   **Búsqueda y Filtrado:** Añadir campos de búsqueda y filtros en las tablas de `ManageUsers`, `ManageSedes` y `ManageAreas` para facilitar la localización de registros.
    -   **Paginación:** Implementar paginación en todas las tablas para manejar de forma eficiente grandes volúmenes de datos.
    -   **Feedback Visual:** Añadir indicadores de carga (esqueletos o *spinners*) mientras se obtienen los datos de la API para mejorar la percepción de rendimiento.

---

### Fase 2: Implementar la Lógica de Negocio Principal (A mediano plazo)

Esta fase se centra en desarrollar los flujos de trabajo que son el corazón del sistema.

-   **[ ] Flujo de Movimientos de Inventario:**
    -   **Registro por Operario:** Integrar el `InventoryForm` en un flujo de trabajo completo para que los operarios puedan registrar entradas y salidas de material.
    -   **Flujo de Aprobación:** Crear la interfaz para que un `jefe_area` o `admin_sede` pueda revisar, aprobar o rechazar los movimientos de inventario pendientes.

-   **[ ] Flujo de Órdenes de Producción:**
    -   Desarrollar la interfaz para crear y dar seguimiento a las `Ordenes de Producción`.
    -   Implementar la lógica para asociar `Lotes de Producción` a una orden existente.
    -   Controlar el consumo de inventario (químicos y materiales) basado en las fórmulas y la producción.

-   **[ ] Flujo de Ventas:**
    -   Desarrollar la interfaz para la creación y gestión de `Pedidos de Venta`.
    -   Implementar la lógica para asociar `Detalles de Pedido` a un pedido.
    -   Integrar el despacho de pedidos con el descuento de inventario.

---

### Fase 3: Paneles de Control (Dashboards) y Reportes (A largo plazo)

Con los flujos de negocio en funcionamiento, el siguiente paso es proporcionar herramientas para el análisis y la toma de decisiones.

-   **[ ] Dashboards Dinámicos y por Rol:**
    -   Crear paneles de control visuales con KPIs (Indicadores Clave de Rendimiento) relevantes para cada rol.
    -   **Ejemplos:**
        -   **Jefe de Planta:** Visualización del estado de las órdenes de producción, eficiencia de máquinas, etc.
        -   **Ejecutivo:** Gráficos de ventas, niveles de inventario generales, etc.
        -   **Operario:** Resumen de sus movimientos registrados y estado.

-   **[ ] Módulo de Reportería:**
    -   Desarrollar una sección para generar reportes en PDF o Excel.
    -   **Ejemplos de reportes:**
        -   Historial de movimientos de un material.
        -   Resumen de inventario valorizado.
        -   Reporte de eficiencia de producción por lote.

---

### Fase 4: Pruebas y Despliegue a Producción

La fase final para asegurar la calidad y estabilidad del sistema.

-   **[ ] Pruebas Unitarias y de Integración (Backend):**
    -   Escribir pruebas con `pytest` para todos los endpoints de la API y la lógica de negocio en Django.

-   **[ ] Pruebas de Componentes y End-to-End (Frontend):**
    -   Utilizar herramientas como `Jest` y `React Testing Library` para probar los componentes de React.
    -   Implementar pruebas E2E con `Cypress` o `Playwright` para validar los flujos de usuario completos.

-   **[ ] Documentación para Despliegue:**
    -   Crear una guía detallada para desplegar el proyecto en un entorno de producción.
    -   Incluir configuraciones recomendadas para `Docker`, `Gunicorn`, `Nginx` y la gestión de variables de entorno.
