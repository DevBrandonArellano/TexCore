# Barrido de Higiene — Fase 2: Código Muerto Confirmado

> **Estado: COMPLETA (2026-09-02), sin commitear.** Ejecutada por implementación directa en sesión
> (no subagent-driven-development — riesgo bajo, son eliminaciones sin cambio de comportamiento, no
> ameritan el overhead de revisión adversarial que sí se usó en Fase 1 para los fixes de seguridad).

**Origen:** `docs/superpowers/specs/2026-09-01-backend-hygiene-sweep-design.md`, sección "Fase 2 —
Código muerto confirmado" (11 ítems).

**Proceso seguido por ítem** (igual al que pide la spec): `graphify explain "<símbolo>"` para ver
conexiones entrantes → si graphify no indexaba el símbolo (constantes de clase) o la conexión era
ambigua, `grep` cruzado de todo el repo (incluyendo scripts `.sh`, docs, `TexCore/celery.py`) → leer
el archivo real para confirmar el contexto exacto → eliminar → si el símbolo tenía un test dedicado,
eliminar/ajustar ese test también (no estaba explícito en la spec para todos los ítems, pero dejar un
test que falle en import por un símbolo borrado no es aceptable).

## Ítems eliminados

| # | Cambio | Archivo(s) | Verificación |
|---|---|---|---|
| 2.1 | Clase `OptionalPagination` — sin `pagination_class` en ningún ViewSet, sin uso en frontend | `gestion/pagination.py` (archivo completo, era su único contenido) | `graphify explain` mostró como único consumidor su propio test dedicado (`OptionalPaginationTestCase`). Se eliminó también `gestion/tests/test_pagination.py` completo (solo testeaba esta clase). Grep confirmó cero imports del módulo `gestion.pagination` en el resto del repo. |
| 2.2 | Comando `verificar_auditoria` — duplica `create_admin.py --verificar` | `gestion/management/commands/verificar_auditoria.py` (archivo completo) | Comparación línea por línea: el `handle()` de este comando es idéntico byte a byte al método `_verificar_auditoria()` que ya vive en `create_admin.py` (Fase 1.1). Grep en docs/scripts/CI no encontró ningún caller que invoque `manage.py verificar_auditoria`. |
| 2.3 | `get_serializer_class()` de `OrdenProduccionViewSet` — las 3 ramas retornan lo mismo | `gestion/views/production_orden_views.py:46-51` | Lectura directa: las 3 ramas (`create`, `completar_detalles`, default) retornan `OrdenProduccionSerializer`, idéntico al `serializer_class` ya declarado a nivel de clase (línea 37). El override es un no-op — se eliminó completo. |
| 2.4 | `ProcessStepSerializer` duplicado | `gestion/serializers/production_serializers.py:509-512` (clase completa + import `ProcessStep` que quedaba sin uso) | `gestion/serializers/__init__.py` importa `ProcessStepSerializer` solo desde `formula_serializers` (línea 19-21), nunca desde `production_serializers`. `gestion/views/formula_views.py` usa la versión de `formula_serializers` como `serializer_class` de un ViewSet real. La copia de `production_serializers.py` no tenía ningún importador. |
| 2.5 | Comando `seed_service_credentials` — reemplazado por `register_services` | `internal_api/management/commands/seed_service_credentials.py` (archivo completo) | `infrastructure/docker/entrypoint.sh:33` solo llama `python manage.py register_services` (existe en `gestion/management/commands/register_services.py`). Grep confirmó que nada más invoca `seed_service_credentials`. |
| 2.6 | `run_mrp()` + constantes `CONVERSION_BANOS_FUNDAS`/`CONVERSION_FUNDAS_CONOS` sin uso (se mantiene `CONVERSION_BANOS_CONOS`, es la única realmente consumida — línea `banos_necesarios = cantidad_pedida / self.CONVERSION_BANOS_CONOS`) | `inventory/services/mrp_engine.py` | `graphify explain "run_mrp"` mostró cero llamadores externos (solo se contiene a sí misma). Grep de `CONVERSION_BANOS_FUNDAS`/`CONVERSION_FUNDAS_CONOS` en todo el repo: cero resultados fuera de su propia definición. |
| 2.7 | `KardexSerializer` completo — la vista arma dicts planos en su lugar | `inventory/serializers.py:85-123` | `graphify explain` + grep: cero importadores en `inventory/views/` ni en ningún otro archivo. Import de `MovimientoInventario` en ese archivo sigue en uso por otros 2 serializers, no se tocó. |
| 2.8 | Loggers instanciados sin uso (re-verificado tras Fase 1.3 — el fix de scoping de `kardex_views.py` no terminó necesitando logging ahí) | `inventory/views/stock_views.py`, `inventory/views/kardex_views.py` (+ `import logging` en ambos, ya sin otro uso) | Grep de `logger` en cada archivo: solo la línea de instanciación, ningún `logger.info/warning/error` en el resto del archivo. |
| 2.9 | `getattr` fallback a campos legacy `producto`/`bodega` en `registrar_lote()` — `OrdenProduccion` nunca tuvo esos campos, solo `producto_entrada`/`producto_salida`/`bodega_entrada`/`bodega_salida` | `gestion/services/registro_lote.py` | Lectura directa de la definición de `OrdenProduccion` (`gestion/models/produccion.py:12-85`): no existe `producto`, `producto_id` ni `bodega` como campo propio. El fallback `or getattr(orden, 'producto', None)` nunca se activaba. Simplificado a acceso directo a los campos FK (ya son nullable, `orden.producto_entrada` retorna `None` igual que el `getattr` fallido). |
| 2.10 | `run_mrp_calculation` completa — sin beat schedule, sin caller salvo su propio test, docstring no coincide con el comportamiento real | `gestion/tasks.py` (función completa) + `gestion/tests/test_tasks.py` (clase `RunMrpCalculationTestCase`, import, línea de docstring) | `graphify explain` mostró como único importador `test_tasks.py`. Grep en `TexCore/celery.py`: sin `beat_schedule` ni referencia a `run_mrp_calculation`/`run_mrp`. |
| 2.11 | Rama muerta `hasattr(obj, 'formula')` en `_get_object_sede_id()` | `gestion/models/core.py:65-66` | Se listaron los 12 modelos que usan `AuditableModelMixin` (grep) y se leyó cada `models.py` relevante: el único campo `formula` del proyecto vive en `FaseReceta` (`gestion/models/formula.py:68`), que **no** hereda `AuditableModelMixin` — nunca llega a esta función. `DetalleFormula` (que sí audita) tiene `fase`, ya cubierto por la rama anterior (línea 56-58, `obj.fase.formula`). Esto además desbloquea la Fase 5.4 del plan general, que dependía explícitamente de este ítem. |

## Verificación de cierre

- `python manage.py check --settings=TexCore.settings_test` → **0 issues**.
- `python manage.py test gestion.tests inventory.tests internal_api --settings=TexCore.settings_test` → descubrimiento e importación de **todos** los módulos de test (incluidos los editados) completó sin `ImportError`; falló recién al intentar conectar a SQL Server real (`django.db.utils.InterfaceError: Data source name not found`) — el mismo bloqueo conocido de siempre en esta máquina ([[no-docker-local]]), no un error introducido por estos cambios. Suite completa pendiente de que Brandon la corra con Docker/SQL Server real.
- `graphify update .` corrido al cierre de la fase.
- Sin cambios de comportamiento — solo eliminación de código confirmado sin uso; no se agregaron tests nuevos (no aplica TDD red/green a una eliminación pura), pero sí se depuraron los tests que solo existían para cubrir el código eliminado (Fase 2.1, 2.10).
- Brandon revisa el diff y decide si commitea como un solo commit o lo separa por ítem — Claude no ejecuta `git commit`/`push`.
