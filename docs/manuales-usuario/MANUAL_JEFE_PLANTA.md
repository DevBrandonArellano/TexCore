# Manual de Usuario — Jefe de Planta

## 1. ¿Qué hace usted en TexCore?

Usted es el planificador central de producción: **es el único rol que crea Órdenes de Producción (OP)**, planifica la reposición de stock (MTS), inicia las corridas continuas y registra las transferencias de material entre áreas. El Jefe de Área, después, asigna cada orden a una máquina y un operario — pero no crea órdenes nuevas.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Jefe de Planta**.

## 3. Su panel principal

Arriba, tres indicadores del día: **Cumplimiento Diario**, **Índice de Desperdicio** y **Alerta WIP Estancado** (se pone en rojo si hay producción en curso detenida). El botón **Acciones Gerenciales** descarga dos reportes en PDF: **Reporte Avance Operativo** y **Balance de Masas Mensual**.

Debajo, cinco pestañas:

| Pestaña | Para qué sirve |
|---|---|
| **Órdenes de Trabajo (OP)** | Crear y administrar las órdenes (secciones 4 a 8). |
| **Plan Maestro (MTS)** | Planificar la producción contra stock (sección 9). |
| **Corridas Continuas (MES)** | Iniciar y supervisar corridas de producción continua (sección 10). |
| **Transferencias Interárea** | Pasar material de una orden a otra área (sección 11). |
| **Buscador de Lotes** | Buscar lotes por fecha, turno, código o calidad y abrir su ficha. |

## 4. Gestión de Órdenes de Producción

La tabla tiene un buscador (por código o producto) y filtros por **estado**, **máquina** y **modalidad** (*Bajo Pedido (MTO)* o *Contra Stock (MTS)*). Por orden muestra producto y fórmula, máquina, entrega, prioridad, peso requerido, progreso y estado; la etiqueta **✓ QUÍMICOS DESCONTADOS** indica que ya se descontaron sus químicos.

El menú de cada fila (⋯) ofrece: **Editar**, **Ver Requisitos**, **Registrar Lote**, **Cambiar Estado** (*En Proceso* / *Finalizada*) y **Eliminar**.

## 5. Crear una nueva Orden de Producción

1. Haga clic en **Nueva Orden**.
2. Complete el formulario:
   - **Código** y **Peso Neto Requerido (Kg)** (obligatorios) — la meta de producción.
   - **Área Responsable** (obligatoria) — el área de la sede que la ejecutará.
   - **Prioridad** (obligatoria): Baja, Normal, Alta o Urgente.
   - **Fórmula de Color** (opcional): solo se ofrecen las fórmulas con **versión oficial**.
   - **Bodega de Químicos** (opcional): de ella se descuentan los químicos de la fórmula. Si elige fórmula y bodega, el descuento se hace al crear la orden; sin bodega no se descuenta nada, y el Jefe de Área puede asignarla después.
   - **Fecha Inicio** y **Fecha Fin** planificadas, y **Observaciones**.
3. Guarde. La orden queda *Pendiente* y visible para que el Jefe de Área de esa área la asigne a máquina y operario.

Los productos y bodegas de entrada y salida aparecen al **editar** la orden (son obligatorios en la edición).

## 6. Detalle de una orden

Al hacer clic en una orden se abre su detalle: información general, progreso de producción, fechas, almacén y notas. Las justificaciones de cambios y eliminaciones se consultan en la **Auditoría**.

Si la orden tiene **fórmula de color**:
- Se ven los **Litros de Baño** (editables con **Guardar**) y la **Relación de Baño**. Si los químicos ya se descontaron, al pulsar **Guardar** se abre un diálogo que pide la justificación (mínimo 10 caracteres) antes de ajustar la descarga.
- **Ver dosificación** calcula cuánto de cada químico necesita la orden según su peso y los litros de baño, y muestra los **procesos que ejecuta la máquina asignada**.

Al final está el **Flujo de Transformaciones**: el árbol de transformaciones de la orden con la merma acumulada y la lista de todos sus registros (máquina, operario, entrada, salida, merma y estado). El Jefe de Planta **consulta** las transformaciones; las registran los Operarios y Jefes de Área.

## 7. Verificar materiales, editar y eliminar

- **Ver Requisitos**: muestra el peso requerido y los insumos necesarios (producto, tipo y cantidad), para comprobar disponibilidad antes de comprometer la planificación.
- **Editar**: si la orden ya tiene químicos descontados, el formulario muestra el campo **Justificación del cambio**, obligatorio; si cambia el peso o la fórmula, el sistema revierte el descuento anterior y aplica el nuevo cálculo.
- **Eliminar** (desde el menú ⋯ o desde el detalle): se abre un diálogo que pide la **justificación** (mínimo 10 caracteres). Si se habían descontado químicos, el sistema los devuelve al stock. La justificación queda en la Auditoría.
- **Fórmula y versión**: cuando la orden sale de *Pendiente* (normalmente al registrarse su primer lote), el sistema fija en ella la **versión oficial** vigente de su fórmula. Desde entonces la orden **no puede cambiar de fórmula** y conserva esa versión aunque Tintorería marque otra después.

