---
description: Gestión comercial, registro de clientes, creación de pedidos y notas de venta.
---

1. **Gestión de Clientes**: Registrar y consultar datos de clientes (RUC/Cédula, correo, teléfono, dirección) y nivel comercial (Normal/Mayorista) (`VendedorDashboard.tsx`).
2. **Control de Límite de Crédito**: Verificar saldo pendiente y crédito disponible antes de autorizar la creación de nuevos pedidos.
3. **Creación de Pedidos de Venta**: Registrar `PedidoVenta` y `DetallePedido` seleccionando productos, cantidades y precios unitarios. El sistema aplica validaciones de margen y precios de lista.
4. **Emisión de Nota de Venta (PDF)**: Generar y descargar el comprobante/nota de venta en PDF para entrega al cliente.
5. **Seguimiento de Estado y Anulación**: Consultar el estado del pedido (`Pendiente`, `En Proceso`, `Despachado`, `Anulado`) y gestionar anulaciones con justificación obligatoria cuando aplique.

