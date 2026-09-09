# Barrido de Higiene y Endurecimiento — Backend Django

**Fecha:** 2026-09-01
**Alcance:** `gestion/`, `inventory/`, `internal_api/`, `TexCore/` (más 2 docs de microservicios ya detectados de paso: `docs/arquitectura/MICROSERVICIOS.md`, `reporting_excel/README.md`)
**Origen:** diagnóstico de 5 agentes de solo lectura (gestion-core, gestion-api, gestion-tests, inventory, internal_api+TexCore) sobre HEAD `cfb5212` en `feature`, cada hallazgo verificado con `graphify` + grep cruzado contra todo el repo antes de reportarse. 3 casos dudosos ("posibles") se investigaron aparte: 2 confirmados como código muerto, 1 (`TransicionBodegaService`) descartado — es lógica de negocio real, no se toca.

## 1. Objetivo

Eliminar código muerto, corregir comentarios/docstrings y documentación desactualizados, cerrar los hallazgos de seguridad y aplicar las mejoras arquitectónicas (SOLID/DRY) que salieron del diagnóstico — sin tocar nada fuera de lo encontrado y verificado.

## 2. Principios guía

- **Clean Code**: nombres que expliquen intención, funciones con una responsabilidad, comentarios solo para el "por qué" no obvio (nunca el "qué").
- **SOLID** (ya exigido por `CLAUDE.md`): SRP para los god-objects encontrados, DRY para las duplicaciones, DIP donde un service importa detalles que debería recibir inyectados.
- **ISO/IEC 25010** (mantenibilidad) e **ISO 27001** (el proyecto ya cita A.12.4/A.9.4/A.10 en `reporting_excel/README.md`) — los fixes de seguridad de la Fase 1 se enmarcan en A.9 (control de acceso) y A.9.4 (gestión de acceso a aplicaciones).
- **ISTQB + TDD** (`CLAUDE.md`): todo fix de *comportamiento* (no solo housekeeping) lleva un test `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]` que falla antes del fix y pasa después.
- **Verificación con graphify antes de tocar algo**: para cada eliminación/refactor, `graphify query "<símbolo>"` / `graphify explain "<símbolo>"` (o `graphify path` si hay que confirmar que dos nodos no quedan huérfanos) antes de editar, para no romper referencias que el grep pudo no capturar (imports dinámicos, `apps.get_model`, señales). `graphify update .` al cerrar cada fase.
- **YAGNI**: si un hallazgo de "mejora" requiere una decisión de producto/datos (no solo de código), se deja marcado como **[DECISIÓN REQUERIDA]** en vez de implementarse a ciegas.
- Cada fase = un commit independiente y revertible (mismo criterio que `docs/superpowers/plans/2026-08-19-division-archivos-dios-backend.md`). Brandon revisa y commitea — Claude no hace `git commit`/`push`.

## 3. Fuera de alcance

- `TransicionBodegaService` (`inventory/services/transicion_bodega_service.py`) — no es código muerto, es lógica de negocio ya probada (7 tests, ✅ en `docs/matriz_trazabilidad_pruebas.md`) pendiente solo de exponerse vía endpoint. No se toca.
- Los 3 microservicios FastAPI y el frontend, salvo los 2 docs ya mencionados arriba.
- `migrations/` no se edita a mano (solo se generan nuevas migraciones donde el plan lo indique explícitamente).
- Los 2 scripts de deploy en conflicto (`scripts/deploy/deploy_prod.sh` vs `scripts/deploy_production.sh`/`.ps1`) — es una decisión de infraestructura/proceso, no de código de aplicación. Se corrige `create_admin.py` en sí (Fase 1.1) pero **cuál script usar en producción queda como [DECISIÓN REQUERIDA] para Brandon**, fuera de este plan.

## 4. Fases

### Fase 1 — Seguridad (bajo riesgo estructural, alto impacto)

