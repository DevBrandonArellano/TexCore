# Plan: dividir los 4 archivos "dios" del backend Django

> **SUPERSEDIDO (2026-08-21).** Este plan fue revalidado línea por línea contra el código actual y se
> encontraron 5 errores que lo harían fallar en ejecución (tests rotos no contemplados, dependencia real
> de la migración inicial, checklist de verificación que no coincide con lo que corre CI, F401 de flake8
> y loggers hardcodeados). Usar en su lugar:
> [`2026-08-21-division-archivos-dios-backend-v2.md`](2026-08-21-division-archivos-dios-backend-v2.md).

## Contexto

La auditoría de deuda técnica de esta sesión identificó 4 archivos monolíticos en el backend que concentran demasiadas responsabilidades en un solo módulo, a diferencia de `gestion/services/` (ya dividido en 12 archivos enfocados por dominio) y de `gestion/views/` (ya es un *paquete* con 8 archivos por dominio — solo uno de ellos, `production_views.py`, sigue siendo un archivo gigante dentro de ese paquete):

| Archivo | Líneas | Clases |
|---|---|---|
| `gestion/views/production_views.py` | 1766 | 12 ViewSets/APIViews + 2 paginadores + 1 helper |
| `inventory/views.py` | 1193 | 13 vistas + 1 paginador |
| `gestion/serializers.py` | 1457 | 49 serializers |
| `gestion/models.py` | 1655 | 38 modelos/mixins/managers |

Son el punto de fricción de merge más frecuente del repo (casi todo commit de producción del CHANGELOG toca `production_views.py`) y dificultan ubicar/revisar cambios. Este plan es **puramente estructural**: mover clases a archivos por dominio sin cambiar ningún comportamiento, preservando cada import externo intacto mediante capas de re-exportación.

**Este documento es solo el plan.** Por decisión explícita del usuario, no se ejecutó en la sesión donde se escribió (2026-08-19) — el entorno local no tenía SQL Server, así que ningún test de Django podía correrse ni verificarse ahí. La ejecución debe hacerse en una máquina/entorno con el stack completo disponible (Docker + SQL Server), de modo que cada fase pueda verificarse de verdad con `pytest` antes de continuar a la siguiente. **Al ejecutar este plan, agregar una entrada en `CHANGELOG.md`** documentando la fecha, el alcance (qué fase/es) y los resultados de los tests corridos.

## Decisiones ya confirmadas con el usuario

- **Ritmo de ejecución**: **fase por fase, con pausa**: correr los tests de esa fase, confirmar verde, y solo entonces seguir con la siguiente.
- **Serializers huérfanos** (7 clases sin ninguna referencia fuera de `serializers.py`: `MachineEfficiencySerializer`, `OperatorDesempenoSerializer`, `AreaEfficiencyReportSerializer`, `DescargaQuimicoOPSerializer`, `StockQuimicoSerializer`, `RegistrarLoteSerializer`, `ConsumoInputSerializer`): **se mueven tal cual**, sin borrarlas — mantiene el refactor 100% mecánico. Limpieza de código muerto queda para un cambio aparte.

## Enfoque: capa de re-exportación por paquete

Dos convenciones ya conviven en este repo:
- **`gestion/services/`** (bajo radio de impacto — cada consumidor importa 1-3 nombres): `__init__.py` vacío, cada consumidor importa directo del submódulo (`from gestion.services.pago_reversion import PagoReversionService`).
- **`gestion/views/`** (alto radio de impacto): `gestion/views/__init__.py` reexporta *todo* con `__all__` explícito; `gestion/urls.py` importa siempre desde el paquete, nunca de un submódulo — así fue posible confirmar que **ningún archivo externo a `gestion/views/` referencia `production_views.py` directamente**, salvo un único `import` en un test.

