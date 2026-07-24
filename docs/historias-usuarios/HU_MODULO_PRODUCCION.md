# Manual de Roles y Flujo de Trabajo (Producción TexCore)

Este documento describe el flujo de trabajo operativo dentro del módulo de producción de TexCore, detallando las responsabilidades y acciones disponibles para cada rol clave.

## 1. Jefe de Planta (Planificación)

**Responsabilidad Principal:** Planificar la producción y asegurar que se cumplan los requerimientos de materiales.

### Funciones Clave:
*   **Crear Órdenes de Producción (OP):**
    *   Define el **Producto** a fabricar (hilo, tela, etc.) y la **Fórmula de Color**.
    *   Establece la meta de producción (**Peso Neto Requerido**).
    *   Inicialmente, la orden nace en estado **`Pendiente`**.
    *   Puede definir fechas estimadas de inicio/fin y observaciones especiales.
*   **Consulta de Requerimientos:**
    *   Visualiza los materiales (hilos base, químicos) necesarios para cumplir con la OP antes de iniciarla.
*   **Monitoreo General:**
    *   Supervisa el avance global de las órdenes en planta.
    *   Al hacer clic en cualquier fila de la tabla de OPs se abre un **panel lateral de detalle** que muestra Producto, Fórmula Color, Sede, Área Responsable, barra de progreso, fechas y almacenes, con accesos directos para Editar, Eliminar, cambiar estado, consultar Requisitos o registrar Lote.
    *   Puede marcar órdenes como **`Finalizada`** manualmente si es necesario, aunque el sistema lo sugiere al completar la meta.
*   **Trazabilidad de Transformaciones (Solo Lectura):**
    *   Desde el panel de detalle de cualquier OP, visualiza el **árbol completo de transformaciones máquina a máquina**: cadena de productos (`producto_entrada → producto_salida`), merma por etapa y merma acumulada total (%).
    *   Vista de solo lectura — el registro de transformaciones es responsabilidad de Jefes de Área y Operarios.
*   **Coordinación de Transferencias Interárea:**
    *   Registra la **transferencia de producción** entre áreas cuando una orden termina en un área y pasa a la siguiente.
    *   Selecciona la orden de origen (producción finalizada) y la orden de destino (siguiente área).
    *   Especifica cantidad a transferir y observaciones (estado de calidad, etc.).
    *   Visualiza el historial de todas las transferencias registradas en la planta para auditoría y trazabilidad.

---

## 2. Jefe de Área (Asignación y Control)

**Responsabilidad Principal:** Gestionar los recursos de su área (maquinaria y personal) para ejecutar las órdenes planificadas.

### Funciones Clave:
*   **Gestión de Maquinaria:**
    *   **Dashboard de Control:** Visualiza el estado de cada máquina (Operativa, Mantenimiento, Inactiva) y su **Carga de Trabajo Actual** (basada en la producción del turno vs. capacidad máxima).
    *   **Mantenimiento:** Puede crear nuevas máquinas, editarlas o cambiar su estado según disponibilidad.
*   **Asignación de Órdenes:**
    *   Recibe las OPs en estado **`Pendiente`** que corresponden a su área.
    *   Asigna una **Máquina** específica y un **Operario Responsable**.
    *   Al guardar la asignación, la orden cambia automáticamente a estado **`En Proceso`**, habilitándola para producción.
*   **Registro de Transformaciones Máquina a Máquina (Fase 16):**
    *   Para cada orden en curso, registra una **transformación**: especifica `producto_salida`, `maquina`, `peso_entrada`, `peso_salida` y observaciones. La merma se calcula automáticamente.
    *   Las transformaciones forman una **cadena trazable**: el `producto_entrada` de cada transformación debe coincidir con el `producto_salida` de la anterior.
    *   Solo puede registrar transformaciones en órdenes de **su propia área y sede** (aislamiento estricto RBAC).
*   **Trazabilidad de Producción (Fase 16):**
    *   La sección "Producción en Curso — Trazabilidad" del dashboard muestra el árbol completo de transformaciones con merma acumulada (%) por cada etapa.
    *   Puede registrar nuevas transformaciones directamente desde la vista de trazabilidad (`allowRegister=true`).
*   **Control de Calidad (Nivel 1):**
    *   Puede ver los últimos lotes producidos en su área.
    *   Tiene facultad para **Rechazar Lotes** defectuosos, lo cual revierte los movimientos de inventario asociados.
