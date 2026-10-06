# ADR-008 — Texto vacío sin NULL (TexCore)

> Numeración continua con los ADR-001 a ADR-007 de `docs/arquitectura/ARQUITECTURA_SISTEMA.md` §10.
**Tema:** Los campos de texto opcionales usan `''` como vacío y dejan de admitir `NULL`
**Fecha:** 5-oct-2026 · **Estado:** Aceptada (decisión del usuario) · **Origen:** regla Ruff `DJ001`, Etapa 4 del plan `docs/superpowers/plans/2026-10-05-migracion-ruff.md`

## 1. Contexto

32 campos `CharField`/`TextField` opcionales se declaraban `blank=True, null=True`. Con eso el vacío tenía dos representaciones, `NULL` y `''`, según quién escribiera:
* El frontend enviaba `null` en productos, químicos y líneas de producción (`valor?.trim() || null`), pero `''` en otros formularios.
* La auditoría guardaba `justificacion=None` desde las señales y el mixin, y `''` o un texto desde las vistas.
* Un filtro como `observaciones=''` no encuentra las filas con `NULL`, y un reporte que concatena columnas tiene que tratar los dos casos.

La guía de Django recomienda que el vacío de un campo de texto sea `''` y que `null=True` en texto se use solo cuando haga falta distinguir "sin dato" de "vacío".

## 2. Decisión

1. Los campos de texto opcionales se declaran `blank=True, default=''`, sin `null=True`.
2. La migración convierte los datos existentes antes de cambiar el esquema, en el mismo archivo: `RunPython` (`NULL` → `''`) y después `AlterField` (`ALTER COLUMN ... NOT NULL`). Así el `ALTER` no falla en SQL Server con filas antiguas.
   - `gestion/migrations/0003_cadenas_vacias_sin_null.py` cubre 26 campos.
   - `inventory/migrations/0002_cadenas_vacias_sin_null.py` cubre 6 campos.
3. **Excepción:** un campo opcional con `unique=True` conserva `null=True` con `# noqa: DJ001` y su motivo. mssql-django crea ese índice único filtrado (`WHERE col IS NOT NULL`): admite varias filas sin valor si son `NULL`, pero no si son `''`. Hoy ningún campo cae en este caso.
4. Ruff (`DJ001`) impide volver a introducir texto nulo; la regla bloquea el CI.

## 3. Campos afectados

| App | Modelo | Campos |
|---|---|---|
| gestion | `AuditLog` | `justificacion` |
| gestion | `Producto` | `presentacion`, `pais_origen`, `calidad` |
| gestion | `LineaProduccion` | `descripcion` |
| gestion | `ProcessStep` | `description` |
| gestion | `FormulaColor` | `description`, `observaciones` |
| gestion | `ProcesoTintoreria` | `descripcion` |
| gestion | `FaseReceta` | `observaciones` |
| gestion | `DetalleFormula` | `notas` |
| gestion | `OrdenProduccion` | `observaciones` |
| gestion | `DescargaQuimicoOP` | `justificacion` |
| gestion | `OrdenProduccionSubproceso` | `observaciones`, `motivo_rechazo` |
| gestion | `LoteProduccion` | `tipo_merma`, `presentacion` |
| gestion | `EventoEtiqueta` | `motivo` |
| gestion | `TransferenciaInterarea` | `observaciones` |
| gestion | `TransformacionProducto` | `observaciones` |
| gestion | `PagoCliente` | `comprobante`, `notas` |
| gestion | `PedidoVenta` | `motivo_anulacion` |
| gestion | `CorridaProduccion` | `observaciones` |
| gestion | `OperacionProduccion` | `observaciones`, `motivo_reversion` |
| inventory | `MovimientoInventario` | `documento_ref`, `pais`, `calidad`, `observaciones` |
| inventory | `HistorialDespacho` | `observaciones` |
| inventory | `OrdenCompraSugerida` | `observaciones` |

## 4. Impacto

* **API:** estos campos ya no devuelven `null` sino `''`. En el frontend los dos son falsos, así que las comprobaciones `if (campo)` siguen funcionando. Los serializers ya **no aceptan `null`** en estos campos: un cliente que envíe `null` recibe 400. Se corrigieron los formularios que lo hacían, y sus pruebas esperan `''`.
* **Escritores corregidos en el backend:**
  - `AuditLog` (`justificacion or ''` en el mixin auditable y `''` en las señales);
  - `RegistroLoteService` (`tipo_merma`) y `TransferenciaView` (`documento_ref`);
  - el comando `load_million`.
* **SQL Server:**
  - Ningún índice nativo de los scripts V2, V4 y V5 usa estas columnas, ni como clave ni en `INCLUDE`. Esto incluye el columnstore `ncci_movimiento_inventario` de la tabla de movimientos, que solo cubre `fecha`, `producto_id`, las bodegas, `tipo_movimiento`, `cantidad` y `saldo_resultante`. SQL Server permite alterar una columna que no forma parte del columnstore.
  - El único índice afectado es el `db_index` de Django en `MovimientoInventario.documento_ref`, que mssql-django elimina y recrea al alterar la columna.
  - Ninguna restricción `CHECK` nativa las referencia.
* **Microservicios:** solo leen la BD de Django por `internal_api`; ninguno distingue `NULL` de `''` en estos campos. El campo `motivo` de `printing_service` vive en su propia base SQLite y no cambia.

## 5. Verificación

* Suite del backend con migraciones (SQLite): 1530 pruebas en verde. CI sobre SQL Server 2022: la BD de pruebas se crea aplicando estas migraciones.
* El CI **no** aplica los scripts nativos V2, V4 y V5 (solo `migrate`), así que no reproduce los índices de producción. Por eso hace falta el paso siguiente.
* **Pendiente antes del despliegue:** ejecutar la migración sobre un **respaldo con datos de producción** en SQL Server, con los scripts nativos ya aplicados, y comprobar lo siguiente:
  1. No queda ningún `NULL` en las columnas de la tabla de la §3; por ejemplo, `SELECT COUNT(*) FROM inventory_movimientoinventario WHERE documento_ref IS NULL` debe dar 0.
  2. El índice de `documento_ref` existe después de la migración.
  3. El tiempo de la migración en la tabla de movimientos (la más grande) es aceptable para la ventana de despliegue.

## 6. Alternativas descartadas

* **Excluir `DJ001` en `pyproject.toml`:** deja las dos representaciones del vacío y la deuda abierta.
* **Normalizar `None → ''` en `save()` de cada modelo:** oculta a los escritores incorrectos en lugar de corregirlos, y no cubre `QuerySet.update()`.