Dado que `serializers.py` (13 archivos consumidores) y sobre todo `models.py` (**86 archivos consumidores confirmados**, muchos con imports masivos multi-dominio en una sola sentencia) tienen un radio de impacto mucho más parecido al de `views/` que al de `services/`, este plan usa **re-exportación tipo `views/`** para los 4 archivos: se crea (o, en el caso de `production_views.py`, se reutiliza) un `__init__.py` que reexporta cada nombre bajo su ruta actual, de modo que `from gestion.models import X` / `from gestion.serializers import X` / `from gestion.views import X` / `from inventory.views import X` sigan funcionando sin tocar la inmensa mayoría de los archivos que los usan.

## Orden de fases y motivo

1. **`gestion/views/production_views.py`** — la capa de reexportación (`gestion/views/__init__.py`) **ya existe**; esta fase valida la mecánica del split sin crear nada nuevo, con el radio de impacto más chico (2 archivos).
2. **`inventory/views.py`** — introduce la única pieza nueva (crear un `__init__.py` de reexportación desde cero) sobre un archivo todavía manejable, antes de aplicarlo al archivo grande.
3. **`gestion/serializers.py`** — depende de `models.py` (nunca al revés), así que conviene dividirlo antes que `models.py` para no tener un refactor de serializers a medio camino cuando se toque `models.py`.
4. **`gestion/models.py`** — el de mayor radio de impacto (86 archivos) y el más fundacional (`AUTH_USER_MODEL`, todas las FKs); se deja al final para apoyarse en las 3 fases ya probadas y verificadas.

Cada fase es un commit independiente y revertible por sí solo.

---

## Fase 1 — `gestion/views/production_views.py` (1766 líneas → 5 archivos + 1 común)

### Catálogo actual (validado línea por línea)
| Clase | Líneas | Dominio | Serializers que usa |
|---|---|---|---|
| `parse_int_param()` | 57-74 | *helper compartido* — usado por 7 de las 12 clases | — |
| `MaquinaViewSet` | 77-139 | Máquina/Línea | `MaquinaSerializer` |
| `ParoMaquinaViewSet` | 141-175 | Máquina/Línea | `ParoMaquinaSerializer` |
| `LineaProduccionViewSet` | 177-232 | Máquina/Línea | `LineaProduccionSerializer` |
| `StandardResultsSetPagination` | 235-239 | *solo usado por OrdenProduccionViewSet* | — |
| `OrdenProduccionViewSet` | 241-680 | OrdenProduccion | `OrdenProduccionSerializer`, `OrdenProduccionEstadoSerializer`, `TransformacionProductoSerializer` |
| `LotesProduccionPagination` | 682-696 | *solo usado por LoteProduccionViewSet* | — |
| `LoteProduccionViewSet` | 698-1470 | **LoteProduccion (~770 líneas, la más grande)** — contiene `_build_zpl_payload`, `_build_zpl_fallback`, `_sanitize_zpl_field` y la referencia a `settings.PRINTING_SERVICE_URL` corregidos el 2026-08-19 | `LoteProduccionSerializer`, `CostoLoteProduccionSerializer` (import local dentro de `obtener_costo`, **preservar tal cual**) |
| `ComponenteMezclaOPViewSet` | 1473-1502 | ComponenteMezclaOP | `ComponenteMezclaOPSerializer` |
| `ConsumoLoteDetalleViewSet` | 1505-1520 | ConsumoLoteDetalle | `ConsumoLoteDetalleSerializer` |
| `RegistrarLoteProduccionView` | 1523-1577 | Puente OrdenProduccion→LoteProduccion | `RegistrarLoteProduccionSerializer`, `LoteProduccionSerializer` |
| `AreaProcessStepViewSet` | 1580-1594 | AreaProcessStep | `AreaProcessStepSerializer` |
| `OrdenProduccionSubprocesoViewSet` | 1597-1698 | Subproceso (máquina de estados) | `OrdenProduccionSubprocesoSerializer` |
| `EtapaProduccionViewSet` | 1700-1724 | EtapaProduccion | `EtapaProduccionSerializer` |
| `TransferenciaInterareaViewSet` | 1726-1766 | TransferenciaInterarea | `TransferenciaInterareaSerializer` |

