# Evidencia de rendimiento y usabilidad — TexCore

> **Versión evaluada:** rama `MES`, migraciones hasta `gestion/0008` · **Fecha de medición:** 8-oct-2026
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
| Despliegue | `infrastructure/docker/docker-compose.prod.yml`, la configuración de producción: Nginx, Django/DRF con Gunicorn (20 workers), scanning_service, printing_service, reporting_excel y SQL Server 2022, cada uno en su contenedor |
| Recursos | Backend 3 CPU / 3 GB. Base de datos 3 CPU / 3 GB (escenario de 100 usuarios) o 6 CPU / 6 GB (escenario de 250) |
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
- **stock = kárdex** en 51 994 combinaciones de bodega, producto y lote, sin descuadres;
- **0 saldos negativos** en stock y en movimientos.

Las operaciones concurrentes de despacho y transferencia no generan inconsistencias.

### 3.4 Exportación de reportes

La tesis no fija un umbral para las exportaciones a Excel (`reporting_excel`):
- con 100 usuarios, p50 de 2,4 s y máximo de 5,5 s (reporte de lotes de producción);
- con 250 usuarios, la exportación de lotes llega a un p50 de 11 s, porque el servicio corre en un solo proceso.

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
| Hasta 100 usuarios | 3 CPU / 3 GB (`DB_CPUS=3`, `DB_MEMORY_LIMIT_MB=3072`) | 3 CPU / 3 GB, 20 workers | Cumple RNF-03 con margen de 4 a 5 veces |
| Hasta 250 usuarios | 6 CPU / 6 GB | 3 CPU / 3 GB, 20 workers (al 100 % de su CPU); se recomiendan 4 a 6 CPU | Cumple RNF-03 |

La memoria de SQL Server queda reservada con `MSSQL_MEMORY_LIMIT_MB` igual al `mem_limit` del contenedor, como ya define el compose de producción.

**Despliegue de esta versión sobre una base con años de datos:**
- las migraciones `gestion/0004`–`0008` tardan **~52 s** en total, de las cuales el relleno de auditoría (`0005`) toma 37 s;
- se ejecutan con el respaldo previo de la base.

## 6. Archivos de respaldo

| Escenario | Archivos (`scripts/loadtest/resultados/`) |
|---|---|
| 100 usuarios, BD 3 CPU | `final_100_2026-10-08_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` |
| 250 usuarios, BD 6 CPU | `db6cpu_250_2026-10-08_stats.csv`, `_failures.csv`, `_stats_history.csv`, `_docker_stats.csv` |