| # | Cambio | Archivo | Test nuevo/actualizado |
|---|---|---|---|
| 1.1 | Quitar credenciales hardcodeadas; generar password segura igual que `seed_production_masters.py:40-64` (`secrets.token_urlsafe` o `DJANGO_SUPERUSER_PASSWORD`) | `gestion/management/commands/create_admin.py:20-22` | Test que falle si el comando produce una contraseña estática/predecible |
| 1.2 | `get_permissions()` por acción (create/update/destroy → vendedor/admin; list/retrieve → autenticado), mismo patrón que `ProductoViewSet`/`BodegaViewSet` | `gestion/views/sales_views.py` (`ClienteViewSet`, `PedidoVentaViewSet`, `DetallePedidoViewSet`) | Operario recibe 403 en create/update/destroy; vendedor/admin 201/200 |
| 1.3 | Scoping por bodega/sede, mismo patrón que `StockBodegaViewSet`/`KardexBodegaAPIView` (`IsInventoryStaffOrAdmin`) | `inventory/views/kardex_views.py` (`RetroKardexAPIView`, `MovimientosPorLoteAPIView`) | Usuario de sede A no ve kardex de bodega de sede B |
| 1.4 | `except Exception as e:` → `logger.error(...)` real (el comentario actual dice "loguear" pero no loguea) | `inventory/views/transferencia_views.py:85-89` | Forzar excepción, verificar que queda registrada |
| 1.5 | `@transaction.atomic` + `select_for_update()` sobre la orden/lote padre, mismo patrón que `PagoClienteViewSet.perform_create` | `gestion/views/production_subproceso_views.py` (iniciar/completar/rechazar/pausar) y `gestion/models/produccion.py` `generate_next_lote_codigo` | Test de lock adquirido (mock `select_for_update`); si el test runner lo permite, test de condición de carrera con 2 transacciones |

### Fase 2 — Código muerto confirmado

Por cada ítem: `graphify explain "<símbolo>"` → confirmar 0 referencias reales → eliminar → correr tests del módulo afectado.

1. `gestion/pagination.py` — `OptionalPagination` (sin `pagination_class` en ningún ViewSet, sin uso en frontend)
2. `gestion/management/commands/verificar_auditoria.py` — archivo completo (duplica `create_admin.py --verificar`)
3. `gestion/views/production_orden_views.py:46-51` — `get_serializer_class()` (retorna lo mismo en las 3 ramas; quitar el override completo, no solo el cuerpo)
4. `gestion/serializers/production_serializers.py:509-512` — `ProcessStepSerializer` duplicado (no importado por nadie; se mantiene solo el de `formula_serializers.py`)
5. `internal_api/management/commands/seed_service_credentials.py` — archivo completo (reemplazado por `register_services`, `entrypoint.sh` ya no lo llama)
6. `inventory/services/mrp_engine.py` — función `run_mrp()` + constantes `CONVERSION_BANOS_FUNDAS`/`CONVERSION_FUNDAS_CONOS` (**ojo**: no tocar `CONVERSION_BANOS_CONOS`, esa se resuelve en Fase 5.1, no se borra)
7. `inventory/serializers.py:85-123` — `KardexSerializer` completo (la vista arma dicts planos)
8. `inventory/views/stock_views.py:13`, `inventory/views/kardex_views.py:15` — loggers instanciados sin uso (verificar de nuevo tras Fase 1.3, por si el fix de scoping termina necesitando logging ahí; si no, eliminar)
9. `gestion/services/registro_lote.py:58,63-64` — `getattr` fallback a campos legacy `producto`/`bodega` (ya no existen en `OrdenProduccion`)
10. `gestion/tasks.py` — `run_mrp_calculation` completa (sin beat schedule en `TexCore/celery.py`, sin caller salvo su propio test, y el docstring miente sobre qué hace — confirmado en la investigación de seguimiento)
11. `gestion/models/core.py:65-66` — rama `hasattr(obj, 'formula')` en `_get_object_sede_id()` (confirmado: ningún modelo con `AuditableModelMixin` tiene atributo `formula` directo)

