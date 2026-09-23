# Prueba de carga — 100 usuarios concurrentes, 11 roles reales

Simula tráfico realista repartido entre los **11 roles RBAC reales** del
sistema (Django Groups, ni uno más): `admin_sistemas`, `admin_sede`,
`bodeguero`, `despacho`, `ejecutivo`, `empaquetado`, `jefe_area`,
`jefe_planta`, `operario`, `tintorero`, `vendedor`. Cada clase de usuario en
`locustfile.py` corresponde 1:1 a uno de estos grupos y solo ejecuta las
acciones HTTP que ese rol tiene permitido hacer en el sistema real (login
JWT real, no acciones inventadas) — los 100 usuarios virtuales se reparten
entre las 11 clases (peso igual, `weight = 9` cada una) y corren todos
simultáneamente, para validar que el rendimiento se mantiene bajo
concurrencia real de todo el flujo de trabajo, no solo lectura.

## ⚠️ Mutación de datos — solo contra Docker de pruebas, NUNCA producción

Los roles `DespachoUser`, `EmpaquetadoUser`, `OperarioUser` y `VendedorUser`
**mutan datos reales** (stock, lotes, pedidos, historial de despacho).
Correr esta prueba EXCLUSIVAMENTE contra un stack Docker de pruebas sembrado
en el paso 1 de abajo. Nunca apuntar `--host` a un servidor de producción real.

## ⚠️ Usar `docker-compose.prod.yml`, NO `docker-compose.yml`, para medir capacidad

**Hallazgo confirmado (22 de septiembre de 2026):** correr esta prueba contra
el stack de desarrollo (`infrastructure/docker/docker-compose.yml`, backend
con `python manage.py runserver` + `DEBUG=True`) da números que **no sirven
para nada** — el logging SQL verboso de `DEBUG=True` y el servidor de
desarrollo mono-proceso degradan tanto el sistema que peticiones GET
simples tardaron hasta **32 segundos** con 100 usuarios concurrentes, y la
tarea de despacho ni siquiera llegó a completar un ciclo de escaneo real en
3 minutos. No es que el endpoint de escaneo sea lento — es que el resto del
sistema está tan saturado que nunca se llega a medirlo.

