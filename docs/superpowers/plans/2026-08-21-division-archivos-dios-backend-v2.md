# Plan: dividir los 4 archivos "dios" del backend Django (v2 — revalidado contra el código actual)

> **EJECUTADO (2026-08-21).** Las 4 fases se implementaron y verificaron en este mismo entorno Docker.
> Resultado: 865/865 tests (baseline sin cambios), flake8 0 violaciones, `manage.py check` 0 issues.
> Ver la entrada correspondiente en `CHANGELOG.md` (21 de agosto de 2026) para el detalle completo.

## Contexto

El pull de hoy (commit `80ce637`) trajo, además de los fixes de impresión/escaneo, el documento
`docs/superpowers/plans/2026-08-19-division-archivos-dios-backend.md`: un plan en 4 fases para dividir
los 4 archivos monolíticos del backend. Ese plan **no se ejecutó** porque la máquina donde se escribió
no tenía SQL Server y ninguna fase podía verificarse con tests.

**Esa condición ya no aplica**: en esta sesión se levantó el stack Docker completo y se corrieron las
suites reales — backend 865/865, scanning 49/49, reporting 129/129, printing 67/67, frontend 994/994
(`tsc --noEmit` limpio). El plan es ejecutable ahora.

Pero al revalidarlo línea por línea contra el código actual aparecieron **5 errores que lo harían
fallar en ejecución**. Este documento es el plan corregido. Los 4 archivos siguen intactos:

| Archivo | Líneas | Símbolos | Consumidores |
|---|---|---|---|
| `gestion/views/production_views.py` | 1766 | 14 clases + 1 helper | 2 archivos |
| `inventory/views.py` | 1193 | **14** clases (el doc decía 13) | 3 archivos |
| `gestion/serializers.py` | 1457 | 49 serializers | 11 archivos |
| `gestion/models.py` | 1655 | 38 clases | **~91 archivos** |

El objetivo es puramente estructural: mover clases a archivos por dominio, cero cambios de
comportamiento, preservando cada import externo mediante capas de re-exportación.

---

## Correcciones al plan original (leer antes de ejecutar)

### C1 — Fase 1 rompe 7 tests que el plan no menciona
El plan afirma que la única referencia externa a `production_views.py` es el import de
`gestion/tests/test_production_views.py:27`, y que el fix de `inventory` es *"la única edición de
comportamiento de test necesaria en las 4 fases"*. **Falso.** Hay 7 `patch()` más en ese mismo archivo:

```
gestion/tests/test_production_views.py:260, 273, 281, 293, 302, 316, 329
    with patch('gestion.views.production_views.PrintingService.generate_label_pdf', ...)
```

`unittest.mock.patch` resuelve por módulo real, no por alias re-exportado. Al borrar
`production_views.py` los 7 fallan con `ModuleNotFoundError`. Deben pasar a
`gestion.views.production_lote_views.PrintingService` (donde vive `LoteProduccionViewSet`).
**Fase 1 = 8 ediciones en ese test, no 1.**

### C2 — La migración inicial SÍ depende de la ruta del módulo
El plan afirma que las migraciones no se ven afectadas. **Falso**:

```
gestion/migrations/0001_initial.py:7    import gestion.models
gestion/migrations/0001_initial.py:394  bases=(gestion.models.SedeResolvableMixin, models.Model),
```

`SedeResolvableMixin` **debe** seguir resolviendo como `gestion.models.SedeResolvableMixin`. El
`__init__.py` re-exportador lo cubre, pero es la migración inicial: si falla, no se puede crear la BD
de test y **CI muere entero**. Verificar explícitamente en Fase 4.

### C3 — El checklist de verificación no refleja lo que corre CI
El plan manda `pytest gestion/tests/...`. CI corre otra cosa (`.github/workflows/ci.yml:217-222`):

```
coverage run --rcfile=.coveragerc manage.py test gestion inventory internal_api --verbosity=2 --failfast
```

`setup.cfg` fija `testpaths = gestion/tests inventory/tests internal_api/tests`, así que **pytest local
NO colecta** 4 archivos que `manage.py test` sí colecta (viven sueltos en la raíz de la app):

| Archivo | Líneas | Importa de `gestion.models` |
|---|---|---|
| `gestion/tests_integrados.py` | 2472 | 14 modelos |
| `gestion/tests_jefe_area.py` | 109 | 7 modelos |
| `gestion/test_sede_filtering.py` | 90 | sí |
| `gestion/tests_cliente_improvements.py` | 70 | sí |

