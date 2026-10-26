# Manual de Usuario — Ejecutivo

## 1. ¿Qué hace usted en TexCore?

Usted tiene visión estratégica de **todas las sedes**, con acceso de **solo lectura** a producción, inventario, ventas y MRP. No crea, modifica ni elimina ningún registro — su panel es para consultar y descargar reportes gerenciales.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel Ejecutivo**.

## 3. Filtros generales

En la cabecera del panel pueden ajustarse dos filtros que aplican a la mayoría de las pestañas:
- **Sede**: permite elegir una sede específica o dejarlo vacío para ver el consolidado de **todas las sedes**.
- **Rango de fechas** (Inicio/Fin): acota producción y reportes al período que se necesite. El sistema no permite ingresar una fecha de inicio posterior a la de fin.

## 4. Sus pestañas

### Resumen
KPIs consolidados en tarjetas: producción, MRP, stock e inventario, y cartera vencida — la fotografía general del negocio.

### Producción
Estado de las Órdenes de Producción por sede, una gráfica de los kilogramos producidos por día (con el selector **Últimos 7 / 15 / 30 / 90 días** o un rango de fechas) y la producción por producto (código, número de lotes y kg).

### MRP
**Planificación de Materiales (MRP)**, con tres indicadores: **Sugerencias de compra**, **Productos a producir** y **Última ejecución MRP**. Usa el selector de sede del panel: con *Todas las sedes*, **Ejecutar MRP (todas las sedes)** calcula cada sede; con una sede elegida, solo esa.

El MRP se calcula **por sede**. El botón **Ejecutar MRP** recalcula todo con las órdenes de producción abiertas, los pedidos pendientes y el stock actual, y en segundos muestra el resultado:

- **Última ejecución**: fecha, quién la lanzó, cuántas sugerencias y productos a producir dejó y sus **advertencias** (por ejemplo, las corridas continuas, que no tienen peso requerido y no se calculan).
- **Sugerencias de compra**: por cada material comprado (materia prima, químicos), lo que piden las órdenes abiertas, su stock mínimo, lo disponible y lo **a comprar** (requerido + mínimo − disponible). Son **informativas**: la compra se gestiona fuera del sistema. Los químicos que ya se descontaron al crear una orden no se vuelven a pedir.
- **Requerimientos por orden**: qué orden pide cada material, cuánto y para qué fecha.
- **Necesidad de producción**: los productos fabricados (hilo, tela) que hay que producir para cubrir los pedidos pendientes, lo que piden otras órdenes y el stock mínimo, descontando lo disponible y lo que ya está en producción. El Jefe de Planta la usa en el Plan Maestro (MTS).

### Stock
Cuatro indicadores: **Productos** y **Bodegas** con existencias, **Stock Total** y **Alertas de Stock**. Debajo, **Stock por Bodega** y **Productos con mayor déficit de stock** (actual, mínimo y faltante), con buscador. A diferencia del Bodeguero, este panel muestra **todas las bodegas** de todas las sedes (o las de la sede elegida en el filtro).

Al hacer clic en una barra de **Stock por Bodega** se abre el detalle de esa bodega: producto, lote y cantidad, paginado. Los totales los calcula el servidor, así que el panel responde igual con años de operación.

### Ventas
Pedidos, estado de la cartera y el listado completo de clientes, sin la restricción por vendedor que tiene un Vendedor normal. El filtro **Vendedor** (por defecto, *Todos los vendedores*) acota los pedidos a los de un vendedor.

### Ficha de lote
Al abrir un lote se ven, además del resumen y los movimientos, sus **Consumos** (lotes de origen consumidos), sus **Materias primas y costos** y su **Costo** (formato F0-002, con el total).

### Reportes
Elija **Fecha inicio** y **Fecha fin** (aplican a todos los reportes con fecha) y pulse **Descargar** en el reporte que necesite. Son 6 reportes gerenciales en Excel:
1. **Ventas del período**
2. **Top clientes**
3. **Deudores / cartera**
4. **Órdenes de producción**
5. **Lotes de producción**
6. **Tendencia de producción**

Mientras se genera una descarga, todos los botones de exportación quedan deshabilitados — se recomienda esperar a que termine antes de solicitar otro reporte.

## 5. Reglas que debe conocer

- El acceso de este rol es **de lectura**: no hay botones para crear, editar o eliminar registros. La única acción disponible es **Ejecutar MRP**, que solo recalcula las sugerencias de compra y la necesidad de producción.
- Puede consultarse información de todas las sedes, no solo de una en particular.

## 6. Preguntas frecuentes

**Se necesita corregir un dato que se ve incorrecto.** No es posible hacerlo desde este panel — debe reportarse al responsable operativo correspondiente (Vendedor, Bodeguero, Jefe de Área, etc.) o al Administrador de Sede/Sistemas.

**El botón de exportar reportes no responde.** Es probable que ya haya una descarga en curso — debe esperarse a que termine; los botones se reactivan automáticamente.

**Se desea ver solo una sede.** Debe usarse el selector de sede en la cabecera del panel; puede dejarse vacío para volver a la vista global.
