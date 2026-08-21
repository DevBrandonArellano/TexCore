# Reporte Gerencial de Funcionalidades — TexCore

> Documento de referencia gerencial. Describe, con el mayor nivel de detalle posible, TODAS las acciones concretas que cada rol puede realizar en TexCore, organizadas por pantalla. Cada viñeta es una capacidad individual del sistema — no una agrupación de varias.
>
> Fecha de elaboración: 2026-08-21 · Basado en revisión directa de las pantallas reales del sistema (no solo de la documentación funcional).

---

## 1. ¿Qué es TexCore?

TexCore es el sistema de gestión integral de la empresa textil: cubre producción (tintura, transformación de materiales, control de máquinas), bodega e inventario, ventas y cartera de clientes, despacho de mercancía, y reportería gerencial — todo bajo un único sistema con permisos diferenciados por rol y por sede.

El sistema define **11 roles de usuario**. Cada persona ve únicamente las herramientas de su función y, normalmente, solo los datos de su propia sede (planta o sucursal) — salvo los roles con visión global (Ejecutivo, Administrador de Sede, Administrador de Sistemas).

---

## 2. Resumen de Roles

| Rol | Función principal | Qué controla |
| :--- | :--- | :--- |
| **Operario** | Ejecuta la producción física | Registro de lotes y transformaciones en su máquina/turno |
| **Empaquetado** | Pesa y etiqueta el producto terminado | Peso neto, etiquetas, control de tolerancia |
| **Despacho** | Entrega la mercancía al cliente | Validación de carga, salida de stock |
| **Bodeguero** | Cuida la integridad del inventario | Stock, transferencias, alertas, kardex |
| **Vendedor** | Gestiona clientes y ventas | Pedidos, créditos, abonos |
| **Jefe de Planta** | Planifica la producción | Creación y ciclo de vida de las órdenes de producción |
| **Jefe de Área** | Supervisa la eficiencia de su sección | Indicadores de calidad/rendimiento, máquinas, rechazos |
| **Tintorero** | Formula el color y los químicos | Fórmulas, cálculos de laboratorio, stock de químicos |
| **Ejecutivo** | Analiza el negocio a nivel gerencial | Reportes consolidados, solo lectura, todas las sedes |
| **Administrador de Sede** | Máxima autoridad de una planta/sucursal | Gestión local y auditoría de su sede |
| **Administrador de Sistemas** | Configuración global del sistema | Maestros de datos, usuarios y permisos de toda la empresa |

---

## 3. Detalle por Rol

### 3.1 Operario

Ejecuta la producción física en planta: registra el trabajo que se hace en su máquina y turno.

**Panel principal (tarjetas de órdenes asignadas)**
- Ve una tarjeta por cada orden de producción activa asignada a su máquina y turno.
- Ve el producto, el código de la orden, la fórmula y la meta en kilos de cada tarjeta.
- Ve una barra de progreso con los kilos ya producidos y los kilos pendientes.
- Recibe un aviso automático cuando la orden está por completarse (90%–99% de avance).
- Recibe un aviso automático cuando la orden alcanza el 100% de la meta.
- Puede leer las notas u observaciones que el Jefe de Planta dejó en la orden (ej. "Prioridad Alta", ajustes de proceso).

**Registrar Avance (botón "Avance")**
- Puede registrar un nuevo lote de producción para la orden asignada.
- Puede ingresar el peso neto producido.
- Puede ingresar el número de unidades (bobinas o conos).
- Puede indicar si hubo desperdicio y cuánto.
- Puede seleccionar el motivo del desperdicio: Falla Técnica/Máquina, Calidad de Hilo/Material, Arranque/Setup, Corte/Empalme, u Otro.
- Si la orden es una mezcla de varios lotes, puede indicar de qué lote de origen tomó cada componente y en qué cantidad.

**Registrar Transformación (botón "Transformación")**
- Puede registrar el paso de producto de una máquina a otra.
- Puede indicar el producto de salida.
- Puede ingresar el peso de entrada.
- Puede ingresar el peso de salida.
- El sistema calcula automáticamente la merma generada.
- Puede consultar el árbol completo de trazabilidad de la orden (todas las transformaciones y su merma, etapa por etapa y acumulada).
- Solo puede operar dentro de las órdenes de su propia área y sede.

**Últimos Ingresos (tabla de sus propios registros)**
- Puede ver sus últimos registros de producción: lote, orden, peso neto, unidades, merma y fecha.
- Puede editar directamente el peso neto de un registro reciente.
- Puede editar directamente las unidades de un registro reciente.
- Puede editar directamente la merma de un registro reciente.
- Puede eliminar un registro de producción indicando una justificación obligatoria.
- Al eliminar, el sistema le muestra exactamente qué se revierte: kilos de stock producido, materia prima devuelta, químicos revertidos y la eliminación del lote.

**Movimientos manuales de inventario**
- Puede registrar una entrada o salida manual de inventario.
- Puede elegir el producto del movimiento.
- Puede elegir la bodega del movimiento.
- Puede indicar el motivo: Entrada - Compra de Material, Entrada - Producción, Salida - Consumo de Producción, Salida - Venta, o Ajuste de Inventario.
- Puede anotar un documento de referencia opcional.
- Puede consultar su propio historial de movimientos: fecha, tipo, producto, origen, destino y cantidad.

### 3.2 Empaquetado

Estación final de producción: pesa y etiqueta el producto antes de almacenarlo o venderlo.

