# Arquitectura del Sistema TexCore

Este documento describe la arquitectura de TexCore, tanto en su estado actual de desarrollo como en la arquitectura objetivo para producción.

---

## 1. Arquitectura de Desarrollo

El entorno de desarrollo actual está completamente contenerizado con Docker Compose, facilitando un levantamiento rápido y consistente del sistema en cualquier máquina.

```mermaid
graph TD
    subgraph "Máquina Host"
        direction LR
        U[Usuario/Desarrollador] -- "localhost:3000" --> C1
        U -- "localhost:8000 (API)" --> C2
    end

    subgraph "Red de Docker"
        C1[Frontend Container <br> React Dev Server] -- "Peticiones API" --> C2[Backend Container <br> Django Dev Server]
        C2 -- "ODBC" --> C3[Database Container <br> MS SQL Server]
    end

    style U fill:#fff,stroke:#000,stroke-width:2px
    style C1 fill:#61DAFB,stroke:#000,stroke-width:2px
    style C2 fill:#0C4B33,stroke:#000,stroke-width:2px,color:#fff
    style C3 fill:#CC2927,stroke:#000,stroke-width:2px,color:#fff
```

### Componentes de Desarrollo:

-   **Frontend Container:**
    -   **Tecnología:** Node.js con `npm start` (Servidor de Desarrollo de React).
    -   **Función:** Sirve la aplicación de React con recarga en caliente para un desarrollo ágil.
    -   **Comunicación:** Se comunica con el backend a través de la red interna de Docker, llamando al servicio `backend` en el puerto 8000.

-   **Backend Container:**
    -   **Tecnología:** Python con `manage.py runserver` (Servidor de Desarrollo de Django).
    -   **Función:** Expone la API REST que gestiona toda la lógica de negocio.
    -   **Comunicación:** Se conecta a la base de datos a través del servicio `db` en el puerto 1433.

-   **Database Container:**
    -   **Tecnología:** Microsoft SQL Server para Linux.
    -   **Función:** Persiste todos los datos de la aplicación.

---

## 2. Arquitectura de Producción (Objetivo)

Para soportar una carga de usuarios real (~50 usuarios simultáneos) y garantizar la seguridad y eficiencia, el sistema evolucionará a la siguiente arquitectura de producción.

```mermaid
graph TD
    subgraph "Internet"
        U[Usuarios]
    end

    subgraph "Servidor de Producción (Docker)"
        U -- "HTTP/HTTPS" --> C1[Nginx Reverse Proxy]
        
        subgraph "Red Privada de Docker"
            C1 -- "Proxy a /api/*" --> C2[Backend Container <br> Gunicorn + Django]
            C1 -- "Sirve archivos estáticos" --> V1(React build)
            C2 -- "ODBC" --> C3[Database Container <br> MS SQL Server]
        end
    end

    style U fill:#fff,stroke:#000,stroke-width:2px
    style C1 fill:#269539,stroke:#000,stroke-width:2px,color:#fff
    style C2 fill:#0C4B33,stroke:#000,stroke-width:2px,color:#fff
    style C3 fill:#CC2927,stroke:#000,stroke-width:2px,color:#fff
    style V1 fill:#61DAFB,stroke:#000,stroke-width:1px,stroke-dasharray: 5 5

```

### Componentes de Producción:

-   **Nginx Reverse Proxy (Contenedor Principal):**
    -   **Función:** Es el **único punto de entrada** a la aplicación. Recibe todo el tráfico web.
    -   **Enrutamiento:**
        1.  Si una petición llega a la ruta `/api/...`, Nginx la redirige internamente al contenedor del `backend` (Gunicorn).
        2.  Para cualquier otra petición, Nginx sirve los archivos estáticos (HTML, CSS, JS) de la aplicación React, que habrán sido pre-compilados con `npm run build`.
    -   **Beneficios:** Balanceo de carga, seguridad (oculta los servicios internos), eficiencia en el servicio de archivos estáticos.

-   **Backend Container:**
    -   **Tecnología:** Python con **Gunicorn** como servidor de aplicaciones WSGI.
    -   **Función:** Ejecuta múltiples procesos de Django simultáneamente para atender varias peticiones de la API a la vez, a diferencia del `runserver` de desarrollo que solo maneja una.

-   **Database Container:**
    -   **Tecnología:** Microsoft SQL Server. Permanece igual que en desarrollo, pero se ejecutará en un hardware más potente y con monitoreo de recursos.