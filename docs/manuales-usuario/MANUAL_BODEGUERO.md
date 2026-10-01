# Manual de Usuario — Bodeguero

## 1. ¿Qué hace usted en TexCore?

Usted es responsable de que el stock del sistema refleje la realidad física de la bodega: recibe la materia prima de los proveedores, mueve mercancía entre bodegas, vigila lo que está por agotarse y responde qué se necesita comprar.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Bodeguero**.

## 3. Su panel principal

Arriba, tres tarjetas con el resumen de su sede: **Productos**, **Bodegas** y **Lotes**, y un botón **Actualizar Datos** para refrescar los números en cualquier momento.

Debajo, cuatro pestañas: **Inventario**, **Alertas**, **MRP** y **Catálogos**.

## 4. Pestaña Inventario

Contiene, a su vez, siete secciones:

| Sección | Para qué sirve |
|---|---|
| **Stock** | Consultar el stock actual por producto, bodega y lote, con buscador y paginación. Muestra el **Físico Total**, lo **Comprometido (MTO)** para pedidos y lo **Disponible**. |
| **Recepción** | Registrar la llegada de material del proveedor (recepción F0-001). Es la **única forma de registrar una compra**: crea un lote de materia prima trazable, suma el stock en la bodega de recepción y registra el movimiento de compra (vea la sección 4.1). |
| **Materia prima** | Consultar los lotes recibidos de los proveedores en sus bodegas: fecha de recepción, lote del proveedor, proveedor, producto, bodega, cantidad recibida, cantidad **disponible** para producción (o la etiqueta **Consumido**), costo unitario y enlace al certificado de calidad. Puede filtrarse por proveedor y marcar **Solo disponibles**. |
| **Transfer** | Mover stock de una bodega a otra de la misma sede: **Producto**, **Bodega Origen**, **Lote** (opcional si el producto no usa lotes), **Cantidad**, **Bodega Destino** y una **justificación obligatoria**; luego **Transferir**. |
| **Transform** | Convertir un producto en otro (por ejemplo, un cambio de código tras tinturado): bodega, producto y lote de origen; bodega y **Nuevo Producto** de destino; **Código de Nuevo Lote** (si se deja vacío, se usa el lote de origen) y **Cantidad a Transformar**. Afecta el stock de dos bodegas y queda auditado. |
| **Kardex** | Historial de movimientos: filtrar por bodega, producto, tipo de operación (entradas / salidas) y rango de fechas, y pulsar **Consultar**. Con **bodega y producto** elegidos se muestra el kárdex en orden cronológico con la columna **Saldo**, calculada por el sistema desde el inicio del historial (es correcta en cualquier página). Sin alguno de los dos se listan los movimientos sin saldo. Los resultados se paginan de 20 en 20 e indican el total de movimientos; cambiar de página mantiene los filtros de la última consulta. **Exportar Excel** descarga el archivo completo generado en el servidor con esos mismos filtros (requiere haber consultado y elegido una bodega). Cada movimiento tiene tres acciones: **historial de cambios** (ícono de escudo), **editar** (lápiz; solo entradas de compra, con razón obligatoria) y **eliminar** (papelera; revierte su efecto en el stock y pide justificación). El botón **Registrar Merma** registra material dañado o perdido: producto, **Bodega de Origen**, cantidad y **Motivo de la Merma**. Debajo está **Stock a fecha de corte** (vea la sección 4.2). |
| **Reportes** | Reportes en Excel generados en el servidor: kárdex de movimientos, snapshot de stock actual, antigüedad del stock (aging), productos con stock cero, análisis de movimientos y rotación, y catálogo maestro de productos. |

### 4.1 Recibir materia prima (Recepción F0-001)

1. En **Inventario → Recepción**, elija el **Proveedor**, el **Producto** y la **Bodega de recepción**.
2. Escriba el **Lote del proveedor** (el que viene en la guía o etiqueta del proveedor), la **Cantidad (kg)**, el **Costo unitario** y la **Fecha de recepción** (por defecto, hoy).
3. Opcionalmente: **N.º de documento** (factura o guía), **País**, **Calidad** y el **Certificado de calidad** (PDF o imagen).
4. Haga clic en **Registrar recepción**.