### Archivos nuevos a crear (todos en `gestion/views/`)
- `_common.py` — `parse_int_param()`.
- `production_maquina_views.py` — `MaquinaViewSet`, `ParoMaquinaViewSet`, `LineaProduccionViewSet`.
- `production_orden_views.py` — `StandardResultsSetPagination`, `OrdenProduccionViewSet`.
- `production_lote_views.py` — `LotesProduccionPagination`, `LoteProduccionViewSet`, `RegistrarLoteProduccionView`.
- `production_componente_views.py` — `ComponenteMezclaOPViewSet`, `ConsumoLoteDetalleViewSet`.
- `production_subproceso_views.py` — `AreaProcessStepViewSet`, `OrdenProduccionSubprocesoViewSet`, `EtapaProduccionViewSet`, `TransferenciaInterareaViewSet`.

### Archivos existentes a editar
- `gestion/views/__init__.py` — reemplazar el bloque `from .production_views import (...)` (líneas 33-46) por 5 bloques apuntando a los archivos nuevos. Mismos 12 nombres, mismo `__all__` — sin cambios ahí.
- `gestion/tests/test_production_views.py` (única referencia externa directa) — la línea `from gestion.views.production_views import LoteProduccionViewSet` pasa a `from gestion.views.production_lote_views import LoteProduccionViewSet`.

### Sin cambios necesarios
- `gestion/urls.py` — importa todo desde el paquete `gestion.views`, nunca de `production_views` directamente. **Cero cambios, ningún `basename`/path en riesgo.**
- El resto de tests (`test_lineas_produccion.py`, `test_paro_maquina.py`, `test_orden_produccion_estados.py`, `test_production_views_extra.py`, y todas las clases de test dentro de `test_production_views.py`) usan `reverse()`/`APIClient`, no importan clases de vista.
- Eliminar `production_views.py` al final de la fase, una vez confirmado que ninguna referencia queda pendiente.

---

## Fase 2 — `inventory/views.py` (1193 líneas → 7 archivos, paquete nuevo)

### Catálogo actual
| Clase | Líneas | Dominio | Nota |
|---|---|---|---|
| `StockBodegaViewSet` | 34-57 | Stock | |
| `HistorialDespachoViewSet` | 60-181 | Despacho | usa `DespachoReversionService` (ya en `inventory/services/`) |
| `MovimientoInventarioViewSet` | 184-527 | **Movimientos/Kardex (~344 líneas, la más grande)** | `select_for_update()` en `create()`/`update()`, cada uno autocontenido dentro de su propio `transaction.atomic()` — seguro mover la clase completa |
| `TransferenciaStockAPIView` | 530-605 | Transferencias | mismo patrón `select_for_update()` autocontenido |
| `KardexBodegaAPIView` | 608-716 | Kardex (lectura) | |
| `AlertasStockAPIView` | 719-758 | Stock | |
| `ValidateLoteAPIView` | 763-816 | Despacho | también referenciada por `inventory/urls_scanning.py` |
| `ProcessDespachoAPIView` | 819-1003 | Despacho | mismo patrón `select_for_update()` autocontenido |
| `RetroKardexAPIView` | 1005-1053 | Kardex | |
| `MovimientosPorLoteAPIView` | 1056-1088 | Kardex/trazabilidad | |
| `AuditLogPagination` | 1091-1094 | *solo usado por AuditLogViewSet* | |
| `AuditLogViewSet` | 1097-1137 | Auditoría | usa `AuditLog` de `gestion.models` |
| `RequerimientoMaterialViewSet` | 1140-1152 | MRP | |
| `OrdenCompraSugeridaViewSet` | 1155-1193 | MRP | usa `MRPEngine` — ver ruptura obligatoria abajo |

