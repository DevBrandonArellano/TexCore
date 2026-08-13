---
description: Planificación de órdenes, seguimiento y trazabilidad completa de producción.
---

1.  **Planificación y Seguimiento (Torre de Control)**: Visualizar el Pulso Diario con métricas en tiempo real de Cumplimiento Diario, Índice de Desperdicio y Alerta de WIP Estancado en tarjetas de alto impacto.
2.  **Gestión Paginada de OP**: Visualización, filtrado (por estado y máquina) y búsqueda de Órdenes de Producción renderizadas desde el backend con paginación server-side.
3.  **Validación Predictiva de Stock**: Al acceder al detalle de una orden pendiente, el sistema evalúa automáticamente los requisitos frente al stock disponible, deshabilitando el botón de "Iniciar Proceso" y mostrando una alerta preventiva si el stock es insuficiente para cumplirla.
4.  **Detalle de OP (clic en fila)**: Panel lateral (`Sheet`) con información unificada: Producto, Fórmula Color, Sede, Área Responsable, y barra de **Rendimiento (Yield)** (% de peso producido vs requerido con código de colores preventivo). Desde el panel se puede editar, eliminar o cambiar estado (sujeto a validación de stock).
5.  **Trazabilidad de Orden (solo lectura)**: Árbol completo de transformaciones máquina a máquina: cadena de productos y merma acumulada.
6.  **Gestión de Requerimientos**: Consulta detallada de materiales y verificación asíncrona de disponibilidad de inventario.
7.  **Coordinación de Transferencias Interárea**: Registra las transferencias de producción cuando una orden termina en un área y pasa a la siguiente.
8.  **Reportes PDF Gerenciales**: Generación de reportes unificados ("Avance Operativo" y "Balance de Masas") accesibles mediante el menú de Acciones Gerenciales.
