---
description: Gestión de inventario, transferencias, ajustes, registro de mermas y auditoría.
---

1. **Consulta de Stock por Bodega**: Visualizar existencias actuales en cada bodega filtrando por producto y categoría (`BodegueroDashboard.tsx`).
2. **Transferencias y Transiciones de Bodega**: Registrar movimientos de salida y entrada entre bodegas con validación atómica y actualización en tiempo real de `StockBodega`.
3. **Auditoría y Edición de Movimientos**: Corregir o editar movimientos realizados mediante diálogos específicos (`EditarMovimientoDialog.tsx`, `EliminarMovimientoDialog.tsx`, `AuditoriaDialog.tsx`), registrando justificación obligatoria.
4. **Registro de Mermas**: Registrar mermas de inventario y consumo de materia prima mediante `RegistrarMermaDialog.tsx`.
5. **Reabastecimiento y Alertas**: Monitorear notificaciones de Stock Bajo y consultar requerimientos de insumos (MRP) para la preparación de órdenes de producción.

