---
description: Gestión logística y validación de salida.
---

1.  **Dashboard de Despacho**: Seleccionar uno o múltiples pedidos pendientes para un mismo despacho.
2.  **Validación de Carga (Escaneo)**: Utilizar lector de códigos de barras (microservicio de escaneo) para validar que los lotes en el bulto correspondan a los pedidos seleccionados.
3.  **Verificación de Cumplimiento**: Comprobar en tiempo real si el producto escaneado coincide con el pedido teórico antes de confirmar.
4.  **Finalización de Despacho**: Confirmar la salida física, lo cual rebaja automáticamente el stock y actualiza el estado a "Despachado".
5.  **Historial de Despachos**: Consultar auditoría completa de salidas anteriores con detalles de lotes y pesos.
6.  **Devoluciones**: Registrar el reingreso de bultos previamente despachados si fuera necesario.