### Fase 3 — Comentarios/docstrings desactualizados

1. `gestion/models/produccion.py:113` — docstring de `DescargaQuimicoOP` dice "inmutable post-creación"; corregir para describir el ciclo de vida real (`aplicada`/`revertida` vía `revertir_descarga_op`)
2. `gestion/services/pago_reversion.py:71` — comentario describe un algoritmo ("iterar pagos posteriores") que no es el implementado (`saldo + monto`); corregir para reflejar el cálculo real
3. `gestion/serializers/production_serializers.py:341-359` — quitar el monólogo de razonamiento del desarrollador, dejar (si aplica) un comentario de una línea con el motivo real de la validación
4. `gestion/views/production_lote_views.py:364` — el comentario dice que `bodega_salida` "ya no se usa"; sí se usa en líneas 384-401 — corregir o quitar el comentario
5. `gestion/views/production_orden_views.py:47-50` — comentarios sobre serializers distintos por rol que ya no existen (se resuelve junto con la eliminación de Fase 2.3)
6. `gestion/tests_integrados.py:591-623` — docstring de `test_empaquetado_consumo_insumos_v2` promete una verificación removida en la Fase 3 del proyecto (nota: este archivo se reorganiza más a fondo en Fase 6; aquí solo se corrige el docstring si el test sobrevive esa reorganización)
7. `inventory/models.py:6-9,44-48` — docstring de `StockBodega`/`MovimientoInventario` ubicado *después* de `campos_auditables`, por lo que Python no lo reconoce como `__doc__`; mover a la primera sentencia de la clase

### Fase 4 — Documentación (`docs/`)

1. `docs/requerimientos/PLAN_PRUEBAS.md` — actualizar referencias `archivo:línea` de `models.py`/`views.py`/`serializers.py` monolíticos (ya no existen desde el God Files Split del 24-ago) a las rutas de paquete actuales; actualizar cifra de cobertura (documenta 379 tests, hay 694+ solo en el alcance auditado)
2. `docs/matriz_trazabilidad_pruebas.md` — agregar trazabilidad para los tests que sobrevivan la reorganización de Fase 6 (secuenciar **después** de Fase 6 para no documentar un estado intermedio)
3. `docs/arquitectura/COMANDOS_OPERACION.md:87` — corregir la afirmación falsa de que los roles RBAC "se crean automáticamente"; documentar que requiere `setup_permissions`/`seed_production_masters` explícito
4. `docs/arquitectura/ARQUITECTURA_SISTEMA.md` (~línea 595) — corregir la tabla que lista a `reporting_excel` como poseedor de `INTERNAL_JWT_PUBLIC_KEY`, contradice la línea 374 del mismo doc que ya documenta que ya no aplica
5. `docs/arquitectura-bd/DICCIONARIO_ELIMINACION.md` — corregir `on_delete` documentados: `Producto→OrdenProduccion` es `PROTECT` (no `SET_NULL`); `FormulaColor→OrdenProduccion` es `CASCADE` (no "SET_NULL u opcional"); corregir el script SQL de la sección "segura" que asume `SET_NULL` sobre una FK `CASCADE` real (es potencialmente destructivo tal como está); agregar `FaseReceta` como entidad intermedia CASCADE entre `FormulaColor` y `DetalleFormula`
6. `docs/arquitectura-bd/MODELO_DATOS.md` — corregir descripción de `saldo_pendiente` (suma TODOS los pedidos no anulados, no solo los no pagados); corregir numeración de secciones duplicada (dos "## 4.", dos "## 5.")
7. `docs/arquitectura/MICROSERVICIOS.md` — corregir nota que dice que los routers viejos de `reporting_excel` "quedaron intactos"; el commit `cfb5212` ya los eliminó
8. `reporting_excel/README.md` — corregir sección "Autenticación con Backend" (describe el flujo JWT viejo contra Django que ya no aplica) y el ejemplo de "Patrón SOLID en los Routers" (usa `/kardex`, router ya eliminado; reemplazar por un ejemplo real de `routers/generate.py`)

