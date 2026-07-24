# Auditoría y Corrección RBAC — Roles Bodeguero / Despacho (módulo `inventory/`)

**Fecha:** 2026-07-22 (última actualización: 2026-07-22)
**Versión:** 1.1
**Autor:** Claude Code (Sonnet 5 / Opus 4.8)

> **Corrección a la v1.0:** la sección "Verificación" de la v1.0 afirmaba que los 19 fallos de la
> suite local eran "todos pre-existentes y confirmados no relacionados" con este cambio. Esa
> afirmación era **incorrecta para 6 de los 19** — no se investigó su causa raíz a fondo en su
> momento, solo se asumió que eran "artefactos del harness sqlite" por costumbre de sesiones
> anteriores. Al investigarlos con traceback real (ver "Corrección de los 19 fallos" más abajo),
> resultaron ser **bugs reales de producción**, reproducibles en MSSQL, ya corregidos en esta
> versión. Los otros 13 sí eran de entorno/configuración, también corregidos.

---

## Resumen Ejecutivo

Se auditó el código de los roles **Bodeguero** (`bodeguero`) y **Despacho** (`despacho`) con la
misma metodología usada para el rol Jefe de Área: lectura línea por línea de `inventory/views.py`,
`inventory/permissions.py`, `TexCore/settings.py` y los tests existentes, comparando contra
prácticas de control de acceso (RBAC / OWASP A01 Broken Access Control, segregación de funciones).

A diferencia de la auditoría de Jefe de Área (brechas frente a un estándar aspiracional), aquí se
encontraron **4 defectos de control de acceso reales y explotables** en el módulo `inventory/`, ya
corregidos con TDD:

- ✅ **Fix 1** — `MovimientoInventarioViewSet` solo exigía `IsAuthenticated`: cualquier rol
  autenticado (vendedor, tintorero, etc.) podía crear/listar/editar/eliminar movimientos de
  inventario de cualquier bodega/sede. Se añadió `IsInventoryWriterOrAdmin` (nueva clase) para
  escritura, se reutilizó `IsInventoryStaffOrAdmin` para lectura, y se añadió aislamiento por sede
  en `get_queryset()` (mismo patrón que `StockBodegaViewSet`).
- ✅ **Fix 2** — `TransferenciaStockAPIView` y `KardexBodegaAPIView` no declaraban
  `permission_classes`; como `REST_FRAMEWORK` no define `DEFAULT_PERMISSION_CLASSES`, ambos
  endpoints eran alcanzables **sin autenticación** (`AllowAny` por defecto de DRF). Se añadieron
  permisos explícitos.
- ✅ **Fix 3** — `HistorialDespachoViewSet.destroy()` heredaba `IsDespachoReader` (incluye
  `ejecutivo`) mientras la acción equivalente `revertir` exigía `IsDespachoWriter` (excluye
  `ejecutivo` a propósito) — mismo efecto de negocio, dos niveles de permiso distintos. Se unificó
  vía `get_permissions()`.
- ✅ **Fix 4** — Se amplió `inventory/tests/test_roles_rbac.py::RBACMatrixTestCase` para cubrir los
  3 endpoints anteriores (antes solo cubría `historial-despachos`, `stock`, `process-despacho`).

Los hallazgos de menor severidad (regresión funcional de `AJUSTE`/`MERMA`, `500` no controlado en
`DELETE` de `MovimientoInventario`, reversión de despacho no granular, KPIs superficiales en
`BodegueroDashboard`) quedan documentados como trabajo futuro (ver más abajo).

---

## Fundamento (RBAC / control de acceso)

- **Segregación de funciones (Segregation of Duties):** quien registra un movimiento de inventario
  no debería tener el mismo nivel de acceso que un rol sin relación con bodega (ventas, tintorería,
  producción). Principio de mínimo privilegio.
- **OWASP A01 — Broken Access Control:** endpoints sin control de rol o sin autenticación son la
  categoría de vulnerabilidad web más común según el OWASP Top 10. `MovimientoInventarioViewSet`
  (control de rol ausente) y `TransferenciaStockAPIView`/`KardexBodegaAPIView` (autenticación
  ausente) son instancias directas de esta categoría.
- **Maker-checker / cuatro ojos:** revertir una transacción ya "cerrada" (un despacho) debería
  requerir un permiso distinto — y más restrictivo — que el de solo consulta. `destroy()` vs.
  `revertir` violaba esto al converger en un permiso más laxo para la misma operación destructiva.

---

## Estado del código antes de la corrección (confirmado línea por línea)