`inventory/reporting_proxy.py` y `inventory/transform_view.py` **ya están fuera de `views.py`** — no se tocan.

### Archivos nuevos a crear (todos en `inventory/views/`)
- `stock_views.py` — `StockBodegaViewSet`, `AlertasStockAPIView`.
- `movimiento_views.py` — `MovimientoInventarioViewSet`.
- `transferencia_views.py` — `TransferenciaStockAPIView`.
- `kardex_views.py` — `KardexBodegaAPIView`, `RetroKardexAPIView`, `MovimientosPorLoteAPIView`.
- `despacho_views.py` — `HistorialDespachoViewSet`, `ValidateLoteAPIView`, `ProcessDespachoAPIView`.
- `audit_views.py` — `AuditLogPagination`, `AuditLogViewSet`.
- `mrp_views.py` — `RequerimientoMaterialViewSet`, `OrdenCompraSugeridaViewSet`.

### `__init__.py` nuevo (no existe hoy)
`inventory/views/__init__.py` — mismo estilo que `gestion/views/__init__.py`: un bloque de import por submódulo + `__all__` con los 13 nombres de vista (no hace falta reexportar `AuditLogPagination`, nada externo la usa).

### Archivos existentes a editar
- `inventory/urls.py` — su único bloque `from .views import (...)` (12 nombres) pasa a 7 bloques por submódulo. Ningún `basename`/path cambia.
- `inventory/urls_scanning.py` — su `from .views import ValidateLoteAPIView` sigue funcionando sin editar, gracias al `__init__.py` de reexportación (verificar igual tras el cambio).

### Ruptura conocida y obligatoria — un archivo de test
`inventory/tests/test_views_extra.py:168` — `with patch('inventory.views.MRPEngine'):`. `unittest.mock.patch` resuelve el nombre en el módulo donde se usa en tiempo de ejecución, no en un alias reexportado. Debe cambiar a:
```python
with patch('inventory.views.mrp_views.MRPEngine'):
```
**Esta es la única edición de comportamiento de test necesaria en las 4 fases — señalarla explícitamente en el commit/PR.**

### Sin cambios necesarios
`inventory/serializers.py` (264 líneas, 12 clases, ya bien organizado) — queda fuera de este refactor. Los 21 archivos de test de `inventory/tests/` usan `reverse()`/`APIClient`, salvo el caso de arriba.

---

## Fase 3 — `gestion/serializers.py` (1457 líneas → 7 archivos + 1 común, paquete nuevo)

