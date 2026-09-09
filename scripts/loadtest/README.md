# Prueba de carga — 100 usuarios concurrentes

Simula tráfico realista (login JWT real + navegación de dashboard + exports de
reportes) contra el stack completo, para validar que el rendimiento se
mantiene bajo concurrencia — no solo con un usuario a la vez.

## Instalación (una sola vez)

```bash
pip install locust
```

## Secuencia recomendada

1. **Sembrar volumen de datos realista** (por defecto el seed es escala demo,
   insuficiente para que los índices marquen diferencia):
   ```bash
   docker exec docker-backend-1 python manage.py stress_test_data --dias 180 --movimientos-por-dia 150
   docker exec docker-backend-1 python manage.py stress_ventas_data --clientes 200 --pedidos 800
   ```

2. **Verificar RCSI** en la BD objetivo (no asumir que la migración corrió):
   ```bash
   docker exec docker-backend-1 python manage.py shell -c "
   from django.db import connection
   with connection.cursor() as c:
       c.execute('SELECT is_read_committed_snapshot_on FROM sys.databases WHERE name=DB_NAME()')
       print(c.fetchone())
   "
   ```

3. **Levantar el stack** tal como se vaya a medir:
   ```bash
   docker compose -f infrastructure/docker/docker-compose.yml up -d
   ```

4. **Correr la prueba** (UI web en http://localhost:8089):
   ```bash
   locust -f scripts/loadtest/locustfile.py --host=http://localhost
   ```
   En la UI: 100 usuarios, spawn rate 5-10/s (ramp-up gradual, no arranque
   instantáneo — evita medir un "stampede" de logins no representativo).

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

| Tipo de endpoint                          | p95 objetivo |
|--------------------------------------------|--------------|
| Dashboard/listados (`navegar_dashboard`)   | < 300 ms     |
| Reportes gerenciales/producción (export)   | < 1000 ms    |
| Exports pesados (kardex)                   | < 3000 ms    |
| Tasa de error                              | 0%           |

Son valores por defecto razonables para un ERP interno; ajustar si existe un
SLA de negocio ya acordado.

## Notas

- Esta primera ronda corre **sin límites de CPU/memoria** en
  `docker-compose.yml` (decisión explícita) — el host sin límites puede
  absorber cuellos de botella que sí aparecerían en producción con recursos
  acotados. Tratar el resultado como una primera aproximación, no como
  validación final de capacidad en producción.
- Este directorio es intencionalmente independiente del test runner de
  Django (`bash scripts/run_backend_tests.sh`) — es una prueba de carga, no
  una prueba unitaria/de integración.
