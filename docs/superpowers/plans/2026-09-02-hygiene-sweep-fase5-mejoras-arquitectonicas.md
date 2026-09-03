# Barrido de Higiene — Fase 5: Mejoras Arquitectónicas (SOLID/DRY)

> **Estado: 13 de 14 ítems completos + 2 de 3 DECISIÓN REQUERIDA resueltas (2026-09-02), sin
> commitear.** 5.1 y el fix de `ConsumoLoteDetalle` completados a pedido explícito de Brandon tras
> checkpoint (ambos incluyen migración de esquema nueva). `registro_lote.py` confirmado que NO se
> toca. Solo queda pendiente `Batch` vs `MateriaPrimaLote` (Brandon no respondió aún). 5.11 se
> investigó y se decidió NO tocarlo — no era un duplicado real.

**Origen:** `docs/superpowers/specs/2026-09-01-backend-hygiene-sweep-design.md`, sección "Fase 5".

## 5.1 — ConfiguracionEmpaqueSede (completado tras checkpoint con Brandon)

Requerido explícitamente por `CLAUDE.md`: "Packaging equivalences (e.g. Yarns: 1 baño = 15 fundas
= 225 conos; Fabrics: 1 baño = 600m) are configurable reference examples per sede, not
system-wide hardcoded constants." Se buscó en todo el repo cualquier hardcodeo de estas
equivalencias — solo existían 2 (la de telas/600m del ejemplo de `CLAUDE.md` no está hardcodeada
en ningún lado hoy, es puramente ilustrativa):

1. `gestion/models/produccion.py::LoteProduccion.clean()` — `presentacion == 'baño'` → 225,
   `'funda'` → 15, `'cono'` → 1 (siempre, no configurable — es la unidad base).
2. `inventory/services/mrp_engine.py::MRPEngine.CONVERSION_BANOS_CONOS = Decimal('225')`.

**Modelo nuevo** `ConfiguracionEmpaqueSede` (`gestion/models/core.py`, junto a `Sede`):
`OneToOneField` a `Sede`, campos `fundas_por_bano`/`conos_por_funda` (ambos `PositiveIntegerField`,
default 15), propiedad calculada `conos_por_bano` (`fundas_por_bano * conos_por_funda`). Sedes sin
fila propia usan el valor de referencia original (225/15) como fallback — no hay `get_or_create`
automático en el camino de lectura (evita escrituras como efecto secundario de una validación).

**Migración** `gestion/migrations/0004_configuracion_empaque_sede.py`: `CreateModel` (generado con
`manage.py makemigrations`, no escrito a mano) + `RunPython` que precarga una fila
`fundas_por_bano=15, conos_por_funda=15` para cada `Sede` ya existente (`get_or_create`,
idempotente). Reverso es no-op (`RunPython.noop`) — no tiene sentido "revertir" un backfill de
datos de referencia. Se verificó que `database/V2__optimize_sqlserver2022_texcore.sql` ya NO tiene
ningún CHECK constraint atado a los valores 225/15/1 (`CK_lote_empaque_bano_225`, etc. — el propio
script los DROPea a favor de un `CK_lote_unidades_empaque_positivo` genérico); no hace falta
tocarlo.

**Consumidores actualizados** (ambos con fallback si la sede no tiene configuración):
- `LoteProduccion.clean()`: rama `'baño'`/`'funda'` ahora consulta
  `ConfiguracionEmpaqueSede.objects.filter(sede=self.orden_produccion.sede).first()` (null-safe si
  `orden_produccion` es `None`, campo nullable).
- `MRPEngine`: nuevo método `_get_conos_por_bano(sede)`, llamado una vez por sede en
  `_procesar_pedidos_venta` (antes recalculaba la constante en cada iteración del loop de
  detalles — pequeña mejora de N+1 de paso). `CONVERSION_BANOS_CONOS` renombrado a
  `CONVERSION_BANOS_CONOS_DEFAULT` (verificado: solo un comentario en
  `inventory/tests/test_mrp.py` lo mencionaba, no código real — nada se rompe por el rename).

**Tests nuevos** (`gestion/tests/test_configuracion_empaque_sede.py`, 10 tests ISTQB) — este
comportamiento no tenía ningún test dedicado antes (gap preexistente, no introducido aquí):
cálculo de `conos_por_bano`, las 3 ramas de presentación con/sin configuración personalizada,
`unidades_empaque` explícito no se sobreescribe, `orden_produccion=None` no falla, y los 2 casos
de `MRPEngine._get_conos_por_bano`. El test preexistente `inventory/tests/test_mrp.py` (sede sin
`ConfiguracionEmpaqueSede`, espera 225 de default) sigue pasando sin cambios — confirma que el
fallback preserva el comportamiento anterior exactamente.

