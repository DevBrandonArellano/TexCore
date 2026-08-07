---
description: Planificación global de órdenes de producción, seguimiento de avance y trazabilidad de planta.
---

1. **Creación de Órdenes de Producción**: Registrar nuevas OPs especificando código de orden, peso neto requerido (kg) y área responsable (`ManageOrdenesProduccion.tsx`). Al crear una nueva orden se ocultan los campos de producto/bodega, los cuales se completan posteriormente al editar o por el Jefe de Área.
2. **Seguimiento y Dashboard de Planta**: Monitorear el progreso en peso producido vs requerido, estado de las OPs (`Pendiente`, `En Proceso`, `Completada`, `Cancelada`) y carga global (`JefePlantaDashboard.tsx`).
3. **Panel Lateral de Detalle (`Sheet`)**: Consultar la información completa de la orden seleccionada (producto, fórmula de color, sede, área responsable, barra de avance, fechas y bodegas). Permite editar, eliminar o ajustar el estado de la OP.
4. **Trazabilidad Completa de Planta**: Visualizar el árbol de transformaciones y cadena de productos máquina a máquina en modo solo lectura (`TrazabilidadProducto.tsx`).
5. **Cierre y Cancelación de Órdenes**: Finalizar manualmente órdenes cuyo requerimiento ha sido alcanzado o cancelar órdenes obsoletas con su respectiva justificación.
6. **Coordinación de Transferencias Interárea**: Registrar transferencias de producción entre áreas (`TransferenciasInterarea.tsx`) vinculando la orden de origen con la de destino.