| Endpoint | Vista | Permiso antes | Problema |
|---|---|---|---|
| `GET/POST/PATCH/DELETE /inventory/movimientos/` | `MovimientoInventarioViewSet` | `IsAuthenticated` | Cualquier rol autenticado escribe/lee cualquier bodega/sede |
| `POST /inventory/transferencias/` | `TransferenciaStockAPIView` | *(ninguno declarado)* | `AllowAny` de facto — sin login |
| `GET /inventory/bodegas/{id}/kardex/` | `KardexBodegaAPIView` | *(ninguno declarado)* | `AllowAny` de facto — sin login |
| `DELETE /inventory/historial-despachos/{id}/` | `HistorialDespachoViewSet.destroy` | `IsDespachoReader` (heredado) | Incluye `ejecutivo`, que `revertir` excluye a propósito |

**Verificación previa relevante:** se confirmó por `Grep` en `frontend/src/` que ningún dashboard
activo depende de un rol distinto a los ya previstos para estos endpoints — el único otro llamador
de `/inventory/movimientos/` (`frontend/src/components/operario/InventoryForm.tsx`) no está
importado por ningún dashboard (solo por su propio test), es decir, es código muerto. Restringir
estos endpoints a los grupos ya establecidos no rompe ningún flujo real de la aplicación.

---

## Corrección implementada

### `inventory/permissions.py`
Nueva clase `IsInventoryWriterOrAdmin`: permite `bodeguero`, `jefe_area`, `jefe_planta`,
`admin_sede`, `admin_sistemas` — el mismo conjunto que ya exigía el chequeo manual (ahora
eliminado) dentro de `MovimientoInventarioViewSet.update()`.

### `inventory/views.py`
- `MovimientoInventarioViewSet`: `get_permissions()` — `list`/`retrieve`/`auditoria` usan
  `IsInventoryStaffOrAdmin` (lectura amplia, excluye solo operario raso, igual que
  `StockBodegaViewSet`); `create`/`update`/`partial_update`/`destroy` usan
  `IsInventoryWriterOrAdmin`. `get_queryset()` ahora filtra por
  `bodega_origen__sede=user.sede` / `bodega_destino__sede=user.sede` para roles no-admin/ejecutivo.
- `TransferenciaStockAPIView.permission_classes = [IsInventoryWriterOrAdmin]`.
- `KardexBodegaAPIView.permission_classes = [IsInventoryStaffOrAdmin]`.
- `HistorialDespachoViewSet.get_permissions()` — `destroy` usa `IsDespachoWriter`; el resto usa
  `IsDespachoReader`.

### Tests (TDD — RED confirmado antes de cada fix, GREEN después)
- `inventory/tests/test_movimiento_views.py::MovimientoRbacTestCase` (nuevo): `vendedor`/
  `operario` denegados, `bodeguero` funcional, aislamiento por sede.
- `inventory/tests/test_views_endpoints.py`: casos `401`/`403` para `TransferenciaStockAPIView` y
  `KardexBodegaAPIView`.
- `inventory/tests/test_despacho_reversion.py::DespachReversionAPITestCase`: `ejecutivo` →
  `DELETE` → `403`.
- `inventory/tests/test_roles_rbac.py::RBACMatrixTestCase`: matriz extendida a `movimientos/`
  (list y create), `transferencias/`, `bodegas/{id}/kardex/`, más los 3 nuevos endpoints en
  `test_unauthenticated_access`.

### Verificación (v1.0)
- `inventory/` completo: sin regresiones en los tests que ya pasaban.
- Al momento de la v1.0, la suite `gestion/`+`inventory/` tenía 19 fallos, que se documentaron
  (incorrectamente, ver corrección arriba) como "todos pre-existentes y no relacionados". La
  investigación real de esos 19 fallos y su corrección se documenta en la siguiente sección.

---

## Corrección de los 19 fallos (v1.1)

Se investigó cada uno de los 19 fallos con traceback real (no conjetura), agrupados por causa raíz:

