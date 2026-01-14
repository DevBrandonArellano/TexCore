# Interfaz de Usuario (Frontend) - Sistema TexCore

Este directorio contiene el código fuente de la interfaz de usuario para el sistema de gestión TexCore. La aplicación está desarrollada con React y permite a los usuarios interactuar con el backend para gestionar inventarios, usuarios, y otras entidades del sistema.

## Tecnologías Principales

El frontend está construido con un stack moderno de tecnologías de JavaScript:

- **React:** Biblioteca principal para la construcción de la interfaz.
- **TypeScript:** Para un tipado estático que mejora la robustez y mantenibilidad del código.
- **React Router:** Para la gestión de rutas y navegación dentro de la aplicación.
- **Tailwind CSS:** Framework de CSS "utility-first" para un diseño rápido y personalizable.
- **Shadcn/UI:** Colección de componentes de UI reutilizables, construidos sobre Radix UI y Tailwind CSS.
- **TanStack Query (React Query):** Para la gestión del estado del servidor (fetching, caching, y actualización de datos).
- **Axios:** Cliente HTTP para la comunicación con la API del backend.
- **React Hook Form:** Para la gestión de formularios.

## Guía de Inicio Rápido

Sigue estos pasos para levantar el entorno de desarrollo del frontend.

### Requisitos Previos

- **Node.js:** Se recomienda una versión LTS (por ejemplo, 18.x o 20.x).
- **npm:** Gestor de paquetes de Node.js (generalmente se instala con Node.js).

### Instalación

1.  **Navega al directorio del frontend:**
    ```bash
    cd frontend
    ```

2.  **Instala las dependencias del proyecto:**
    ```bash
    npm install
    ```

## Scripts Disponibles

Dentro del directorio `frontend/`, puedes ejecutar los siguientes comandos:

### `npm start`

Inicia la aplicación en modo de desarrollo.
Abre [http://localhost:3000](http://localhost:3000) para verla en tu navegador.

La página se recargará automáticamente si realizas cambios en el código. También verás cualquier error de linting en la consola.

### `npm run build`

Compila la aplicación para producción en la carpeta `build/`.
Este comando empaqueta React en modo de producción y optimiza la compilación para obtener el mejor rendimiento.

### `npm test`

Ejecuta el corredor de pruebas en modo interactivo.

### `npm run eject`

**Nota: esta es una operación de un solo sentido. ¡Una vez que haces `eject`, no puedes volver atrás!**

Este comando elimina la dependencia de `react-scripts` y copia todas las herramientas de compilación (Webpack, Babel, ESLint, etc.) directamente en tu proyecto para que tengas control total sobre ellas. No es recomendable usarlo a menos que sea estrictamente necesario.

## Estructura del Proyecto

A continuación, se describe la organización de los directorios principales en `src/`:

-   `components/`: Contiene los componentes de React.
    -   `ui/`: Componentes base de la interfaz (Botones, Inputs, Tarjetas, etc.), basados en Shadcn/UI.
    -   `admin-sistemas/`, `jefe-area/`, etc.: Componentes específicos para las vistas y dashboards de cada rol de usuario.
-   `hooks/`: Hooks de React personalizados para lógica reutilizable.
-   `lib/`: Módulos y utilidades centrales.
    -   `api.ts`: Configuración de la API y lógica de peticiones.
    -   `axios.ts`: Instancia preconfigurada de Axios.
    -   `auth.tsx`: Lógica relacionada con la autenticación (contexto, tokens, etc.).
    -   `types.ts`: Definiciones de tipos y interfaces de TypeScript.
-   `styles/`: Archivos de estilos globales.