### Agrupación por dominio (validada contra el archivo actual)
- `_common.py` — `ALPHANUMERIC_ACCENTS_REGEX` (línea 49; usada por `AreaSerializer` y `CustomUserSerializer` en Core, y por `LineaProduccionSerializer` en Máquina/Línea — cruza dominios).
- `production_serializers.py` — todo el dominio Producción, espejo de la Fase 1: `MaquinaSerializer`, `ParoMaquinaSerializer`, `LineaProduccionSerializer`, `OrdenProduccionEstadoSerializer`, `OrdenProduccionSerializer`, `TransformacionProductoSerializer`, `ComponenteMezclaOPSerializer`, `LoteProduccionSerializer`, `RegistrarLoteProduccionSerializer`, `CostoLoteProduccionSerializer`, `ConsumoLoteDetalleSerializer`, `AreaProcessStepSerializer`, `OrdenProduccionSubprocesoSerializer`, `EtapaProduccionSerializer`, `TransferenciaInterareaSerializer` — **más los 4 huérfanos de este dominio**, movidos tal cual: `DescargaQuimicoOPSerializer`, `StockQuimicoSerializer`, `RegistrarLoteSerializer`, `ConsumoInputSerializer`. (15+4 = 19 clases; revisar si conviene sub-dividir solo si crece más allá de ~500-600 líneas — no dividir preventivamente.)
- `_reporting_serializers.py` — los 3 huérfanos restantes, movidos tal cual: `MachineEfficiencySerializer`, `OperatorDesempenoSerializer`, `AreaEfficiencyReportSerializer` (líneas 21-46; forman su propio mini-dominio de "reporte de eficiencia", separarlos de `production_serializers.py` evita mezclarlos con clases sí usadas).
- `catalog_serializers.py` — `ProductoSerializer`, `ProveedorSerializer`.
- `core_serializers.py` — `GroupSerializer`, `SedeSerializer`, `AreaSerializer`, `CustomUserSerializer`.
- `inventory_serializers.py` — `BodegaSerializer`.
- `formula_serializers.py` — `BatchSerializer`, `ProcessStepSerializer`, `DetalleFormulaSerializer`, `DetalleFormulaEscrituraSerializer`, `FaseRecetaSerializer`, `FaseRecetaEscrituraSerializer`, `FormulaColorSerializer`, `FormulaColorWriteSerializer`, `DosificacionSerializer`.
- `sales_serializers.py` — `DetallePedidoSerializer`, `PedidoVentaResumenSerializer`, `PagoClienteSerializer`, `ClienteListSerializer`, `ClienteSerializer`, `PedidoVentaSerializer`, `AnulacionPedidoSerializer`, `ModificacionPedidoSerializer`, más el helper `_fecha_pedido_to_iso_utc()` (líneas 52-69, usado solo en este dominio — se mueve entero, sin extraer a `_common.py`).
- `materia_prima_serializers.py` — `MateriaPrimaLoteSerializer`, `RegistrarMateriaPrimaSerializer`, `ConsumoMateriaPrimaSerializer`.

### `__init__.py` nuevo (no existe hoy)
`gestion/serializers/__init__.py` — un bloque de import por cada uno de los 9 archivos de arriba + `__all__` completo. Con esta capa, **ningún consumidor externo necesita editarse**: `gestion/views/production_*_views.py` (Fase 1), `sales_views.py`, `core_views.py` (incluida su única fuga cruzada de dominio: importa `LoteProduccionSerializer` para un dashboard), `formula_views.py`, `catalog_views.py`, `inventory_views.py`, `materia_prima_views.py`, `gestion/profile_views.py`, `gestion/custom_jwt_views.py` (import local dentro de una función), `gestion/tests/test_serializers.py`, `gestion/tests/test_serializers_extra.py` — los 12 archivos confirmados que hacen `from gestion.serializers import ...` / `from .serializers import ...` siguen funcionando sin tocar una línea.

### Sin cambios necesarios
Ningún archivo consumidor requiere edición gracias a la reexportación. Eliminar `gestion/serializers.py` al final de la fase.

---

## Fase 4 — `gestion/models.py` (1655 líneas → 7 archivos, paquete nuevo)

### Agrupación por dominio (validada, sin ciclos de FK reales)
- `core.py` — `SedeResolvableMixin`, `_get_object_sede_id()`, `AuditLog`, `AuditableModelMixin` (base abstracta de la que heredan 11 modelos de otros dominios — debe cargar primero), `Sede`, `Area`, `CustomUser`.
- `catalogo.py` — `Producto`, `Batch`, `Proveedor`, `Bodega`.
- `maquina.py` — `Maquina`, `ParoMaquina`, `LineaProduccion`, `ProcessStep`.
- `formula.py` — `FormulaColor`, `FaseReceta`, `DetalleFormula`.
- `ventas.py` — `ClienteManager`, `Cliente`, `PagoCliente`, `PedidoVenta`, `DetallePedido`.
- `produccion.py` — `OrdenProduccion`, `DescargaQuimicoOP`, `AreaProcessStep`, `OrdenProduccionSubproceso`, `LoteProduccion`, `ComponenteMezclaOP`, `ConsumoLoteDetalle`, `EtapaProduccion`, `TransferenciaInterarea`, `TransformacionProducto` (el dominio más grande — espejo de la Fase 1/3).
- `trazabilidad.py` — `EventoEtiqueta`, `MateriaPrimaLote`, `ConsumoMateriaPrima`.
- `costeo.py` — `TarifaOperario`, `CostoHoraMaquina`, `CostoLoteProduccion`.

