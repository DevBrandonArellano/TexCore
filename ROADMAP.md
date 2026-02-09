# Roadmap de Producción para TexCore

Este documento describe la hoja de ruta para evolucionar TexCore desde su estado actual de desarrollo a un sistema robusto, optimizado y listo para un entorno de producción con un objetivo de **soportar ~50 usuarios simultáneos**.

---

### Fase 0: Estabilización del Entorno de Desarrollo (Completado)

Esta fase se centró en crear un entorno de desarrollo Docker robusto, portable y fácil de usar, sentando las bases para todo el desarrollo futuro.

-   **[x] Automatización del Arranque del Backend:**
    -   **Tarea:** Se implementó un `entrypoint.sh` que automatiza toda la secuencia de inicio: espera de la BD, creación de la BD, ejecución de migraciones y creación de directorios necesarios.
    -   **Razón:** Elimina la necesidad de pasos manuales post-inicio, haciendo que `docker-compose up` sea el único comando necesario para tener un entorno funcional.

-   **[x] Corrección de Portabilidad entre Windows y Linux:**
    -   **Tarea:** Se solucionaron errores críticos relacionados con los finales de línea (CRLF vs. LF) en los scripts de shell.
    -   **Razón:** Garantiza que el proyecto pueda ser desarrollado sin problemas tanto en Windows como en sistemas Unix-like.

-   **[x] Documentación Exhaustiva del Entorno:**
    -   **Tarea:** Se actualizó y expandió la documentación de Docker (`docker_setup.md`) y el `README.md` para reflejar la nueva arquitectura y el proceso de inicio simplificado.
    -   **Razón:** Facilita la incorporación de nuevos desarrolladores al proyecto.

---

### Fase 1: Implementación de la Arquitectura de Producción (A corto plazo)

El objetivo principal de esta fase es reemplazar los componentes de desarrollo (servidores de `runserver` y `npm start`) por una arquitectura de contenedores de alto rendimiento utilizando Gunicorn y Nginx.

-   **[x] Contenerizar el Backend para Producción:**
    -   Añadir `Gunicorn` al proyecto como el servidor de aplicaciones WSGI profesional para Django.
    -   Crear un `Dockerfile.prod` para el backend que inicie la aplicación usando Gunicorn.

-   **[x] Contenerizar el Frontend para Producción:**
    -   Utilizar el `Dockerfile` existente del frontend que ya está preparado para producción (usa `npm run build` y Nginx) para servir los archivos estáticos de React.

-   **[x] Orquestación con Docker Compose para Producción:**
    -   Crear un archivo `docker-compose.prod.yml` que defina la arquitectura de servicios para producción.
    -   Este archivo orquestará:
        1.  El servicio de base de datos (`db`).
        2.  El servicio `backend` corriendo con Gunicorn.
        3.  Un nuevo servicio `nginx` que actuará como **reverse proxy**.

-   **[x] Configurar Nginx como Reverse Proxy:**
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

### Fase 5: Automatización de Despliegues con CI/CD (Completado)

Para mejorar la velocidad, fiabilidad y seguridad del ciclo de desarrollo, se implementó un pipeline de Integración Continua y Despliegue Continuo (CI/CD) utilizando GitLab.

-   **[x] Configurar el Pipeline de CI/CD (`.gitlab-ci.yml`):**
    -   Se definió el flujo de trabajo automatizado con etapas de `build`, `test` y `deploy`.

-   **[x] Integrar Pruebas Automatizadas:**
    -   El pipeline ejecuta automáticamente las pruebas.

-   **[x] Automatizar la Construcción de Imágenes Docker:**
    -   Se construyen y suben las imágenes al Registry de GitLab.

-   **[x] Automatizar el Despliegue en Producción:**
    -   Implementado despliegue seguro sin SSH usando el Runner local.

---

### Fase 6: Robustecimiento de Seguridad (Próximo Objetivo)

Para mitigar riesgos de seguridad y proteger la infraestructura en un entorno expuesto a internet.

-   **[ ] Hardening de Nginx:**
    -   Implementar cabeceras de seguridad estrictas: `HSTS` (Strict-Transport-Security), `X-Frame-Options`, `Content-Security-Policy` (CSP).
    -   Ocultar versión del servidor (`server_tokens off`).

-   **[ ] Rate Limiting (Limitación de Tasa):**
    -   Configurar Nginx para limitar el número de peticiones por IP, previniendo ataques de fuerza bruta y DoS.

-   **[ ] Seguridad de Aplicación Django:**
    -   Forzar cookies seguras (`Secure`, `HttpOnly`, `SameSite`).
    -   Validar configuración de hosts y orígenes confiables (`CSRF_TRUSTED_ORIGINS`).

-   **[ ] Aislamiento de Red Docker:**
    -   Asegurar que la base de datos no exponga puertos al host externo, comunicándose solo a través de la red interna de Docker.

---

### Fase 7: Escalabilidad Horizontal (Futuro)

Preparar el sistema para escalar más allá de un solo servidor cuando la carga supere los 50-100 usuarios.

-   **[ ] Separación de Base de Datos:**
    -   Mover SQL Server a un servidor dedicado o servicio gestionado (como Azure SQL o AWS RDS) para liberar recursos en el nodo de aplicación.

-   **[ ] Balanceo de Carga:**
    -   Desplegar múltiples réplicas del contenedor `backend` y configurar Nginx como balanceador de carga (Load Balancer) para distribuir el tráfico.

-   **[ ] Almacenamiento Estático Externo:**
    -   Mover archivos estáticos y media (imágenes subidas por usuarios) a un servicio de almacenamiento de objetos como AWS S3 o Azure Blob Storage, servidos vía CDN.

-   **[ ] Monitoreo Avanzado:**
    -   Implementar Prometheus y Grafana para visualizar métricas de rendimiento en tiempo real (CPU, RAM, latencia de peticiones).
