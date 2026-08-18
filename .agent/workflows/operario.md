---
description: Gestión de producción física, registro de avance de lotes y transformaciones en máquina.
---

1. **Consulta de Asignaciones**: Acceder al panel de operario (`OperarioDashboard.tsx`) para visualizar exclusivamente las Órdenes de Producción en estado `En Proceso` asignadas a su máquina y turno.
2. **Registro de Avance y Lote**: Registrar el peso neto producido y unidades completadas mediante `InventoryForm.tsx`, generando el código de lote y descontando el stock correspondiente.
3. **Registro de Transformación Máquina a Máquina**: Registrar transformaciones (`RegistrarTransformacion.tsx`) especificando producto de salida, peso de entrada, peso de salida y observaciones con cálculo automático de mermas.
4. **Consulta de Histórico de Movimientos**: Revisar movimientos de inventario realizados en el turno a través de `InventoryHistory.tsx`.
5. **Trazabilidad y Especificaciones**: Consultar la cadena de transformaciones del lote y las instrucciones técnicas (fórmula, metas, notas del Jefe de Planta/Área).

