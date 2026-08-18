---
description: Gestión de maquinaria, supervisión técnica, OEE, paros de máquina y trazabilidad de transformaciones.
---

1. **Dashboard de Control de Área (KPIs + OEE)**: Monitorear el estado de las máquinas (`Operativa`, `Mantenimiento`, `Inactiva`), la carga de trabajo y los indicadores de área: Producción Total (kg), Rendimiento/Yield %, First Pass Yield %, distribución de calidad (Primera, Segunda, Saldo) y OEE = Disponibilidad × Rendimiento × Calidad (`JefeAreaDashboard.tsx`).
2. **Registro de Paros de Máquina (Downtime)**: Registrar paros operacionales desde `RegistrarParoModal.tsx` especificando códigos de razón de las Seis Grandes Pérdidas (Avería, Setup, Microparo, Velocidad Reducida, Rechazo Arranque, Defecto Proceso, Falta Material, Mantenimiento Planificado, Otro) que alimentan la Disponibilidad del OEE.
3. **Asignación de Órdenes y Completar Detalles**: Recibir Órdenes de Producción en estado `Pendiente` (creadas por el Jefe de Planta) y asignar Máquina y Operario. Utilizar `completar_detalles` para asociar producto de entrada, producto de salida, bodega de entrada y bodega de salida del área.
4. **Transformaciones y Mermas Máquina a Máquina**: Registrar transformaciones con cálculo automático de mermas y consumo de mezclas (`ComponenteMezclaPanel.tsx`, `RegistrarTransformacion.tsx`).
5. **Gestión de Líneas de Producción**: Configurar células de manufactura flexibles (`ManageLineas.tsx`) agrupando máquinas del área para agregar capacidad compartida (TOC / ISA-95).
6. **Supervisión de Movimientos y Reetiquetado In-Situ**: Monitorear movimientos del área (`AreaMovementsTable.tsx`) y actuar como supervisor autorizador para la reclasificación o corrección de lotes (`ReetiquetarModal.tsx`).
7. **Transferencias Interárea**: Transferir la producción terminada del área hacia la bodega de entrada de la siguiente etapa secuencial del proceso.