**Verificación específica de la migración** (sin poder aplicarla contra una BD real —
[[no-docker-local]]): `makemigrations --check --dry-run` → sin cambios pendientes (el modelo y la
migración están en sync exacto). Aplicarla contra SQLite (`settings_test_local`) para probarla
de punta a punta no fue posible — `0002_fix_token_blacklist_mssql.py` (migración previa, no tocada
en esta sesión) tiene SQL crudo específico de SQL Server que bloquea cualquier `migrate` en SQLite
mucho antes de llegar a `0004`; limitación preexistente del repo. Brandon debe correr
`manage.py migrate` contra SQL Server real para la verificación end-to-end.

## Completados (resto de la fase)

- **5.2** — `_ajustar_stock_por_cambio_peso` y la reversión manual de stock en `rechazar()`
  (`gestion/views/production_lote_views.py`, 949 líneas) extraídos a
  `gestion/services/lote_stock_adjustment.py::LoteStockAdjustmentService`
  (`ajustar_por_cambio_peso()`, `revertir_por_rechazo()`). La vista ahora solo hace parseo HTTP y
  traduce `ValidationError` a la respuesta 400 original (mismo texto de error, mismo shape
  `{"error": "..."}"`). `rechazar()` perdió las variables `bodega_salida`/`bodega_entrada_op`
  (ya sin uso, la lógica vive en el service) y el archivo perdió los imports de
  `StockBodega`/`MovimientoInventario`/`safe_get_or_create_stock` (sin más uso en la vista).
- **5.3** — Mixins `SedeAutoAssignMixin` y `AuditedDestroyMixin` (`gestion/views/_common.py`)
  aplicados a los 6 ViewSets: `ChemicalViewSet` (solo create), `ProductoViewSet`,
  `ProveedorViewSet`, `BodegaViewSet`, `ClienteViewSet`, `FormulaColorViewSet`. Los 2 casos con
  kwargs extra al guardar (`FormulaColorViewSet.creado_por`,
  `ClienteViewSet.vendedor_asignado` condicional) usan el hook
  `get_perform_create_extra_kwargs()` en vez de sobreescribir `perform_create()` completo.
- **5.4** — `SedeResolvableMixin`/`get_audit_sede_id()` completado en los 10 modelos de
  `gestion/models/` que faltaban (`Producto`, `CostoLoteProduccion`, `FormulaColor`,
  `DetalleFormula`, `OrdenProduccion`, `ComponenteMezclaOP`, `ConsumoLoteDetalle`,
  `TransformacionProducto`, `MateriaPrimaLote`, `Cliente`, `PedidoVenta`) — mismo dato que ya
  calculaba el fallback de `_get_object_sede_id()`, salvo `ConsumoLoteDetalle` (no tenía ninguna
  rama que aplicara — antes devolvía `None` siempre; ahora resuelve via
  `lote_produccion.orden_produccion.sede_id`, un gap de auditoría real cerrado de paso). También
  se extendió a `inventory.models.StockBodega`/`MovimientoInventario` (fuera del alcance
  declarado "gestion/models/" de la spec, pero necesario — ver nota abajo).
  **`_get_object_sede_id()` NO se simplificó** como sugería la spec: se descubrió que
  `gestion/signals.py` usa la misma función para un sistema de auditoría paralelo basado en
  señales (`post_save`/`pre_delete`) que cubre 15 modelos que no usan `AuditableModelMixin`
  (`Sede`, `Area`, `Bodega`, `Maquina`, `CustomUser`, `PagoCliente`, `LoteProduccion`,
  `DetallePedido`, `Batch`, `Proveedor`, `ProcessStep`, `FaseReceta`, `HistorialDespacho`,
  `RequerimientoMaterial`, `OrdenCompraSugerida`) y por tanto no implementan (ni deben, fuera de
  alcance) el protocolo. Eliminar el fallback les habría roto `object_sede_id` en sus logs de
  auditoría — se dejó intacto y se corrigió el docstring para explicar por qué debe quedarse.
- **5.5** — `get_ultima_compra()` (duplicado byte a byte entre `ClienteListSerializer` y
  `ClienteSerializer`) extraído a `UltimaCompraMixin` en `gestion/serializers/sales_serializers.py`.
  `ClienteViewSet.get_queryset()` (`gestion/views/sales_views.py`) ya no salta el
  `prefetch_related` en `list` — el listado masivo tenía el mismo N+1 que el detalle.
