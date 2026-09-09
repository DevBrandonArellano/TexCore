# Manual de Usuario — Administrador de Sistemas

## 1. ¿Qué hace usted en TexCore?

Usted es la máxima autoridad técnica del sistema completo: crea las **Sedes**, **Áreas** y **Bodegas**, mantiene los catálogos maestros de **Productos**, **Químicos**, **Fórmulas** y **Proveedores**, y gestiona **todos los usuarios** de la plataforma con sus roles. Sin este rol, ningún otro puede comenzar a operar — al iniciar el sistema no existen sedes ni áreas creadas: deben crearse desde este panel.

## 2. Ingresar al sistema

Vea [Cómo ingresar al sistema](README.md#cómo-ingresar-al-sistema-todos-los-roles). Su panel se llama **Panel de Administración**.

## 3. Cómo está organizado su panel

A la izquierda hay un **menú de sedes** (barra lateral): permite elegir la sede sobre la que se va a trabajar. La mayoría de las pestañas y de las acciones de creación (por ejemplo, crear un usuario) usan la sede que esté seleccionada allí — si no se elige ninguna, se muestra el consolidado de todas las sedes en las vistas de solo lectura.

A la derecha, cinco pestañas principales: **Resumen**, **Producción**, **Inventario**, **Gestión** y **Auditoría**.

## 4. Pestaña Resumen

Vista general de la sede seleccionada: áreas, bodegas y datos generales.

## 5. Pestaña Producción

Estado de las Órdenes de Producción de la sede seleccionada, con paginación.

## 6. Pestaña Inventario

Las mismas 6 secciones que utiliza un Bodeguero (Stock, Entrada, Transfer, Transform, Kardex, Reportes), aplicadas a la sede seleccionada en el menú lateral — vea el detalle en el [Manual del Bodeguero](MANUAL_BODEGUERO.md#4-pestaña-inventario).

## 7. Pestaña Gestión — Maestros del sistema

Es la pestaña principal de trabajo de este rol. Tiene 10 sub-secciones:

| Sub-sección | Qué se gestiona allí |
|---|---|
| **Usuarios** | Altas, edición y bajas de cuentas de todos los roles (vea la sección 8). |
| **Sedes** | Crear, editar y eliminar las sedes físicas de la empresa. |
| **Áreas** | Crear, editar y eliminar las áreas de producción dentro de cada sede. |
| **Productos** | Catálogo maestro de productos (materia prima y producto terminado). |
| **Químicos** | Catálogo maestro de insumos químicos. |
| **Fórmulas** | Catálogo global de fórmulas de color (además de lo que gestiona cada Tintorero). |
| **Bodegas** | Crear, editar y eliminar bodegas dentro de cada sede. |
| **Clientes** | Vista global de clientes de todas las sedes. |
| **Proveedores** | Catálogo de proveedores. |
| **Roles** | Vista de solo lectura: lista los grupos/roles configurados en el sistema y cuántos usuarios tiene cada uno. |

## 8. Crear un usuario nuevo

1. Primero, debe **elegirse la sede** en el menú lateral (salvo que se vaya a crear un usuario **Administrador de Sistemas**, que no pertenece a ninguna sede en particular).
2. En **Gestión → Usuarios**, haga clic en **Nuevo Usuario**.
3. Complete el formulario:
   - **Usuario** (obligatorio) — el nombre con el que iniciará sesión.
   - **Contraseña** (obligatoria al crear; al editar puede dejarse vacía para no cambiarla).
   - **Nombre** y **Apellido** (obligatorios).
   - **Email** (opcional).
   - **Rol** (obligatorio) — determina qué panel verá el usuario al iniciar sesión.
   - **Sede**: se asigna automáticamente según la sede elegida en el menú lateral; no es editable desde este formulario (para cambiarla, debe volverse a la barra lateral).
   - **Área**: solo aparece para los roles **Operario** y **Jefe de Área** — debe seleccionarse el área de esa sede a la que pertenece.
4. Guarde — el usuario ya puede iniciar sesión con las credenciales definidas.

Para editar o dar de baja un usuario existente, deben usarse las acciones disponibles en su fila dentro del listado.

## 9. Crear una Sede o Área nueva

Al iniciar el sistema por primera vez no existen sedes ni áreas — es responsabilidad de este rol crearlas antes de que el resto de los usuarios pueda operar:

1. Vaya a **Gestión → Sedes** para crear la sede (nombre, ubicación, datos generales).
2. Vaya a **Gestión → Áreas**, seleccione la sede correspondiente y cree las áreas de producción que la componen (por ejemplo, Tejeduría, Tintorería, Empaque).
3. Luego, cree las **Bodegas** de esa sede en **Gestión → Bodegas**.

## 10. Preguntas frecuentes

**Se creó un usuario, pero quedó en la sede equivocada.** Debe verificarse cuál sede estaba seleccionada en el menú lateral antes de crearlo — la sede del formulario depende de esa selección, no se escribe directamente en el formulario.

**No aparece el campo Área al crear un usuario.** Solo se muestra para los roles Operario y Jefe de Área; el resto de roles no lo requiere.

**Se desea ver cuántos usuarios tiene cada rol.** Debe accederse a **Gestión → Roles** — es una vista de solo lectura con el conteo de usuarios por grupo.

**No se muestran datos en Producción/Inventario.** Debe confirmarse que haya una sede seleccionada en el menú lateral izquierdo.