Verificar con pytest daría verde y CI rojo. **Todas las fases se verifican con `manage.py test`.**

### C4 — flake8 no ignora F401
CI corre `flake8 ... --extend-ignore=E203,W503` — **F401 no está ignorado**. Cada `__init__.py` de
re-exportación necesita `__all__` explícito (que es exactamente cómo `gestion/views/__init__.py:59-94`
lo resuelve hoy). Nunca `# noqa`, nunca `import *`.

### C5 — Los loggers tienen nombre hardcodeado
`production_views.py:54` es `logging.getLogger('gestion.views')` — **no `__name__`** — con 24 usos
repartidos entre 4 clases que irían a archivos distintos. Ídem `inventory/views.py:31` con
`'inventory.views'` y 15 usos. `TexCore/settings.py` declara loggers por nombre en `LOGGING`.
**Copiar la línea literal en cada archivo nuevo**; usar `__name__` cambia el comportamiento en runtime.

---

## Enfoque: re-exportación con `__all__` (patrón `gestion/views/`)

En el repo conviven dos patrones:
- **Patrón A** (`gestion/views/`): `__init__.py` re-exporta todo con `__all__` explícito. Los
  consumidores importan del paquete.
- **Patrón B** (`gestion/services/`, `internal_api/views/`): `__init__.py` vacío, import por ruta profunda.

Las 4 fases usan **Patrón A**, porque el radio de impacto (11 archivos para serializers, ~91 para
models, con 26 importando 5+ nombres de dominios mezclados) hace inviable editar cada consumidor.

Nota de contexto: `gestion/views/materia_prima_views.py` ya existe en el paquete pero **no** está en el
`__init__.py`; `gestion/urls.py:40` lo importa por ruta profunda. Es una inconsistencia preexistente —
no tocarla en este refactor.

---

## Fase 1 — `gestion/views/production_views.py` → 5 archivos + 1 común

La capa `gestion/views/__init__.py` ya existe; esta fase valida la mecánica sin crear nada nuevo.

**Archivos nuevos en `gestion/views/`:**
- `_common.py` → `parse_int_param()` (L57-74). Tiene **12 call-sites en 7 clases** repartidas por todo
  el archivo; obligatorio que viva aparte. No se re-exporta (nada externo lo usa).
- `production_maquina_views.py` → `MaquinaViewSet` (77-138), `ParoMaquinaViewSet` (141-174),
  `LineaProduccionViewSet` (177-232).
- `production_orden_views.py` → `StandardResultsSetPagination` (235-238), `OrdenProduccionViewSet` (241-679).
- `production_lote_views.py` → `LotesProduccionPagination` (682-695), `LoteProduccionViewSet` (698-1470),
  `RegistrarLoteProduccionView` (1523-1577).
- `production_componente_views.py` → `ComponenteMezclaOPViewSet` (1473-1502), `ConsumoLoteDetalleViewSet` (1505-1520).
- `production_subproceso_views.py` → `AreaProcessStepViewSet` (1580-1594),
  `OrdenProduccionSubprocesoViewSet` (1597-1697), `EtapaProduccionViewSet` (1700-1723),
  `TransferenciaInterareaViewSet` (1726-1766).

**Archivos a editar:**
- `gestion/views/__init__.py` — reemplazar el bloque `from .production_views import (...)` (L33-46)
  por 5 bloques. Mismos 12 nombres, `__all__` sin cambios.
- `gestion/tests/test_production_views.py` — **8 ediciones**: el import de L27 y los 7 `patch()` de C1.

**Cuidados específicos:**
- El trío ZPL (`_build_zpl_payload` 1129-1162, `_sanitize_zpl_field` 1164-1173, `_build_zpl_fallback`
  1175-1195) **se queda dentro de `LoteProduccionViewSet`**. `_build_zpl_fallback` es `@classmethod` y
  llama `cls._sanitize_zpl_field` 3 veces (L1178-1180); extraerlos a funciones libres rompería eso.
  Moverlos byte por byte — son el código corregido el 2026-08-19.
- Replicar `logger = logging.getLogger('gestion.views')` literal en los 5 archivos que lo usen (C5).
- `TexCore/settings.py:357` tiene un comentario que apunta a
  `# (gestion/views/production_views.py:_build_zpl_payload)` — actualizar la ruta.
- Los 4 imports diferidos dentro de métodos (L543, 574, 806, 808) duplican imports top-level ya
  existentes. **Moverlos tal cual, no "limpiarlos".**

