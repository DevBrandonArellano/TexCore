# Evidencia de rendimiento y usabilidad — TexCore

> **Versión medida:** rama `MES`, migraciones hasta `gestion/0008` · **Fecha de medición:** 8-oct-2026 (100 y 250 usuarios) y 27-oct-2026 (uso previsto, §3.5, con exportes por Celery y Redis)
> **Vigencia:** revisada contra la versión actual de `MES` (migraciones hasta `gestion/0009`, 14-oct-2026). Lo añadido desde la medición no toca las rutas medidas; el §5 incluye el tiempo de la migración `0009`.
> **Propósito:** respaldar el paso a producción, contrastando el sistema con los requisitos de la tesis.
> **Requisitos contrastados:** RNF-03 (Tabla 8), RNF-05 (Tabla 10) y la DoD del Sprint 7 (Tabla 14).

## 1. Criterios de la tesis

| Requisito | Criterio (texto de la tesis) |
|---|---|
| RNF-03 | «Motor de base de datos Microsoft SQL Server. Consultas de inventario y producción < 3 segundos. Validación de escaneo QR en bodega < 2500 ms.» |
| RNF-05 | «Las tareas frecuentes (registro de lote, escaneo) no deben superar los 3 pasos. Capacitación máxima de 2 horas para usuarios operativos.» |
| Tabla 14, Sprint 7 | «Microservicio scanning_service (QR/código de barras, < 2500 ms)» |

## 2. Entorno y elementos usados

| Elemento | Detalle |
|---|---|
| Despliegue | `infrastructure/docker/docker-compose.prod.yml`, la configuración de producción: Nginx, Django/DRF con Gunicorn, `celery_worker` y Redis (§3.5), scanning_service, printing_service, reporting_excel y SQL Server 2022, cada uno en su contenedor |
| Recursos | Uso previsto (§3.5): base de datos 2 CPU / 2 GB, backend 1 CPU / 1 GB con 4 workers, `celery_worker` 1 CPU / 0,5 GB con 2 procesos, y Redis. Escenarios de 100 y 250 usuarios: backend 3 CPU / 3 GB y base de datos 3 CPU / 3 GB o 6 CPU / 6 GB |
| Base de datos | SQL Server 2022 con 3 años de operación simulada de 4 empresas (1000 t/año cada una): 25 222 lotes, ~290 000 movimientos de inventario y ~1 000 000 de registros de auditoría |
| Generador de carga | Locust 2.46.6, `scripts/loadtest/locustfile.py`. Usuarios virtuales repartidos entre los **11 roles** del sistema, cada uno ejecutando solo las acciones que su rol permite: lectura, registro de lotes, transferencias, pedidos, escaneo y despacho |
| Perfil de carga | Arranque de 10 usuarios/s y 6 minutos por corrida |
| Medición del servidor | `docker stats` cada 5 s y Query Store de SQL Server |
| Criterio de fallo | Cualquier respuesta HTTP ≥ 400. El escaneo, el kárdex y el panel de planta también se marcan como fallidos si superan su umbral |

Para el escenario de 250 usuarios, que Locust genera desde **una sola IP**, se elevó durante la prueba el límite de peticiones por IP de Nginx (`api_zone`). En producción cada usuario tiene su propia IP y ese límite no interviene.

## 3. RNF-03 — Rendimiento y tiempo de respuesta

### 3.1 100 usuarios concurrentes (base de datos 3 CPU / 3 GB)

| Criterio | Medición | Peticiones | Resultado |
|---|---|---:|---|
| Escaneo QR en bodega < 2500 ms (TEX-44 CA-3) | p95 **89 ms** · máx. **539 ms** | 433 | ✅ **Cumple** |
| Consulta de producción < 3 s: panel del Jefe de Planta (TEX-17 CA-3) | p95 **220 ms** · máx. **667 ms** | 365 | ✅ **Cumple** |
| Consulta de inventario < 3 s: kárdex por bodega (TEX-22 CA-3) | p95 **610 ms** · máx. **1,4 s** | 132 | ✅ **Cumple** |
| Motor Microsoft SQL Server | SQL Server 2022 | — | ✅ **Cumple** |

**Resultado global:** 11 761 peticiones, **0,09 % de error**, p50 de 32 ms, p95 de 270 ms y p99 de 800 ms.
- Los errores son rechazos correctos del negocio: dos despachadores escanean el mismo lote al mismo tiempo y el sistema rechaza el segundo despacho.
- Ningún proceso se reinició.

### 3.2 250 usuarios concurrentes (base de datos 6 CPU / 6 GB)

| Criterio | Medición | Peticiones | Resultado |
|---|---|---:|---|
| Escaneo QR en bodega < 2500 ms | p95 **200 ms** · máx. **715 ms** | 983 | ✅ **Cumple** |
| Panel del Jefe de Planta < 3 s | p95 **380 ms** · máx. **872 ms** | 901 | ✅ **Cumple** |
| Kárdex por bodega < 3 s | p95 **390 ms** · máx. **697 ms** | 341 | ✅ **Cumple** |

**Resultado global:** 27 893 peticiones, **0,31 % de error** (solo rechazos de negocio por concurrencia sobre el mismo lote o saldo), p50 de 50 ms, p95 de 410 ms y p99 de 980 ms.

### 3.3 Integridad del inventario bajo concurrencia

Al terminar todas las corridas se verificó sobre la base completa:
- **stock = kárdex** en 52 123 combinaciones de bodega, producto y lote, sin descuadres;
- **0 saldos negativos** en stock y en movimientos.

