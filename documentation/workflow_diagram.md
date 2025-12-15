# Diagrama de Flujo de Trabajo del Proyecto TexCore

Este documento describe los principales flujos de trabajo y procesos dentro del sistema TexCore, detallando las interacciones de los diferentes roles de usuario con los módulos clave.

---

## 1. Gestión de Usuarios

Este flujo es manejado principalmente por el rol **Administrador de Sistemas**.

### Roles del Sistema

-   **Administrador de Sistemas (`admin_sistemas`):** Rol de más alto nivel. Gestiona catálogos maestros (usuarios, sedes, productos, etc.) y tiene una visión global de todo el sistema. No está asociado a ninguna sede.
-   **Jefe de Planta (`jefe_planta`):** Responsable de gestionar y supervisar las órdenes de producción.
-   **Jefe de Área (`jefe_area`):** Supervisa las operaciones y el personal dentro de un área específica.
-   **Administrador de Sede (`admin_sede`):** Gestiona los recursos y operaciones de una sede específica.
-   **Operario (`operario`):** Ejecuta las tareas de producción, como registrar lotes.
-   **Ejecutivo (`ejecutivo`):** Rol de consulta para visualizar reportes y el estado general del negocio.

### Flujo de Creación de Usuario

1.  **Acceso:** El `admin_sistemas` navega al **Panel de Administración** -> **Gestión** -> **Usuarios**.
2.  **Creación:**
    -   Hace clic en "Nuevo Usuario".
    -   Completa los datos del formulario (nombre, usuario, contraseña, etc.).
    -   **Asigna un Rol:** Selecciona un grupo como `jefe_planta`, `operario`, etc.
3.  **Validación de Sede (Regla de Negocio):**
    -   **Si el rol NO es `admin_sistemas`:** El campo **Sede** es **obligatorio**. El `admin_sistemas` debe asociar al nuevo usuario con una sede existente.
    -   **Si el rol ES `admin_sistemas`:** El campo Sede no se muestra, ya que este rol tiene acceso global.
4.  **Guardado:** Al guardar, el usuario es creado y puede iniciar sesión con los permisos de su rol y el alcance de su sede (si aplica).

```
+---------------------+      +----------------------+      +-------------------------+
| Admin de Sistemas   | ---> | Formulario de Usuario| ---> |  Validación de Rol/Sede |
+---------------------+      +----------------------+      +-------------------------+
                                                            |
             +----------------------------------------------+
             |
             v
+-----------------------------+      +-------------------------+
| Rol != 'admin_sistemas' ?   |--SI->| Sede es OBLIGATORIA     |
+-----------------------------+      +-------------------------+
             |
             NO
             |
             v
+-------------------------+      +-------------------------+
| Sede es OPCIONAL        | ---> | Guardar Usuario en BBDD |
+-------------------------+      +-------------------------+
```

---

## 2. Flujo de Órdenes de Producción

Este flujo es manejado por el **Jefe de Planta**.

### Ciclo de Vida de una Orden de Producción

Una orden de producción pasa por tres estados: `pendiente`, `en_proceso`, y `finalizada`.

1.  **Creación de la Orden:**
    -   El `jefe_planta` accede a su panel y va a la sección de "Gestión de Órdenes de Producción".
    -   Crea una nueva orden, especificando código, producto, fórmula de color, peso requerido y sede.
    -   La orden se crea con el estado **`pendiente`**.

2.  **Inicio del Proceso:**
    -   Cuando la producción está lista para comenzar, el `jefe_planta` busca la orden `pendiente`.
    -   En el menú de acciones de la orden, selecciona **"Iniciar Proceso"**.
    -   El estado de la orden cambia a **`en_proceso`**.

3.  **Ejecución y Registro de Lote:**
    -   Para una orden que se encuentra `en_proceso`, el `jefe_planta` puede registrar los lotes de producción a medida que se completan.
    -   En el menú de acciones, selecciona **"Registrar Lote"**.

