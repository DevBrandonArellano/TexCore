# TexCore - Sistema de Gestión de Inventario y Producción

Este proyecto es un sistema integral para una empresa textil, construido con un backend de Django y un frontend de React. El entorno está completamente contenerizado con Docker para facilitar el desarrollo, el despliegue y la escalabilidad.

## Tecnologías Principales

- **Backend**: Python / Django & Django REST Framework
- **Frontend**: React / TypeScript
- **Base de Datos**: Microsoft SQL Server
- **Infraestructura**: Docker & Docker Compose
- **CI/CD**: GitLab CI/CD con GitLab Runner

---

## Arquitectura de Contenedores Dual (Linux & Windows)

Este proyecto ha sido diseñado para tener una portabilidad máxima, soportando dos tipos de entornos de contenedores:

1.  **Contenedores de Linux:** La configuración estándar y recomendada para entornos de desarrollo en Linux y macOS. Utiliza imágenes oficiales de Linux para Python y SQL Server.
2.  **Contenedores Nativos de Windows:** Una configuración alternativa para servidores como **Windows Server 2019** que operan con contenedores nativos de Windows. Utiliza imágenes base de `Windows Server Core`.

**La complejidad de elegir entre estos dos entornos se gestiona automáticamente a través de un único script.**

---

## Guía de Inicio Rápido (Método Unificado)

Para levantar todo el entorno de desarrollo, solo necesitas un prerrequisito y un comando.

### Prerrequisitos

- Docker (Docker Desktop en Windows/Mac, o Docker Engine en Linux)
- Git

### Iniciar el Entorno

Abre una terminal **PowerShell (en Windows)** o **bash (en Linux/Mac)** en la raíz del proyecto y ejecuta:

```powershell
# En Windows (usando PowerShell)
./deploy.ps1

# En Linux/macOS
./deploy.sh
```

Este script se encargará de todo:

1.  **Detectará tu sistema operativo** (Windows o Linux).
2.  **Creará un archivo `.env`** desde el ejemplo si no existe.
3.  **Seleccionará el archivo `docker-compose` adecuado** (`docker-compose.windows.yml` o `docker-compose.yml`).
4.  **Construirá las imágenes y levantará los contenedores** en segundo plano.

Una vez finalizado, los servicios estarán disponibles en:

- **Frontend**: `http://localhost:3000` (si no se comentó en el compose)
- **API del Backend**: `http://localhost:8000`

---

## Comandos de Gestión

Para ejecutar comandos dentro del contenedor del backend (como poblar la base de datos), primero necesitas saber qué archivo de compose se está usando. El script `deploy.ps1` te lo indicará.

**Ejemplo: Poblar la base de datos con datos de prueba**

- Si estás en **Windows** (usando contenedores nativos):

  ```powershell
  docker compose -f docker-compose.windows.yml exec backend python manage.py seed_data
  ```

- Si estás en **Linux/macOS**:
  ```bash
  docker compose -f docker-compose.yml exec backend python manage.py seed_data
  ```

### Credenciales de Prueba

Una vez ejecutado `seed_data`, puedes usar estas cuentas:

- **Usuarios:** `user_operario`, `user_jefe_area`, `user_jefe_planta`, `user_admin_sede`, `user_ejecutivo`, `user_admin_sistemas`
- **Contraseña (para todos):** `password123`

---

## Pruebas Automatizadas

El proyecto incluye una suite completa de pruebas para garantizar la calidad del código.

### Ejecutar Todas las Pruebas

```bash
# Dentro del contenedor
docker compose exec backend python3 manage.py test

# O localmente (si tienes Python configurado)
python3 manage.py test
```

### Ejecutar Pruebas por Módulo

```bash
# Solo pruebas de gestión
python3 manage.py test gestion

# Solo pruebas de inventario
python3 manage.py test inventory

# Ambos módulos
python3 manage.py test gestion inventory
```

### Ejecutar Pruebas Específicas

```bash
# Una clase de pruebas específica
python3 manage.py test inventory.tests.TransferenciaStockTestCase

# Un test individual
python3 manage.py test inventory.tests.TransferenciaStockTestCase.test_transferencia_success
```

### Cobertura de Pruebas

El proyecto incluye:

- **Módulo `gestion`**: 289 líneas de pruebas cubriendo:
  - CRUD de Sedes, Productos y Áreas
  - Autenticación con JWT y cookies HttpOnly
  - Manejo de errores personalizado
  
- **Módulo `inventory`**: 445 líneas de pruebas cubriendo:
  - Modelos de Stock y Movimientos
  - Lógica de actualización de inventario (COMPRA, VENTA)
  - Transferencias entre bodegas
  - Cálculo de Kardex
  - Alertas de stock bajo

**Importante**: Las pruebas se ejecutan en una base de datos temporal (`test_texcore`) que se crea y destruye automáticamente. **Tus datos de producción están completamente seguros**.

---

## Integración y Despliegue Continuo (CI/CD)

El proyecto cuenta con un pipeline completo en **GitLab CI/CD** configurado en `.gitlab-ci.yml`.

### Características del Pipeline

1.  **Build**: Construye imágenes de Docker para Backend y Nginx y las sube al **GitLab Container Registry**.
2.  **Test**: Ejecuta todas las pruebas automáticas (`gestion` e `inventory`).
3.  **Deploy**: Despliega automáticamente en el servidor de producción usando GitLab Runner.
    - Utiliza una estrategia de tags dinámicos (`$CI_COMMIT_SHA`).
    - Antes de desplegar, etiqueta la versión actual como `backup`.
