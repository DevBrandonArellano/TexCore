# Roadmap de Producción para TexCore

Este documento describe la hoja de ruta para evolucionar TexCore desde su estado actual de desarrollo a un sistema robusto, optimizado y listo para un entorno de producción con un objetivo de **soportar ~50 usuarios simultáneos**.

---

### Fase 1: Implementación de la Arquitectura de Producción (A corto plazo)

El objetivo principal de esta fase es reemplazar los componentes de desarrollo (servidores de `runserver` y `npm start`) por una arquitectura de contenedores de alto rendimiento utilizando Gunicorn y Nginx.

-   **[ ] Contenerizar el Backend para Producción:**
    -   Añadir `Gunicorn` al proyecto como el servidor de aplicaciones WSGI profesional para Django.
    -   Crear un `Dockerfile.prod` para el backend que inicie la aplicación usando Gunicorn.

-   **[ ] Contenerizar el Frontend para Producción:**
    -   Utilizar el `Dockerfile` existente del frontend que ya está preparado para producción (usa `npm run build` y Nginx) para servir los archivos estáticos de React.

-   **[ ] Orquestación con Docker Compose para Producción:**
    -   Crear un archivo `docker-compose.prod.yml` que defina la arquitectura de servicios para producción.
    -   Este archivo orquestará:
        1.  El servicio de base de datos (`db`).
        2.  El servicio `backend` corriendo con Gunicorn.
        3.  Un nuevo servicio `nginx` que actuará como **reverse proxy**.

-   **[ ] Configurar Nginx como Reverse Proxy:**
    -   Crear la configuración de Nginx (`nginx.conf`) para que funcione como el punto de entrada principal a la aplicación.
    -   **Responsabilidades de Nginx:**
        -   Recibir todo el tráfico en el puerto 80/443.
        -   Dirigir las peticiones a la API (ej. `/api/*`) al servicio `backend` de Gunicorn.
        -   Servir directamente los archivos estáticos de la aplicación React para todas las demás peticiones.

---

### Fase 2: Optimización de Código y Base de Datos (A mediano plazo)

Con la arquitectura de producción en su lugar, el foco se mueve a optimizar el código de la aplicación para manejar la carga de manera eficiente y evitar cuellos de botella.

-   **[ ] Optimización de Consultas a la Base de Datos (Querysets):**
    -   Realizar un análisis del código de `views.py` y `serializers.py` para identificar consultas ineficientes (problemas N+1).
    -   Implementar `select_related` (para relaciones uno-a-uno o muchos-a-uno) y `prefetch_related` (para relaciones muchos-a-muchos o uno-a-muchos) para reducir drásticamente el número de consultas a la base de datos.

-   **[ ] Indexación de la Base de Datos:**
    -   Analizar los modelos en `models.py` y las consultas más frecuentes.
    -   Añadir índices (`db_index=True`) a los campos de la base de datos que se usen comúnmente en operaciones de filtrado (`filter()`) o búsqueda para acelerar las lecturas.

-   **[ ] Implementación de Estrategias de Caché:**
    -   Identificar endpoints de la API que sean de solo lectura y muy consultados (ej. listas de productos, categorías).
    -   Implementar caché (ej. usando `django.core.cache` con Redis) en estos puntos para servir respuestas desde memoria y reducir la carga sobre la base de datos.

-   **[ ] Revisión de Lógica de Negocio Compleja:**
    -   Evaluar funciones o métodos con alta carga computacional (ej. cálculos complejos en reportes) y optimizarlos.
    -   Considerar si alguna tarea muy pesada (ej. generación de reportes PDF/Excel) debería ser movida a un proceso en segundo plano (aunque para 50 usuarios podría no ser necesario).

---

### Fase 3: Pruebas de Carga y Despliegue Final (A largo plazo)

La fase final para validar el rendimiento, asegurar la estabilidad y documentar el proceso de despliegue.

-   **[ ] Pruebas de Carga y Estrés:**
    -   Utilizar herramientas como `Locust` o `k6` para simular una carga de 50-100 usuarios concurrentes sobre el entorno de producción.
    -   Identificar y corregir los cuellos de botella que surjan durante las pruebas.
    -   Validar que los tiempos de respuesta se mantienen aceptables bajo carga.

-   **[ ] Pruebas de Integración y End-to-End (E2E):**
    -   Escribir pruebas automatizadas que validen los flujos críticos de la aplicación en el entorno de producción.

-   **[ ] Configuración de Logging y Monitoreo para Producción:**
    -   Configurar Gunicorn y Nginx para que generen logs de acceso y errores en un formato estructurado.
    -   Centralizar los logs de todos los contenedores para facilitar la depuración.

-   **[ ] Documentación Final para Despliegue:**
    -   Crear una guía paso a paso para desplegar la aplicación en un servidor nuevo usando el archivo `docker-compose.prod.yml`.
    -   Documentar la gestión de secretos y variables de entorno en producción.

---

## Fase 4: Mejoras de Arquitectura y Seguridad (Propuestas)

