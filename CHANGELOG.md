# Changelog

## Enero 2026

### 26 de Enero de 2026

#### Implementación de Pipeline CI/CD Completo

Se ha implementado un flujo de trabajo de Integración y Despliegue Continuo (CI/CD) robusto utilizando GitLab CI.

**Características Implementadas:**

- **Build & Push**: Las imágenes de Docker ahora se construyen en el runner de CI y se almacenan en el GitLab Container Registry, mejorando la consistencia y velocidad de despliegue.
- **Despliegue Automatizado**: El servidor de producción descarga y ejecuta las imágenes pre-construidas.
- **Rollback Manual**: Se añadió una capacidad de "vuelta atrás" (rollback) manual que permite revertir el servidor a la versión inmediatamente anterior con un solo clic en GitLab.
- **Health Checks**: Verificación automática de disponibilidad post-despliegue.

---

## Diciembre 2025

### 22 de Diciembre de 2025

#### Estabilización del Entorno de Desarrollo Docker

Se realizó una refactorización completa del entorno de Docker para solucionar problemas críticos de arranque, portabilidad y fiabilidad, resultando en un proceso de inicio de un solo comando (`docker-compose up`).

**Problemas Resueltos:**

1.  **Error de Finales de Línea en Scripts (`bash\r`):**
    - Se corrigieron los finales de línea de Windows (CRLF) en los scripts `entrypoint.sh` y `wait-for-it.sh`, que causaban fallos al ejecutarse en el contenedor Linux. Se documentó la solución para futuros desarrolladores en Windows.

2.  **Automatización de la Creación de la Base de Datos:**
    - Anteriormente, la base de datos `texcore_db` no se creaba automáticamente, lo que provocaba errores de conexión (Error 4060 en SQL Server) y que las migraciones se ejecutaran en la base de datos `master` incorrecta.
    - Se implementó la ejecución del script `create_db.py` desde el `entrypoint.sh` del backend para garantizar que la base de datos se cree de forma automática antes de aplicar las migraciones.

3.  **Fiabilidad del Inicio:**
    - Se corrigió el script `wait-for-it.sh` para que manejara correctamente los argumentos y no fallara.
    - Se añadió la creación automática del directorio de logs (`/app/logs`) para prevenir errores de la aplicación Django al iniciar.

**Estado Actual:**

- El entorno de desarrollo es completamente estable.
- El comando `docker-compose up` ahora levanta, inicializa (crea la BD, aplica migraciones) y ejecuta todo el stack de la aplicación sin necesidad de pasos manuales adicionales.
- Se ha mejorado significativamente la experiencia del desarrollador y la portabilidad del proyecto.

## Noviembre 2025

### 13 de Noviembre de 2025

#### Correcciones y Mejoras de Estabilidad

Se realizó una sesión intensiva de depuración y refactorización para estabilizar la aplicación y asegurar la correcta persistencia de los datos.

**Problema Inicial:**

- Las operaciones CRUD (Crear, Leer, Actualizar, Eliminar) en el módulo de gestión de usuarios no persistían los datos después de reiniciar el servidor o cerrar sesión.

**Proceso de Depuración y Soluciones:**

1.  **Refactorización del Estado del Frontend:**
    - Se diagnosticó que el estado se manejaba localmente en el componente `ManageUsers` y no se comunicaba con el backend.
    - Se refactorizó la lógica para centralizar el estado y las llamadas a la API en el componente padre `AdminSistemasDashboard`, pasando los datos y las funciones como `props` al componente hijo.

2.  **Resolución de Problemas de Compilación:**
    - Se encontró y corrigió una versión inválida (`0.0.0`) del paquete `react-scripts` en `frontend/package.json`, que impedía que el servidor de desarrollo se iniciara correctamente.
    - La actualización de `react-scripts` reveló una gran cantidad de errores de tipo (TypeScript) en todo el proyecto debido a un chequeo más estricto.
    - Se corrigió un error de sintaxis fatal en `src/lib/auth.tsx` que impedía la exportación del contexto de autenticación.
    - Se desactivaron temporalmente los dashboards no esenciales (`Jefe de Área`, `Operario`, etc.) que dependían de datos de prueba (`mockData`) inconsistentes, vaciando su contenido para permitir la compilación.

3.  **Resolución de Problemas de Autenticación y Roles:**
    - Se diagnosticó que la aplicación no reconocía el rol del usuario después de iniciar sesión ("Rol no reconocido").
    - Mediante logs, se descubrió que una llamada a la API para obtener la lista de roles (`/api/groups/`) estaba fallando con un error `401 Unauthorized`.
    - Se corrigió el backend (`gestion/views.py`) para permitir el acceso público a la lista de roles.
    - Se detectó que el servidor de backend no estaba aplicando los cambios, probablemente debido a un proceso "zombie".
    - Se modificó el script `seed_data.py` para forzar la recreación de los usuarios de prueba, asegurando la consistencia de los IDs de los grupos en la base de datos.
    - Se proveyeron instrucciones explícitas para forzar el reinicio del servidor de backend y asegurar que todos los cambios fueran aplicados.

**Estado Actual:**

- La aplicación compila exitosamente.
- El inicio de sesión y el reconocimiento de roles funcionan correctamente.
- El CRUD de usuarios en el `AdminSistemasDashboard` es funcional y los datos persisten en la base de datos.
- Los dashboards secundarios han sido desactivados temporalmente y deben ser reparados en el futuro (ver `ROADMAP.md`).
