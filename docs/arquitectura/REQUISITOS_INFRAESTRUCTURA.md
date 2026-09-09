# Requisitos de infraestructura para 100 usuarios concurrentes

> Basado en la auditoría de performance realizada el 31 de agosto de 2026 (ver `CHANGELOG.md`,
> secciones del 31 de agosto). Stack: Django + SQL Server 2022 + microservicios FastAPI, todo en
> Docker, herramienta de carga: Locust (`scripts/loadtest/`).

## 1. Resumen ejecutivo

Durante la sesión del 31 de agosto de 2026 se ejecutó una serie extensa de pruebas de carga con
Locust (login JWT real, mezcla ponderada de tráfico dashboard/reportes/exports) contra el stack
completo de TexCore, primero con 100 usuarios concurrentes y después con 250, variando en cada
corrida la CPU, la RAM y el número de `BACKEND_WORKERS` de gunicorn asignados a los contenedores
`backend` y `db`. En paralelo se corrigieron dos bugs de código (un DSL "SP" innecesario en
`reporting_excel` y un N+1 de queries en `/api/inventory/stock/`) y se alinearon los timeouts de
nginx con los de gunicorn.

El hallazgo más importante de toda la auditoría es que el cuello de botella real **no fue nunca la
CPU ni la RAM en bruto**: en las corridas de 100 usuarios con recursos suficientes, la CPU del
backend casi nunca superó el 30-85% de uso, y aun bajando los recursos hasta un -40% del
dimensionamiento inicial (3.6 CPU / 4.3GB) el sistema siguió sosteniendo 100 usuarios con 0% de
fallos. El límite real resultó ser la combinación de (a) dos bugs de código que multiplicaban el
trabajo por request, (b) el timeout de nginx desalineado con el de gunicorn, y (c) el número de
`BACKEND_WORKERS` de gunicorn frente al pico de conexiones concurrentes reales — la fórmula clásica
`2×CPU+1` resultó muy conservadora para este tráfico, mayormente I/O-bound (espera a SQL Server).

Por eso este documento no presenta un único número de "requisitos mínimos", sino tres niveles
(mínimo, uso normal, óptimo) derivados directamente de los escalones medidos, y deja explícito qué
parte del comportamiento observado depende de recursos de hardware y qué parte depende de
parámetros de configuración (workers, timeouts) que hay que ajustar junto con el hardware, no en
su lugar.

## 2. Metodología de la prueba de carga

### 2.1 Herramienta y escenario simulado

