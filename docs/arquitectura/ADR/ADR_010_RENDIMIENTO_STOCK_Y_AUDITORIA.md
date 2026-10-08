# ADR-010 — Stock paginado y auditoría filtrable por índice (TexCore)

> Numeración continua con ADR-009 (`ADR_009_LOTE_CON_VARIOS_PRODUCTOS.md`).
**Tema:** Los dos cuellos de botella de la prueba de carga del 6-oct-2026
**Fecha:** 7-oct-2026 · **Estado:** Aceptada · **Origen:** pendiente 1 de la entrada del 6–7 oct del `CHANGELOG.md`

## 1. Contexto

La prueba de carga con 3 años de operación simulada (4 empresas, ~1 M de auditorías) concluyó que el límite es de código, no de hardware:

1. `GET /api/inventory/stock/` no paginaba: el administrador recibía 28 799 filas (8 MB) por petición y los workers de gunicorn morían por memoria.
2. El `COUNT` de la paginación de `GET /api/inventory/audit-logs/` consumía el 75 % de la CPU de SQL Server (895 ejecuciones × 603 ms). El filtro `usuario__sede_id OR object_sede_id` obligaba a unir con el usuario e impedía usar índices.

## 2. Decisión

### Stock
* `StockBodegaViewSet` usa `PaginacionAcotada`, el mismo patrón que kárdex y materia prima: 50 filas por defecto y tope de 500. Filtra en el servidor por `sede_id`, `bodega_id`, `producto_id`, `lote_id` y `search`, con orden estable.
* `GET /api/inventory/stock/resumen/` (`StockResumenAPIView`) entrega los totales por bodega calculados en la base, para los gráficos y KPI del dashboard ejecutivo.
* **Frontend:**
  - `StockView` pagina con `usePaginacionIncremental` y busca en el servidor (con 300 ms de espera).
  - Transferencia y transformación piden solo los lotes del producto en la bodega elegidos (`useStockDeProductoEnBodega`).
  - El detalle por bodega del ejecutivo pide sus filas al abrirse.

### Auditoría
* `AuditLog.usuario_sede_id` guarda la sede del usuario **al momento del cambio**. Lo llena `AuditLog.save()`, así que cubre a todos los escritores (mixin, señales y comandos).
* Dos índices compuestos: `(object_sede_id, -fecha_hora)` y `(usuario_sede_id, -fecha_hora)`, uno por cada rama del OR. Se retira el índice simple de `object_sede_id`, que el compuesto ya cubre. **Reemplazados el 8-oct por un índice cubriente por fecha** (ver la revisión más abajo).
* El listado filtra `Q(usuario_sede_id=X) | Q(object_sede_id=X)` sin unir con el usuario. Los grupos del usuario se leen una sola vez.
* **Migraciones:**
  - `gestion/0004` agrega el campo y los índices.
  - `gestion/0005` rellena las filas existentes en bloques de 10 000 (`atomic = False`, se puede repetir) con la sede **actual** del usuario, la única disponible para esas filas.
* Además se implementó el `search` que `AuditLogViewer` ya enviaba y el backend ignoraba: busca por usuario, tabla o id del registro.

### Revisión del 8-oct-2026: un índice cubriente por fecha (`gestion/0008`)

La medición en SQL Server 2022 con ~1 M de auditorías refutó el supuesto de los dos índices compuestos.

**El problema:** el optimizador no busca por sede en cada rama del `OR`. Recorre los dos índices completos y los cruza.
- El `COUNT` del listado hace ~10 000 lecturas lógicas, igual que antes de la `0004`.
- Con 250 usuarios fue el **40,7 % de la CPU** de la base: 2 956 ejecuciones × 388 ms (Query Store).

**La solución:** como el listado siempre acota por fecha (30 días por defecto), basta un índice `(-fecha_hora) INCLUDE (usuario_sede_id, object_sede_id)`.
- Lee solo el rango de fechas.
- Sirve también el `ORDER BY -fecha_hora`.
- Reemplaza a los dos compuestos y al índice simple de `fecha_hora`, así que hay un índice menos que mantener en cada inserción.

| Consulta (sede 1, 30 días) | Antes (`0004`) | Con `0008` |
|---|---|---|
| `COUNT` de la paginación | 10 356 lecturas | **299** |
| Primera página (`TOP 50`) | 10 356 | **14** |
| `COUNT` del administrador (sin sede) | 478 | **299** |

La migración `0008` tardó 7,9 s sobre ~1 M de filas. Prueba: `IndiceListadoAuditoriaTestCase`.

## 3. Consecuencias

* El contrato de `/api/inventory/stock/` cambia de lista plana a `{count, next, previous, results}`. Se adaptaron sus tres consumidores en el frontend.
* Un usuario que cambia de sede ya no "lleva" sus registros anteriores a la sede nueva. Cada registro queda en la sede donde ocurrió el cambio, que es lo correcto para una auditoría.
* **Falta medir** (requiere SQL Server con el millón de filas):
  - el plan de ejecución y el tiempo del `COUNT`;
  - la duración de `0005`;
  - repetir Locust con 100 y 250 usuarios.

  Ver `REGISTRO_RIESGOS.md` (RD-06).