- **5.6** — `LoteProduccion.objects.get(codigo_lote=code)` en el loop principal de
  `ProcessDespachoAPIView.post()` ahora usa el mismo `select_related` que ya tenía
  `_calcular_incompletos` para la misma consulta. El loop de `_calcular_incompletos` se reemplazó
  por un `filter(codigo_lote__in=...)` + diccionario de stocks, en vez de un `.get()` por código
  en un loop (`inventory/views/despacho_views.py`).
- **5.7** — `DATABASES['default']` (`ENGINE`/`NAME`/`USER`/`PASSWORD`/`HOST`/`PORT`/`driver`) y
  `INTERNAL_JWT_PRIVATE_KEY`/`INTERNAL_JWT_PUBLIC_KEY` en `TexCore/settings.py` ahora usan
  `get_env_variable()` (fail-fast), igual patrón que `SECRET_KEY`/`CORS_ALLOWED_ORIGINS`.
  **Riesgo real evitado:** `settings_test.py`/`settings_test_local.py` hacen
  `from TexCore.settings import *`, así que el fail-fast se ejecuta ANTES de que esos módulos
  puedan sobreescribir `DATABASES` — se verificó que `.env`/`.env.test` ya tienen todos los
  valores (local y CI, `ci.yml` los inyecta explícitamente), y se agregaron
  `os.environ.setdefault(...)` con valores ficticios para `DB_*` en `settings_test_local.py`
  (que corre contra SQLite y antes no necesitaba esas variables en absoluto).
- **5.8** — `INTERNAL_JWT_ACCESS_TTL_SECONDS`/`REFRESH_TTL_SECONDS` en `TexCore/settings.py` ahora
  leen de `os.environ.get(..., default)` en vez de ser constantes fijas.
- **5.9** — Bloque común (`PASSWORD_HASHERS`, `CELERY_TASK_ALWAYS_EAGER`, `LOGGING` de
  silenciamiento) extraído a `TexCore/settings_test_common.py`, importado por
  `settings_test.py` y `settings_test_local.py` después de definir su propio `DATABASES`.
- **5.10** — `IsInternalServiceOrUser` (`internal_api/views/pdf_produccion_views.py`) dividido:
  la mitad "servicio interno" ahora usa `IsInternalService & HasScope('reports:read')`
  (ya existían en `internal_api/permissions.py`), la mitad "usuario humano" quedó en
  `IsProductionReportRole` (nueva clase, antes era una rama inline del mismo método). Compuestas
  con `|`, mismo comportamiento, igual patrón que `reporting_views.py`.
- **5.12** — Comentario agregado a `HasScope.__call__(self): return self`
  (`internal_api/permissions.py`) explicando por qué existe (DRF llama cada permission_class
  instanciada; `HasScope` ya se usa pre-instanciada con el scope como argumento).
- **5.13** — `_verificar_alertas` (`gestion/services/descarga_quimicos.py`) ya no hace
  `Producto.objects.get()` por insumo dentro del loop de `descargar_para_op` — recibe
  `stock_minimo`/`producto_descripcion` ya resueltos, agregados a `ResultadoInsumo`
  (`gestion/services_formula.py`) en `DosificacionCalculator.calcular()`, que ya hacía
  `select_related('producto')` sobre los detalles.
- **5.14** — `gestion/services/costeo_service.py`: cuando `tarifa.tipo_contrato == 'pieza'`
  (costeo por pieza no implementado), ahora se deja un `logger.warning` explícito en vez de
  dejar `costo_operario=0` en silencio.

## Descartado tras investigación — NO se tocó

- **5.11** — La spec asumía que `resolve_sede_scope()` (`internal_api/views/reporting_views.py`)
  y `_resolve_sede_scope()` (`internal_api/views/pdf_produccion_views.py`) eran duplicados.
  Verificado: implementan políticas de aislamiento por sede **distintas** —
  `resolve_sede_scope` solo maneja el caso `ServicePrincipal` (claim de sede firmado vs. query
  param), asumiendo que el aislamiento de usuarios humanos ya lo impuso una capa anterior
  (`inventory/reporting_proxy.py`); `_resolve_sede_scope` maneja AMBOS casos directamente
  (`ServicePrincipal` Y roles de `CustomUser` — jefe_planta/jefe_area/admin_sede forzados a su
  sede, admin/superuser sin restricción). Forzar un merge en código de control de acceso
  multi-tenant sin poder correr la suite real (sin Docker local) era un riesgo de regresión de
  seguridad no justificado por el ahorro de líneas — se dejaron ambas funciones tal cual.

## Verificación de cierre

- `python manage.py check --settings=TexCore.settings_test` → **0 issues**.
- `python manage.py makemigrations --check --dry-run --settings=TexCore.settings_test_local` →
  **sin cambios** (los mixins agregados no tienen campos, no requieren migración).