**Configuración de impresión y balanza**
- Puede elegir su modo de impresión preferido: Automático (Zebra o PDF), Zebra ZPL Nativo, o PDF Universal.
- Esa preferencia queda guardada en su propio equipo (no se pierde al cerrar sesión).
- Puede conectar una balanza física al computador con el botón "Conectar Balanza (COM)".
- Ve un indicador visual (punto verde/rojo) de si la balanza está conectada.

**Indicadores del turno**
- Ve cuántos bultos ha empacado hoy.
- Ve el peso total acumulado del turno.
- Ve el promedio de peso por bulto.

**Registrar Nuevo Bulto/Caja**
- Puede seleccionar la orden de producción a la que pertenece el bulto.
- Al seleccionar la orden, ve automáticamente su porcentaje de avance ("X% — Y de Z kg requeridos").
- Puede usar el código de lote/bulto que el sistema le sugiere automáticamente.
- Puede elegir el tipo de presentación: Caja, Funda, Cono o Rollo.
- El sistema autocompleta la tara según el tipo de presentación elegido (y puede editarla).
- Puede indicar el número de unidades.
- Puede elegir el turno: Mañana, Tarde o Noche.
- Puede ingresar el peso bruto manualmente o dejar que se autocomplete desde la balanza conectada.
- El sistema calcula el peso neto automáticamente y en tiempo real (peso bruto − tara).
- Si el producto es tela, puede ingresar la cantidad de metros.
- Puede registrar la hora de inicio y la hora final del proceso.
- Puede marcar la casilla "Finalizar Orden de Producción" si es el último bulto de esa orden.
- Al registrar, el sistema imprime la etiqueta automáticamente.
- Si el peso pesado se aleja más de un 10% del esperado, el sistema le exige confirmar explícitamente antes de continuar.

**Historial reciente**
- Puede ver sus últimos registros: código de lote y peso neto.
- Puede reimprimir la etiqueta de cualquier registro reciente con un ícono de impresora.

**Buscador de lotes (para trabajar con lotes de otros días)**
- Puede buscar lotes de cualquier fecha, no solo del día actual.
- Puede filtrar por rango de fechas (desde/hasta).
- Puede filtrar por turno.
- Puede filtrar por código de lote.
- Puede filtrar por calidad: Primera Calidad, Segunda Calidad, Saldo/Retazo, o todas.

**Reimprimir etiqueta**
- Puede reimprimir una etiqueta idéntica a la original.
- Debe indicar el motivo: Etiqueta Dañada, Etiqueta Perdida, Atasco de Impresora, Reempaque, u Otro.
- Puede agregar un detalle opcional en texto libre.
- La reimpresión no requiere autorización de un supervisor, pero queda registrada en auditoría.

**Solicitar Reetiquetado (corrección de un lote ya registrado)**
- Puede solicitar la corrección de un lote ya registrado (peso o calidad).
- Puede ingresar el usuario y la clave de su Jefe de Área (u otro supervisor) directamente en el mismo puesto, sin cerrar su propia sesión.
- El código de lote y el código QR de trazabilidad del lote no cambian aunque se corrija el dato.
- Solo un supervisor (Jefe de Área, Jefe de Planta, Administrador de Sede o de Sistemas) puede autorizar y ejecutar el reetiquetado.

### 3.3 Despacho

Gestiona la salida física de mercancía hacia los clientes.

**Selección de pedidos**
- Puede buscar pedidos pendientes por nombre de cliente o número de guía.
- Puede ver la lista de pedidos pendientes con cliente, cantidad de ítems, estado de pago (Pagado/Crédito) y peso total.
- Puede seleccionar varios pedidos a la vez para despacharlos juntos.
- Si selecciona pedidos de clientes distintos, el sistema le avisa (pero le permite continuar).
- Puede iniciar el proceso de despacho.
- Puede consultar el historial de despachos ya realizados.

**Despacho en proceso**
- Puede escanear el código de barras de cada bulto para validar la carga.
- El sistema le avisa si un lote ya fue escaneado previamente.
- Puede quitar de la lista un ítem que escaneó por error.
- Puede ver en tiempo real, producto por producto, si lo cargado coincide con lo que exige el pedido (barra de progreso "escaneado / requerido").
- Puede confirmar la salida del despacho.
- Si falta mercancía por escanear, el sistema le muestra el detalle exacto del faltante antes de confirmar.
- Puede decidir despachar de todas formas con lo que ya escaneó (despacho parcial).
- Al confirmar, el sistema descuenta el stock automáticamente.
- Al confirmar, el pedido cambia de estado a "Despachado".
- Al completar, el sistema imprime/descarga automáticamente el PDF de cada pedido incluido.

**Historial de Despachos**
- Puede filtrar el historial por rango de fechas (desde/hasta).
- Puede ver, por cada despacho, la fecha y hora, el responsable, los pedidos incluidos, los bultos y el peso total.
- Puede abrir el detalle completo de un despacho: total de pedidos, total de bultos, peso total.
- Puede ver la lista de pedidos abarcados en ese despacho (cliente y guía).
- Puede ver la lista de lotes escaneados en ese despacho (producto, código de lote, peso).
- Si hubo faltantes, puede ver qué quedó sin despachar (requerido vs. escaneado vs. faltante).
- Puede revertir un despacho ya finalizado.
- Al revertir, debe indicar una justificación obligatoria.
- Al revertir, el sistema le muestra cuántos kilos de stock se restaurarán y a qué bodegas de origen.
- *Nota: la devolución parcial de un lote específico (sin revertir todo el despacho) no está confirmada como funcionalidad operativa hoy — se recomienda validarla con el equipo técnico.*

