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
    *   Puede marcar órdenes como **`Finalizada`** manualmente si es necesario, aunque el sistema lo sugiere al completar la meta.

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
*   **Control de Calidad (Nivel 1):**
    *   Puede ver los últimos lotes producidos en su área.
    *   Tiene facultad para **Rechazar Lotes** defectuosos, lo cual revierte los movimientos de inventario asociados.
*   **Alertas:**
    *   Recibe notificaciones inmediatas sobre **Stock Bajo** de insumos críticos (químicos, hilos base).

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
*   **Cierre de Orden:**
    *   El operario continúa registrando lotes hasta que la orden se completa o se detiene.

---

## Resumen del Flujo de Estado (Orden de Producción)

1.  **PENDIENTE** (Jefe de Planta): La orden es creada pero no tiene recursos asignados.
2.  **EN PROCESO** (Jefe de Área): Se asigna máquina y operario. El operario comienza a registrar lotes.
3.  **FINALIZADA** (Automático/Manual):
    *   **Automático:** Cuando el peso producido alcanza o supera el peso requerido (si está configurado así en el sistema).
    *   **Manual:** El Jefe de Planta cierra la orden si la producción se detiene antes de la meta.

## Notas Adicionales
*   **Permisos Cruzados:** Los Jefes de Área y Planta tienen permisos de escritura sobre las entidades de producción (Máquinas, OPs), mientras que el Operario tiene acceso restringido solo a sus tareas.
*   **Trazabilidad:** Cada lote registrado queda vinculado al Operario, Máquina y Hora exacta, permitiendo auditoría completa.
