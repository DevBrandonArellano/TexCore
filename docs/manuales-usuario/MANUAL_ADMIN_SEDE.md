# Manual de Usuario — Administrador de Sede

## 1. ¿Qué hace usted en TexCore?

Usted es el responsable gerencial de su sede: **monitorea** la producción, el inventario, las ventas y la planificación de materiales para tomar decisiones, y revisa la **auditoría** de lo que ocurre en la sede. Su panel es el mismo panel gerencial del **Ejecutivo**, limitado a su sede, más las pestañas **Auditoría** y **Configuración** (equivalencias de empaque de la sede).

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Administrador de Sede** y se abre en la pestaña **Aprobaciones**.

## 3. Sus pestañas

| Pestaña | Para qué sirve |
|---|---|
| **Aprobaciones** | Hoy solo muestra un aviso: **el módulo de aprobación de movimientos no está activo**. Todos los movimientos de inventario se procesan de inmediato, sin aprobación previa. |
| **Resumen, Producción, MRP, Stock, Ventas, Reportes** | Los mismos paneles del Ejecutivo (vea el [Manual del Ejecutivo](MANUAL_EJECUTIVO.md#4-sus-pestañas)), con los datos de **su sede**: a diferencia del Ejecutivo, no tiene selector de sede. Puede descargar los mismos 6 reportes en Excel. |
| **Auditoría** | El **Registro de Auditoría** de su sede (vea la sección 4). |
| **Configuración** | Las **equivalencias de empaque** de su sede: cuántas fundas tiene un baño y cuántos conos una funda (vea la sección 5). |

## 4. Revisar la auditoría

La pestaña **Auditoría** lista cada creación, edición y eliminación registrada en la sede, con **Fecha y Hora**, **Usuario / IP**, **Objeto Afectado**, la **Justificación** y el **Detalle de Cambios** (valor anterior y nuevo).

Por defecto se ven los cambios de los **últimos 30 días**. Para consultar otro período o un tipo de cambio:

1. Escriba en el buscador parte del nombre de usuario, el nombre de la tabla (por ejemplo, *pedidoventa* o *stockbodega*) o el ID exacto del registro (opcional).
2. Elija las fechas **Desde** y **Hasta** (opcional; con **Desde** se pueden consultar registros de cualquier antigüedad).
3. Elija la **Operación**: *Todas*, *Creación*, *Edición* o *Eliminación*.
4. Pulse **Buscar**.

Los registros de auditoría no se pueden modificar ni borrar desde ningún lugar del sistema.

Se ven los cambios hechos por usuarios de su sede y los cambios sobre objetos de su sede. Si un usuario se traslada a otra sede, lo que hizo mientras estaba en la suya sigue apareciendo aquí.

Úsela para responder «quién cambió esto, cuándo y por qué» ante cualquier incidencia.

## 5. Configurar las equivalencias de empaque

Producción registra lotes por **baño**, **funda** o **cono**. Para convertirlos, el sistema usa las equivalencias de **su** sede (por ejemplo, 1 baño = 15 fundas = 225 conos); cada sede tiene las suyas.

1. Abra la pestaña **Configuración**.
2. Indique **Fundas por baño** y **Conos por funda** (números enteros, mínimo 1). El total de conos por baño se calcula solo.
3. Escriba la **Justificación** del cambio (al menos 10 caracteres): queda en la Auditoría.
4. Pulse **Guardar equivalencias**.

Si la sede no tiene equivalencias, la pestaña lo avisa. Mientras tanto, producción **no puede** registrar lotes por baño o funda sin indicar las unidades, y el MRP no calcula los pedidos de la sede: el sistema no usa un valor fijo en su lugar.

## 6. Qué puede hacer y qué no

Este rol es **gerencial y de monitoreo**:

- Consulta los indicadores, la planificación y la auditoría de su sede.
- Desde el **MRP** puede ejecutar el cálculo de requerimientos (**Ejecutar Motor MRP**).
- Las **transferencias interárea** de material las registra el Jefe de Planta (o el Administrador de Sistemas). Este rol puede consultarlas, pero no registrarlas.
- La creación de **usuarios, sedes y áreas** la realiza el **Administrador de Sistemas**: si necesita dar de alta a un empleado o crear un área, solicíteselo.

## 7. Preguntas frecuentes

**La pestaña Aprobaciones dice que el módulo no está activo.** Es correcto: la aprobación manual se deshabilitó para no frenar la operación. Para controlar lo que se hizo, use la pestaña **Auditoría**.

**Necesito saber quién modificó un movimiento o un pedido.** En **Auditoría**, busque por el usuario, la tabla o el ID del registro; verá la justificación y el detalle del cambio.

**No veo datos de otra sede.** Es correcto: este panel muestra solo su sede. La vista consolidada de todas las sedes corresponde al Ejecutivo.

**Necesito crear un usuario nuevo para la sede.** Solicítelo al Administrador de Sistemas.

**Producción dice que la sede no tiene equivalencias de empaque.** Regístrelas en la pestaña **Configuración** (sección 5).
