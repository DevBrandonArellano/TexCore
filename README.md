# TexCore - Sistema de Gestión de Inventario y Producción

Este proyecto es un sistema integral para una empresa textil, construido con un backend de Django y un frontend de React. Está diseñado para gestionar usuarios, permisos basados en roles, y controlar el inventario y las operaciones a través de múltiples sedes y áreas.

## Tecnologías Principales

-   **Backend**:
    -   Python
    -   Django & Django REST Framework
    -   Simple JWT para autenticación por token
-   **Frontend**:
    -   React
    -   TypeScript
    -   Tailwind CSS
    -   Componentes de Shadcn/UI
-   **Base de Datos**:
    -   SQLite (para desarrollo)

## Características Clave

-   **Autenticación Segura**: Sistema de login basado en tokens JWT.
-   **Gestión de Roles y Permisos**: Roles predefinidos (Administrador, Jefe de Área, Operario, etc.) con permisos específicos.
-   **CRUD Dinámico**: Interfaces para crear, leer, actualizar y eliminar:
    -   Usuarios
    -   Sedes (ubicaciones)
    -   Áreas
-   **UI 100% Reactiva**: La interfaz de usuario se alimenta completamente de los datos proporcionados por la API, sin datos quemados o de prueba.

## Puesta en Marcha y Desarrollo

Sigue estos pasos para configurar y ejecutar el proyecto en tu entorno local.

### Prerrequisitos

-   Python 3.8 o superior
-   Node.js 18.x o superior y npm

### 1. Configuración del Backend

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/DevBrandonArellano/TexCore.git
    cd TexCore
    ```

2.  **Crea y activa un entorno virtual:**
    ```bash
    # Para Linux/macOS
    python3 -m venv venv
    source venv/bin/activate

    # Para Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Instala las dependencias de Python:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Inicializa la Base de Datos:**
    Ejecuta los siguientes comandos en orden para configurar la base de datos SQLite y poblarla con datos iniciales.
    ```bash
    # 1. Aplica las migraciones para crear las tablas
    python manage.py migrate

    # 2. Crea los grupos de roles y asigna permisos
    python manage.py setup_permissions

    # 3. Puebla la base de datos con datos de prueba (sedes, áreas, etc.)
    python manage.py seed_data
    ```

5.  **Crea tu Superusuario:**
    Para poder acceder con todos los privilegios, crea una cuenta de administrador. Este comando creará un usuario `admin` con contraseña `admin`.
    ```bash
    python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin')"
    ```

6.  **Ejecuta el servidor de Django:**
    ```bash
    python manage.py runserver
    ```
    El backend estará disponible en `http://127.0.0.1:8000`.

### 2. Configuración del Frontend

1.  **Navega al directorio del frontend:**
    (En una nueva terminal, desde la raíz del proyecto)
    ```bash
    cd frontend
    ```

2.  **Instala las dependencias de Node.js:**
    ```bash
    npm install
    ```

3.  **Ejecuta el servidor de desarrollo de React:**
    ```bash
    npm start
    ```
    El frontend estará disponible en `http://localhost:3000`.

### Nota sobre el Flujo de Desarrollo

Durante el desarrollo, el sistema utiliza dos servidores simultáneamente:
-   **Backend (Django):** Se ejecuta en `http://127.0.0.1:8000` y sirve la API.
-   **Frontend (React):** Se ejecuta en `http://localhost:3000` y es la interfaz con la que debes interactuar.

Debes tener **ambos servidores ejecutándose** en terminales separadas. Toda la interacción en el navegador debe hacerse a través de `http://localhost:3000`.

## Usuarios por Defecto

Una vez que la base de datos ha sido inicializada, puedes usar las siguientes cuentas para probar los diferentes roles:

-   **Superusuario:**
    -   **Usuario:** `admin`
    -   **Contraseña:** `admin`

-   **Usuarios de Prueba (creados por `seed_data`):**
    -   **Usuario:** `user_operario`
    -   **Usuario:** `user_jefe_area`
    -   **Usuario:** `user_jefe_planta`
    -   **Usuario:** `user_admin_sede`
    -   **Usuario:** `user_ejecutivo`
    -   **Usuario:** `user_admin_sistemas`
    -   **Contraseña para todos los usuarios de prueba:** `password123`