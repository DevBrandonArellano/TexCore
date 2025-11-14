# Changelog

## Noviembre 2025

### 13 de Noviembre de 2025

#### Correcciones y Mejoras de Estabilidad

Se realizó una sesión intensiva de depuración y refactorización para estabilizar la aplicación y asegurar la correcta persistencia de los datos.

**Problema Inicial:**
- Las operaciones CRUD (Crear, Leer, Actualizar, Eliminar) en el módulo de gestión de usuarios no persistían los datos después de reiniciar el servidor o cerrar sesión.

**Proceso de Depuración y Soluciones:**

1.  **Refactorización del Estado del Frontend:**
    -   Se diagnosticó que el estado se manejaba localmente en el componente `ManageUsers` y no se comunicaba con el backend.
    -   Se refactorizó la lógica para centralizar el estado y las llamadas a la API en el componente padre `AdminSistemasDashboard`, pasando los datos y las funciones como `props` al componente hijo.

2.  **Resolución de Problemas de Compilación:**
    -   Se encontró y corrigió una versión inválida (`0.0.0`) del paquete `react-scripts` en `frontend/package.json`, que impedía que el servidor de desarrollo se iniciara correctamente.
    -   La actualización de `react-scripts` reveló una gran cantidad de errores de tipo (TypeScript) en todo el proyecto debido a un chequeo más estricto.
    -   Se corrigió un error de sintaxis fatal en `src/lib/auth.tsx` que impedía la exportación del contexto de autenticación.
    -   Se desactivaron temporalmente los dashboards no esenciales (`Jefe de Área`, `Operario`, etc.) que dependían de datos de prueba (`mockData`) inconsistentes, vaciando su contenido para permitir la compilación.

3.  **Resolución de Problemas de Autenticación y Roles:**
    -   Se diagnosticó que la aplicación no reconocía el rol del usuario después de iniciar sesión ("Rol no reconocido").
    -   Mediante logs, se descubrió que una llamada a la API para obtener la lista de roles (`/api/groups/`) estaba fallando con un error `401 Unauthorized`.
    -   Se corrigió el backend (`gestion/views.py`) para permitir el acceso público a la lista de roles.
    -   Se detectó que el servidor de backend no estaba aplicando los cambios, probablemente debido a un proceso "zombie".
    -   Se modificó el script `seed_data.py` para forzar la recreación de los usuarios de prueba, asegurando la consistencia de los IDs de los grupos en la base de datos.
    -   Se proveyeron instrucciones explícitas para forzar el reinicio del servidor de backend y asegurar que todos los cambios fueran aplicados.

**Estado Actual:**
- La aplicación compila exitosamente.
- El inicio de sesión y el reconocimiento de roles funcionan correctamente.
- El CRUD de usuarios en el `AdminSistemasDashboard` es funcional y los datos persisten en la base de datos.
- Los dashboards secundarios han sido desactivados temporalmente y deben ser reparados en el futuro (ver `ROADMAP.md`).