**Sin cambios:** `gestion/urls.py` importa siempre del paquete. Borrar `production_views.py` al final.

---

## Fase 2 — `inventory/views.py` → 7 archivos (paquete nuevo)

`inventory/views/` **no existe** como directorio: hay que crear el paquete y borrar `views.py` en el
mismo commit (asimétrico respecto a la Fase 1, donde el paquete ya existía).

**Archivos nuevos en `inventory/views/`:**
- `stock_views.py` → `StockBodegaViewSet` (34-57), `AlertasStockAPIView` (719-758).
- `movimiento_views.py` → `MovimientoInventarioViewSet` (184-527) — la más grande, 344 líneas.
- `transferencia_views.py` → `TransferenciaStockAPIView` (530-605).
- `kardex_views.py` → `KardexBodegaAPIView` (608-716), `RetroKardexAPIView` (1005-1053),
  `MovimientosPorLoteAPIView` (1056-1088).
- `despacho_views.py` → `HistorialDespachoViewSet` (60-181), `ValidateLoteAPIView` (763-816),
  `ProcessDespachoAPIView` (819-1002).
- `audit_views.py` → `AuditLogPagination` (1091-1094), `AuditLogViewSet` (1097-1137).
- `mrp_views.py` → `RequerimientoMaterialViewSet` (1140-1152), `OrdenCompraSugeridaViewSet` (1155-1193).

**`inventory/views/__init__.py` nuevo** — estilo `gestion/views/__init__.py`, con `__all__` de los 13
nombres de vista (`AuditLogPagination` no hace falta, nada externo la usa).

**Ruptura obligatoria — el único caso donde el alias no salva:**
```
inventory/tests/test_views_extra.py:168
    with patch('inventory.views.MRPEngine'):   →   patch('inventory.views.mrp_views.MRPEngine')
```
Ojo: sin este fix el test **no falla, pasa a ser un no-op silencioso** (parchea el alias mientras
`ejecutar_mrp` sigue resolviendo el `MRPEngine` real). Es peor que un error: es cobertura fantasma.

**Cuidados:** `HistorialDespachoViewSet` usa `logging.error` directo en L139 y L177 (el resto usa
`logger`) → `despacho_views.py` necesita `import logging` **además** del logger. Replicar
`getLogger('inventory.views')` literal. Los 3 imports diferidos (L116, 161, 377) se mueven tal cual.

**Sin cambios:** `inventory/urls_scanning.py` (`from .views import ValidateLoteAPIView`) sigue
resolviendo por el `__init__.py`. `inventory/urls.py` puede quedarse con su bloque único. Ni
`transform_view.py` ni `reporting_proxy.py` pasan por `views.py` — no se tocan.

---

## Fase 3 — `gestion/serializers.py` → 9 archivos (paquete nuevo)

Verificado: el grafo de serializers anidados es un **DAG estricto de 14 aristas, ninguna cruza
dominio** → dividir por dominio no genera ciclos. Los 20 `SerializerMethodField` no instancian
serializers.

- `_common.py` → `ALPHANUMERIC_ACCENTS_REGEX` (L49). **Único símbolo que cruza dominios**: lo usan
  `AreaSerializer` (L139) y `CustomUserSerializer` (L310, L315) en core, y `LineaProduccionSerializer`
  (L248) en producción.
- `_reporting_serializers.py` → `MachineEfficiencySerializer` (21-26), `OperatorDesempenoSerializer`
  (29-36), `AreaEfficiencyReportSerializer` (39-46).
- `core_serializers.py` → `GroupSerializer`, `SedeSerializer`, `AreaSerializer`, `CustomUserSerializer`.
- `catalog_serializers.py` → `ProductoSerializer`, `ProveedorSerializer`.
- `inventory_serializers.py` → `BodegaSerializer`.
- `formula_serializers.py` → `BatchSerializer`, `ProcessStepSerializer`, `DetalleFormulaSerializer`,
  `DetalleFormulaEscrituraSerializer`, `FaseRecetaSerializer`, `FaseRecetaEscrituraSerializer`,
  `FormulaColorSerializer`, `FormulaColorWriteSerializer`, `DosificacionSerializer`.
- `sales_serializers.py` → `DetallePedidoSerializer`, `PedidoVentaResumenSerializer`,
  `PagoClienteSerializer`, `ClienteListSerializer`, `ClienteSerializer`, `PedidoVentaSerializer`,
  `AnulacionPedidoSerializer`, `ModificacionPedidoSerializer` + el helper `_fecha_pedido_to_iso_utc()`
  (52-69). El helper tiene sus 4 usos **dentro de este dominio** → se mueve entero, no va a `_common`.
