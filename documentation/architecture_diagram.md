# Arquitectura del Sistema

Este documento describe la arquitectura general del sistema, desde la interfaz de usuario hasta la base de datos.

## Diagrama de Arquitectura

El sistema sigue una arquitectura de aplicación de página única (SPA) con un backend de API REST.

```mermaid
graph TD
    subgraph "Navegador del Cliente"
        A[React SPA]
    end

    subgraph "Servidor"
        B[Django REST Framework API]
        C[Base de Datos (PostgreSQL)]
    end

    A --"Peticiones HTTP (JSON)"--> B
    B --"Consultas SQL"--> C

    style A fill:#61DAFB,stroke:#000,stroke-width:2px
    style B fill:#0C4B33,stroke:#000,stroke-width:2px,color:#fff
    style C fill:#336791,stroke:#000,stroke-width:2px,color:#fff
```

## Flujo de Autenticación y Acceso

1.  **Login:** El usuario ingresa credenciales en la `React SPA`.
2.  **Autenticación:** La SPA envía las credenciales al endpoint de autenticación JWT de Django (`/api/token/`).
3.  **Token:** Si las credenciales son válidas, el API de Django retorna un `access token` y un `refresh token`. El `access token` incluye el rol del usuario.
4.  **Acceso por Rol:** La aplicación de React decodifica el rol del `access token` y renderiza el "Dashboard" correspondiente (ej. `AdminSistemasDashboard`, `OperarioDashboard`). Cada dashboard contiene las herramientas y vistas específicas para ese rol.

## Interacción Frontend-Backend

-   El **Frontend (React)** está organizado en componentes basados en roles de usuario. Por ejemplo, los componentes en `src/components/admin-sistemas/` son para el administrador de sistemas.
-   Estos componentes realizan llamadas a los **Endpoints del API (Django)** para leer, crear, actualizar o eliminar datos. Por ejemplo, el componente `ManageUsers.tsx` interactúa con el endpoint `/api/users/`.
-   El **Backend (Django)** procesa estas peticiones, aplica la lógica de negocio y se comunica con la base de datos para persistir los cambios.