### 3.4 Bodeguero

Responsable de la integridad del stock y la organización de los almacenes.

**Indicadores generales**
- Ve el total de productos registrados en el catálogo.
- Ve el total de bodegas del sistema.
- Ve el total de lotes de producción registrados.

**Stock**
- Puede consultar el stock en tiempo real de cualquier producto.
- Puede filtrar el stock por sede.
- Puede filtrar el stock por bodega.
- Puede buscar por texto: producto, bodega o lote.

**Entrada de materia prima**
- Puede registrar el ingreso de materia prima a una bodega.
- Puede indicar el producto.
- Puede indicar la bodega destino.
- Puede indicar el lote (opcional).
- Puede indicar la cantidad.
- Puede indicar el proveedor.
- Puede indicar el país de origen.
- Puede indicar la calidad.
- Puede indicar una referencia (ej. número de factura).
- Debe indicar una justificación obligatoria de la entrada.

**Transferencias entre bodegas**
- Puede transferir stock de una bodega a otra.
- Puede elegir el producto a transferir.
- Puede elegir la bodega de origen.
- Al elegir producto y bodega de origen, el sistema le muestra solo los lotes que tienen stock disponible ahí, con su cantidad exacta.
- El sistema valida que la cantidad a transferir no supere el stock disponible del lote elegido.
- Puede elegir la bodega de destino (excluye automáticamente la de origen).
- Puede agregar observaciones.
- Debe indicar una justificación obligatoria.

**Transformación de producto**
- Puede transformar un producto en otro dentro de la bodega.
- Puede indicar la bodega y el lote de origen.
- Puede indicar el producto y la bodega de destino.
- Puede indicar la cantidad transformada.
- Debe indicar una justificación obligatoria.

**Kardex (historial de movimientos)**
- Puede filtrar el historial por bodega.
- Puede filtrar por producto.
- Puede filtrar por tipo de operación: todos, solo entradas o solo salidas.
- Puede filtrar por rango de fechas.
- Puede exportar el resultado a Excel/CSV.
- Puede registrar una merma de inventario: producto, bodega de origen, cantidad y motivo.
- Si filtra un producto y una bodega específicos a la vez, puede ver el saldo acumulado corrido de ese producto en esa bodega.
- Puede abrir el historial de auditoría de cualquier movimiento: quién lo cambió, cuándo, qué campo, el valor anterior, el valor nuevo y el motivo.
- Puede editar la cantidad o la referencia de un movimiento (con un motivo de al menos 10 caracteres).
- Puede eliminar un movimiento indicando una justificación; el sistema revierte el stock automáticamente antes de borrarlo.
- Si el movimiento pertenece a un despacho, el sistema le bloquea el borrado directo y lo obliga a usar el flujo de reversión de despacho.

**Reportes**
- Debe elegir primero una bodega principal para poder descargar reportes.
- Puede descargar el Kardex de Movimientos en Excel (filtrable por producto y rango de fechas).
- Puede descargar una foto (snapshot) del Stock Actual.
- Puede descargar un reporte de Antigüedad de Stock, eligiendo el rango: Reciente (0-30 días), Medio (31-90), Lento (91-180) o Crítico (más de 180 días o sin movimiento).
- Puede descargar un reporte de Productos con Stock Cero (agotados en esa bodega).
- Puede descargar un reporte de Rotación de Movimientos.
- Puede descargar el Catálogo maestro de Productos completo.

**Alertas de stock bajo**
- Puede ver todos los productos que cayeron bajo su stock mínimo configurado.
- Puede ver, por cada alerta, el código, el producto, la bodega, el stock actual y el stock mínimo.

**MRP (planificación de requerimientos de materiales)**
- Puede ejecutar el motor de MRP con un botón para recalcular qué materiales faltan.
- Puede ver las órdenes de compra sugeridas por el sistema: producto, sede, cantidad, estado, fecha de generación.
- Puede ver de dónde viene cada necesidad de material (de qué pedido u orden de producción), la cantidad requerida, la sede y la fecha en que se necesita.

### 3.5 Vendedor (Ejecutivo de Ventas)

Motor comercial de la empresa: gestiona la cartera de clientes y los créditos.

**Indicadores generales**
- Ve el total de cuentas por cobrar de toda su cartera.
- Ve el total de pedidos que ha realizado.
- Ve el total de clientes que tiene a cargo.
- Ve cuántos de sus clientes tienen un beneficio/descuento especial activo.

**Gestión de clientes**
- Puede registrar un cliente nuevo.
- Puede ingresar el RUC o cédula del cliente.
- Puede ingresar el nombre o razón social.
- Puede ingresar la dirección de envío.
- Puede asignar el nivel de precio del cliente: Normal o Mayorista.
- Puede definir el límite de crédito del cliente.
- Puede definir el plazo de crédito: Contado (0 días), 8, 30, 45 o 60 días.
- Puede editar los datos de un cliente existente (debe indicar una justificación).
- No puede activar por su cuenta el beneficio/descuento especial de un cliente — eso requiere autorización de un administrador.
- Puede inactivar un cliente.
- Puede buscar un cliente por nombre o RUC.
- Puede ver la lista completa de sus clientes con su estado de cuenta.
- Puede ver cuánto le debe cada cliente (saldo pendiente) frente a su límite de crédito, con una barra visual que se pone roja si supera el 80%.
- Puede ver si un cliente está en mora, y cuántos días de atraso tiene.
- Puede ver la fecha y el primer producto de la última compra de cada cliente.
- Puede abrir el expediente completo de un cliente con un clic: saldo pendiente, cartera vencida, límite de crédito.