Solo el Jefe de Planta y los administradores pueden editar los datos de una orden.

## 8. Registrar un lote (excepcional)

De ser necesario registrar producción manualmente (por ejemplo, para corregir una situación en planta), use **Registrar Lote** en el menú de la orden: **Código de Lote**, **Peso Neto Producido (Kg)**, **Máquina**, **Turno**, **Hora de Inicio** y **Hora Final**.

## 9. Plan Maestro (MTS)

**Planificación y Producción Contra Stock (MTS)** controla la reposición de los productos que deben mantenerse en stock mínimo.

1. La tabla de déficits lista los productos bajo su mínimo (sede, código, stock actual, mínimo y **Déficit (Reposición)**). Si no hay ninguno, muestra *«Stock en niveles óptimos»*.
2. **Crear Plan desde Déficits** genera un plan con esos productos. Puede indicar un **Código de Plan** (opcional), la **Sede** y las fechas de **Inicio** y **Fin**. El plan nace en *Borrador*.
3. **Aprobar Plan** lo deja listo para ejecutar.
4. En cada producto del plan, **Generar OP** crea la orden de producción: **Cantidad a Requerir**, **Prioridad** y **Bodega de Destino (PT)**.
5. El plan muestra lo planificado, lo ejecutado (1ra y 2da calidad), el saldo pendiente, el **Cumplimiento** y la **Desviación**. Al terminar, **Cerrar Plan**.

Los planes se filtran por estado: Borrador, Aprobado, En Ejecución, Cerrado o Cancelado.

## 10. Corridas Continuas (MES)

1. **Iniciar Corrida de Producción**: elija el **Área Productiva**, la **Máquina Principal** (opcional), el **Turno** (Mañana, Tarde o Noche) y, si quiere, **Observaciones**.
2. Registre la primera transformación de la corrida: **Producto de Entrada**, **Bodega Origen**, **Peso Consumido (kg)**, **Producto Resultante**, **Bodega Destino**, **Peso Neto Producido (kg)**, **Calidad**, **Merma / Desperdicio** con su tipo y, si es tela, los **Metros**. El **Balance de Masa** compara entrada y salida. Pulse **Confirmar Transformación y Generar Etiqueta**. Desde ese momento los operarios pueden registrar avance en esa corrida.
3. Con **Pausar**, **Reanudar** y **Finalizar** controla el estado de la corrida.
4. En **Operaciones de la Corrida**, **Revertir** anula una operación completada; pide un **Motivo de la Reversión**.

## 11. Transferencias Interárea

En **Transferencias a Otras Áreas**, **Nueva Transferencia** pasa la producción final de una orden a la siguiente área:

1. Elija la **Orden de Origen**.
2. Elija el **Área Destino**: allí se crea la nueva orden que recibe el material.
3. Indique la **Cantidad a Transferir (kg)** y, si quiere, **Observaciones**.

Las transferencias no se editan ni se borran. Solo las registran el Jefe de Planta y el Administrador de Sistemas.

## 12. Ficha de lote

Al abrir un lote (por ejemplo, desde el **Buscador de Lotes**) se ven las pestañas **Resumen**, **Genealogía**, **Movimientos**, **Consumos** (lotes de origen consumidos), **Materias primas y costos** y **Costo** (formato F0-002, con el total).

## 13. Preguntas frecuentes

**Al registrar el primer lote aparece «La fórmula no tiene una versión oficial: apruébela antes de lanzar la orden».** La fórmula sigue sin versión oficial. Pida a Tintorería que marque una versión como oficial. No se registró nada: el sistema revierte el lote y el stock.

**Intenté cambiar la fórmula de una orden en proceso y el sistema lo rechaza.** Es correcto: una orden lanzada conserva la fórmula y la versión con la que empezó, para que su trazabilidad sea confiable.

**¿Por qué el Jefe de Área no puede crear ni editar órdenes?** La planificación corresponde al Jefe de Planta; la ejecución (asignar máquina y operario, y producir), al Jefe de Área.

**¿Por qué piden un motivo para cambiar una orden?** Porque ya se descontaron químicos con el cálculo anterior: el motivo queda en auditoría y el sistema reajusta el inventario.

**Los operarios dicen que no pueden registrar avance en una corrida.** La corrida necesita su primera transformación (sección 10, paso 2), que define qué se produce.