| Grupo | # | Causa raíz confirmada | Tipo |
|---|---|---|---|
| A — `AuditLogViewSetTestCase` | 4 | venv local con `djangorestframework==3.14.0` desincronizado de `requirements.txt` (`3.16.1`); DRF 3.14 rompe con `ip_address_validators` de Django 5.x (`ValueError: not enough values to unpack`) | Entorno |
| B — `test_reporting_proxy*.py` | 9 | `TexCore/settings_test_local.py` no cargaba `INTERNAL_JWT_PRIVATE_KEY`/`PUBLIC_KEY` de `.env.test` — esa carga vivía solo en `manage.py::main()` (vía `python-dotenv`), que `pytest` no ejecuta; CI las inyecta a mano en `ci.yml` | Config de test |
| C — `...usa_sede_del_usuario` / `autoasigna...sede` | 5 | DRF forzaba el campo `sede` a `required=True` por estar en un `unique_together` sin `default=`, pese a `blank=True` en el modelo — la rama de auto-asignar `sede` del usuario en `perform_create` nunca se alcanzaba | Bug de producción (versión de DRF) |
| D — `RecursoCompartidoTestCase` | 1 | `Prefetch('maquinas', queryset=annotate(Count('lineas_produccion')))` reutilizaba la misma relación M2M que el propio `Prefetch` usa para el join externo → el `GROUP BY` generado agrupaba por (línea, máquina) en vez de por máquina → el conteo de líneas activas por máquina compartida siempre daba 1 | Bug de producción (Django ORM) |

**Corrección aplicada:**
- **Grupo A:** `pip install -r requirements.txt` (sincroniza el venv local a DRF 3.16.1, la versión que ya fija el proyecto). Adicionalmente, `AuditLogSerializer.ip_address` (`inventory/serializers.py`) ahora se declara explícitamente como `serializers.CharField(required=False, allow_null=True)` en vez de dejar que DRF autogenere el campo desde el `GenericIPAddressField` del modelo — blindaje ante futuros desajustes de versión (el campo solo se usa para mostrar el valor, nunca para validar escritura).
- **Grupo B:** `TexCore/settings_test_local.py` ahora carga `.env.test` con `python-dotenv` (`override=False`, para no pisar variables ya seteadas por CI/entorno) antes de importar `TexCore.settings`, replicando lo que `manage.py`/CI ya hacían.
- **Grupo C:** al actualizar a DRF 3.16.1 (Grupo A), el comportamiento de `get_uniqueness_extra_kwargs` sobre campos con `blank=True` cambió y los 5 tests **pasaron sin ningún cambio de código de producción** — se verificó explícitamente que la rama de auto-asignación de `sede` en los `perform_create` de `catalog_views.py`, `production_views.py` y `sales_views.py` ahora sí se alcanza y funciona correctamente. No se tocó código (habría sido refactorizar algo que ya funciona).
- **Grupo D:** `LineaProduccionViewSet._base_queryset()` (`gestion/views/production_views.py`) reemplaza el `annotate(Count(...))` sobre la M2M compartida por una `Subquery`/`OuterRef` independiente del join del `Prefetch`:
  ```python
  conteo_activas = LineaProduccion.objects.filter(
      maquinas=OuterRef('pk'), estado='activa'
  ).order_by().values('maquinas').annotate(c=Count('id')).values('c')
  maquinas_anotadas = Maquina.objects.annotate(
      num_lineas_activas=Coalesce(Subquery(conteo_activas, output_field=IntegerField()), 0))
  ```
- **Hallazgo adicional durante la corrección:** al arreglar A+B apareció un 20º fallo no reportado originalmente — `test_historial_despachos.py::HistorialDespachoUnitTests::test_api_view_filters_and_returns_data` — causado por `HistorialDespachoViewSet.get_queryset()` ordenando solo por `-fecha_despacho` (`auto_now_add`); en este entorno Windows, dos despachos creados en rápida sucesión pueden recibir timestamps idénticos por resolución de reloj del SO, dejando el orden de `ORDER BY` indefinido. Se corrigió añadiendo `-id` como desempate: `.order_by('-fecha_despacho', '-id')`.

**Resultado:** `pytest gestion/ inventory/ --no-migrations` → **668 passed, 0 failed** (antes: 649 passed, 19 failed).

---

## Control de Mermas y Reversión de Movimientos (v1.1)

Investigación adicional pedida por el usuario: "revisar lo que es mermas para poder controlarlo y
hacer reversión cuando se elimina".

### Estado antes de la corrección
- `'MERMA'` ya existía como choice en `MovimientoInventario.TIPO_MOVIMIENTO_CHOICES`
  (`inventory/models.py`), pero `MovimientoInventarioViewSet.create()` no lo incluía en ninguna
  rama (ni entrada ni salida) — un `POST` con `tipo_movimiento='MERMA'` creaba el registro en el
  Kardex con `saldo_resultante=0.00` pero **nunca descontaba `StockBodega`** (movimiento huérfano).