- `materia_prima_serializers.py` → `MateriaPrimaLoteSerializer`, `RegistrarMateriaPrimaSerializer`,
  `ConsumoMateriaPrimaSerializer`.
- `production_serializers.py` → los 15 de producción + los 4 huérfanos del dominio
  (`DescargaQuimicoOPSerializer`, `StockQuimicoSerializer`, `RegistrarLoteSerializer`,
  `ConsumoInputSerializer`) + `CostoLoteProduccionSerializer`.

**Huérfanos**: los 7 serializers sin consumidor se mueven tal cual, sin borrarlos — mantiene el
refactor 100% mecánico. Limpieza de código muerto = cambio aparte.

**`gestion/serializers/__init__.py` nuevo** con `__all__` completo → **ningún consumidor se edita**
(11 archivos, todos dentro de `gestion/`). Ninguna app externa importa serializers de gestion.

**Cuidados:** preservar los 2 imports diferidos (`custom_jwt_views.py:42`,
`production_views.py:713`→ ahora `production_lote_views.py`) y el import diferido de modelo en L1086
(`from gestion.models import Cliente as ClienteModel`, con su comentario que explica el re-fetch por el
manager). `BodegaSerializer` (L79) depende de `related_name='usuarios_asignados'` definido en
`CustomUser` — acoplamiento invisible core↔inventario que sobrevive al split pero conviene conocer.

---

## Fase 4 — `gestion/models.py` → 8 archivos (paquete nuevo)

La fase de mayor consecuencia: **~91 archivos consumidores**, 26 de ellos importando 5+ nombres de
dominios mezclados (`seed_data.py:41` importa 26 nombres en una sola sentencia).

- `core.py` → `SedeResolvableMixin` (17-27), `_get_object_sede_id()` (30-82), `AuditLog` (85-114),
  `AuditableModelMixin` (117-247), `Sede`, `Area`, `CustomUser`.
  **Este bloque L17-247 es el núcleo inseparable**: la cadena
  `SedeResolvableMixin → _get_object_sede_id → AuditableModelMixin → AuditLog` sostiene 12 modelos de
  todos los dominios **y** `inventory/models.py:3`, que hereda de `AuditableModelMixin` desde otra app.
  Carga primero.
- `catalogo.py` → `Producto`, `Batch`, `Proveedor`, `Bodega`.
- `maquina.py` → `Maquina`, `ParoMaquina`, `LineaProduccion`, `ProcessStep`.
- `formula.py` → `FormulaColor`, `FaseReceta`, `DetalleFormula`.
- `ventas.py` → `ClienteManager`, `Cliente`, `PagoCliente`, `PedidoVenta`, `DetallePedido`.
- `produccion.py` → `OrdenProduccion`, `DescargaQuimicoOP`, `AreaProcessStep`,
  `OrdenProduccionSubproceso`, `LoteProduccion`, `EventoEtiqueta`, `ComponenteMezclaOP`,
  `ConsumoLoteDetalle`, `EtapaProduccion`, `TransferenciaInterarea`, `TransformacionProducto`.
- `trazabilidad.py` → `MateriaPrimaLote`, `ConsumoMateriaPrima`.
- `costeo.py` → `TarifaOperario`, `CostoHoraMaquina`, `CostoLoteProduccion`.

**Sin ciclos reales**: de 16 FKs por string solo 2 son forward-refs genuinas (`CustomUser.bodegas_asignadas
→ 'Bodega'` L275, `LoteProduccion.materias_primas → 'MateriaPrimaLote'` L1001). El único par
bidireccional cross-dominio (producción ↔ materia prima) ya está mitigado por string del lado de
`LoteProduccion`. Las 32 `class Meta:` **no declaran `app_label`** — Django lo infiere del paquete
padre, correcto mientras los submódulos se importen desde `gestion/models/__init__.py`.

**Los 3 puntos frágiles:**
1. `ClienteManager.get_queryset()` L643 hace `from .models import PedidoVenta, PagoCliente` — hoy es un
   **self-import benigno** (el módulo ya está en `sys.modules`). Tras el split se vuelve un import
   cross-módulo real (`ventas.py` → sí mismo). Como ambos targets quedan en `ventas.py`, se puede
   eliminar el diferido… **pero no hacerlo**: mantener el import diferido apuntando a `.ventas`
   preserva el comportamiento sin razonar sobre orden de carga.
