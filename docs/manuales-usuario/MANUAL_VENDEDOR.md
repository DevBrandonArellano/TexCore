# Manual de Usuario — Vendedor

## 1. ¿Qué hace usted en TexCore?

Usted gestiona la cartera de clientes, genera los pedidos de venta y registra los cobros. El sistema valida automáticamente el límite de crédito de cada cliente para evitar que se vendan pedidos que excedan lo autorizado.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Ventas**, con tres pestañas: **Clientes**, **Pedidos** y **Reportes**.

## 3. Pestaña Clientes

Muestra el **Directorio de Clientes** de la sede.

**Registrar un cliente nuevo:**
1. Haga clic en **Registrar Nuevo Cliente**.
2. Complete sus datos y elija el **perfil de precio**: Normal o Mayorista (define qué lista de precios y descuentos se aplica automáticamente en sus pedidos).
3. Defina su **límite de crédito**.
4. Haga clic en **Registrar**.

Para modificar un cliente, use el ícono de editar (lápiz) en su fila; para darlo de baja, use el ícono de inactivar.

**Ver el detalle de un cliente:** haga clic sobre su nombre para abrir su ficha, donde es posible:
- Ver su **estado financiero** (Saldo Pendiente vs. Límite de Crédito).
- Registrar un **Abono** a su cuenta por cobrar.
- **Revertir un Abono** ya registrado: requiere escribir una **justificación obligatoria**. Al confirmar, el sistema restaura automáticamente el saldo pendiente del cliente al monto anterior y vuelve a aplicar el cobro a las facturas más antiguas primero (reconciliación automática) — se recomienda usar esta opción solo si el pago fue registrado por error.

## 4. Pestaña Pedidos

Muestra el **Historial de Ventas Recientes**.

**Crear un pedido nuevo:**
1. Abra el formulario de nueva venta, seleccione el **cliente** y agregue los **productos** con sus cantidades.
2. El sistema aplica automáticamente el precio/descuento según el perfil del cliente (Normal/Mayorista) y valida que el total no supere su **límite de crédito** disponible — si lo supera, no permitirá continuar.
3. Confirme para generar el pedido.

**Sobre un pedido ya creado**, en su fila hay tres acciones disponibles:
- **Imprimir PDF**: descarga la nota de venta.
- **Editar** (solo si aún no fue despachado): permite corregir productos, cantidades o datos del pedido.
- **Anular**: solicita un motivo obligatorio; el pedido queda anulado y su motivo puede consultarse después con el ícono "Ver motivo de anulación".

## 5. Pestaña Reportes

Permite descargar a Excel los reportes comerciales de la gestión:
- **Exportar Ventas** del período.
- **Top Clientes** por monto de compra.
- **Deudores/Cartera** — clientes con saldo pendiente.

## 6. Reglas que debe conocer

- No es posible crear un pedido que exceda el **límite de crédito** del cliente — el sistema lo valida automáticamente antes de guardar.
- Solo se ven y gestionan los clientes/pedidos de la propia sede.
- Anular un pedido y revertir un abono siempre exigen un motivo, ya que son acciones auditadas.

## 7. Preguntas frecuentes

**El sistema no permite crear el pedido.** Debe revisarse el saldo pendiente del cliente en su ficha — probablemente el pedido excede su límite de crédito disponible.

**Se registró mal un abono.** Debe abrirse desde la ficha del cliente y usarse **Revertir Abono** con la justificación correspondiente; el sistema recalcula el saldo automáticamente.

**Se necesita editar un pedido que ya fue despachado.** No es posible desde este panel — un pedido despachado ya afectó el stock; debe consultarse con el Jefe de Área o Administrador de Sede cómo proceder (por ejemplo, mediante una devolución desde Despacho).