4.  **Health-Check**: Verifica que el servicio responda después del despliegue.
5.  **Rollback**: Job manual para revertir rápidamente a la versión anterior (`backup`) en caso de fallo.

### Configuración de GitLab Runner (On-Premise)

Para servidores on-premise, se recomienda usar GitLab Runner en lugar de SSH:

#### 1. Instalar GitLab Runner

```bash
# Descargar el binario
sudo curl -L --output /usr/local/bin/gitlab-runner https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64

# Dar permisos de ejecución
sudo chmod +x /usr/local/bin/gitlab-runner

# Crear usuario
sudo useradd --comment 'GitLab Runner' --create-home gitlab-runner --shell /bin/bash

# Instalar como servicio
sudo gitlab-runner install --user=gitlab-runner --working-directory=/home/gitlab-runner
sudo gitlab-runner start
```

#### 2. Registrar el Runner

Obtén el token de registro desde GitLab (Settings > CI/CD > Runners):

```bash
sudo gitlab-runner register \
  --non-interactive \
  --url "https://gitlab.com/" \
  --registration-token "TU_TOKEN_DE_REGISTRO" \
  --executor "docker" \
  --docker-image docker:24.0.5 \
  --description "TexCore Production Runner" \
  --tag-list "production" \
  --docker-privileged
```

#### 3. Agregar Usuario al Grupo Docker

```bash
sudo usermod -aG docker gitlab-runner
```

#### 4. Verificar

Una vez configurado, el Runner aparecerá como "Online" en GitLab. Cada push a `main` activará el pipeline automáticamente.

### Optimizaciones del Pipeline

- **Caching**: Las dependencias de `pip` y `npm` se cachean para reducir tiempos de build.
- **Ejecución Paralela**: Los tests de backend y frontend se ejecutan en paralelo.
- **Despliegue Local**: El Runner ejecuta comandos directamente en el servidor sin necesidad de SSH.

---

## Estructura de Archivos de Docker

- `deploy.ps1` / `deploy.sh`: Scripts de inicio unificados. **Usa estos scripts para iniciar el proyecto.**
- **Configuración para Linux (Estándar):**
  - `docker-compose.yml`: Orquesta los contenedores de Linux.
  - `Dockerfile`: Define el backend para desarrollo.
  - `Dockerfile.prod`: Define el backend para producción.
  - `database/Dockerfile`: Define la base de datos para Linux.
  - `entrypoint.sh`: Script de inicialización para el contenedor de backend de Linux.
- **Configuración para Windows (Nativo):**
  - `docker-compose.windows.yml`: Orquesta los contenedores nativos de Windows.
  - `dockerfile.windows`: Define el backend para Windows.
  - `database/Dockerfile.windows`: Define la base de datos para Windows.
  - `entrypoint.ps1`: Script de inicialización para el contenedor de backend de Windows.
- **Archivos comunes:**
  - `.gitattributes`: Asegura que los scripts de shell tengan los finales de línea correctos (LF).
  - `create_db.py`: Script de Python para crear la base de datos (usado por ambos entrypoints).

Para una explicación más profunda de la arquitectura original, puedes consultar `documentation/docker_setup.md` o la **[guía detallada de despliegue en Ubuntu/Hyper-V](documentation/guia_detallada_ubuntu_hyperv.md)**.

## Documentación y Diagramas del Sistema

Se ha generado una serie de diagramas para facilitar la comprensión de la arquitectura, flujo de datos y contexto estratégico del proyecto. Estos se encuentran en la carpeta `documentation/diagramas/`.

### Diagramas Técnicos (UML)

- **[Casos de Uso](documentation/diagramas/diagrama_casos_uso.md)**: Actores principales y sus interacciones.
- **[Arquitectura](documentation/diagramas/diagrama_arquitectura.md)**: Estructura de contenedores y servicios.
- **[Flujo de Trabajo](documentation/diagramas/diagrama_flujo_trabajo.md)**: Proceso de negocio (Ventas -> Producción -> Despacho).
- **[Entidad-Relación (ERD)](documentation/diagramas/diagrama_entidad_relacion.md)**: Modelo lógico de datos.
- **[Estructura de Tablas](documentation/diagramas/diagrama_tablas.md)**: Detalle del esquema de base de datos.

### Análisis Estratégico (Industria Textil Ecuador)

- **[Diagrama de Ishikawa](documentation/diagramas/diagrama_ishikawa.md)**: Análisis de causas de baja competitividad.
- **[Análisis FODA (SWOT)](documentation/diagramas/diagrama_foda.md)**: Fortalezas, Oportunidades, Debilidades y Amenazas.

---

## Flujo de Trabajo de Desarrollo

1. **Desarrollo Local**: Usa `./deploy.sh` para levantar el entorno
2. **Ejecutar Pruebas**: `python3 manage.py test` antes de hacer commit
3. **Commit y Push**: Al hacer push a `main` o `fixgitlab`, el pipeline se activa automáticamente
4. **Revisión del Pipeline**: Verifica que todas las etapas pasen en GitLab
5. **Despliegue Automático**: Si todo pasa, se despliega automáticamente en producción
6. **Rollback Manual**: Si algo falla, usa el job manual de rollback en GitLab