**Pedidos de venta**
- Puede crear un nuevo pedido de venta.
- Puede elegir el cliente del pedido (el sistema le muestra su límite de crédito de inmediato).
- El sistema le avisa si el cliente tiene cartera vencida antes de continuar.
- El sistema valida automáticamente que el pedido no supere el límite de crédito del cliente.
- Puede ingresar el número de guía o factura.
- Puede agregar varios productos a un mismo pedido.
- Puede aplicar automáticamente un 15% de IVA a un producto del pedido.
- Puede ingresar el peso o los metros del producto vendido.
- Puede definir el precio unitario de cada producto (no puede vender por debajo del precio mínimo del catálogo, protegiendo el margen).
- El sistema calcula el total del pedido en tiempo real, a medida que agrega productos.
- Puede indicar si el cliente emite retención, y su valor.
- Puede marcar si el cliente pagó en caja (contado).
- El sistema le advierte si el cliente es de contado y el pedido aún no está marcado como pagado.
- El sistema le asigna automáticamente el pedido a sí mismo como vendedor responsable, sin pasos manuales.
- Puede ver el historial de sus últimas ventas: fecha, cliente, guía, estado de pago (Pagado / Abonado X% / Pendiente / Anulado) y total.
- Puede buscar sus ventas por guía o por cliente.
- Puede reimprimir el PDF de cualquier pedido en cualquier momento.
- Puede editar un pedido mientras esté pendiente (guía, fecha de despacho, valor de retención, marcarlo como pagado), indicando un motivo de al menos 10 caracteres.
- Puede anular un pedido mientras esté pendiente, indicando un motivo de al menos 10 caracteres.
- Puede ver el motivo de anulación de un pedido ya anulado.

**Pagos y cartera**
- Puede registrar un abono (pago) de un cliente a su cuenta por cobrar.
- Puede indicar el monto del abono.
- Puede indicar el método de pago: Transferencia, Efectivo, Cheque u Otro.
- Puede indicar una referencia o número de comprobante.
- Puede marcar el pago como un anticipo.
- Puede ver el historial completo de abonos/recibos de cada cliente: fecha, método, monto.
- Puede revertir un abono registrado por error, indicando una justificación de al menos 5 caracteres.
- Al revertir un abono, el sistema restaura automáticamente el saldo pendiente del cliente a su valor anterior.

**Reportes**
- Puede elegir un rango de fechas (inicio y fin) para sus reportes.
- Puede descargar en Excel el reporte de Ventas Detalladas del período.
- Puede descargar en Excel el ranking de Top Clientes por monto comprado.
- Puede descargar en Excel el reporte de Cartera Vencida (saldos impagos a la fecha).

### 3.6 Jefe de Planta

Planificador central de toda la producción.

**Indicadores de control ("torre de control")**
- Ve el % de cumplimiento diario (kilos producidos hoy vs. planificados hoy), con semáforo de color (verde 90% o más, ámbar entre 70% y 89%, rojo menos de 70%).
- Ve el índice de desperdicio del día (% de merma sobre lo producido).
- Ve si hay trabajo en proceso estancado (kilos de WIP detenido), con alerta parpadeante si existe.

**Órdenes de producción**
- Puede crear una nueva orden de producción — es el único rol autorizado para crearlas.
- Puede definir el código de la orden.
- Puede definir el peso neto requerido.
- Puede definir el producto y la bodega de entrada.
- Puede definir el producto y la bodega de salida.
- Puede asignar el área responsable de la orden.
- Puede definir la prioridad: Baja, Normal, Alta o Urgente.
- Puede definir la fecha de inicio y la fecha de fin planificadas.
- Puede agregar observaciones/notas a la orden (las verá luego el operario asignado).
- Puede asignar cada orden a una sede específica.
- Puede editar una orden existente.
- Puede eliminar una orden.
- Puede cambiar el estado de una orden (iniciar proceso, marcar finalizada).
- Puede buscar órdenes por texto (código o producto).
- Puede filtrar órdenes por estado: Pendiente, En Proceso o Finalizada.
- Puede filtrar órdenes por máquina.
- Ve la fecha de entrega de cada orden resaltada en rojo si está vencida o en ámbar si vence hoy.
- Ve un badge que indica si ya se descontaron los químicos de la fórmula de esa orden.
- Al hacer clic en una orden, puede ver su panel completo de detalle: producto, fórmula, sede, área, progreso, fechas, bodegas y notas.
- Puede consultar (solo lectura) la trazabilidad completa de cualquier orden: el árbol de transformaciones con el % de merma acumulada. No puede registrar transformaciones directamente — esa tarea es de Jefes de Área y Operarios.
- Puede consultar los requisitos de materiales de una orden: qué químicos y materia prima necesita, con cantidad y unidad.
- Puede registrar un lote de producción directamente desde el panel de la orden: código de lote, peso neto, máquina, turno, hora de inicio y fin.

**Transferencias entre áreas**
- Puede ver el historial completo de transferencias de producto entre áreas de toda la planta.
- Puede registrar una nueva transferencia entre áreas.
- Puede elegir la orden de origen.
- Puede elegir el área de destino.
- Puede indicar la cantidad transferida.
- Puede agregar observaciones de calidad.

