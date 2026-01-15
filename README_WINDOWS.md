# Guía de Inicio para Windows (PowerShell)

Este documento proporciona las instrucciones para configurar y ejecutar el proyecto TexCore en un entorno de Windows (específicamente Windows Server 2019) utilizando PowerShell como terminal.

La arquitectura del proyecto se basa en **contenedores de Linux**, y Docker en Windows es perfectamente capaz de ejecutarlos. **No es necesario convertir los contenedores a Windows.**

## Paso 0: Prerrequisitos

### 1. Configuración de Git
Este proyecto contiene scripts de shell (`.sh`) que deben mantener el formato de final de línea de Linux (`LF`) para funcionar dentro de los contenedores. Se ha incluido un archivo `.gitattributes` para forzar este comportamiento.

**Acción Requerida:** Si ya has clonado el proyecto en Windows, los finales de línea podrían ser incorrectos. Abre una terminal PowerShell en la raíz del proyecto y ejecuta el siguiente comando para que Git corrija los archivos:
```powershell
git reset --hard HEAD
```

### 2. Instalar Docker
Asegúrate de que tienes Docker instalado en tu máquina. Para Windows Server 2019, sigue la guía oficial. Es crucial que Docker esté configurado para usar su motor de **contenedores de Linux** (esta es la configuración por defecto y la correcta para este proyecto).

### 3. Terminal
Usa **PowerShell** para todos los comandos.

---

## Gestión del Entorno

La gestión se realiza enteramente a través de `docker compose`.

### 1. Archivo de Entorno (`.env`)
El proyecto necesita un archivo `.env` para almacenar secretos, como la contraseña de la base de datos. Para crearlo, copia el archivo de ejemplo.

En PowerShell, el comando `cp` de Linux se reemplaza por `Copy-Item`.
```powershell
# Crea tu propio archivo .env a partir del ejemplo
Copy-Item .env.example -Destination .env
```
Puedes editar este archivo para cambiar la contraseña de la base de datos si lo deseas.

---

## Entorno de Desarrollo (Recomendado)

Este entorno está optimizado para la programación, con recarga en caliente para backend y frontend.

### 1. Levantar el Entorno
Desde la raíz del proyecto, ejecuta el siguiente comando en PowerShell. Es idéntico al de Linux.
```powershell
docker compose up -d --build
```
Esto construirá las imágenes y levantará los tres contenedores (`frontend`, `backend`, `db`).

-   El **Frontend** será accesible en `http://localhost:3000`.
-   La **API del Backend** estará en `http://localhost:8000`.

### 2. Inicialización y Comandos de Gestión

**Inicialización Automática:**
El `entrypoint.sh` dentro del contenedor `backend` se encargará de crear la base de datos y aplicar las migraciones automáticamente la primera vez que se inicie.

**Poblar con Datos de Prueba (Recomendado):**
Después del primer inicio, puedes poblar la base de datos con usuarios y datos de prueba.
```powershell
docker compose exec backend python manage.py seed_data
```

**Crear un Superusuario (Opcional):
```powershell
docker compose exec backend python manage.py createsuperuser
```

### 3. Pausar y Dar de Baja el Entorno
```powershell
# Para pausar los servicios sin eliminarlos
docker compose stop

# Para dar de baja los servicios (detiene y elimina los contenedores)
# Los datos de la base de datos persisten gracias al volumen de Docker.
docker compose down
```

---

## Entorno de Producción

Este entorno está optimizado para rendimiento y seguridad.

### 1. Levantar el Entorno de Producción
Usa el archivo `docker-compose.prod.yml` para iniciar en modo producción.
```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

### 2. Acceder a la Aplicación
En modo producción, Nginx sirve toda la aplicación en un solo puerto.

-   La **Aplicación** será accesible en `http://localhost` (puerto 80).

### 3. Comandos de Gestión en Producción
Los comandos son los mismos, pero siempre apuntando al archivo de configuración de producción.
```powershell
# Ejemplo: Aplicar migraciones en producción
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Para dar de baja los servicios de producción
docker compose -f docker-compose.prod.yml down
```

Con estas instrucciones y el archivo `.gitattributes`, el proyecto está completamente optimizado para ser desarrollado y gestionado desde un entorno Windows con PowerShell.