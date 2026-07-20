---
description: Gestión de maquinaria, supervisión técnica y trazabilidad de transformaciones.
---

1.  **Dashboard de Control (KPIs reales)**: Monitorear el estado de cada máquina (Operativa, Mantenimiento, Inactiva), su carga de trabajo actual y los KPIs de calidad/rendimiento del área: Producción Total (kg), **Rendimiento/Yield** (neto/(neto+merma)), **First Pass Yield** (primera calidad/total), **distribución por calidad** (primera/segunda/saldo) y tiempo promedio por lote.
2.  **Asignación de Órdenes**: Recibir las OPs en estado **Pendiente** y asignar una Máquina y un Operario responsable. Esto cambia el estado de la OP a **En Proceso**.
3.  **Registro de Transformación**: Registrar transformaciones máquina a máquina para las órdenes de tu área. Especifica producto de salida, máquina, pesos (entrada/salida) y observaciones. La merma se calcula automáticamente. Solo se permiten transformaciones en órdenes de tu área y sede (aislamiento estricto).
4.  **Trazabilidad de Producción**: Visualizar el árbol completo de transformaciones de cualquier orden en curso: cadena de productos, merma por etapa y merma acumulada total (%). La sección "Producción en Curso — Trazabilidad" muestra el timeline con opción de registrar nuevas transformaciones.
5.  **Control de Calidad**: Ver lotes producidos en su área y rechazar aquellos defectuosos indicando un **motivo obligatorio** (ISO 9001), lo que revierte automáticamente los movimientos de stock, consumo de mezcla y merma asociados. También puede **reetiquetar** un lote (corregir peso o reclasificar calidad) como supervisor autorizado; el `codigo_lote` y el QR de trazabilidad nunca cambian (ver [GESTION_ETIQUETAS.md](../../docs/modulos/GESTION_ETIQUETAS.md)).
6.  **Gestión de Insumos Críticos**: Atender alertas de Stock Bajo de químicos o hilos en su área.
7.  **Mantenimiento de Máquinas**: Registrar cambios en el estado de las máquinas y su eficiencia esperada. Configurar producto y bodega de merma vendible por máquina.
8.  **Transferencia de Producción**: Una vez completado el procesamiento de una orden, transferir la producción final a la siguiente área. Selecciona de tus órdenes completadas cuál transferir, especifica cantidad y observaciones sobre el estado del producto.
9.  **Gestión de Líneas de Producción**: Configurar y administrar Células de Manufactura Flexibles (Líneas de Producción) dentro de su área. Asignar/desasignar máquinas del área a cada línea, gestionar estado (activa/inactiva) y descripciones. Las máquinas pueden ser compartidas entre varias líneas (TOC / ISA-95) manteniendo la agregación de capacidad a nivel de área.