2. `gestion/utils.py:64` — `PaymentReconciler.reconcile_client_orders()` con
   `from .models import PedidoVenta, PagoCliente` y el comentario *"para evitar dependencias
   circulares"*. Sigue funcionando por el `__init__.py`; verificar explícitamente.
3. `gestion/signals.py:10-13` importa `_get_object_sede_id` (**función privada**, necesita línea
   explícita en `__init__.py` — `import *` la ignoraría), registra `@receiver(sender=...)` con clases
   de modelo (L22, L84, L125), conecta 11 modelos más por bucle (L225-231), y llama
   `_register_inventory_signals()` **a nivel de módulo** (L236-243), que importa de `inventory.models`.
   `gestion/apps.py` lo dispara desde `ready()`. **Cualquier ciclo nuevo explota acá, en el arranque.**

**`gestion/models/__init__.py` nuevo** con `__all__` de las 38 clases + `_get_object_sede_id`.
**Ningún archivo consumidor se edita.**

**Verificar sí o sí en esta fase:** `AUTH_USER_MODEL = 'gestion.CustomUser'` (resuelve por app registry,
no por archivo) y el `bases=(gestion.models.SedeResolvableMixin, ...)` de la migración inicial (C2).
No se necesita ninguna migración nueva.

---

## Prácticas transversales

1. **Mover, no reescribir.** Extraer rangos exactos y pegar sin retipear (~115 clases en total).
   Los rangos de este documento son AST-exactos; el doc original tiene 8 off-by-1 en el límite superior
   (siempre incluyendo una línea en blanco de más — seguros para `sed`, nunca cortan código).
2. **Cero cambios de comportamiento.** Ningún fix, ninguna limpieza "ya que estoy acá", ningún renombre.
   Bugs detectados al mover → anotarlos aparte.
3. **Imports absolutos** (`from gestion.models import X`), como ya hacen `gestion/services/` y `gestion/views/`.
4. **`__all__` explícito** en cada `__init__.py` (C4). Nunca `import *`.
5. **Loggers literales**, nunca `__name__` (C5).
6. **Una fase = un commit**, revertible por separado. El hook `conventional-pre-commit` exige prefijo →
   `refactor(gestion): ...`. **Los commits los hace el usuario, no el agente.**
7. **Borrar el archivo viejo solo al final de cada fase.**
8. Al ejecutar, **actualizar `docs/superpowers/plans/2026-08-19-division-archivos-dios-backend.md`** con
   estas correcciones y **agregar entrada en `CHANGELOG.md`** (fecha, fases, resultado de tests).

---

## Verificación por fase

**Sin base de datos:**
1. `python -m py_compile` en cada archivo nuevo/editado.
2. `flake8 gestion/ inventory/ TexCore/ internal_api/ --max-line-length=120 --extend-ignore=E203,W503 --exclude=*/migrations/* --statistics --count` → **0 violaciones** (flags exactos de CI; F401 es el riesgo real).
3. `git diff --stat` → solo los archivos esperados.
4. `git diff` de cada archivo **existente** tocado → el único cambio debe ser el bloque de imports.
5. Grep de que no quede referencia al archivo viejo en todo el repo.

**Con el stack Docker levantado** (`docker-compose -f infrastructure/docker/docker-compose.yml`):
1. `docker-compose ... exec -T backend python manage.py check` → 0 issues.
2. **Tests con el runner de Django, no pytest** (C3), replicando CI:
   - Fase 1: `python manage.py test gestion --settings=TexCore.settings_test --keepdb`
   - Fase 2: `python manage.py test inventory --settings=TexCore.settings_test --keepdb`
   - Fase 3: `python manage.py test gestion --settings=TexCore.settings_test --keepdb`
   - Fase 4: `python manage.py test gestion inventory internal_api --settings=TexCore.settings_test --keepdb`
   
   Baseline conocido de esta sesión: **865 tests, OK, ~49s**. Cualquier número distinto de 865 es una
   señal (tests que dejaron de colectarse).
3. **Arranque real de la app** sin errores de import — el chequeo más importante de la Fase 4: una
   cadena de modelos rota falla en `AppConfig.ready()` antes de correr un solo test.
4. Solo con todo en verde, seguir a la fase siguiente.

**Riesgo residual conocido:** `.coveragerc` fija `fail_under = 89` (no bloqueante en CI, sí visible).
El refactor no debería mover cobertura, pero un archivo nuevo sin ejercitar la bajaría.