**Reportes gerenciales**
- Puede descargar en PDF el Reporte de Avance Operativo.
- Puede descargar en PDF el Balance de Masas Mensual.

**Buscador de lotes**
- Puede buscar lotes por fecha, turno, código de lote o calidad.
- Puede reimprimir la etiqueta de cualquier lote encontrado.

### 3.7 Jefe de Área

Supervisor de la eficiencia operativa y la calidad en una sección específica.

**Indicadores de su área**
- Ve la producción total en kilos de su área.
- Ve el rendimiento (yield) en porcentaje.
- Ve el porcentaje de producto de primera calidad (FPY — componente "Calidad" del OEE).
- Ve la distribución de su producción por calidad (primera/segunda/saldo).
- Ve el tiempo promedio por lote.
- Ve cuántas alertas de stock bajo tiene activas.
- Ve el indicador OEE de su área, con semáforo (verde 85% o más, ámbar 60% o más, rojo por debajo).
- Ve el desglose del OEE en Disponibilidad, Desempeño y Calidad.
- Ve el OEE individual de cada máquina de su área.

**Asignación de órdenes**
- Puede ver las órdenes de su área que están pendientes de iniciar.
- Puede ver las notas que dejó el Jefe de Planta en cada orden.
- Puede elegir la máquina para ejecutar la orden.
- Puede elegir el operario que la ejecutará.
- Puede asignar la orden (esto inicia su producción) — no puede crear órdenes nuevas, eso es exclusivo del Jefe de Planta.

**Producción en curso**
- Puede ver el flujo/trazabilidad de cada orden en proceso de su área.
- Puede registrar una transformación de producto: máquina, producto de salida, peso de entrada y peso de salida.
- El sistema calcula la merma automáticamente y no permite que el peso de salida supere al de entrada.
- Solo puede registrar transformaciones dentro de las órdenes de su propia área y sede.

**Gestión de máquinas**
- Puede ver el estado de cada máquina: Operativa, Mantenimiento o Inactiva.
- Puede ver si una máquina es un recurso compartido entre varias líneas de producción.
- Puede ver la carga de trabajo (barra de avance) de cada máquina.
- Puede ver qué operarios están asignados a cada máquina.
- Puede crear una máquina nueva: nombre, estado, capacidad máxima (kg/turno), eficiencia ideal.
- Puede configurar a qué producto y bodega va la merma vendible generada por una máquina.
- Puede editar una máquina existente.
- Puede activar o desactivar una máquina.
- Puede eliminar una máquina (con justificación de al menos 10 caracteres).

**Paros de máquina**
- Puede registrar un paro de máquina.
- Debe indicar la categoría del paro: Avería, Setup, Microparo, Velocidad Reducida, Rechazo de Arranque, Defecto de Proceso, Falta de Material, Mantenimiento Planificado, u Otro.
- Puede indicar la hora de inicio del paro.
- Puede indicar la hora de fin del paro (o dejarlo abierto, "en curso").
- Puede marcar el paro como "planificado" para que no penalice el indicador de Disponibilidad.
- Puede agregar una descripción del paro.

**Líneas de producción**
- Puede crear una línea de producción nueva (agrupación de máquinas que trabajan como una célula de manufactura flexible).
- Puede definir el nombre, la descripción y el estado de la línea.
- Puede elegir qué máquinas forman parte de esa línea.
- Puede compartir una misma máquina entre varias líneas sin duplicar su capacidad.
- Puede editar o eliminar una línea de producción.

**Etapas de producción del área**
- Puede definir la secuencia de etapas del proceso de su área.
- Puede definir el nombre y el orden secuencial de cada etapa.
- Puede asignar la máquina de cada etapa.
- Puede asignar la bodega de entrada (materia prima) y de salida (producto terminado) de cada etapa.
- Puede definir el tiempo estimado (en minutos) de cada etapa.
- Puede editar o eliminar una etapa.
- Puede ver el flujo general de producción de toda su área como una línea de tiempo, orden por orden.

**Lotes y rechazos**
- Puede ver los lotes recientes de su área con su máquina, operario y peso.
- Puede rechazar un lote de producción, indicando un motivo obligatorio (trazabilidad ISO 9001).
- Al rechazar, el sistema revierte automáticamente el stock, el consumo de mezcla y la merma asociados a ese lote.
- Puede reetiquetar un lote ya registrado (corregir peso o reclasificar su calidad), con motivo obligatorio; el código de lote y el QR de trazabilidad no cambian.

**Alertas de inventario**
- Puede ver qué insumos (químicos o hilos) de su área están por agotarse, con código, descripción y stock mínimo.

**Transferencias entre áreas**
- Puede registrar el paso de producto terminado de su área hacia la siguiente etapa de producción.
- Puede ver el historial de esas transferencias.

### 3.8 Tintorero

Especialista en color y formulación química para los procesos de tintura y acabado.

