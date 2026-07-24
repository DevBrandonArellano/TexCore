# Plan de Estabilización, Consolidadación y Despliegue a Producción — TexCore

**Sistema de Control de Piso de Planta y Órdenes de Producción Textil**  
*Ecosistema Híbrido: Django 5 (`gestion`, `inventory`, `internal_api`) + FastAPI (`scanning_service`, `reporting_excel`, `printing_service`) + SQL Server 2022*

---

## 🎯 Objetivo General
Establecer una hoja de ruta estricta, reproducible y automatizada para la **fase de estabilización y lanzamiento limpio desde cero a producción (Go-Live Baseline)** del sistema TexCore. Este plan consolida el código fuente, la base de datos SQL Server 2022, los servicios satélites y la infraestructura Docker para garantizar cero deuda técnica, latencia óptima y máxima seguridad operativa.

---

## 🚀 Fases del Plan de Despliegue

```mermaid
flowchart TD
    A[Fase 1: Consolidación de Código y Baseline] --> B[Fase 2: Despliegue Atómico de Base de Datos SQL Server 2022]
    B --> C[Fase 3: Hardening de Seguridad e Infraestructura ISO 27001]
    C --> D[Fase 4: Orquestación y Levantamiento con Docker Compose]
    D --> E[Fase 5: Pruebas de Aceptación y Humo (Smoke Testing)]
```

---

## 1. Fase 1: Consolidación de Código y Baseline (Code Unification)

### 1.1 Unificación de Migraciones Django (Baseline Reset)
- **Estado Actual**: Migraciones aplanadas y unificadas en un único `0001_initial.py` por app (`gestion`, `inventory`, `internal_api`).
- **Acciones de Verificación**:
  - Verificar que no existan archivos residuales en las carpetas `migrations/` excepto `0001_initial.py` e `__init__.py`.
  - Confirmar que `python manage.py check` devuelva `0 issues`.

### 1.2 Limpieza y Consolidación del Backend y los Servicios Satélites
- **Django Monolito**:
  - Confirmar que `DEBUG = False` en `.env.prod`.
  - Asegurar la recolección de archivos estáticos: `python manage.py collectstatic --noinput`.
- **Servicios Satélites FastAPI (`scanning_service`, `reporting_excel`, `printing_service`)**:
  - Validar que todos los clientes REST (`DjangoApiClient`, `DjangoReportRepository`) utilicen las URLs de la red interna Docker (`http://web:8000`).
  - Asegurar la rotación y verificación de llaves RSA JWT (`jwt_token_manager.py`).
- **Frontend React / TypeScript**:
  - Ejecutar build de producción: `npm run build` o `vite build`.
  - Verificar que no queden llamadas `console.log` de depuración en código cliente.

---

## 2. Fase 2: Despliegue Atómico de Base de Datos (SQL Server 2022)

En el servidor de producción, la base de datos se inicializará completamente limpia mediante la ejecución secuencial atómica:

### Step 2.1: Inicialización del Contenedor SQL Server 2022
- Creación de la base de datos `texcore_db` y el usuario del sistema.

### Step 2.2: Migraciones + Optimizaciones DDL/Stored Procedures (automático)
```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d web
```
Al arrancar, `infrastructure/docker/entrypoint.sh` ejecuta automáticamente, en orden:
1. `python manage.py migrate` — aplica las migraciones `0001_initial.py` (~2 segundos).
2. `python manage.py apply_sql_optimizations` — aplica, vía la propia conexión Django/pyodbc
   (sin depender de `sqlcmd` ni de que los `.sql` existan dentro del contenedor `db`,
   que no los tiene montados):
   - `database/V2__optimize_sqlserver2022_texcore.sql`: habilita **Read Committed
     Snapshot Isolation (RCSI)**, **CHECK Constraints** nativos para mermas e
     integridad textil, **Filtered/Covering Indexes** y **Columnstore Index**
     (`ncci_movimiento_inventario`), `OPTIMIZE_FOR_SEQUENTIAL_KEY = ON` y
     `FILLFACTOR = 85` en `inventory_stockbodega`.
   - `database/V3__optimize_stored_procedures_texcore.sql`: despliega los 21
     Stored Procedures de Kardex, Cartera, Ventas, Aging y Producción.
3. `python manage.py register_services` — credenciales de servicio para los servicios satélite.

Ambos scripts SQL son idempotentes (`CREATE OR ALTER`, `IF NOT EXISTS`); repetir
la aplicación en cada arranque del contenedor es seguro. Para forzar una
re-aplicación manual sin reiniciar: `docker compose exec -T web python manage.py
apply_sql_optimizations`.

