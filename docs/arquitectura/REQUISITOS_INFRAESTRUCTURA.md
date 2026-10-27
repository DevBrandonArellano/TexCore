# Requisitos de infraestructura para producción

> **Fecha de medición:** 27-oct-2026 para el uso previsto (§3.1), con Celery y Redis; 8-oct-2026 para 100 y 250 usuarios (§3.2).
> **Uso previsto:** 50 personas conectadas, de las cuales unas 10 trabajan a la vez.
> **Propósito:** dimensionar el servidor de producción para que cumpla el RNF-03 de la tesis.
> **Evidencia de rendimiento:** `docs/requerimientos/EVIDENCIA_RENDIMIENTO_USABILIDAD.md`.

## 1. Criterio y servidor de destino

| Elemento | Detalle |
|---|---|
| Requisito (RNF-03, Tabla 8) | «Motor de base de datos Microsoft SQL Server. Consultas de inventario y producción < 3 segundos. Validación de escaneo QR en bodega < 2500 ms.» |
| Servidor (§5.3 de la tesis) | Máquina virtual Ubuntu Server en Hyper-V, en la infraestructura física de Interfibra S.A. |
| Base de datos | SQL Server 2022, con la edición que licencia la organización (`MSSQL_PID`) |
| Despliegue | `infrastructure/docker/docker-compose.prod.yml`: Nginx, Django/DRF con Gunicorn, `celery_worker`, Redis, `scanning_service`, `printing_service`, `reporting_excel` y SQL Server, cada uno en su contenedor |

## 2. Cómo se midió

- **Entorno:** la configuración de despliegue de producción, con 3 años de operación simulada de 4 empresas: 25 222 lotes, ~290 000 movimientos de inventario y ~1 000 000 de registros de auditoría.
- **Carga:** Locust (`scripts/loadtest/locustfile.py`) con usuarios repartidos entre los 11 roles, cada uno con las acciones que su rol permite, a 10 usuarios/s y durante 6 minutos por corrida.
- **Medición del servidor:** `docker stats` cada 5 s y el Query Store de SQL Server.

## 3. Configuración por contenedor

Los recursos se fijan en el `.env.prod` del servidor (plantilla: `.env.prod.example`, que ya trae los valores del §3.1).

### 3.1 Uso previsto: 10 usuarios simultáneos (recomendado)

Los 40 conectados que no están trabajando casi no generan carga: solo el panel del Ejecutivo se refresca solo, una vez por minuto. Cada usuario de Locust actúa cada 1 a 6 s sin pausa, más intenso que una persona real. Para dejar un margen prudente, la configuración se validó también con **20 usuarios simultáneos, el doble de lo previsto**.

| Variable | Valor |
|---|---|
| `DB_CPUS` / `DB_MEMORY_LIMIT_MB` | 2 / 2048 (2 GB es el mínimo de SQL Server 2022) |
| `BACKEND_CPUS` / `BACKEND_MEMORY_LIMIT_MB` / `BACKEND_WORKERS` | 1 / 1024 / 4 |
| `CELERY_CONCURRENCY` / `CELERY_CPUS` / `CELERY_MEMORY_LIMIT_MB` | 2 / 1 / 512 |
| `REDIS_MAXMEMORY_MB` / `REDIS_MEMORY_LIMIT_MB` | 64 / 128 |

| Resultado | 10 usuarios | 20 usuarios (margen ×2) |
|---|---|---|
| Errores reales | 0 % | 0 % |
| Consulta más lenta (RNF-03: < 3 s) | ✅ 284 ms | ✅ 565 ms |
| Escaneo QR (RNF-03: < 2500 ms) | ✅ p95 37 ms · máx 219 ms | ✅ p95 32 ms · máx 54 ms |
| Exportes por la cola (de que se piden a que se descargan) | p50 1,5 s · máx 3,0 s | p50 1,5 s · máx 3,0 s |
| Throughput | 3,8 req/s | 7,2 req/s |

**Picos por contenedor con 20 usuarios:**

| Contenedor | CPU (100 % = un núcleo) | RAM | Uso de su límite |
|---|---|---|---|
| db | 96 % | 1,7 GB | 48 % de la CPU |
| reporting_excel | 94 % | 0,19 GB | sin límite; corre en un solo proceso |
| backend | 40 % | 0,34 GB | 40 % de la CPU y 33 % de la RAM |
| celery_worker | 29 % | 0,22 GB | 29 % de la CPU y 43 % de la RAM |
| scanning · printing · nginx · redis | 18 % · 6 % · 0 % · 2 % | 0,07 · 0,07 · 0,03 · 0,01 GB | — |
| **Total simultáneo** | **2,8 núcleos** | **2,7 GB** | |

Los exportes por la cola tardan al menos 1,5 s porque el frontend consulta el estado cada 1,5 s, y los que tardan casi 2 s en generarse quedan cerca de 3 s. Con un solo proceso en el worker (`CELERY_CONCURRENCY=1`) y 20 usuarios, dos exportes simultáneos esperaban en fila: un exporte llegó a 6 s. Con 2 procesos, el máximo vuelve a 3 s.

### 3.2 Crecimiento: 100 y 250 usuarios simultáneos (8-oct-2026, sin la cola)

Medido antes de pasar los exportes a Celery. Sirve de referencia si la concurrencia crece.

