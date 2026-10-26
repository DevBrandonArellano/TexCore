# Manual de Usuario — Vendedor

## 1. ¿Qué hace usted en TexCore?

Usted gestiona la cartera de clientes, genera los pedidos de venta y registra los cobros. El sistema valida automáticamente el límite de crédito de cada cliente para evitar ventas que excedan lo autorizado.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Ventas**. Arriba están los botones **Nuevo Cliente** y **Venta Nueva**, y cuatro indicadores: **Cuentas por Cobrar**, **Pedidos Realizados**, **Clientes Totales** y **Beneficiarios**. Debajo, tres pestañas: **Clientes**, **Últimas Ventas** y **Reportes Excel**.

## 3. Pestaña Clientes

Muestra el **Directorio de Clientes** con buscador y, por cliente, su **Estado Cuenta**, **Beneficio** y **Última Compra**.

**Registrar un cliente nuevo:**
1. Haga clic en **Nuevo Cliente**.
2. Complete la identificación (cédula o RUC), la razón social y la **Dirección**.
3. Elija el **Nivel de Precio**: *Normal* o *Mayorista* (define la lista de precios que se aplica en sus pedidos).
4. Indique el **Límite de Crédito ($)** y el **Plazo Crédito**: *Contado (0 Días)*, 8, 30, 45 o 60 días.
5. Active **Tiene Beneficios** si el cliente tiene descuentos especiales.
6. Guarde.

Para modificar un cliente use el ícono de editar (lápiz): el cambio pide una **Justificación**. Para darlo de baja use el ícono de inactivar.

**Ficha del cliente:** al pulsar sobre su nombre se abre su ficha, con:
- Su **Cartera Vencida**, su **Límite Crédito** y el **Cupo Disponible** (límite menos saldo pendiente; *Sin cupo* si ya lo alcanzó).
- La deuda por pedido (**Deuda**) y los pagos recibidos (**Recibos**).
- **Registrar un abono:** indique **Monto a Abonar ($)**, **Método de Pago** (Transferencia, Efectivo, Cheque u Otro), el número de **Comprobante** y, si corresponde, marque **Es Anticipo**. El abono se aplica primero a las facturas más antiguas.
- **Revertir un pago** (ícono en la fila del recibo): pide una justificación de al menos 5 caracteres. El sistema restaura el saldo del cliente y vuelve a repartir los cobros. Úselo solo si el pago se registró por error.

## 4. Pestaña Últimas Ventas

Muestra el **Historial de Ventas Recientes** con buscador (por guía o cliente), estado de pago y total.

**Crear un pedido (Venta Nueva):**
1. Pulse **Venta Nueva** y seleccione el **Cliente**. Puede indicar la guía o factura de referencia.
2. Agregue cada producto con su peso o metros y su **Precio Unit ($)**, y pulse **Añadir**. Con **Aplicar +15% IVA** se suma el IVA a esa línea.
3. Si el cliente le emite retención, active **¿El cliente te emite retención?** e indique el **Valor de Retención ($)**. El sistema muestra el **TOTAL PEDIDO** y el **TOTAL A COBRAR (Menos Retención)**.
4. Si el cliente ya pagó, active **¿El cliente pagó en caja?** (vea la sección 6).
5. Pulse **Finalizar y Guardar**. El sistema valida precios, pesos y crédito antes de guardar.

**Acciones sobre un pedido** (íconos de su fila):
- **Seguimiento de Fabricación MTO**: muestra, por producto, lo solicitado, lo fabricado y el avance. Si falta producir, **Crear OP** genera la orden de producción bajo pedido (con prioridad Baja, Normal o Alta).
- **Imprimir PDF**: descarga la nota de venta.
- **Editar pedido** (solo pedidos *pendientes*, sin despachar): permite corregir la fecha de despacho, el valor de retención y **Marcar como pagado**. Pide un **motivo de modificación** obligatorio.
- **Anular pedido** (solo pedidos pendientes): pide el motivo; el pedido queda anulado y el motivo se consulta después con **Ver motivo de anulación**.

## 5. Pestaña Reportes Excel

Elija la **Fecha de Inicio del Periodo** y la **Fecha de Fin del Periodo** y pulse **Bajar Excel** en el reporte que necesite:
- **Ventas Detalladas**: cada producto vendido en el período.
- **Top Clientes**: ranking por monto comprado.
- **Cartera Vencida**: saldos pendientes e impagos a la fecha.

## 6. Reglas que debe conocer

- No es posible crear un pedido que exceda el **límite de crédito** del cliente.
- **Venta de contado:** si al crear el pedido se activa **¿El cliente pagó en caja?**, el sistema no lo valida contra el límite de crédito ni contra los pedidos impagos del cliente, aunque el pago se registre después (se da un día para pagar). Es gestión interna: el producto **no se entrega** hasta recibir el pago. Si el cliente es de contado y el pedido **no** está pagado, el sistema lo advierte y no permite otro pedido mientras tenga uno impago.
- Cada producto del pedido debe tener peso mayor que cero y un precio que no sea menor a su costo base.
- Un pedido no se borra: se corrige con **Editar** o se cancela con **Anular**, y un abono se corrige solo con **Revertir**. Todas estas acciones piden motivo y quedan auditadas.
- Solo se ven y gestionan los clientes y pedidos de la propia sede.

## 7. Preguntas frecuentes

**El sistema no permite crear el pedido.** Revise en la ficha del cliente su saldo y su cartera vencida: probablemente el pedido excede su crédito disponible o tiene pedidos de contado sin pagar.

**Se registró mal un abono.** Ábralo en la ficha del cliente, pestaña **Recibos**, y use **Revertir pago** con la justificación; el sistema recalcula el saldo.

**No aparece el botón Editar en un pedido.** Solo se editan pedidos pendientes. Un pedido despachado ya afectó el stock: si hay que corregirlo, Despacho debe revertir el despacho desde su historial.

**El cliente pide un producto que no hay en stock.** Use **Seguimiento de Fabricación MTO** en el pedido y **Crear OP** para que planta lo fabrique.
