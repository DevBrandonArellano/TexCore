# Manual de Usuario — Bodeguero

## 1. ¿Qué hace usted en TexCore?

Usted es responsable de que el stock del sistema refleje la realidad física de la bodega: registra entradas, mueve mercancía entre bodegas, vigila lo que está por agotarse y responde qué se necesita comprar.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Bodeguero**.

## 3. Su panel principal

Arriba, tres tarjetas con el resumen de su sede: **Productos**, **Bodegas** y **Lotes**, y un botón **Actualizar Datos** para refrescar los números en cualquier momento.

Debajo, tres pestañas: **Inventario**, **Alertas** y **MRP**.

## 4. Pestaña Inventario

Contiene, a su vez, seis secciones:

| Sección | Para qué sirve |
|---|---|
| **Stock** | Consultar el stock actual por producto y bodega, con buscador y paginación. |
| **Entrada** | Registrar el ingreso de mercancía nueva (por ejemplo, una compra). |
| **Transfer** | Mover stock de una bodega a otra dentro de la misma sede. |
| **Transform** | Registrar una transformación de un producto en otro (cambio de presentación/estado). |
| **Kardex** | Historial de movimientos de un producto: filtrar por bodega, producto, proveedor, rango de fechas o lote, y exportar el resultado a Excel. |
| **Reportes** | Dos herramientas: **Retro-Kardex** (cuánto stock había en una fecha pasada) y **Consulta de Lote** (traza el historial completo de un lote específico). |

## 5. Pestaña Alertas — Stock Bajo

Lista los productos cuyo stock actual está por debajo del mínimo configurado, con Código, Producto, Bodega, Stock Actual y Stock Mínimo.

**Exportar a Excel:**
1. Seleccione la **Bodega** a exportar en el desplegable.
2. Haga clic en **Exportar Excel**.
3. El archivo se descarga con el detalle de los productos en alerta de esa bodega — útil para remitirlo a compras o al jefe de sede.

## 6. Pestaña MRP

Permite consultar qué insumos faltan según las Órdenes de Producción activas y ver las sugerencias de compra generadas automáticamente por el sistema a partir de esos faltantes.

## 7. Reglas que debe conocer

- Por lo general, solo se verán las **bodegas asignadas a la sede** del usuario — si se necesita ver otra, debe solicitarse acceso al Administrador de Sede.
- El sistema **no permite** dejar el stock en negativo: si una salida supera lo que hay físicamente, la operación se rechaza.
- Cualquier ajuste manual de inventario debe quedar **justificado** — el sistema solicitará el motivo antes de aplicarlo.

## 8. Preguntas frecuentes

**No se encuentra un producto en Stock.** Debe revisarse que se esté en la bodega correcta — el filtro por bodega puede estar acotando la búsqueda.

**Se necesita mover stock de una bodega que no aparece.** Esa bodega probablemente pertenece a otra sede o no está asignada al usuario; debe solicitarse el acceso al Administrador de Sede/Sistemas.

**¿Cómo se sabe qué comprar?** Debe revisarse la pestaña **MRP** — muestra los faltantes calculados según las órdenes de producción activas.