- `python manage.py test gestion inventory internal_api --settings=TexCore.settings_test` →
  descubrimiento e importación de todos los módulos sin `ImportError`, falla solo al conectar a
  SQL Server real (bloqueo conocido, [[no-docker-local]]).
- `settings_test_local` (SQLite) no pudo usarse para correr tests reales — las migraciones tienen
  SQL crudo específico de SQL Server (`DECLARE @...`) incompatible con SQLite; esto es una
  limitación preexistente del repo, no algo introducido en esta sesión. Sí sirvió para confirmar
  que ningún mixin nuevo requiere migración.
- `graphify update .` corrido dos veces: al cierre de 5.2-5.14 (7586 nodos) y de nuevo tras 5.1
  (7620 nodos, 16694 edges, 471 comunidades).
- **Específico de 5.1:** `makemigrations --check --dry-run` → sin cambios (modelo y migración en
  sync). No se pudo aplicar `migrate` de punta a punta ni contra SQLite (`0002_fix_token_blacklist_mssql.py`,
  no tocada en esta sesión, tiene SQL crudo de SQL Server que bloquea SQLite antes de llegar a
  `0004`) ni contra SQL Server real (sin Docker local). Brandon debe correr `manage.py migrate`
  contra SQL Server real antes de mergear para confirmar que `0004` aplica limpio.

## [DECISIÓN REQUERIDA] resueltas tras conversación con Brandon (2026-09-02)

- **`ConsumoLoteDetalle` sin `bodega_id`/`producto_id` — CONFIRMADO Y CORREGIDO.** Brandon confirmó
  que el escenario es frecuente en operación real: "un lote nace desde que llega de materia prima
  y... se mantiene el mismo lote[,] entre áreas y entre bodegas... suele existir reprocesos" — es
  decir, no es un edge case teórico, un mismo `lote_origen` termina con stock en más de una bodega
  con regularidad.
  - `ConsumoLoteDetalle` (`gestion/models/produccion.py`) ganó 2 campos nuevos, `bodega`/`producto`
    (FK nullable — no se puede reconstruir con certeza el valor histórico de filas ya existentes).
  - Migración `gestion/migrations/0005_consumo_lote_detalle_bodega_producto.py` (`AddField` × 2,
    generada con `makemigrations`, sin migración de datos — no hay nada que backfillear con
    certeza).
  - `ConsumoMezclaService.consumir()` (`gestion/services/consumo_mezcla.py`) ya recibía
    `bodega_id`/`producto_id` en `consumos_data` (los usa para descontar el stock correcto) pero no
    los guardaba en `ConsumoLoteDetalle` — ahora sí.
  - `ConsumoMezclaService.revertir()`: cuando el `ConsumoLoteDetalle` tiene `bodega`/`producto`
    guardados, busca el `StockBodega` exacto por esos 3 campos (`bodega`, `producto`, `lote`) en
    vez de solo `lote`. Filas legacy (sin ese dato) caen al comportamiento anterior (best-effort,
    `.first()` en caso de `MultipleObjectsReturned`) — documentado en el código como tal, no
    silencioso.
  - 2 tests ISTQB nuevos en `gestion/tests/test_consumo_mezcla_service.py`
    (`ConsumoMezclaServiceRevertirMultiplesBodegas`): un lote con stock en 2 bodegas, se consume de
    una, se revierte — confirma que restaura la bodega correcta (no la primera que encuentra).
- **`registro_lote.py` — Brandon confirmó NO tocarlo** ("3 no lo toquemos"). Se deja tal cual,
  YAGNI.
- **`Batch` vs `MateriaPrimaLote` — sigue sin resolver**, Brandon no respondió sobre este punto
  todavía. Pendiente de que confirme si `Batch` sigue en uso real o se puede deprecar a favor de
  `MateriaPrimaLote`.

## Verificación de cierre — fix de ConsumoLoteDetalle

- `python -m py_compile` sobre los 4 archivos tocados → sin errores.
- `makemigrations --check --dry-run` (vía `settings_test_local`) → sin cambios (modelo y
  migración en sync).
- `manage.py check --settings=TexCore.settings_test` → 0 issues.
- `manage.py test gestion inventory internal_api --settings=TexCore.settings_test` → descubrimiento
  sin `ImportError` (incluidos los 2 tests nuevos), falla solo al conectar a SQL Server real
  (bloqueo conocido).
- `graphify update .` corrido (7628 nodos).
- Misma limitación que 0004: no se pudo aplicar `migrate` de punta a punta (ni SQLite por
  `0002_fix_token_blacklist_mssql.py`, ni SQL Server real sin Docker local). Brandon debe correr
  `manage.py migrate` antes de mergear.

Brandon revisa el diff y decide cómo commitear — Claude no ejecuta `git commit`/`push`.