**Fórmulas químicas**
- Puede crear una fórmula de color nueva.
- Puede editar una fórmula existente.
- Puede versionar una fórmula (llevar su historial de cambios).
- Puede definir el código de la fórmula.
- Puede definir el nombre del color.
- Puede marcar el estado de la fórmula: En Pruebas o Aprobada.
- Puede definir las fases del proceso: Pre-Tratamiento/Blanqueo, Tintura Principal, Lavado/Jabonado, Suavizado/Acabado Final, o Baño de Auxiliares Extras.
- Puede definir la temperatura de cada fase.
- Puede definir el tiempo de cada fase.
- Puede agregar los químicos o colorantes de cada fase.
- Puede buscar un químico por código o descripción al agregarlo a una fase.
- Puede definir cómo se calcula la dosis de cada químico: en g/L o en % de agotamiento.
- Puede reordenar los químicos dentro de una fase.
- Puede eliminar una fase o un químico de la fórmula.
- Puede buscar fórmulas existentes por código o color.

**Calculadora de laboratorio**
- Puede ingresar el volumen de tela a procesar (en kg).
- Puede ingresar la relación de baño (1:X).
- El sistema recalcula automáticamente, en tiempo real, el peso exacto de cada químico de cada fase.

**Sincronización con máquinas dosificadoras**
- Puede exportar una fórmula en el formato que usan las máquinas dosificadoras automáticas (sincronización Infotint).

**Stock de químicos**
- Puede ver el total de químicos registrados.
- Puede ver cuántos están en stock bajo.
- Puede ver cuántos están disponibles.
- Puede ver, por cada químico, su cantidad disponible y su mínimo configurado.
- Puede ver el historial de descargas (consumos) de un químico específico: fecha, orden de producción que lo consumió, cantidad y estado.
- El sistema descuenta o repone automáticamente el stock de químicos cuando se crea, edita o elimina una orden de producción con fórmula asignada; si la orden ya generó consumo, exige una justificación para modificarla o eliminarla.

### 3.9 Ejecutivo

Análisis estratégico y seguimiento gerencial multi-sede. Acceso de **solo lectura** a todos los módulos.

**Filtros generales (aplican a todo el panel)**
- Puede elegir ver todas las sedes a la vez o filtrar por una sede específica.
- Puede actualizar los datos manualmente con un botón.
- Puede activar la actualización automática cada 60 segundos.
- Puede elegir un rango de fechas para producción y reportes.

**Resumen**
- Puede ver cuántas órdenes de producción están en proceso.
- Puede ver cuántas están pendientes.
- Puede ver los kilos producidos hoy.
- Puede ver los kilos producidos en el mes.
- Puede ver cuántas órdenes de compra sugeridas están pendientes de decisión (con alerta si hay).
- Puede ver cuántos productos están en déficit de stock.
- Puede ver cuántas órdenes de compra ya fueron aprobadas.
- Puede ver cuántas alertas de stock bajo hay activas.
- Puede ver el total de cuentas por cobrar.
- Puede ver la cartera vencida, con semáforo automático si supera el 40% del límite total de crédito.
- Puede ver cuántos pedidos están pendientes.
- Puede ver cuántos pedidos ya fueron despachados.

**Producción**
- Puede ver los kilos producidos hoy, en la semana y en el mes.
- Puede ver el tiempo promedio por lote.
- Puede ver un gráfico con la distribución de órdenes por estado.
- Puede ver la tendencia de producción, eligiendo el rango (7/15/30/90 días).
- Puede alternar la vista de tendencia entre diaria, semanal o mensual.
- Puede descargar el reporte de Órdenes de Producción del rango de fechas elegido.
- Puede descargar el reporte de Lotes de Producción del rango de fechas elegido.

**MRP (planificación de materiales)**
- Puede ejecutar el motor de MRP con un botón ("Ejecutar Motor MRP").
- Puede ver las órdenes de compra sugeridas: producto, sede, cantidad, estado.
- Puede ver de dónde viene cada necesidad de material — de qué pedido u orden de producción se originó —, cuánto se requiere y para cuándo: esta es su visión completa del consumo que sustenta cada sugerencia de compra.

**Stock**
- Puede ver el total de productos del catálogo.
- Puede ver la cantidad de bodegas activas del sistema.
- Puede ver el stock total en unidades.
- Puede ver cuántas alertas de stock hay activas.
- Puede ver un gráfico de barras con el stock por bodega.
- **Puede hacer clic en una bodega del gráfico para que se despliegue el detalle completo de todo lo que tiene esa bodega** (producto, lote y cantidad).
- Puede ver un ranking de los 8 productos con mayor faltante.
- Puede buscar en la tabla de alertas de stock bajo por código o nombre de producto.

**Ventas**
- Puede ver el total de cuentas por cobrar.
- Puede ver la cartera vencida.
- Puede ver el total de ventas del período.
- Puede ver cuántos clientes activos hay, y cuántos de ellos tienen un beneficio especial.
- Puede ver el embudo de pedidos: Pendientes, luego Despachados, luego Facturados.
- Puede hacer clic en una etapa del embudo para ver la lista de pedidos en ese estado.
- Puede ver un ranking de ventas por vendedor (top 10).
- Puede hacer clic en un vendedor para ver sus pedidos y el estado de pago de cada uno.
- Puede ver un gráfico de estado de cobranza (pagado vs. pendiente).
- Puede ver un ranking de los clientes que más compran (top 8).
- Puede hacer clic en un cliente para ver su historial de compras.
- Puede ver un ranking de los clientes más deudores (top 8).
- Puede hacer clic en un cliente deudor para ver su perfil de riesgo financiero: deuda actual, límite de crédito y % de riesgo (deuda/límite).
- Puede descargar el reporte de Ventas del período.
- Puede descargar el reporte de Top Clientes.
- Puede descargar el reporte de Cartera Deudores.