Esta sección detalla una serie de mejoras propuestas basadas en un análisis detallado del código y la arquitectura, con el objetivo de aumentar la seguridad, mantenibilidad y robustez de la aplicación.

### Configuración y Seguridad

-   **[x] [CRÍTICO] Externalizar la Configuración del Frontend:**
    -   **Tarea:** Mover la URL de la API (`http://127.0.0.1:8000/api`) del código fuente a una variable de entorno (ej. `REACT_APP_API_URL`).
    -   **Razón:** Evita tener que modificar el código para cada entorno (desarrollo, producción), aumentando la flexibilidad y reduciendo errores.

-   **[x] [CRÍTICO] Mejorar la Seguridad en el Almacenamiento de Tokens:**
    -   **Tarea:** Cambiar el almacenamiento de tokens JWT de `localStorage` a cookies `HttpOnly`.
    -   **Razón:** Protege contra ataques XSS al impedir que el token sea accesible desde scripts del lado del cliente.

-   **[x] [CRÍTICO] Implementar HTTPS:**
    -   **Tarea:** Configurar Nginx para que gestione certificados SSL/TLS y fuerce todo el tráfico a través de HTTPS.
    -   **Razón:** Cifra toda la comunicación entre el cliente y el servidor, protegiendo datos sensibles como contraseñas y tokens.

### Arquitectura Frontend

-   **[x] [RECOMENDADO] Adoptar una Librería de Gestión de Estado de Servidor:**
    -   **Tarea:** Integrar una herramienta como **React Query (TanStack Query)** para manejar la obtención, cacheo y sincronización de datos con la API.
    -   **Razón:** Reduce el "prop drilling", simplifica el manejo de estados de carga/error, mejora el rendimiento y hace que los componentes sean más limpios y mantenibles.

-   **[x] [RECOMENDADO] Reforzar la Seguridad de Tipos:**
    -   **Tarea:** Eliminar el uso de `any` en el código TypeScript, ajustando los serializers del backend para que devuelvan una estructura de datos predecible y actualizando los tipos del frontend en consecuencia.
    -   **Razón:** Aprovecha al máximo TypeScript para prevenir bugs en tiempo de desarrollo y mejorar la legibilidad del código.

### Arquitectura Backend

-   **[x] [RECOMENDADO] Desarrollar un Conjunto de Pruebas Automatizadas:**
    -   **Tarea:** Crear pruebas unitarias para la lógica de negocio crítica y pruebas de integración para los endpoints de la API.
    -   **Razón:** Garantiza la estabilidad del código, previene regresiones y da confianza para realizar cambios y refactorizaciones a futuro.

-   **[x] [RECOMENDADO] Estandarizar el Manejo de Errores de la API:**
    -   **Tarea:** Implementar un manejador de excepciones global en Django REST Framework para que todas las respuestas de error sigan un formato JSON consistente.
    -   **Razón:** Simplifica la gestión de errores en el frontend y crea una API más robusta y predecible.
---

### Fase 5: Automatización de Despliegues con CI/CD (Propuesta)

Para mejorar la velocidad, fiabilidad y seguridad del ciclo de desarrollo, se propone la implementación de un pipeline de Integración Continua y Despliegue Continuo (CI/CD) utilizando GitLab.

-   **[ ] Configurar el Pipeline de CI/CD (`.gitlab-ci.yml`):**
    -   Crear un archivo `.gitlab-ci.yml` que defina el flujo de trabajo automatizado.
    -   Establecer etapas claras: `test` (pruebas), `build` (construcción de imágenes) y `deploy` (despliegue).

-   **[ ] Integrar Pruebas Automatizadas:**
    -   Asegurar que el pipeline ejecute automáticamente las pruebas del backend y del frontend en la etapa `test`.
    -   Configurar el pipeline para que se detenga si las pruebas fallan, previniendo que el código con errores llegue a producción.

-   **[ ] Automatizar la Construcción de Imágenes Docker:**
    -   En la etapa `build`, configurar trabajos para construir las imágenes de producción de Docker (`backend` y `nginx`).
    -   Subir y versionar automáticamente estas imágenes en el Registro de Contenedores de GitLab.

-   **[ ] Adaptar `docker-compose.prod.yml` para Despliegue Continuo:**
    -   Modificar el archivo para que los servicios utilicen variables de entorno (ej. `${BACKEND_IMAGE}`) en lugar de nombres de imagen fijos o directivas de `build`.

-   **[ ] Automatizar el Despliegue en Producción:**
    -   Crear un trabajo en la etapa `deploy` que se conecte de forma segura al servidor de producción (vía SSH).
    -   El script de despliegue deberá:
        1.  Autenticarse con el registro de GitLab.
        2.  Descargar las nuevas versiones de las imágenes.
        3.  Reiniciar los servicios con `docker compose` para aplicar la actualización.
    -   Configurar el despliegue para que se active automáticamente solo en los pushes a la rama principal (`main`).

-   **[ ] Gestionar Secretos de Forma Segura:**
    -   Configurar las variables de CI/CD de GitLab para almacenar de forma segura los secretos necesarios para el despliegue (contraseñas, llaves SSH).