El lote recibido aparece en **Materia prima** y la compra en el **Kardex**. Si después se descubre un error en la cantidad, puede corregirse editando ese movimiento de compra en el Kardex: el sistema ajusta también el lote, pero **no permite dejarlo por debajo de lo que producción ya consumió**. Una recepción solo puede eliminarse si su lote todavía no se usó en producción.

### 4.2 Stock a fecha de corte

Responde «¿cuánto stock había de este producto en tal fecha?».

1. En **Inventario → Kardex**, baje hasta **Stock a fecha de corte**.
2. Elija el **Producto**, la **Fecha de corte** y, si lo desea, una **Bodega** (por defecto, todas).
3. Haga clic en **Consultar stock**: se muestra el saldo de cada bodega al **cierre** de ese día (incluye todos los movimientos de esa fecha), con la sede y el total.

Solo se calcula sobre las bodegas que usted ve.

## 5. Pestaña Alertas — Stock Bajo

Lista los productos cuyo stock actual está por debajo del mínimo configurado, con Código, Producto, Bodega, Stock Actual y Stock Mínimo.

**Exportar a Excel:**
1. Seleccione la **Bodega** a exportar en el desplegable.
2. Haga clic en **Exportar Excel**.
3. El archivo se descarga con el detalle de los productos en alerta de esa bodega — útil para remitirlo a compras o al jefe de sede.

## 6. Pestaña MRP

Permite consultar qué insumos faltan según las Órdenes de Producción activas y ver las **Órdenes de Compra Sugeridas** que el sistema genera a partir de esos faltantes. El botón **Ejecutar Motor MRP** recalcula las sugerencias con los pedidos y el stock actuales.

## 7. Pestaña Catálogos

**Gestión de Productos e Insumos**: crear y actualizar los productos e insumos (**Productos e Insumos**) y los químicos (**Químicos**) para mantener los catálogos de bodega al día.

## 8. Reglas que debe conocer

- Por lo general, solo se verán las **bodegas asignadas a la sede** del usuario — si se necesita ver otra, debe solicitarse acceso al Administrador de Sede.
- Toda operación que mueve stock (recepción, ajuste, merma, transferencia, transformación) solo puede hacerse **desde bodegas que usted opera**. En una transferencia o transformación, la bodega de destino debe ser **de la misma sede** que la de origen.
- Las **compras** se registran solo desde **Recepción**; el sistema rechaza una compra registrada como movimiento suelto, porque quedaría fuera de la trazabilidad (sin proveedor, lote ni costo).
- El sistema **no permite** dejar el stock en negativo: si una salida supera lo que hay físicamente, la operación se rechaza.
- Cualquier ajuste manual de inventario debe quedar **justificado** — el sistema solicitará el motivo antes de aplicarlo.

## 9. Preguntas frecuentes

**No se encuentra un producto en Stock.** Debe revisarse que se esté en la bodega correcta — el filtro por bodega puede estar acotando la búsqueda.

**Se necesita mover stock de una bodega que no aparece.** Esa bodega probablemente pertenece a otra sede o no está asignada al usuario; debe solicitarse el acceso al Administrador de Sede/Sistemas.

**¿Cómo se sabe qué comprar?** Debe revisarse la pestaña **MRP** — muestra los faltantes calculados según las órdenes de producción activas. Si acaba de entrar un pedido u orden nueva, pulse **Ejecutar Motor MRP**.

**Se registró un movimiento por error.** En el **Kardex**, use eliminar (papelera) con la justificación: el sistema revierte su efecto en el stock. Si solo estaba mal la cantidad de una compra, edítela.

**¿Por qué el sistema pide lote del proveedor y costo al registrar una compra?** Porque cada recepción crea un lote de materia prima trazable: si un cliente reclama, el sistema puede responder con qué lote del proveedor, a qué costo y con qué certificado se produjo.

**Al editar la cantidad de una compra aparece que no puede ser menor a lo ya consumido.** Esa materia prima ya se usó en producción; la cantidad recibida no puede quedar por debajo de lo consumido.
