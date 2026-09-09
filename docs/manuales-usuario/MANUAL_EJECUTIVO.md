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
Estado de las Órdenes de Producción por sede y una gráfica de la serie temporal de kilogramos producidos por día.

### MRP
Requerimientos de materiales pendientes y las órdenes de compra sugeridas por el sistema.

### Stock
Stock actual e historial de alertas de stock bajo mínimo — a diferencia del Bodeguero, este panel muestra **todas las bodegas** de todas las sedes, no solo las asignadas.

### Ventas
Pedidos, estado de la cartera y el listado completo de clientes, sin la restricción por vendedor que tiene un Vendedor normal.

### Reportes
Permite descargar 6 reportes gerenciales en Excel para el período seleccionado:
1. **Ventas del período**
2. **Top clientes**
3. **Deudores / cartera**
4. **Órdenes de producción**
5. **Lotes de producción**
6. **Tendencia de producción**

Mientras se genera una descarga, todos los botones de exportación quedan deshabilitados — se recomienda esperar a que termine antes de solicitar otro reporte.

## 5. Reglas que debe conocer

- El acceso de este rol es **exclusivamente de lectura** — no se mostrarán botones para crear, editar o eliminar en ninguna pestaña.
- Puede consultarse información de todas las sedes, no solo de una en particular.

## 6. Preguntas frecuentes

**Se necesita corregir un dato que se ve incorrecto.** No es posible hacerlo desde este panel — debe reportarse al responsable operativo correspondiente (Vendedor, Bodeguero, Jefe de Área, etc.) o al Administrador de Sede/Sistemas.

**El botón de exportar reportes no responde.** Es probable que ya haya una descarga en curso — debe esperarse a que termine; los botones se reactivan automáticamente.

**Se desea ver solo una sede.** Debe usarse el selector de sede en la cabecera del panel; puede dejarse vacío para volver a la vista global.