### Fase 5 — Mejoras arquitectónicas (SOLID/DRY)

| # | Cambio | Alcance | Nota |
|---|---|---|---|
| 5.1 | Nuevo modelo de configuración de equivalencias de empaque por sede (p. ej. `ConfiguracionEmpaqueSede`: baño→fundas, fundas→conos), con migración de datos que precarga los valores actuales (225/15/1) como default por sede existente. `inventory/services/mrp_engine.py` y `gestion/models/produccion.py` (`LoteProduccion.clean()`) leen de ahí en vez de hardcodear. | `inventory/`, `gestion/models/` | Requerido explícitamente por `CLAUDE.md` ("configurable reference examples per sede, not system-wide hardcoded constants"). Es el cambio de mayor tamaño del plan — incluye migración nueva. |
| 5.2 | Extraer `_ajustar_stock_por_cambio_peso` y la reversión manual de stock en `rechazar()` a un `LoteStockAdjustmentService`, siguiendo el patrón ya usado en `kpi_views.py` (vista solo hace parseo HTTP, service hace el trabajo) | `gestion/views/production_lote_views.py` (949 líneas → reduce sustancialmente) | SRP |
| 5.3 | Mixins `SedeAutoAssignMixin` (auto-asignar sede en `perform_create`) y `AuditedDestroyMixin` (justificación de auditoría en `perform_destroy`), aplicados a los 6 ViewSets que hoy duplican esa lógica | `ChemicalViewSet`, `ProductoViewSet`, `ProveedorViewSet`, `BodegaViewSet`, `ClienteViewSet`, `FormulaColorViewSet` | DRY |
| 5.4 | Completar la adopción de `SedeResolvableMixin`/`get_audit_sede_id()` en los 10 modelos con `AuditableModelMixin` que aún no lo implementan (hoy solo `ParoMaquina` lo hace); una vez completo, simplificar `_get_object_sede_id()` a solo el camino del protocolo | `gestion/models/` | Depende de Fase 2.11 (ya se quitó la rama muerta) |
| 5.5 | Extraer `get_ultima_compra()` duplicado de `ClienteListSerializer`/`ClienteSerializer` a un mixin/método compartido; agregar `prefetch_related` en el queryset de listado masivo | `gestion/serializers/sales_serializers.py` | Corrige N+1 documentado en el propio docstring del serializer |
| 5.6 | `select_related` en el loop principal de `ProcessDespachoAPIView.post()` (falta, existe en `_calcular_incompletos` para la misma consulta); reemplazar el loop de `_calcular_incompletos` por un solo `filter(codigo_lote__in=...)` | `inventory/views/despacho_views.py` | N+1 en flujo de escritura real |
| 5.7 | `get_env_variable()` (fail-fast) para `DATABASES['default']` e `INTERNAL_JWT_PRIVATE_KEY`/`INTERNAL_JWT_PUBLIC_KEY`, igual patrón que `SECRET_KEY`/`CORS_ALLOWED_ORIGINS` | `TexCore/settings.py` | Falla clara al arrancar en vez de `InvalidKeyError` críptico en runtime |
| 5.8 | `INTERNAL_JWT_ACCESS_TTL_SECONDS`/`REFRESH_TTL_SECONDS` → `os.environ.get(..., default)` en vez de constantes fijas | `TexCore/settings.py:340-341` | Consistencia con el resto de parámetros operacionales del archivo |
| 5.9 | Extraer bloque común (`PASSWORD_HASHERS`, `CELERY_TASK_ALWAYS_EAGER`, `LOGGING` de silenciamiento) a un módulo base compartido | `TexCore/settings_test.py`, `TexCore/settings_test_local.py` | DRY |
| 5.10 | Dividir `IsInternalServiceOrUser` en permisos componibles (`IsInternalService \| (IsAuthenticated & ...)`), igual patrón que `reporting_views.py` | `internal_api/views/pdf_produccion_views.py:86-110` | ISP/SRP |
| 5.11 | Extraer `resolve_sede_scope()`/`_resolve_sede_scope()` duplicados a un helper compartido | `internal_api/views/reporting_views.py`, `internal_api/views/pdf_produccion_views.py` | DRY |
| 5.12 | Comentario explicando el porqué del patrón `__call__(self): return self` (no rediseñar, está testeado y funciona) | `internal_api/permissions.py:23-33` (`HasScope`) | Solo clarificación, cero cambio de comportamiento |
| 5.13 | `_verificar_alertas`: agregar `stock_minimo` a `ResultadoInsumo` al construirlo, evitar `Producto.objects.get()` por insumo en el loop | `gestion/services/descarga_quimicos.py:222-244` | N+1 menor |
| 5.14 | Log de advertencia explícito cuando `tipo_contrato='pieza'` retorna costo 0 (hoy es silencioso) | `gestion/services/costeo_service.py:68` | Evita que un costo 0 se lea como "correcto" |