**Sin riesgo de ciclos**: ningún par de modelos tiene FK/M2M bidireccional directa. El archivo ya usa referencias de FK como string (`'MateriaPrimaLote'`, `through='ConsumoMateriaPrima'`, e incluso cross-app: `inventory/models.py` ya usa `'gestion.PedidoVenta'` sin ciclo alguno hoy) — este mecanismo funciona igual entre archivos separados dentro del mismo app, sin necesidad de import Python real en la declaración del campo.

**Dos precedentes de import diferido ya existen en el código y deben preservarse tal cual al mover, no "arreglarse":**
1. `ClienteManager.get_queryset()` (dentro de `gestion/models.py`) — `from .models import PedidoVenta, PagoCliente`, porque esas clases están definidas más abajo en el archivo actual. Al dividir, se convierte en `from .ventas import PedidoVenta, PagoCliente` (o vía el paquete) dentro de `ventas.py`.
2. `PaymentReconciler.reconcile_client_orders()` (en `gestion/utils.py`) — `from .models import PedidoVenta, PagoCliente`, con el comentario explícito "Importaciones locales para evitar dependencias circulares". Con el `__init__.py` de reexportación esto sigue funcionando sin editar, pero merece verificación explícita post-split ya que es el segundo (y único otro) punto del repo con este patrón.

### `__init__.py` nuevo (no existe hoy)
`gestion/models/__init__.py` — un bloque de import por cada uno de los 7 archivos (orden: `core` primero, ya que `AuditableModelMixin` es la base compartida — no es un requisito técnico de Django, solo legibilidad) + `__all__` con las 38 clases/función/manager. **Importante**: `_get_object_sede_id` es una función con guion bajo — necesita una línea de import explícita en `__init__.py` (no un `import *`, que ignora nombres con guion bajo por convención).

### Archivos existentes a editar
**Ninguno**, gracias a la reexportación — confirmado por búsqueda exhaustiva: 83 archivos con `from gestion.models import ...` + 3 con `from .models import ...` (`gestion/admin.py`, `gestion/serializers/*` ya migrado en Fase 3, `gestion/signals.py`) siguen resolviendo sin cambios. `gestion/utils.py` también resuelve sin cambios (import diferido dentro de una función, ver arriba).

### Verificación específica de esta fase (la más sensible)
- `TexCore/settings.py`: `AUTH_USER_MODEL = 'gestion.CustomUser'` — Django resuelve esto por `app_label.ModelName` vía el registro de apps, no por ruta de archivo. **No requiere cambio**, pero es el punto de mayor consecuencia: si algo sale mal aquí, la aplicación completa no arranca.
- Migraciones (`gestion/migrations/0001_initial.py`, `0002_fix_token_blacklist_mssql.py`, ya consolidadas) — referencian modelos por `app_label.ModelName` congelado en su estado, no por archivo. **No se necesita ninguna migración nueva.**
- Recomendación: ejecutar esta fase con la suite completa (`gestion/`, `inventory/`, `internal_api/`) corrida al final, no un subconjunto — es la fase que sostiene a todas las demás.

---

## Prácticas transversales (aplican a las 4 fases)