- `DELETE /inventory/movimientos/{id}/` devolvía **500** para cualquier tipo de movimiento: el
  `destroy()` genérico de DRF llama a `instance.delete()` sin setear `_justificacion_auditoria`
  (exigida por `AuditableModelMixin.delete()`), lo que lanzaba una `ValidationError` de Django no
  capturada por ningún handler — sin revertir stock.
- Ya existía `MermaStockService` (`gestion/services/merma_stock.py`) para la merma **vendible** por
  máquina (`producto_merma`/`bodega_merma` configurados en `Maquina`), con su propio `revertir()` —
  pero eso es un flujo distinto al del Kardex genérico (`MovimientoInventario`).
- No existía UI para registrar ni para eliminar/revertir movimientos de inventario en
  `BodegueroDashboard`/`InventoryDashboard`.

### Corrección implementada (TDD)
- **`inventory/views.py`** — `MovimientoInventarioViewSet.create()`: `MERMA` se añadió a la rama de
  **salida** (junto a `VENTA`/`CONSUMO`) — descuenta `StockBodega`, valida stock suficiente. Se
  aprovechó para eliminar las referencias muertas a `'AJUSTE_POSITIVO'`/`'AJUSTE_NEGATIVO'` (choices
  eliminados del modelo desde la migración `0027`, ya detectado en la auditoría v1.0) tanto de las
  ramas de `create()` como del filtro `tipo=entrada/salida` en `get_queryset()`.
- **`inventory/services/movimiento_reversion.py`** (nuevo) — `MovimientoReversionService.revertir()`:
  mismo patrón que `DespachoReversionService` (`@transaction.atomic`, justificación obligatoria,
  crea un movimiento compensatorio `DEVOLUCION` en vez de borrar el histórico contable a ciegas).
  Revierte entradas (resta de `bodega_destino`), salidas incluida `MERMA` (devuelve a
  `bodega_origen`) y transferencias (ambas bodegas). **Guarda:** si el movimiento está referenciado
  por un `DetalleHistorialDespacho.movimiento_venta`, lanza `ValueError` — ese movimiento debe
  revertirse vía el flujo de despacho (`DespachoReversionService`), no aquí, para no dejar
  `HistorialDespacho` inconsistente.
- **`MovimientoInventarioViewSet.destroy()`** ahora está sobreescrito (antes no lo estaba): exige
  `justificacion` (400 si falta), invoca `MovimientoReversionService.revertir()` dentro de
  `transaction.atomic`, solo entonces borra — mismo patrón que
  `HistorialDespachoViewSet.destroy()`. Captura `ValueError`→400 (incluye la guarda de despacho),
  `Exception`→500 con logging.
- **Frontend** — `frontend/src/components/bodeguero/RegistrarMermaDialog.tsx` (nuevo: producto,
  bodega de origen, cantidad, motivo → `POST /inventory/movimientos/` tipo `MERMA`) y
  `EliminarMovimientoDialog.tsx` (nuevo: justificación obligatoria → `DELETE
  /inventory/movimientos/{id}/`), ambos montados en `KardexView`
  (`admin-sistemas/InventoryDashboard.tsx`, reutilizado por `BodegueroDashboard`) — botón
  "Registrar Merma" en el header y botón de eliminar (ícono de basura) en la columna Acciones de
  cada movimiento.
- **Tests**: `test_merma_movimiento.py` (5), `test_movimiento_reversion.py` (7),
  `test_movimiento_destroy.py` (4) en backend; `RegistrarMermaDialog.test.tsx` (7),
  `EliminarMovimientoDialog.test.tsx` (7) y 2 tests de wiring en `InventoryDashboard.test.tsx` en
  frontend. Todos TDD (RED confirmado antes de cada implementación).

---

## Trabajo futuro (fuera de alcance de esta corrección)

- Reversión de despacho sigue siendo siempre total; no existe reingreso granular por bulto/lote (la
  documentación de rol promete esto, el código no lo implementa).
- `BodegueroDashboard.tsx` muestra KPIs superficiales (conteos, no valor de inventario ni
  exactitud); podría alinearse con `JefeAreaDashboard` (OEE) en una próxima ronda.
- El movimiento `MovimientoInventario(tipo_movimiento='MERMA', ...)` creado directamente en
  `registro_lote.py` (registro de lote con merma) sigue sin tener una reversión explícita más allá
  de `MermaStockService.revertir()` (que solo cubre el stock vendible de merma por máquina) — con
  `MovimientoReversionService` ahora disponible, ese movimiento del Kardex sí podría revertirse por
  `DELETE /inventory/movimientos/{id}/` si se identifica manualmente.
