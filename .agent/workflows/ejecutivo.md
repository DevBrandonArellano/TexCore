---
description: Supervisión ejecutiva global, consulta de indicadores de negocio, ventas e inventario por bodega.
---

1. **Dashboard Ejecutivo**: Monitorear KPIs globales de negocio (`EjecutivosDashboard.tsx`): Ventas Totales ($), Pedidos Pendientes, Margen Promedio (%), Cumplimiento de Órdenes (%) y OEE Consolidado.
2. **Navegación Drill-Down (`DrillDownModals.tsx`)**:
   - **Pedidos por Estado**: Filtrar y consultar pedidos vigentes por estado comercial.
   - **Inventario por Bodega**: Visualizar el contenido y existencias en tiempo real de la bodega seleccionada.
   - **Clientes Top**: Consultar el desglose de ventas por cliente principal.
   - **Cumplimiento de Órdenes**: Analizar el porcentaje de cumplimiento y avance de producción de las OPs.
3. **Modo Solo Lectura**: Acceso de consulta multi-sede y multi-bodega sin permisos de mutación sobre datos operativos.
