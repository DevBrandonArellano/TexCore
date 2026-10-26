---
description: Gestión logística, validación de salida por escaneo e historial de despachos.
---

1. **Dashboard de Despacho**: Visualizar y seleccionar pedidos de venta pendientes para su consolidación y salida física (`DespachoDashboard.tsx`).
2. **Validación de Carga mediante Escaneo**: Utilizar el escáner de códigos de barras (integrado con el microservicio satélite `scanning_service`) para validar los bultos/lotes contra la orden teórica.
3. **Verificación de Cumplimiento**: Validar en tiempo real la coincidencia entre los lotes escaneados y los detalles del pedido antes de autorizar la salida.
4. **Confirmación de Salida**: Despachar el bulto/pedido, lo cual ejecuta el descuento automático en `StockBodega` y actualiza el estado a "Despachado".
5. **Historial de Despachos**: Consultar la auditoría completa de salidas pasadas con detalle de bultos, pesos y usuario responsable (`HistorialDespachos.tsx`).

