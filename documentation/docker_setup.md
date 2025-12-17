# Documentación de la Configuración de Docker en TexCore

Este documento detalla la arquitectura de la contenerización de la aplicación TexCore, explicando las decisiones tomadas y las mejores prácticas implementadas para garantizar un entorno robusto, seguro y portable tanto para desarrollo como para producción.

---

## Resumen de Mejoras Implementadas

La configuración original de Docker presentaba varios problemas de portabilidad, seguridad y eficiencia. Se realizó una auditoría y refactorización completa, resultando en las siguientes mejoras clave:

1.  **Seguridad Mejorada:**
    *   **Usuario No-Root:** El contenedor del backend de producción ahora se ejecuta como un usuario sin privilegios (`appuser`), reduciendo drásticamente la superficie de ataque en caso de que la aplicación sea comprometida.
    *   **Contexto de Build Limpio:** Se introdujo un archivo `.dockerignore` exhaustivo para prevenir que archivos sensibles (como `.git`, `.env`) o innecesarios (`node_modules`, `venv`) se copien en las imágenes de Docker, evitando fugas de información y reduciendo su tamaño.

2.  **Eficiencia y Rendimiento:**
    *   **Cacheo de Capas Optimizado:** Los `Dockerfile` fueron reestructurados para copiar primero los archivos de dependencias (`requirements.txt`, `package.json`) e instalarlas, antes de copiar el resto del código fuente. Esto aprovecha el cacheo de capas de Docker, acelerando significativamente las reconstrucciones cuando solo cambia el código.
    *   **Imágenes Ligeras:** Gracias al `.dockerignore` y a la optimización de los `Dockerfile`, las imágenes generadas son más pequeñas, rápidas de construir y de desplegar.

3.  **Robustez y Portabilidad:**
    *   **Proceso de Inicio predecible:** Se eliminó la ejecución automática de migraciones (`migrate`) y scripts de inicialización del `command` en el entorno de desarrollo. Ahora, el `command` solo inicia el servidor, y las tareas de base de datos se ejecutan manualmente con `docker compose exec`, como se documenta en el `README.md`. Esto evita errores en reinicios y hace el comportamiento más explícito y robusto.
    *   **Gestión de `node_modules` Aislada:** Se simplificó y corrigió el montaje de volúmenes del frontend en desarrollo para usar un patrón estándar que aísla la carpeta `node_modules` dentro del contenedor, evitando conflictos con el sistema de archivos del host, una fuente común de problemas de portabilidad.

4.  **Claridad y Mantenibilidad:**
    *   **Eliminación de Redundancia:** Se eliminó un `Dockerfile` de producción para el frontend que no se utilizaba, haciendo que `nginx/Dockerfile` sea la única fuente de verdad para la construcción del frontend y el proxy en producción.
    *   **Estrategia de Estáticos Centralizada:** Se implementó una estrategia clara para los archivos estáticos de Django en producción, usando un volumen compartido (`prod_django_static`) para que Nginx pueda servirlos eficientemente, corrigiendo el problema que impedía el funcionamiento del panel de administración.

---

## Arquitectura del Entorno de Desarrollo

El entorno de desarrollo (`docker-compose.yml`) está optimizado para la agilidad y la facilidad de uso.

-   **Backend:**
    -   Usa el `Dockerfile` base, que solo instala las dependencias de Python y del sistema.
    -   El código fuente se monta a través de un volumen (`.:/app`), permitiendo recarga en caliente instantánea al guardar cambios.
    -   El `command` solo ejecuta `runserver`. Las migraciones son manuales.

-   **Frontend:**
    -   Usa `frontend/Dockerfile.dev` para instalar las dependencias de Node.js.
    -   El código fuente se monta con un volumen (`./frontend:/app`).
    -   Un segundo volumen nombrado (`frontend_node_modules`) se usa para `/app/node_modules`, previniendo conflictos.

---

## Arquitectura del Entorno de Producción

El entorno de producción (`docker-compose.prod.yml`) está optimizado para seguridad, rendimiento y escalabilidad.

-   **Backend (`Dockerfile.prod`):**
    -   Construye una imagen optimizada y auto-contenida.
    -   Crea un **usuario no-root (`appuser`)** para ejecutar la aplicación.
    -   Utiliza `pip wheel` para un cacheo de dependencias más eficiente.
    -   Ejecuta `collectstatic` para reunir todos los archivos estáticos de Django en un directorio específico (`/home/appuser/app/staticfiles`). Este directorio se monta en un volumen.
    -   Utiliza `gunicorn` como servidor de aplicaciones WSGI para manejar múltiples peticiones concurrentes.

-   **Nginx (`nginx/Dockerfile`):**
    -   Utiliza una **construcción multi-etapa**:
        1.  **Etapa `builder`:** Instala Node.js, copia el código del frontend y lo compila para producción (`npm run build`).
        2.  **Etapa final:** Usa una imagen limpia de `nginx:alpine`, elimina la configuración por defecto y copia la configuración personalizada (`nginx.conf`).
    -   Copia los archivos estáticos del frontend desde la etapa `builder`.
    -   El contenedor de Nginx es el único punto de entrada a la aplicación.
    -   **Monta dos volúmenes de solo lectura:**
        1.  `./nginx/certs`: Para los certificados SSL.
        2.  `prod_django_static`: Para servir los archivos estáticos del backend (ej. Admin) directamente y de forma eficiente.

-   **Flujo de Peticiones en Producción:**
    1.  El usuario accede vía HTTPS. Nginx maneja la terminación SSL.
    2.  Si la URL es `/api/...`, Nginx actúa como proxy reverso, enviando la petición al backend (Gunicorn).
    3.  Si la URL es `/static/...`, Nginx sirve los archivos estáticos de Django desde el volumen compartido.
    4.  Para cualquier otra URL, Nginx sirve la aplicación de React (SPA).