Se usó [Locust](https://locust.io/) contra el stack completo levantado con
`docker-compose.prod.yml` (nginx real, gunicorn real, SQL Server real — no mocks), atacando
`http://localhost` desde la misma máquina. El script (`scripts/loadtest/locustfile.py`) simula
un usuario real, no una ráfaga sintética:

- **Autenticación real**: login vía `POST /api/token/` con cookies JWT httponly, igual que el
  navegador — no se saltan el proxy ni la negociación de contenido de DRF, para que el costo
  medido sea el costo real de una petición.
- **4 usuarios demo reutilizados, no 100 logins distintos**: `user_ejecutivo`, `user_jefe_planta`,
  `user_bodeguero`, `user_vendedor`. Cada uno se autentica una sola vez al arrancar la prueba
  (`test_start`, con 3s de espera entre logins para no chocar con el rate-limit de login de nginx
  — 5 intentos/min por IP) y su sesión ya autenticada se reparte en round-robin entre los N
  usuarios virtuales simulados. Esto imita 100 pestañas de navegador de 4 personas reales (todas
  las peticiones de Locust salen de la misma IP, a diferencia de 100 usuarios reales en
  producción que vendrían de 100 IPs distintas).
- **Tiempo de "pensar" entre acciones**: cada usuario virtual espera entre 1 y 4 segundos
  (aleatorio) entre una petición y la siguiente (`wait_time = between(1, 4)`) — no es una ráfaga
  continua sin pausas, imita el ritmo de una persona navegando.
- **Mezcla de tráfico ponderada** (probabilidad de cada acción por usuario virtual en cada
  ciclo):
  - **60%** — navegación normal de dashboard/listados: una de `/api/productos/`, `/api/clientes/`,
    `/api/pedidos-venta/`, `/api/ordenes-produccion/`, `/api/inventory/stock/`,
    `/api/inventory/movimientos/`, `/api/kpi-ejecutivo/`, `/api/kpi-area/`,
    `/api/produccion/resumen/` (elegida al azar).
  - **30%** — lectura de reportes gerenciales/producción con exportación a Excel
    (`?format=xlsx`, la ruta completa que genera el archivo, no solo el JSON): una de
    `gerencial/ventas`, `gerencial/top-clientes`, `gerencial/deudores`, `produccion/ordenes`,
    `produccion/lotes`, `produccion/tendencia`.
  - **10%** — el export más pesado del sistema: `/api/reporting/export/kardex` sobre una bodega
    con movimientos reales (`bodega_id=10002`).

### 2.2 Duración y parámetros de cada corrida

- **100 usuarios concurrentes**: *spawn rate* 10 usuarios/segundo (arranque gradual en ~10s, no
  instantáneo — evita medir un "estampido" de logins no representativo) y **3 minutos** de
  duración sostenida por corrida (`--run-time 3m --headless`).
- **250 usuarios concurrentes** (escalón de búsqueda de límites, sección 3.3 más abajo):
  *spawn rate* 20/s, también 3 minutos sostenidos.
- Cada configuración de recursos (CPU/RAM/`BACKEND_WORKERS`) se probó en una corrida
  independiente de 3 minutos — los contenedores `backend`/`db` se recrean entre corridas para
  aplicar el nuevo límite antes de medir.

### 2.3 Qué se midió en cada corrida

1. **Latencia por endpoint y agregada**, reportada por Locust: mediana (p50), p66, p75, p80, p90,
   p95, p98, p99, p99.9 y máximo real observado — no solo el promedio, para poder detectar colas
   largas que un promedio esconde.
2. **Throughput**: peticiones totales completadas en la ventana de 3 minutos y peticiones/segundo
   agregadas.
3. **Tasa de error real**: % de peticiones que terminaron en HTTP 4xx/5xx (incluye 500 del
   timeout interno `reporting_excel`→Django y 502/504 de nginx/gunicorn), separado por endpoint,
   no solo el agregado — para poder distinguir "todo falla un poco" de "un solo endpoint
   concentra el problema".
4. **Uso real de CPU y RAM de los contenedores**, con `docker stats --no-stream` muestreado cada
   9-10 segundos durante toda la corrida (proceso en paralelo a Locust), comparado contra el
   límite (`cpus`/`mem_limit`) configurado en ese escalón — esto es lo que permitió distinguir
   "está lento porque falta CPU/RAM" de "está lento por cola de workers" o "por un bug de código",
   en vez de asumirlo.
5. **Logs de aplicación** (`docker logs docker-backend-1`) para confirmar la causa exacta de cada
   error: duración exacta de la petición fallida (para identificar qué timeout específico la
   cortó — 30s del salto interno, 120s de nginx/gunicorn), mensajes de `WORKER TIMEOUT` o
   `SIGKILL... Perhaps out of memory?` (para diferenciar cola de conexiones vs. crash por OOM), y
   el estado del contenedor (`docker inspect ... OOMKilled`) tras cada corrida.

## 3. Tabla resumen de escalones probados

Todas las corridas usan el mismo `scripts/loadtest/locustfile.py`. Salvo que se indique lo
contrario, spawn rate 10/s y duración 3 min para 100 usuarios, 20/s y 3 min para 250 usuarios.

### 3.1 Escalones sobre el dimensionamiento original (100 usuarios), con los 2 bugs de código ya corregidos

| Escalón | CPU backend/db | RAM db | BACKEND_WORKERS | CPU pico backend | CPU pico db | % fallos | Peticiones | Mediana | p95 | p99 | Máximo |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 100% (post nginx fix, dev) | 6 / 6 | 7168MB | 13 | ~4% (reposo) | ~3% (reposo) | 0.00% | 3695 | 70ms | 230ms | 810ms | 982ms |
| 100% (`docker-compose.prod.yml` real) | 6 / 6 | 7168MB | 13 | — | — | 0.00% | 5750 | 75ms | 350ms | 3000ms | 4535ms |
| -20% (con ambos fixes de código) | 4.8 / 4.8 | 5734MB | 11 | — | — | 0.00% | 6334 | 65ms | 200ms | 270ms | 490ms |
| -40% (con ambos fixes de código) | 3.6 / 3.6 | 4301MB | 8 | 58% (210% de cap 360%) | 23.5% (84.72% de cap 360%) | 0.00% | 6333 | 67ms | 200ms | 280ms | 580ms |

Nota: la corrida "-20% (con ambos fixes)" no reporta explícitamente el % de uso de CPU pico en el
CHANGELOG (solo la corrida a -40%); el throughput medido en -20% fue 35-39 req/s.

### 3.2 Escalón previo a los fixes de código, con -20% de recursos (para contraste)

| Escalón | CPU backend/db | RAM db | BACKEND_WORKERS | CPU pico backend | CPU pico db | % fallos | Peticiones | Cola alta |
|---|---|---|---|---|---|---|---|---|
| -20% (sin fixes, antes del DSL/N+1) | 4.8 / 4.8 | 5734MB | 11 | 448% de cap 480% (saturado) | 230% de cap 480% (con margen) | 0.67% (22/3292) | 3292 | p98-p99.9 entre 32000-63000ms |

### 3.3 Escalón de 250 usuarios, buscando el límite de workers a CPU fija (2.4 CPU / 2.8GB, -60% del original)

| BACKEND_WORKERS | % fallos | # peticiones | CPU pico backend (cap 240%) | CPU pico BD (cap 240%) |
|---|---|---|---|---|
| 6 (fórmula 2×2.4+1) | 78.62% | 290 | 158% (66%) | 82% (34%) |
| 20 | 53.76% | 372 | 205% (85%) | 5% |
| 40 | 24.51% | 816 | 204% (85%) | 44% |
| 60 | **3.40%** | 2353 | **252% (105%, sobre el cap)** | 84% (35%) |

Con 60 workers, el 3.40% de fallos restante está concentrado enteramente en `/api/reporting/*`
(5.8%-12.5% por endpoint) — la firma del timeout interno arquitectónico de 30s ya conocido, no un
problema de recursos. Todos los demás endpoints llegaron a 0% de fallos.

### 3.4 Escalón mínimo, 100 usuarios, 1 CPU / 1GB fijos

| BACKEND_WORKERS | RAM en reposo | CPU pico | % fallos | Resultado |
|---|---|---|---|---|
| 10 | 660MB (65% de 1GB) | 36% | 33.75% | 0% de fallos en endpoints normales, pero medianas de 30.000-115.000ms — funciona, pero inutilizable |
| 16 | — | — | 57.76% | Empeoró: 502 Bad Gateway, workers muriendo por OOM y reiniciándose |
| 40 | 1GB (100%) ya en reposo, sin tráfico | — | — | OOM-kill en loop desde el arranque, ni llegó a levantar la prueba |

### 3.5 Escalón adicional: 1 CPU con más RAM (2GB / 24 workers) — confirma un techo físico de CPU

Continuando el afinado anterior, se subió `BACKEND_MEMORY_LIMIT_MB` de 1024 a 2048 (manteniendo
`BACKEND_CPUS=1` fijo) y `BACKEND_WORKERS` a 24. 100 usuarios, mismos parámetros:

| BACKEND_CPUS | BACKEND_MEMORY_LIMIT_MB | BACKEND_WORKERS | CPU pico backend | RAM pico backend | % fallos totales | % fallos en endpoints normales | Mediana |
|---|---|---|---|---|---|---|---|
| 1 | 2048 | 24 | 108.99% de cap 100% (saturado) | 78.73% de 2GB (con margen) | 21.75% | 0.00% | 28.000-29.000ms |

El 100% de los fallos restantes es, de nuevo, `/api/reporting/*` (45-68% cada uno) — la firma del
timeout interno de 30s ya documentado, no un problema de recursos. **Conclusión clave**: con 1 CPU
real, más RAM sí permite más workers sin crashear (de 10 a 24, sin OOM) y sí sube el % de éxito
general, pero **no resuelve la latencia** — con un solo núcleo, las peticiones hacen cola
genuinamente por tiempo de CPU, no por memoria ni por cantidad de procesos. La RAM extra ayuda a
*no colapsar*, pero el techo de *velocidad* con 100 usuarios concurrentes es la cantidad de
núcleos físicos disponibles, un límite que ningún tuning de `BACKEND_WORKERS`/RAM puede superar.

### 3.6 Escalón dedicado: piso mínimo para que TODAS las consultas respondan en menos de 1 segundo

A pedido explícito del usuario ("las consultas deben ser rápidas, todas menos de 1 segundo"), se
buscó el punto más bajo de recursos que garantice esa cota de latencia con 100 usuarios — un
criterio más estricto que "0% de errores" (una petición puede completar sin error y aun así tardar
segundos). Con los 2 fixes de código ya aplicados:

| CPU backend/db | RAM (ambos) | BACKEND_WORKERS | CPU pico backend | CPU pico db | % fallos | Mediana | p95 | p99 | Máximo | ¿Cumple <1s en TODAS? |
|---|---|---|---|---|---|---|---|---|---|---|
| 2 / 2 | 2048MB | 16 | 200% de cap 200% (saturado) | 90% de cap 200% (con margen) | 0.00% | 93ms | 510ms | 960ms | **1568ms** | **No** — el máximo real supera 1s (también 1458-1475ms en otros endpoints) |
| 3 / 3 | 3072MB | 20 | 230% de cap 300% (76%, con margen) | 113% de cap 300% (38%, con margen) | 0.00% | 69ms | 200ms | 290ms | **705ms** | **Sí** — ninguna petición superó 1 segundo, y ningún contenedor llegó a saturar su cap |

**Conclusión**: 2 CPU deja al backend genuinamente saturado (200% de su propio cap, sostenido) y
aunque el 99% de las peticiones queda bajo 1s, la cola del 1% restante sí la rompe (hasta
1568ms) — no cumple el criterio estricto de "todas". **3 CPU / 3GB / 20 workers es el piso mínimo
real que garantiza <1s en el 100% de las peticiones** a 100 usuarios, con margen de sobra (ningún
contenedor llegó a saturar su límite). Este es el número a usar cuando el requisito es "rápido
siempre", no solo "sin errores".

## 4. Tres niveles de requisitos recomendados

### 4.1 MÍNIMO

| Parámetro | Valor |
|---|---|
| CPU (backend) | 1 vCPU |
| RAM | 1GB (`BACKEND_MEMORY_LIMIT_MB=1024`) |
| BACKEND_WORKERS | 10 |
| DB_CPUS / DB_MEMORY_LIMIT_MB | No medido directamente en este escalón — estimado por proporcionalidad con los escalones de la sección 3.1/3.4; requiere prueba dedicada antes de fijarse |
| Experiencia esperada | El sistema no se cae, pero es **inutilizable en la práctica**: 33.75% de fallos duros y, en las peticiones que sí completan, medianas de 30.000-115.000ms. Subir `BACKEND_WORKERS` por encima de 10 en este nivel de RAM empeora el resultado (OOM: 16 workers da 502 por crashes, 40 workers ni siquiera levanta). Este nivel solo sirve como referencia de "piso absoluto que no colapsa por completo" — no se recomienda para ningún entorno con usuarios reales. |

**Importante — 1 CPU es un techo físico de latencia, no solo de RAM.** Se probó además subir la
RAM a 2GB con 24 workers (sección 3.5), manteniendo 1 CPU fijo: el % de fallos totales mejoró
(21.75%, con 0% en endpoints normales) y la CPU por fin se saturó de verdad (108.99% de su cap),
pero la mediana de latencia siguió siendo mala (28.000-29.000ms) — prácticamente igual de mala que
con 1GB/10 workers. Con un solo núcleo real, las peticiones hacen cola por tiempo de CPU, no por
memoria ni por cantidad de procesos; ningún tuning de `BACKEND_WORKERS` o de RAM adicional supera
ese límite. Conclusión: **1 CPU no es viable para 100 usuarios bajo ningún dimensionamiento de
RAM/workers** — el mínimo real recomendado para un servicio siquiera aceptable requiere más de 1
núcleo (ver nivel USO NORMAL, a partir de 3.6 CPU).

### 4.2 USO NORMAL

Basado en los escalones -20%/-40% del dimensionamiento original, ambos con los dos fixes de
código ya aplicados (DSL "SP" eliminado, N+1 de `/api/inventory/stock/` corregido) y con los
timeouts de nginx/gunicorn alineados a 120s.

| Parámetro | Valor |
|---|---|
| CPU (backend y db) | 3.6-4.8 vCPU cada uno |
| RAM (db) | 4301-5734 MB (`DB_MEMORY_LIMIT_MB`) |
| BACKEND_WORKERS | 8-11 |
| DB_CPUS / DB_MEMORY_LIMIT_MB | 3.6/4301MB (punto -40%) hasta 4.8/5734MB (punto -20%) |
| Experiencia esperada | 0.00% de fallos reales en ambos escalones, mediana 65-70ms, p95 ~200ms, p99 270-280ms, máximo 490-580ms. Margen amplio observado: a -40% el backend llegó solo a 58% de su cap de CPU y la db a 23.5%. Excluye el bug arquitectónico conocido del timeout interno `reporting_excel`→Django de 30s (ver sección 5c), que no depende de estos recursos. |

**Si el requisito es "todas las consultas por debajo de 1 segundo" de forma estricta** (no solo
"0% de errores"), usar el piso dedicado de la sección 3.6: **3 CPU / 3GB / 20 workers** — es el
punto más bajo verificado donde ni el peor caso (máximo real: 705ms) supera 1 segundo. Con 2 CPU
el máximo real llegó a 1568ms a pesar de 0% de errores, por lo que 2 CPU no cumple ese criterio
aunque sí sea "funcional".

### 4.3 ÓPTIMO

Dos variantes válidas según el objetivo (throughput/latencia a 100 usuarios vs. margen para picos
de hasta 250 usuarios):

**Variante A — dimensionamiento original completo (mejor latencia medida a 100 usuarios):**

| Parámetro | Valor |
|---|---|
| CPU (backend y db) | 6 vCPU cada uno |
| RAM (db) | 7168 MB |
| BACKEND_WORKERS | 13 |
| Experiencia esperada | 0.00% de fallos, mediana 70-75ms, p95 230-350ms, p99 810-3000ms (la cola alta en `docker-compose.prod.yml` real la explica en parte `/api/inventory/stock/` antes del fix N+1), máximo hasta 4535ms. `docker stats` en reposo tras la corrida: backend ~4% CPU/1GB RAM, db ~3% CPU/4.3GB de 7GB — amplio margen sobrante. |

**Variante B — mejor margen de seguridad frente a picos de concurrencia (250 usuarios):**

| Parámetro | Valor |
|---|---|
| CPU (backend y db) | 2.4 vCPU cada uno |
| RAM (db) | 2867 MB |
| BACKEND_WORKERS | 60 |
| BACKEND_MEMORY_LIMIT_MB | Obligatorio fijar un techo (ver advertencia 5b); con 60 workers sin límite el backend llegó a ~4.2GB de RSS en la prueba — dimensionar el `mem_limit` real según la RAM total disponible en el host. |
| Experiencia esperada | A 250 usuarios concurrentes: 3.40% de fallos, concentrados enteramente en `/api/reporting/*` (bug arquitectónico del timeout de 30s, no de recursos) — todos los demás endpoints en 0% de fallos, con 2353 peticiones completadas en la ventana de 3 minutos. El backend satura de verdad su cap de CPU (252% de 240%) solo en este punto, confirmando que 2.4 CPU sí alcanzan para 250 usuarios reales si el número de workers está bien dimensionado. |

La Variante B demuestra que, con el número correcto de workers, se puede sostener el doble de
concurrencia (250 vs. 100 usuarios) con menos de la mitad de la CPU del dimensionamiento original
(2.4 vs. 6 vCPU) — el verdadero factor limitante es `BACKEND_WORKERS`, no la CPU asignada.

## 5. Advertencias operativas clave

**(a) La fórmula `2×CPU+1` es demasiado conservadora para este tráfico.** Está pensada para
trabajo CPU-bound; los endpoints de TexCore son mayormente I/O-bound (esperan a SQL Server o al
microservicio de reportes). En la prueba de 250 usuarios a 2.4 CPU fijos, la fórmula daba 6
workers (78.62% de fallos); el punto donde el CPU real se saturó de verdad fue 60 workers (~25×
CPU en vez de 2×), con solo 3.40% de fallos y esos concentrados en el bug arquitectónico conocido,
no en falta de recursos. Para producción, no aplicar la fórmula a ciegas: dimensionar
`BACKEND_WORKERS` probando escalones hasta encontrar el punto de saturación real de CPU, como se
hizo en esta auditoría.

**(b) Cada worker de gunicorn es un proceso Django completo — siempre poner `mem_limit` al
backend.** A diferencia de la CPU (que se reparte con cola, sin crashear), la RAM sin techo puede
causar OOM-kills en cascada: en la prueba de 1 CPU/1GB, subir de 10 a 16 workers no mejoró la
capacidad, la empeoró (502 Bad Gateway por workers muriendo y reiniciándose), y 40 workers ni
siquiera llegó a levantar el servicio (OOM-kill en loop desde el arranque, sin recibir tráfico).
Se agregó en esta sesión la variable `BACKEND_MEMORY_LIMIT_MB` (antes `docker-compose.prod.yml`
nunca le ponía límite de memoria al backend, solo `cpus`) — debe configurarse siempre, en todos
los niveles de la sección 4, acorde a `BACKEND_WORKERS` × footprint por worker y a la RAM total
disponible en el host.

**(c) El bug arquitectónico del timeout interno de 30s (`reporting_excel`→Django) no se resuelve
subiendo CPU/RAM.** Afecta a cualquier nivel de recursos de este documento — apareció como el
3.40% de fallos restante incluso en el mejor escalón probado (Variante B, con el backend saturando
de verdad su CPU). La causa es que la cadena de cada reporte hace un salto redundante
(`nginx → backend Django → reporting_excel → de vuelta al mismo backend Django`), y ese último
salto usa un timeout (`django_client.py:151`, 30s) más corto que el resto de la cadena (60-120s),
así que es el primer eslabón en agotarse bajo contención. Subir ese timeout interno fue evaluado y
descartado deliberadamente por su costo en seguridad (retiene workers síncronos por más tiempo
ante un cliente lento o un ataque de agotamiento de recursos). El fix pendiente y de mayor impacto
es eliminar el salto redundante (que `reporting_proxy` llame directamente a `internal_api` sin
pasar por `reporting_excel`, o mover la generación del Excel al propio backend) — ningún
dimensionamiento de infraestructura de este documento sustituye ese fix de código.

## 6. Nota al pie

Estos números se midieron en un entorno de prueba local (VM) con datos de estrés sintéticos
(~50.502 movimientos de inventario generados con `stress_test_data --dias 180
--movimientos-por-dia 150`, ~3465 filas de stock). Deben validarse contra el volumen de datos real
y el hardware real de producción antes de fijarse como definitivos — en particular, repetir la
búsqueda de "workers óptimos por CPU" (sección 3.3) con el `BACKEND_CPUS` real que se decida para
producción, ya que el múltiplo óptimo puede no ser el mismo a otra escala de CPU.