**Reportes (centro consolidado)**
- Puede elegir un rango de fechas y una sede, aplicable a todos los reportes de esta pestaña.
- Puede descargar el reporte de Ventas Gerencial.
- Puede descargar el reporte de Top Clientes.
- Puede descargar el reporte de Cartera Deudores.
- Puede descargar el reporte de Órdenes de Producción.
- Puede descargar el reporte de Lotes de Producción.
- Puede descargar el reporte de Tendencia de Producción.
- Puede ver una tabla de referencia rápida con las 10 alertas de stock más recientes.

**Restricciones**
- No puede crear, editar ni eliminar ningún registro — es un rol de solo lectura.
- Mientras descarga un reporte, no puede iniciar otra descarga hasta que la primera termine (previene descargas simultáneas).

### 3.10 Administrador de Sede

Máxima autoridad operativa en una ubicación física. Hereda **todas** las funciones del Ejecutivo (arriba: Resumen, Producción, MRP, Stock, Ventas, Reportes — incluyendo el drill-down de bodegas y el botón de MRP), fijas a su propia sede, más:

**Funciones adicionales propias de su rol**
- Puede supervisar todas las áreas de su sede: producción, ventas y bodega.
- Puede gestionar usuarios a nivel local (de su propia sede).
- Puede gestionar áreas a nivel local (de su propia sede).
- Puede entrar a la pestaña de Aprobaciones. *(Nota: hoy esta función está desactivada en el sistema; los movimientos de inventario se procesan de forma automática, sin pasar por una aprobación manual — el propio sistema lo indica así en pantalla.)*
- Puede consultar la auditoría de su sede: quién hizo cada cambio, cuándo, qué se modificó (valor anterior vs. nuevo) y con qué justificación.

**Diferencia frente al Ejecutivo**
- No tiene selector para cambiar de sede — opera siempre sobre la suya.
- Al entrar, su pantalla por defecto es Aprobaciones, no Resumen.

### 3.11 Administrador de Sistemas

Configuración técnica y gestión de los datos maestros a nivel de toda la empresa.

**Panel general de sedes**
- Puede ver la lista de todas las sedes de la empresa como tarjetas.
- Puede hacer clic en una sede para que todo el panel se filtre por esa sede.
- Puede ver, por cada sede, cuántas áreas, usuarios, bodegas y órdenes tiene.
- Puede ver el estado de cada sede (Activa/Inactiva).

**Resumen de la sede seleccionada**
- Puede ver cuántas áreas tiene esa sede.
- Puede ver cuántos usuarios tiene esa sede.
- Puede ver cuántas bodegas tiene esa sede.
- Puede ver cuántas ventas/pedidos tiene esa sede.
- Puede ver el listado de sus áreas.
- Puede ver el listado de sus bodegas.

**Producción de la sede seleccionada**
- Puede ver la tabla de órdenes de producción: código, producto, peso requerido, estado, fecha.
- Puede ver el catálogo de fórmulas de color.
- Puede ver los lotes producidos: código, peso, máquina y turno.

**Inventario (mismas 6 funciones que el Bodeguero, a nivel de toda la organización)**
- Puede consultar el stock por producto y bodega.
- Puede registrar entradas de materia prima.
- Puede ejecutar transferencias entre bodegas.
- Puede ejecutar transformaciones de producto.
- Puede consultar y exportar el Kardex.
- Puede auditar, editar o eliminar cualquier movimiento de inventario.
- Puede registrar mermas de inventario.
- Puede descargar los mismos 6 reportes que el Bodeguero (Kardex, Snapshot de Stock, Antigüedad de Stock, Stock Cero, Rotación, Catálogo de Productos).

**Gestión de Usuarios**
- Puede crear un usuario nuevo.
- Puede definir su nombre de usuario y contraseña.
- Puede definir sus nombres y apellidos.
- Puede definir su correo electrónico.
- Puede asignarle un rol.
- Puede asignarle una sede.
- Puede asignarle un área (esta opción se habilita solo después de elegir la sede).
- Puede editar un usuario existente.
- Puede eliminar un usuario existente.

**Gestión de Sedes**
- Puede crear una sede nueva: nombre, ubicación, estado.
- Puede editar una sede existente.
- Puede desactivar una sede.

**Gestión de Áreas**
- Puede crear un área nueva, asociada a una sede.
- Puede editar un área.
- Puede eliminar un área.

**Gestión de Productos**
- Puede crear un producto nuevo: código, descripción, tipo (Hilo, Tela, Sub-producto, Químico, Insumo, Materia Prima, Merma-Desperdicio Vendible), presentación, país, calidad, unidad de medida, stock mínimo y precio base.
- Puede editar un producto.
- Puede eliminar un producto.
- Puede filtrar el catálogo de productos por tipo.

**Gestión de Químicos**
- Puede crear un químico nuevo con el mismo esquema que los productos.
- Puede editar o eliminar un químico.

**Gestión de Fórmulas**
- Puede crear o editar el catálogo de fórmulas de color: código, nombre del color, descripción.
- Al editar una fórmula, debe indicar una justificación.

**Gestión de Bodegas**
- Puede crear una bodega nueva, asociada a una sede.
- Puede asignar qué bodegueros administran cada bodega (checklist de usuarios de esa sede).
- Debe indicar una justificación al crear o editar una bodega.

**Gestión de Clientes**
- Puede crear un cliente nuevo directamente, sin depender del rol Vendedor.
- Puede editar un cliente: RUC/cédula, razón social, dirección, nivel de precio, límite y plazo de crédito.
- Debe indicar una justificación al editar.