Las operaciones concurrentes de despacho y transferencia no generan inconsistencias.

### 3.4 Exportación de reportes

La tesis no fija un umbral para las exportaciones a Excel. Los exportes pesados se generan en la cola (`celery_worker` + Redis) y el usuario los descarga al terminar:
- con el uso previsto (§3.5), cada exporte tarda, de que se pide a que se descarga, **1,5 s de p50 y 3,0 s como máximo**, con 0 exportes fallidos;
- en modo síncrono, con 100 usuarios, el p50 era de 2,4 s y el máximo de 5,5 s; con 250, la exportación de lotes llegaba a un p50 de 11 s, porque `reporting_excel` corre en un solo proceso.

### 3.5 Uso previsto: 10 usuarios simultáneos (base de datos 2 CPU / 2 GB)

Uso previsto: 50 personas conectadas, de las cuales unas 10 trabajan a la vez. Se validó también con 20, el doble.

| Criterio | 10 usuarios | 20 usuarios | Resultado |
|---|---|---|---|
| Escaneo QR en bodega < 2500 ms | p95 **37 ms** · máx. **219 ms** (63) | p95 **32 ms** · máx. **54 ms** (91) | ✅ **Cumple** |
| Panel del Jefe de Planta < 3 s | p95 **62 ms** · máx. **76 ms** (41) | p95 **99 ms** · máx. **258 ms** (84) | ✅ **Cumple** |
| Kárdex por bodega < 3 s | p95 **68 ms** · máx. **68 ms** (19) | p95 **91 ms** · máx. **182 ms** (36) | ✅ **Cumple** |
| Consulta más lenta de inventario o producción < 3 s | máx. **284 ms** | máx. **565 ms** | ✅ **Cumple** |

Entre paréntesis, la cantidad de peticiones.

**Resultado global:**
- 10 usuarios: 1 347 peticiones, **0,45 % de error**, p50 de 25 ms y p95 de 170 ms.
- 20 usuarios: 2 571 peticiones, **0,62 % de error**, p50 de 26 ms y p95 de 190 ms.
- Todos los errores son rechazos correctos del negocio: dos despachadores toman el mismo lote y el sistema rechaza el segundo despacho.
- Con 20 usuarios, el uso máximo simultáneo fue de **2,8 núcleos y 2,7 GB**. La base de datos usó el 48 % de su CPU y el backend, el 40 %.

## 4. RNF-05 — Usabilidad para el usuario operativo

| Criterio | Evidencia | Resultado |
|---|---|---|
| Registro de lote ≤ 3 pasos (TEX-12 CA-5) | Grabación del Operario registrando un lote, con cada clic numerado | ⏳ **Pendiente de grabación** |
| Escaneo ≤ 3 pasos | Grabación del despacho: escanear el lote y confirmar | ⏳ **Pendiente de grabación** |
| Pesaje y etiqueta ≤ 3 pasos (TEX-41 CA-3) | Grabación del Empaquetado pesando y emitiendo la etiqueta | ⏳ **Pendiente de grabación** |
| Panel ejecutivo legible en móvil, tableta y escritorio (TEX-46 CA-4) | Capturas a 375, 768 y 1366 px | ⏳ **Pendiente de captura** |
| Capacitación ≤ 2 h por grupo | Se ejecuta en la puesta en marcha de marzo de 2027 (§5.4 de la tesis) | 📅 **Planificada**: no se puede verificar antes de la puesta en marcha |

## 5. Configuración requerida en producción

| Concurrencia esperada | Base de datos | Backend | Resultado medido |
|---|---|---|---|
| **Uso previsto: 10 simultáneos (50 conectados)** | **2 CPU / 2 GB** (`DB_CPUS=2`, `DB_MEMORY_LIMIT_MB=2048`) | **1 CPU / 1 GB, 4 workers**; `celery_worker` 1 CPU / 0,5 GB con 2 procesos | Cumple RNF-03 también con el doble de usuarios. Máquina virtual de 4 vCPU y 8 GB |
| Hasta 100 usuarios | 3 CPU / 3 GB (`DB_CPUS=3`, `DB_MEMORY_LIMIT_MB=3072`) | 3 CPU / 3 GB, 20 workers | Cumple RNF-03 con margen de 4 a 5 veces |
| Hasta 250 usuarios | 6 CPU / 6 GB | 3 CPU / 3 GB, 20 workers (al 100 % de su CPU); se recomiendan 4 a 6 CPU | Cumple RNF-03 |

La memoria de SQL Server queda reservada con `MSSQL_MEMORY_LIMIT_MB` igual al `mem_limit` del contenedor, como ya define el compose de producción.

**Despliegue de esta versión sobre una base con años de datos:**
- las migraciones `gestion/0004`–`0008` tardan **~52 s** en total, de las cuales el relleno de auditoría (`0005`) toma 37 s;
- la migración `gestion/0009` (columna `origen` de `ParoMaquina`, con valor por omisión) tarda **1,3 s**;
- se ejecutan con el respaldo previo de la base.

## 6. Archivos de respaldo

| Escenario | Archivos (`scripts/loadtest/resultados/`) |
|---|---|
| Uso previsto, 10 y 20 usuarios, BD 2 CPU | `dim_C_10_2026-10-27_*` y `dim_C_20_2026-10-27_*`: `_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` y `_worker_tareas.txt` |
| 100 usuarios, BD 3 CPU | `final_100_2026-10-08_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` |
| 250 usuarios, BD 6 CPU | `db6cpu_250_2026-10-08_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` |