*   **Alertas:**
    *   Recibe notificaciones inmediatas sobre **Stock Bajo** de insumos críticos (químicos, hilos base).
*   **Transferencia de Producción:**
    *   Una vez que su área termina el procesamiento de una orden, **transfiere la producción final** a la siguiente área.
    *   Selecciona de sus órdenes completadas cuál va a transferir.
    *   Especifica la cantidad exacta y observaciones sobre el estado del producto (sin defectos, listo para siguiente fase, etc.).
    *   Visualiza el historial de sus transferencias (salidas hacia otras áreas) para auditoría.

---

## 3. Operario (Ejecución)

**Responsabilidad Principal:** Ejecutar la producción física y registrar el avance en tiempo real.

### Funciones Clave:
*   **Mis Asignaciones:**
    *   Accede a un panel simplificado donde solo ve las OPs en estado **`En Proceso`** que le han sido asignadas específicamente.
    *   Visualiza instrucciones clave: Fórmula, Meta y **Observaciones/Notas** del Jefe de Planta (ej: "Prioridad Alta", "Ajustar tensión").
*   **Registro de Producción (Lotes):**
    *   Registra el **Avance** cada vez que termina una unidad de producción (ej: una bobina, un rollo).
    *   Ingresa el **Peso Neto** real y la cantidad de unidades.
    *   El sistema genera automáticamente un **Código de Lote** y descuenta las materias primas del inventario (teórico) o registra el producto terminado.
*   **Registro de Transformación Máquina a Máquina (Fase 16):**
    *   Desde la grilla de 2 botones del dashboard (Avance + Transformación), accede al registro de transformaciones.
    *   Especifica `producto_salida`, `maquina`, `peso_entrada`, `peso_salida` y observaciones. La merma se calcula automáticamente.
    *   Puede ver el árbol de trazabilidad completo de la orden seleccionada antes o después de registrar.
    *   Solo puede registrar en órdenes de **su propia área y sede**.
*   **Cierre de Orden:**
    *   El operario continúa registrando lotes hasta que la orden se completa o se detiene.

---

## 4. Tintorero (Formulación)

**Responsabilidad Principal:** Garantizar la precisión de las recetas químicas y el color final del producto.

### Funciones Clave:
*   **Creación de Recetas:** Define las fases (pre-tratamiento, tintura, etc.) y los químicos necesarios para cada color.
*   **Cálculo de Laboratorio:** Utiliza la calculadora integrada para determinar el peso exacto de cada insumo según el lote de tela.
*   **Interoperabilidad:** Exporta las fórmulas para su uso en sistemas de dosificación automática (Infotint).

---

## Resumen del Flujo de Estado (Orden de Producción)

1.  **PENDIENTE** (Jefe de Planta): La orden es creada pero no tiene recursos asignados.
2.  **EN PROCESO** (Jefe de Área): Se asigna máquina y operario. El operario comienza a registrar lotes.
3.  **FINALIZADA** (Automático/Manual):
    *   **Automático:** Cuando el peso producido alcanza o supera el peso requerido (si está configurado así en el sistema).
    *   **Manual:** El Jefe de Planta cierra la orden si la producción se detiene antes de la meta.

## Notas Adicionales
*   **Permisos Cruzados:** Los Jefes de Área y Planta tienen permisos de escritura sobre las entidades de producción (Máquinas, OPs), mientras que el Operario tiene acceso restringido solo a sus tareas.
*   **Trazabilidad de Lotes:** Cada lote registrado queda vinculado al Operario, Máquina y Hora exacta, permitiendo auditoría completa.
*   **Trazabilidad Granular (Fase 16):** Además de los lotes, cada **transformación máquina a máquina** (`TransformacionProducto`) queda registrada con: entrada, salida, merma calculada, operario, máquina y secuencia. El servicio `TrazabilidadService` construye el árbol completo cruzando áreas via `TransferenciaInterarea`. Aislamiento estricto por área y sede (RBAC).
*   **Endpoints de Trazabilidad:** `GET /api/ordenes-produccion/{id}/trazabilidad/` devuelve el árbol completo con merma acumulada %. `POST /api/ordenes-produccion/{id}/registrar-transformacion/` crea una nueva transformación (solo Operario/JefeArea de la misma área/sede).