**Gestión de Proveedores**
- Puede crear un proveedor nuevo (nombre).
- Puede editar o eliminar un proveedor.

**Roles y permisos**
- Puede ver cuántos usuarios tiene asignados cada rol del sistema (vista de solo lectura).
- Gestiona los grupos de permisos: define qué puede hacer cada rol.

**Auditoría**
- Puede consultar el historial de auditoría de toda la organización.
- Puede activar la opción de ver todas las sedes a la vez (a diferencia del Administrador de Sede, que solo ve la suya).

---

## 4. Funcionalidad Transversal del Sistema

Capacidades que no pertenecen a un solo rol, sino que sostienen la operación de todos los módulos anteriores.

- Cada persona inicia sesión con su propio usuario y contraseña.
- El sistema solo muestra las herramientas que el rol de esa persona tiene permitidas.
- Toda operación crítica (crear, editar, eliminar, revertir) queda registrada de forma permanente: quién, cuándo, qué campo cambió, el valor anterior, el valor nuevo y el motivo cuando aplica.
- Ese registro de auditoría es consultable como pantalla propia para Ejecutivo, Administrador de Sede y Administrador de Sistemas.
- Las etiquetas se imprimen con tres niveles de respaldo: impresora Zebra dedicada, PDF universal para cualquier impresora, o copiar al portapapeles como último recurso.
- El sistema distingue una simple reimpresión de etiqueta (copia idéntica) de un reetiquetado (corrección de peso o calidad con autorización de supervisor).
- El código de lote y el código QR de trazabilidad nunca cambian, aunque se corrija un dato del lote.
- El escaneo de código de barras valida en el momento que el producto exista, tenga stock disponible y su información esté completa.
- Los reportes gerenciales en Excel se generan bajo demanda, filtrables por fecha y por sede.
- Por defecto, cada usuario ve solo la información de su propia sede.
- Ejecutivo, Administrador de Sede y Administrador de Sistemas son la excepción: pueden ver varias o todas las sedes.
- Los despachos, pagos, movimientos de inventario y consumos de químicos pueden revertirse.
- Toda reversión exige un motivo obligatorio.
- Toda reversión genera un movimiento de compensación en el historial — nunca se borra un registro directamente.
- Cualquier edición o eliminación de datos sensibles (movimientos de stock, clientes, fórmulas, bodegas, precios) exige que el usuario explique por qué, con un mínimo de caracteres — este patrón se repite en todos los módulos administrativos.

---

## 5. Reglas de Negocio que Protegen la Operación

1. **Aislamiento por sede**: cada usuario interactúa solo con los datos de su sede asignada.
2. **Validación de crédito**: no se permiten ventas si el cliente excede su límite de crédito, y el vendedor no puede vender por debajo del precio mínimo del producto.
3. **Procesos "todo o nada"**: operaciones críticas (despacho, transferencia, rechazo de lote) se ejecutan de forma atómica — si un paso falla, se revierte todo el proceso.
4. **Trazabilidad máxima**: cada movimiento de inventario registra el usuario, la hora y el documento de referencia; el código de lote y el QR de trazabilidad nunca cambian.
5. **Stock nunca negativo**: el sistema impide sacar mercancía de una bodega si no hay existencia física validada.

---

## 6. Funcionalidad Construida pero No Activa Hoy (a revisar con el equipo técnico)

Estos casos se detectaron al revisar el código real de las pantallas — vale la pena que gerencia los tenga presentes porque **la documentación anterior los describía como disponibles, pero hoy no operan así**:

- **Aprobación de movimientos de inventario (Administrador de Sede)**: la pantalla existe pero el propio sistema indica que el módulo está desactivado; todos los movimientos se procesan de forma inmediata sin pasar por aprobación manual.
- **Movimientos del Área (Jefe de Área)**: la sección aparece en el panel pero muestra el mensaje "en reconstrucción, próximamente" — no está operativa.
- **Panel de mezclas por porcentaje** (definir una receta de mezcla con validación de que sume 100%): el componente está construido pero no está enlazado a ningún dashboard actual — no es accesible para ningún rol todavía.
- **Devolución parcial de despacho** (devolver un lote específico sin revertir todo el despacho): no se confirmó como operativa en el sistema — solo existe la reversión completa de un despacho ya finalizado.

---

## 7. Funcionalidad en Desarrollo (No Disponible Aún)

Para evitar expectativas erróneas, estas capacidades **no existen hoy en ninguna forma** — están en el plan de trabajo futuro:

- Guía de despacho en PDF imprimible.
- Panel de métricas propio del módulo de Despacho.
- Gestión formal de no conformidades y planes de acción correctiva.
- Bitácora digital de entrega de turno entre operarios.
- Alertas visuales de escalamiento de problemas en planta (tipo semáforo).
- Mantenimiento autónomo de máquinas.
- Cálculo automático del cumplimiento de plan de entrega (a tiempo y completo).
- Panel de metas y comisiones para el equipo de ventas.
- Alertas automáticas de clientes morosos.
- Envío de notas de venta por WhatsApp.

---

*Documento elaborado combinando la documentación funcional del sistema con una revisión directa de las pantallas reales (componentes de interfaz) de los 11 dashboards. Se recomienda validar con el equipo técnico los puntos de la sección 6 antes de distribuir este documento fuera del área de sistemas.*
