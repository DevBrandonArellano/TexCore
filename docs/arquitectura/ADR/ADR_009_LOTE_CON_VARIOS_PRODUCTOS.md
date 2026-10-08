# ADR-009 — Un lote puede tener varios productos vendibles (TexCore)

> Numeración continua con ADR-008 (`ADR_008_TEXTO_VACIO_SIN_NULL.md`).
**Tema:** Qué filas de stock de un lote salen al escanearlo en el despacho
**Fecha:** 7-oct-2026 · **Estado:** Aceptada (decisión del usuario) · **Origen:** pendiente 3 de la entrada del 6–7 oct del `CHANGELOG.md`

## 1. Contexto

Un lote (`LoteProduccion`) puede tener varias filas de `StockBodega`:

* **El producto del lote:** el de su OP (`LoteProduccion.producto_del_stock_id`).
* **La merma vendible:** la registra `MermaStockService` con el producto y la bodega de merma de la máquina, junto con un movimiento `PRODUCCION` con `documento_ref = 'MERMA-<lote>'`.
* **Otros productos registrados a mano:** el movimiento manual (`POST /api/inventory/movimientos/`) acepta cualquier producto en un lote.

`fc403f0` (6-oct) corrigió que el despacho vendiera la merma fijando la búsqueda al producto del lote. Eso dejó sin vender el stock de los productos registrados a mano. Además, el Kardex siempre registraba la VENTA con el producto de la OP.

## 2. Decisión

1. El movimiento manual **sigue aceptando** otro producto en un lote, y el despacho lo vende.
2. **Filas vendibles** (`inventory.utils.stock_vendible_del_lote`): todas las filas del lote salvo la merma. La merma se reconoce por su movimiento `MERMA-<lote>` (mismo lote y producto). No se usa la configuración actual de la máquina, que puede cambiar después de producir. La regla vale aunque la merma se haya trasladado a otra bodega.
3. **Qué sale al escanear** (`ProcessDespachoAPIView._lote_y_filas`):
   - la fila del producto del lote, siempre (como antes);
   - las filas de otros productos, solo si algún pedido seleccionado los pide. Un producto agregado a mano que nadie pidió queda en stock.
4. Cada fila se vende con **su propio producto**: VENTA en el Kardex, `DetalleHistorialDespacho` y asignación al pedido. La reversión ya restauraba por `detalle.producto` y la bodega del movimiento VENTA, así que devuelve cada fila a su origen.
5. **Escáner:** tanto la vista directa (`ValidateLoteAPIView`) como la interna que usa `scanning_service` en producción (`internal_api.ValidateLoteView`):
   - informan la fila principal en los campos de siempre (`producto_id`, `peso`, `bodega_id`);
   - agregan `peso_total` y `productos` con todas las filas vendibles.

   `DespachoDashboard` suma cada línea al requerimiento de su producto, con la misma regla del punto 3.
6. **Reserva MTO:** sigue comprometiendo solo la fila del producto del lote (`stock_del_lote`). La reserva se calcula con `peso_neto_producido`, que es el peso de ese producto.

## 3. Consecuencias

* El stock agregado a mano a un lote se puede vender y el Kardex refleja el producto que salió.
* Un lote en el que solo queda un producto agregado a mano (el principal ya se vendió) se puede despachar si el pedido lo pide.
* **Defecto relacionado que se corrigió:** `internal_api.ValidateLoteView` todavía tomaba la primera fila de stock del lote. Podía informar la merma, el mismo defecto que `fc403f0` corrigió solo en la vista directa. El escáner de producción pasa por esa vista.
* **Supuesto:** el producto de merma de una máquina no es el mismo que el producto que produce.