**[DECISIÓN REQUERIDA — no se implementan sin confirmación de Brandon]:**
- `ConsumoLoteDetalle` no guarda `bodega_id`/`producto_id` del stock consumido → `revertir()` puede restaurar a la bodega incorrecta si el lote origen tiene stock en más de una bodega (`gestion/services/consumo_mezcla.py:105-143`). Corregirlo implica una migración de esquema — **queda fuera de este plan hasta que Brandon confirme la prioridad**.
- `Batch` (marcado legacy) vs `MateriaPrimaLote` coexistiendo sin relación (`gestion/models/catalogo.py`) — decisión de deprecación/consolidación de producto, no solo de código — **queda fuera de este plan**.
- `registro_lote.py` (`RegistroLoteService.registrar_lote()`, 215 líneas) — ya delega a 3 services; dado que funciona y no hay una violación SRP tan clara como en `production_lote_views.py`, **no se toca en este plan** (YAGNI) salvo que Brandon pida lo contrario.

### Fase 6 — Limpieza de tests de `gestion/`

1. Eliminar/reescribir los 2 tests sin asserts reales en `gestion/tests_integrados.py` (`test_seguridad_permisos_operario`, `test_unauthenticated_access`) — o se les agregan los asserts que faltan, o se eliminan si ya están cubiertos correctamente en otro archivo
2. Resolver la duplicación entre `gestion/tests_integrados.py` y los archivos ISTQB-compliant de `gestion/tests/` (fórmulas, descarga de químicos) — conservar la versión con nombre ISTQB correcto, eliminar el duplicado
3. `gestion/tests_cliente_improvements.py` y `gestion/test_sede_filtering.py` — mover/renombrar a `gestion/tests/` con convención ISTQB y factories, en vez de quedar sueltos en la raíz
4. Tras 1-3, actualizar `docs/matriz_trazabilidad_pruebas.md` (Fase 4.2)

## 5. Verificación global (todas las fases)

- `pytest gestion/ inventory/ internal_api/` o `python manage.py test --settings=TexCore.settings_test` tras cada fase — **si no es posible correrlo sin Docker/SQL Server real en esta máquina, se deja el comando exacto listo para que Brandon lo corra** (ya sabemos que no hay Docker local disponible aquí).
- `cd frontend && npx tsc --noEmit` solo si Fase 1.2/1.3 cambia contratos de API que el frontend consuma (verificar primero si el frontend ya maneja 403 en esos endpoints).
- `graphify update .` al cerrar cada fase.
- Brandon revisa el diff y commitea cada fase por separado — Claude no ejecuta `git commit`/`push`.

## 6. Orden de ejecución recomendado

Fase 1 (seguridad) → Fase 2 (código muerto) → Fase 6 (tests) → Fase 3 (comentarios) → Fase 4 (docs, depende de que Fase 6 ya haya cerrado) → Fase 5 (mejoras arquitectónicas, la de mayor tamaño y riesgo, al final y con checkpoints por sub-ítem).
