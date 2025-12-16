# TexCore - Sistema de Gestión de Inventario y Producción

Este proyecto es un sistema integral para una empresa textil, construido con un backend de Django y un frontend de React. Todo el entorno está completamente contenerizado con Docker para facilitar el desarrollo, el despliegue y la escalabilidad.

## Tecnologías Principales

-   **Backend**:
    -   Python / Django & Django REST Framework
    -   Gunicorn (para producción)
    -   Simple JWT para autenticación por token
-   **Frontend**:
    -   React / TypeScript
    -   Tailwind CSS & Shadcn/UI
-   **Base de Datos**:
    -   Microsoft SQL Server
-   **Infraestructura**:
    -   Docker & Docker Compose
    -   Nginx (como reverse proxy en producción)

## Arquitectura

El proyecto utiliza una arquitectura de contenedores Docker que separa el `frontend`, el `backend` y la `base de datos`. Esta configuración está orquestada por Docker Compose y tiene dos modos principales: desarrollo y producción.

Para una explicación visual y detallada de ambas arquitecturas, consulta el [**Diagrama de Arquitectura**](./documentation/architecture_diagram.md).

## Optimización y Rendimiento

El sistema ha sido optimizado para soportar una carga de ~50 usuarios simultáneos. Se implementaron técnicas avanzadas de optimización de consultas (reducción de complejidad algorítmica O(N) a O(1)) y de indexación de la base de datos.

Para un análisis técnico y académico de estas mejoras, consulta el documento [**Recursos Algorítmicos y Optimización**](./documentation/recursos_algoritmicos.md).

---

## Gestión de Entornos

Este proyecto está diseñado para ser gestionado enteramente a través de Docker. No es necesario instalar Python, Node.js o SQL Server manualmente en tu máquina.

### Prerrequisitos

-   Docker
-   Docker Compose

### Archivo de Entorno (`.env`)

Ambos entornos, desarrollo y producción, cargan sus secretos (como la contraseña de la base de datos) desde un archivo `.env`. Para empezar, simplemente copia el archivo de ejemplo:

```bash
# Crea tu propio archivo .env a partir del ejemplo
cp .env.example .env
```
Puedes editar este archivo para cambiar la contraseña de la base de datos si lo deseas.

---

## Entorno de Desarrollo

Este entorno está optimizado para la programación ágil, con recarga en caliente (hot-reloading) tanto para el backend como para el frontend.

### 1. Levantar el Entorno

Desde la raíz del proyecto, ejecuta el siguiente comando:
```bash
docker compose up -d --build
```
Esto construirá las imágenes y levantará los tres contenedores (`frontend`, `backend`, `db`).

-   El **Frontend** será accesible en `http://localhost:3000`.
-   La **API del Backend** estará en `http://localhost:8000`.

### 2. Ejecutar Comandos de Gestión

Para ejecutar comandos de Django (`manage.py`), como crear un superusuario o poblar la base de datos, utiliza `docker compose exec`.

```bash
# Ejemplo: Crear un superusuario
docker compose exec backend python manage.py createsuperuser

# Ejemplo: Poblar la base de datos con datos de prueba (muy recomendado)
docker compose exec backend python manage.py seed_data

# Ejemplo: Aplicar migraciones (si hay nuevos cambios en los modelos)
docker compose exec backend python manage.py migrate
```

### 3. Pausar y Dar de Baja el Entorno

Para gestionar el ciclo de vida de los contenedores:

```bash
# Para pausar los servicios sin eliminarlos (conserva los datos)
docker compose stop

# Para dar de baja los servicios (detiene y elimina los contenedores)
# El volumen de la base de datos no se elimina, por lo que tus datos persisten.
docker compose down
```

---

## Entorno de Producción

Este entorno está optimizado para el rendimiento, la seguridad y la escalabilidad. Utiliza Gunicorn para servir el backend y Nginx como reverse proxy.

### 1. Levantar el Entorno

Asegúrate de que tu archivo `.env` esté configurado con claves seguras para producción. Luego, desde la raíz del proyecto, ejecuta el siguiente comando:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```
**Nota:** El flag `-f` es crucial para indicarle a Docker que use el archivo de configuración de producción.

### 2. Acceder a la Aplicación

En modo producción, la aplicación completa (frontend y backend) se sirve a través de Nginx en un solo puerto.

-   La **Aplicación** será accesible en `http://localhost` (puerto 80).

### 3. Comandos de Gestión en Producción

Los comandos se ejecutan de la misma manera, pero apuntando al archivo de producción.

```bash
# Ejemplo: Aplicar migraciones en producción
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### 4. Pausar y Dar de Baja el Entorno

La gestión del ciclo de vida es similar, pero siempre especificando el archivo de producción.

```bash
# Para pausar los servicios de producción
docker compose -f docker-compose.prod.yml stop

# Para dar de baja los servicios de producción
docker compose -f docker-compose.prod.yml down
```

---

## Usuarios por Defecto

Una vez que la base de datos ha sido inicializada con `seed_data`, puedes usar las siguientes cuentas:

-   **Superusuario (si lo creas manualmente):**
    -   **Usuario:** `admin` / **Contraseña:** `admin` (o la que elijas)

-   **Usuarios de Prueba (creados por `seed_data`):**
    -   **Usuario:** `user_operario`
    -   **Usuario:** `user_jefe_area`
    -   **Usuario:** `user_jefe_planta`
    -   **Usuario:** `user_admin_sede`
    -   **Usuario:** `user_ejecutivo`
    -   **Usuario:** `user_admin_sistemas`
    -   **Contraseña para todos los usuarios de prueba:** `password123`