### Step 2.3: Sembrado de Infraestructura Global RBAC (Seeds)
```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml exec -T web \
  python manage.py seed_production_masters
```
- Delega en `setup_permissions` la creación de los **11 grupos RBAC reales**
  del sistema (`admin_sistemas`, `admin_sede`, `jefe_planta`, `jefe_area`,
  `tintorero`, `empaquetado`, `despacho`, `bodeguero`, `operario`, `ejecutivo`,
  `vendedor` — el slug exacto que usa todo el código de permisos) con su
  matriz de permisos, y crea la cuenta inicial del **Administrador de
  Sistemas** (`admin`, asignado al grupo `admin_sistemas`).
- La contraseña inicial se toma de la variable de entorno
  `DJANGO_SUPERUSER_PASSWORD` si está definida en `.env.prod`; si no, el
  comando genera una aleatoria y la imprime una sola vez en la salida —
  anótala de inmediato.
- *Nota*: Las Sedes y Áreas reales de la planta **no se pre-crean hardcodeadas**; son dadas de alta dinámicamente por el Administrador de Sistemas desde la interfaz gráfica al iniciar la operación de cada sede.

---

## 3. Fase 3: Hardening de Seguridad e Infraestructura (ISO 27001 / COBIT)

### 3.1 Gestión de Secretos (`.env.prod`)
- Generar un archivo `.env.prod` seguro con permisos `600` en el servidor:
  - `SECRET_KEY`: Cadena aleatoria de 64 caracteres.
  - `DB_PASSWORD`: Contraseña fuerte para la cuenta `sa` de SQL Server.
  - `INTERNAL_JWT_PRIVATE_KEY` / `INTERNAL_JWT_PUBLIC_KEY`: Par de llaves RSA PEM de 2048 bits para autenticación entre servicios satélite.

### 3.2 Seguridad de Red y Reverse Proxy (Nginx + SSL)
- Nginx actuará como único punto de entrada expuesto a Internet (puertos 80 y 443).
- **SSL/TLS**: Certificados Let's Encrypt / Certbot con redirección automática de HTTP a HTTPS.
- **Aislamiento Docker**:
  - SQL Server (`db`) escucha **únicamente en la red privada Docker** `backend-net`, deshabilitando el mapeo de puerto 1433 al host externo.

---

## 4. Fase 4: Orquestación y Despliegue en Servidor

### 4.1 Script de Lanzamiento Consolidado

Los scripts reales — [`scripts/deploy_production.sh`](../../scripts/deploy_production.sh)
(Linux/macOS) y [`scripts/deploy_production.ps1`](../../scripts/deploy_production.ps1)
(Windows) — son la fuente de verdad de este flujo; no se duplican aquí para
evitar que este documento quede desincronizado del código (como ocurrió antes:
una versión anterior de este plan embebía una copia de `deploy_production.sh`
que invocaba `sqlcmd` contra archivos `.sql` que nunca estuvieron montados en
el contenedor `db`, y que quedó obsoleta en cuanto el script real se corrigió).

En resumen, el script: construye las imágenes → levanta `db`+`redis` → espera
a que SQL Server acepte conexiones → levanta `web` y los servicios satélite
(migraciones y optimizaciones DDL/SPs se aplican solas en el arranque de
`web`, ver Step 2.2) → espera a que `web` termine su arranque → siembra RBAC
(`seed_production_masters`).

---

## 5. Fase 5: Pruebas de Aceptación y Humo (Smoke Testing)

### 5.1 Verificación de Salud de Servicios (Healthchecks)
- `GET https://texcore.tudominio.com/api/health/` → `200 OK`
- `GET http://localhost:8001/health/` (`scanning_service`) → `200 OK`
- `GET http://localhost:8002/health/` (`reporting_excel`) → `200 OK`

### 5.2 Pruebas de Humo Transaccionales en Piso de Planta
1. **Puesta en marcha por Administrador de Sistemas**: Creación de la primera Sede real y sus Áreas de producción.
2. **Login de Operario y Escaneo**: Registrar un escaneo de lote desde la PWA/Mobile y verificar respuesta `< 100 ms`.
3. **Transformación Máquina a Máquina**: Crear una orden de producción y ejecutar un paso de transformación verificando el registro automático de merma.
4. **Generación de Reporte Masivo**: Solicitar la exportación del Kardex de Inventario a Excel desde `reporting_excel` y verificar que la lectura se realice en Snapshot Mode sin bloquear inserciones en piso de planta.

### 5.3 Verificación de Respaldos Automáticos (Backups SQL Server)
- Configuración de tarea Cron en el servidor host para ejecuciones diarias de backup:
  ```bash
  BACKUP DATABASE [texcore_db] TO DISK='/var/opt/mssql/backup/texcore_daily.bak' WITH COMPRESSION;
  ```