4.  **Finalización y Revisión:**
    -   Una vez que todo el peso requerido de la orden se ha producido en uno o más lotes, el `jefe_planta` revisa la orden `en_proceso`.
    -   En el menú de acciones, selecciona **"Marcar como Finalizada"**.
    -   El estado de la orden cambia a **`finalizada`**. Esto indica que el proceso ha sido completado y aprobado.

### 3.1. Registro de Lote y Consumo Automático

Este es el paso clave que conecta la producción con el inventario.

1.  **Acción:** El `jefe_planta` hace clic en "Registrar Lote" para una orden `en_proceso`.
2.  **Formulario:** Se abre un formulario para introducir los detalles del lote (código del lote, peso producido, máquina, turno, etc.).
3.  **Envío:** Al enviar el formulario, el sistema ejecuta una única transacción que realiza lo siguiente:
    -   **Consume el Producto Base:** Descuenta del inventario la cantidad de producto base (ej. "Hilo Crudo") equivalente al "peso neto producido" del lote.
    -   **Consume los Químicos:** Si la orden tiene una fórmula, calcula la cantidad necesaria de cada químico según el "peso neto producido" y los descuenta del inventario.
    -   **Crea el Lote:** Registra el nuevo `LoteProduccion` en la base de datos, asociándolo a la orden.
    -   **Incrementa el Inventario:** Añade el nuevo lote al inventario como un producto terminado o semiterminado.

Este proceso garantiza que el inventario esté siempre actualizado en tiempo real con lo que sucede en la planta de producción.

```
+--------------------+   +---------------------+   +--------------------------------+
| Estado: En Proceso |-->| Registrar Lote      |-->|  API /registrar-lote           |
| (Jefe de Planta)   |   | (Formulario Lote)   |   |  (Transacción Atómica)         |
+--------------------+   +---------------------+   +--------------------------------+
                                                     |
                                                     v
      +---------------------------------------------------------------------------------+
      | 1. Descontar Insumos (Stock)                                                    |
      | 2. Descontar Químicos de Fórmula (Stock)                                        |
      | 3. Crear LoteProduccion en BBDD                                                 |
      | 4. Añadir nuevo Lote al Inventario (Stock)                                      |
      +---------------------------------------------------------------------------------+

```

---

## 4. Flujo de Gestión de Inventario

Este flujo puede ser manejado por varios roles, pero la funcionalidad está centralizada en el **Panel de Administración**.

### Funcionalidades Clave

1.  **Visualización de Stock:**
    -   **Acceso:** Panel de Administración -> Inventario -> **Stock Actual**.
    -   **Funcionalidad:** Muestra una tabla con el saldo actual de cada producto en cada bodega. Permite buscar y filtrar para encontrar rápidamente los niveles de inventario.

2.  **Transferencia de Stock:**
    -   **Acceso:** Panel de Administración -> Inventario -> **Transferencias**.
    -   **Flujo:**
        1.  Seleccionar el **Producto** a transferir.
        2.  Seleccionar la **Bodega de Origen**.
        3.  Seleccionar la **Bodega de Destino** (no puede ser la misma que el origen).
        4.  Ingresar la **Cantidad** a transferir. El sistema valida que haya stock suficiente en la bodega de origen.
        5.  Hacer clic en "Realizar Transferencia". La operación es atómica: se descuenta del origen y se incrementa en el destino en una sola transacción.

3.  **Consulta de Kardex:**
    -   **Acceso:** Panel de Administración -> Inventario -> **Kardex**.
    -   **Flujo:**
        1.  Seleccionar una **Bodega**.
        2.  Seleccionar un **Producto**.
        3.  Hacer clic en "Consultar".
        4.  El sistema muestra una tabla con el historial completo de movimientos (entradas, salidas, transferencias, etc.) para ese producto en esa bodega, mostrando el saldo resultante después de cada transacción.
```