1. **Mover, no reescribir.** Extraer rangos de línea exactos y pegarlos sin retipear, para eliminar riesgo de transcripción en ~110 clases combinadas.
2. **Cero cambios de comportamiento.** Ningún fix, ninguna limpieza "ya que estoy aquí", ningún renombre. Si se detecta un bug o mejora durante el movimiento, anotarlo aparte — no corregirlo en este refactor.
3. **Preservar docstrings, comentarios y decoradores exactos.** En particular, todo el código de `LoteProduccionViewSet` tocado el 2026-08-19 (`_build_zpl_payload`, `_build_zpl_fallback`, `_sanitize_zpl_field`, referencia a `settings.PRINTING_SERVICE_URL`) debe moverse byte-por-byte idéntico.
4. **Imports absolutos** (`from gestion.models import X`), nunca relativos con `..`, igual que ya hace `gestion/services/` y `gestion/views/`.
5. **Un commit por fase.** Permite revertir cualquier fase sin tocar las otras 3.
6. **Borrar el archivo viejo solo al final de cada fase**, una vez el `__init__.py` nuevo está completo y no queda ninguna referencia colgante al archivo plano original.

## Checklist de verificación por fase

**Auto-verificable sin base de datos (puede correr cualquier agente, incluso sin el stack completo):**
1. `python -m py_compile` en cada archivo nuevo/editado de la fase.
2. `flake8 gestion/ inventory/ TexCore/ internal_api/ --max-line-length=120 --extend-ignore=E203,W503 --exclude=*/migrations/*` (flags exactos de `.github/workflows/ci.yml`) — debe dar 0 violaciones.
3. `git diff --stat` — confirmar que solo aparecen los archivos nuevos esperados + el `__init__.py` + los archivos de import listados arriba, nada más.
4. `git diff` completo de cada archivo *existente* tocado (no los nuevos) — confirmar que el único cambio es el bloque de imports, cero cambios en cuerpos de función/clase.
5. Grep de que no quede ninguna referencia al archivo viejo eliminado en todo el repo (fuera de este plan y el historial de git).

**Requiere el stack completo (Docker + SQL Server):**
1. `python manage.py check`.
2. Los tests de la fase específica:
   - Fase 1: `pytest gestion/tests/test_production_views.py gestion/tests/test_production_views_extra.py gestion/tests/test_lineas_produccion.py gestion/tests/test_paro_maquina.py gestion/tests/test_orden_produccion_estados.py`
   - Fase 2: `pytest inventory/tests/` completo (atención especial a `test_mrp.py` y `test_views_extra.py` por el fix del `MRPEngine`)
   - Fase 3: `pytest gestion/tests/test_serializers.py gestion/tests/test_serializers_extra.py` + `pytest gestion/` completo (los serializers se ejercitan indirectamente en casi todos los tests de vistas)
   - Fase 4: `pytest gestion/ inventory/ internal_api/` completo — la fase que sostiene todo lo demás
3. Arranque real de la app (`python manage.py runserver` o equivalente) sin errores de import — el chequeo más importante de la Fase 4 en particular, ya que una cadena de imports de modelos rota falla en el arranque, antes de correr un solo test.
4. Solo tras confirmar todo lo anterior en verde, continuar con la siguiente fase.
5. **Agregar entrada en `CHANGELOG.md`** con fecha, fase(s) ejecutada(s) y resultado de los tests.

## Archivos críticos de referencia para la implementación

- `gestion/views/__init__.py` — el patrón de reexportación exacto a replicar en las otras 3 capas nuevas.
- `gestion/views/production_views.py` — fuente de la Fase 1.
- `inventory/urls.py` / `inventory/urls_scanning.py` — los dos puntos de import que obligan a crear `inventory/views/__init__.py` en la Fase 2.
- `inventory/tests/test_views_extra.py:168` — el único fix de test obligatorio de todo el plan.
- `gestion/serializers.py` — fuente de la Fase 3, incluye `ALPHANUMERIC_ACCENTS_REGEX` y los 7 serializers huérfanos.
- `gestion/models.py` — fuente de la Fase 4, incluye `AuditableModelMixin` y el precedente de `ClienteManager`.
- `gestion/utils.py` (`PaymentReconciler.reconcile_client_orders`) — segundo precedente de import diferido, a preservar en la Fase 4.