Usar en su lugar `infrastructure/docker/docker-compose.prod.yml`
(`Dockerfile.prod`, gunicorn con 3 workers, `DEBUG=0`) — es la config real
de despliegue del repo, solo que no la usa nadie para stress testing.
Con eso, el mismo run de 100 usuarios dio una mediana global de 92ms y
`scanning/validate` en despacho con p95 de 270ms (ver "Resultado de
referencia" más abajo). Diferencia de 2-3 órdenes de magnitud — no es un
detalle menor, es la diferencia entre un resultado inútil y uno real.

```bash
export CI_REGISTRY_IMAGE=texcore-local
export TAG=stress-test
docker compose -f infrastructure/docker/docker-compose.prod.yml -p texcore-prod build
docker compose -f infrastructure/docker/docker-compose.prod.yml -p texcore-prod up -d
```
`docker-compose.prod.yml` no incluye `frontend`/`celery_worker`/`redis`
(no hacen falta para probar la API vía Locust) y usa un volumen de BD propio
(`texcore-prod_mssql_data`, project name `-p texcore-prod`) — no comparte
datos con el stack de desarrollo. Sembrar con `docker exec
texcore-prod-backend-1 python manage.py stress_test_data ...` /
`stress_ventas_data ...` igual que en el paso 1, apuntando al nombre de
contenedor `texcore-prod-backend-1`. Todas las variables de entorno
requeridas (`SECRET_KEY`, `DB_PASSWORD`, `INTERNAL_JWT_*`,
`*_SERVICE_SECRET`, etc.) ya están en `.env`.

## Instalación (una sola vez)

```bash
pip install locust
```

## Secuencia recomendada

1. **Levantar el stack de producción local** (ver sección de arriba — NO el
   de desarrollo):
   ```bash
   export CI_REGISTRY_IMAGE=texcore-local
   export TAG=stress-test
   docker compose -f infrastructure/docker/docker-compose.prod.yml -p texcore-prod build
   docker compose -f infrastructure/docker/docker-compose.prod.yml -p texcore-prod up -d
   ```

2. **Sembrar volumen de datos realista** (por defecto el seed es escala demo,
   insuficiente para que los índices marquen diferencia):
   ```bash
   docker exec texcore-prod-backend-1 python manage.py stress_test_data --dias 180 --movimientos-por-dia 150
   docker exec texcore-prod-backend-1 python manage.py stress_ventas_data --clientes 200 --pedidos 800
   ```

3. **Verificar RCSI** en la BD objetivo (no asumir que la migración corrió):
   ```bash
   docker exec texcore-prod-backend-1 python manage.py shell -c "
   from django.db import connection
   with connection.cursor() as c:
       c.execute('SELECT is_read_committed_snapshot_on FROM sys.databases WHERE name=DB_NAME()')
       print(c.fetchone())
   "
   ```

4. **Correr la prueba** (UI web en http://localhost:8089). La autenticación
   inicial de los 11 usuarios demo (uno por rol) tarda **~2.5 minutos**
   antes de que empiecen a llegar requests — respeta a propósito el
   rate-limit de login de nginx (`login_zone`, 5/min, burst 3). Es
   comportamiento esperado, no que la prueba esté colgada.

   ```bash
   locust -f scripts/loadtest/locustfile.py --host=http://localhost
   ```
   En la UI: 100 usuarios, spawn rate 5-10/s (ramp-up gradual, no arranque
   instantáneo — evita medir un "stampede" de logins no representativo).

   Recomendado antes de la corrida completa de 100 usuarios: un checkpoint
   con al menos ~25 usuarios (con menos, el reparto por peso entre 11 clases
   puede no instanciar alguna) para confirmar que los roles mutables
   (despacho, empaquetado, operario, vendedor) ejecutan sin errores contra
   el pool de datos sembrado:
   ```bash
   locust -f scripts/loadtest/locustfile.py --host=http://localhost \
       --users 25 --spawn-rate 10 --run-time 45s --headless
   ```
   Presta especial atención a la fila `/api/scanning/validate (en despacho)`
   en el resumen final — es donde se ve si el umbral de <1s se está
   cumpliendo (ver sección "Umbral de escaneo" más abajo).

   Modo headless (para CI o comparación automatizada), ~3 minutos:
   ```bash
   locust -f scripts/loadtest/locustfile.py --host=http://localhost \
       --users 100 --spawn-rate 10 --run-time 3m --headless \
       --csv=scripts/loadtest/resultado_baseline
   ```

5. **Guardar el resultado** (baseline, antes de aplicar los fixes de
   `internal_api/views/reporting_views.py` e índices). Repetir el mismo
   comando después de aplicar los fixes, con `--csv=scripts/loadtest/resultado_post_fix`,
   y comparar.

## Cómo leer los resultados

Locust reporta por endpoint (columna `Name`, agrupado por el `name=` de cada
`self.client.get(...)` en `locustfile.py`):

- **p50/p95/p99** (columnas `50%`, `95%`, `99%`): tiempo de respuesta en ms.
- **Failures**: cualquier valor > 0 a 100 usuarios concurrentes es una
  regresión real a esta escala, no ruido.
- **RPS**: requests/segundo sostenidos.

### Umbrales de referencia ("sigue siendo rápido")

| Tipo de endpoint                                              | p95 objetivo |
|-----------------------------------------------------------------|--------------|
| Dashboard/listados (navegación de cada rol)                    | < 300 ms     |
| Reportes gerenciales/producción (export)                       | < 1000 ms    |
| Exports pesados (kardex)                                        | < 3000 ms    |
| **Escaneo en despacho** (`/api/scanning/validate (en despacho)`)| **< 1000 ms — umbral de negocio, ver abajo** |
| Despacho (`process-despacho`)                                   | < 2000 ms    |
| Reversión de despacho                                            | < 1500 ms    |
| Transferencia entre bodegas                                      | < 1000 ms    |
| Creación de pedido                                                | < 1000 ms    |
| Tasa de error                                                     | 0%           |

Son valores por defecto razonables para un ERP interno; ajustar si existe un
SLA de negocio ya acordado.

### Umbral de escaneo (<1s) — cómo se valida

El escaneo de lotes durante el despacho (flujo real: N llamadas a
`/api/scanning/validate`, una por lote, seguidas de un solo
`process-despacho/` — igual que `DespachoDashboard.tsx`) tiene un umbral de
negocio explícito de **menos de 1 segundo por escaneo**, para que se sienta
instantáneo en planta. Se valida en dos niveles:

1. **Nivel servicio** (piso de referencia, sin red real):
   `pytest scanning_service/tests/integration/test_validate_latency.py -v`
   — mide el overhead interno de FastAPI + `LoteValidationService` con el
   cliente Django mockeado.
2. **Nivel end-to-end bajo carga real** (el que importa para UX): la tarea
   `DespachoUser.flujo_despacho` en `locustfile.py` marca **cada
   llamada de escaneo como fallo explícito** (`response.failure(...)`) si
   `response.elapsed.total_seconds() > 1.0`, además de registrarla bajo el
   nombre `/api/scanning/validate (en despacho)` para poder ver su p95 por
   separado del resto de tareas en el CSV/UI de Locust. Si aparecen fallos
   en esa fila con mensaje "supera el umbral", el sistema está incumpliendo
   el requisito de negocio bajo la carga simulada.

## Fallos esperados (no son bugs del stress test)

- **`POST /api/pedidos-venta/ (crear)` con 400 "excedido su límite de crédito"**:
  validación de negocio real — tras sembrar mucho volumen con `stress_ventas_data`,
  varios clientes quedan sobre su límite. Es correcto que la API lo rechace;
  no intentar "arreglarlo" reduciendo la tasa a 0%.
- **`POST /api/inventory/process-despacho/` con 400 "ya no tiene stock disponible"**
  bajo carga alta: contención real entre varios `DespachoUser` compitiendo
  por el mismo pool de lotes sembrados — esperado con pools pequeños
  (`--dias`/`--movimientos-por-dia` bajos en `stress_test_data`). Sembrar
  más lotes reduce la tasa, no la elimina (ni debería).
- **`GET /api/reporting/*` con 404** en la rama `refactorizacion`: esos
  endpoints (`internal_api` con reporting reestructurado) son trabajo de la
  rama `MES` que todavía no se portó a `refactorizacion` — no es un bug de
  esta tarea, no perseguirlo aquí.

## Resultado de referencia (22 de septiembre de 2026)

Corrida de 100 usuarios / 3 min contra `docker-compose.prod.yml` (gunicorn
3 workers, `DEBUG=False`), seed con `stress_test_data --dias 30
--movimientos-por-dia 30` + `stress_ventas_data --clientes 50 --pedidos 150`:

- 1227 peticiones totales, mediana global 92ms, p95 380ms, p99 690ms.
- **`POST /api/scanning/validate (en despacho)`: 96 peticiones, 0 fallos,
  p95 = 270ms, máximo 323ms** — umbral de negocio de <1s confirmado bajo
  carga real de 100 usuarios concurrentes con los 11 roles simultáneos.
- Tasa de error total 4.16%, 100% explicada por los "fallos esperados" de
  la sección de arriba (contención de stock en despacho, límite de crédito,
  reportes 404 fuera de alcance) — ningún fallo real de aplicación.
- CSVs de esta corrida en `scripts/loadtest/resultado_prod_*.csv`.

Con un seed más grande (`--dias 180 --movimientos-por-dia 150`, más
clientes/pedidos) la tasa de contención en despacho debería bajar, sin
eliminarse del todo — es contención real por recursos compartidos, parte
esperada de una prueba de carga concurrente.

## Notas

- Este directorio es intencionalmente independiente del test runner de
  Django (`bash scripts/run_backend_tests.sh`) — es una prueba de carga, no
  una prueba unitaria/de integración.