| Variable | Hasta 100 usuarios | Hasta 250 usuarios |
|---|---|---|
| `DB_CPUS` | 3 | 6 |
| `DB_MEMORY_LIMIT_MB` | 3072 | 6144 |
| `BACKEND_CPUS` | 3 | 3 medidos (al 100 % de su CPU); se recomiendan 4 a 6 |
| `BACKEND_MEMORY_LIMIT_MB` | 3072 | 3072 |
| `BACKEND_WORKERS` | 20 | 20 |
| Resultado RNF-03 | ✅ p95 del escaneo de 89 ms, del panel de planta de 220 ms y del kárdex de 610 ms | ✅ p95 del escaneo de 200 ms, del panel de planta de 380 ms y del kárdex de 390 ms |

**Picos medidos por contenedor** (CPU: 100 % equivale a un núcleo; RAM en uso):

| Contenedor | 100 usuarios | 250 usuarios |
|---|---|---|
| db | 316 % · 2,7 GB | 288 % · 2,9 GB |
| backend | 142 % · 1,7 GB | 303 % · 2,1 GB (tope de su límite de 3 CPU) |
| reporting_excel | 105 % · 0,28 GB | 101 % · 0,36 GB |
| scanning | 19 % · 0,11 GB | 24 % · 0,11 GB |
| printing | 5 % · 0,06 GB | 7 % · 0,06 GB |
| nginx | 3 % · 0,02 GB | 4 % · 0,02 GB |
| **Total simultáneo** | **5,1 núcleos · 4,8 GB** | **6,9 núcleos · 5,3 GB** |

## 4. Tamaño de la máquina virtual

El tamaño se obtiene de los límites de la sección 3, más los satélites y un margen para el sistema operativo y Docker.

| Concurrencia | vCPU | RAM | Base del cálculo |
|---|---|---|---|
| **Uso previsto: 10 simultáneos (50 conectados)** | **4** | **8 GB** | Límites del §3.1: BD 2 CPU / 2 GB, backend 1 / 1 GB, worker 1 / 0,5 GB y Redis 0,125 GB. Se suman los satélites (~0,5 GB) y ~1,5 GB para el sistema operativo y Docker. Pico medido con 20 usuarios: 2,8 núcleos y 2,7 GB |
| Hasta 100 usuarios | **8** | **10 GB** | Límites de BD (3/3 GB) y backend (3/3 GB), más los satélites (~1,5 núcleos y 0,5 GB). Pico medido de 5,1 núcleos y 4,8 GB |
| Hasta 250 usuarios | **12 a 14** | **14 a 16 GB** | BD con 6/6 GB y backend con 4 a 6 CPU. El backend con 4 a 6 CPU es una recomendación: se midió con 3, al 100 % |

**Disco:** sistema operativo, imágenes, volumen de la base y respaldos. El respaldo completo de la base con 3 años de datos pesa 170 MB. La retención de respaldos la fija la organización.

## 5. Despliegue sobre una base con datos

- Las migraciones `gestion/0004`–`0008` tardan **~52 s** sobre la base de 3 años. La más larga es el relleno de auditoría (`0005`), con 37 s.
- Antes de migrar se toma un respaldo `COPY_ONLY` de la base (170 MB en 5,2 s).
- El `HEALTHCHECK` del backend tolera la migración: tiene un `start-period` de 600 s y pasa a `healthy` apenas responde.

## 6. Condiciones de operación

1. **`mem_limit` siempre definido en el backend.** Cada worker de Gunicorn es un proceso Django completo. Sin límite, la memoria crece sin techo al subir `BACKEND_WORKERS`.
2. **`MSSQL_MEMORY_LIMIT_MB` igual a `DB_MEMORY_LIMIT_MB`.** El compose de producción ya los vincula. Si SQL Server cree tener más memoria de la que le da Docker, queda bloqueado.
3. **`BACKEND_WORKERS` no sigue la regla `2 × CPU + 1`.** El tráfico espera sobre todo a SQL Server. Con 10 a 20 usuarios bastan 4 workers en 1 CPU; para 100 usuarios se midieron 20 workers en 3 CPU. Si la concurrencia crece, se suben los workers junto con `BACKEND_MEMORY_LIMIT_MB`.
4. **Exportaciones a Excel:** los exportes pesados pasan por la cola (`celery_worker`). `reporting_excel` corre en un solo proceso y es el contenedor que más CPU usa durante los exportes (94 % con 20 usuarios). La tesis no fija umbral para las exportaciones. Con el uso previsto, cada exporte tarda 1,5 s de p50 y 3 s como máximo. Antes de la cola, con 100 usuarios, el p50 era de 2,4 s y el máximo de 5,5 s; con 250, la exportación de lotes llegaba a un p50 de 11 s.
5. **Satélites sin límites propios:** `scanning_service`, `printing_service` y `reporting_excel` no declaran `cpus`/`mem_limit`. Se recomienda fijarlos con los picos de la sección 3 más un margen. `redis` y `celery_worker` sí tienen límites (§3.1).
6. **Límite de Nginx de 100 peticiones/s por IP** (`api_zone`). No interviene con usuarios reales, cada uno con su IP. Una prueba de carga desde una sola máquina debe tenerlo en cuenta.
7. **Solo HTTPS:** el puerto 80 redirige a 443 (`NGINX_REDIRIGIR_HTTP=1`). Una prueba de carga contra el servidor usa `--host=https://…` y `LOADTEST_CA_BUNDLE`.

## 7. Archivos de respaldo

| Escenario | Archivos (`scripts/loadtest/resultados/`) |
|---|---|
| Uso previsto, 10 y 20 usuarios (27-oct, con la cola) | `dim_C_10_2026-10-27_*` y `dim_C_20_2026-10-27_*`: `_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` y `_worker_tareas.txt` |
| 100 usuarios, BD 3 CPU | `final_100_2026-10-08_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` |
| 250 usuarios, BD 6 CPU | `db6cpu_250_2026-10-08_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` |
