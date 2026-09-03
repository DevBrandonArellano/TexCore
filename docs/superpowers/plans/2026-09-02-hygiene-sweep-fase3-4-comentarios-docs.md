# Barrido de Higiene — Fases 3 y 4: Comentarios/Docstrings y Documentación

> **Estado: COMPLETAS (2026-09-02), sin commitear.** Ejecutadas por implementación directa en
> sesión — ambas son correcciones de texto/comentarios sin cambio de comportamiento, riesgo bajo.

**Origen:** `docs/superpowers/specs/2026-09-01-backend-hygiene-sweep-design.md`, secciones
"Fase 3 — Comentarios/docstrings desactualizados" (7 ítems) y "Fase 4 — Documentación" (8 ítems).

## Fase 3 — Comentarios/docstrings desactualizados

Los 7 ítems, verificados contra el código real antes de tocarse:

1. `gestion/models/produccion.py` — el comentario de `DescargaQuimicoOP` decía "inmutable
   post-creación"; se confirmó que `DescargaQuimicosService.revertir_descarga_op()`
   (`gestion/services/descarga_quimicos.py:140`) sí muta `estado` a `'revertida'`. Corregido para
   describir el ciclo de vida real.
2. `gestion/services/pago_reversion.py` — el comentario describía "iterar pagos posteriores"; el
   código real es `saldo_calculado + monto` (una sola operación, sin iterar historial). Corregido.
3. `gestion/serializers/production_serializers.py` — se quitó el monólogo de 15 líneas de
   razonamiento del desarrollador sobre la validación de peso ±5%, dejando un comentario de 4
   líneas con el motivo real (alerta no bloqueante, para que el jefe de área revise).
4. `gestion/views/production_lote_views.py` — la línea `_ = bodega_salida  # alias formerly
   used; bodega_entrada_op used below` era código muerto con un comentario falso: `bodega_salida`
   sí se usa directamente en líneas posteriores (confirmado por grep). Eliminada la línea completa.
5. `gestion/views/production_orden_views.py:47-50` — **ya resuelto incidentalmente en Fase 2**
   (ítem 2.3 eliminó el `get_serializer_class()` no-op completo, que era donde vivía este
   comentario). Verificado: no queda rastro.
6. `gestion/tests_integrados.py` — el docstring de `test_empaquetado_consumo_insumos_v2` prometía
   verificar "descuento de insumo automático", pero el propio código de la prueba (línea 620-621,
   ya presente) admite que esa lógica se quitó de `RegistroLoteService` en la Fase 3 del proyecto.
   Docstring corregido para describir lo que el test realmente verifica (creación del lote +
   generación de ZPL).
7. `inventory/models.py` — los docstrings de `StockBodega` y `MovimientoInventario` estaban
   ubicados *después* de `campos_auditables`/`requiere_justificacion_auditoria`, por lo que
   Python no los reconoce como `__doc__` de la clase. Movidos a la primera sentencia de cada
   clase.

## Fase 4 — Documentación (`docs/`)

1. **`docs/requerimientos/PLAN_PRUEBAS.md`** — este documento (fechado 2026-03-24, anterior al
   God Files Split de agosto) tiene ~64 referencias `archivo.py#Lxx-Lyy` a `models.py`/`views.py`/
   `serializers.py` monolíticos, dispersas en las secciones 1.1 (RN), 3 (CW) y 6 (D). **Decisión
   de alcance:** re-mapear cada una individualmente a su ubicación exacta en el nuevo árbol de
   paquetes no es mantenible (vuelven a quedar obsoletas con el próximo cambio de línea) ni es el
   propósito de este documento (registro histórico de diseño de pruebas, no navegación de
   código). Se agregó una nota al inicio del documento explicando el mapeo a nivel de archivo
   (`models.py` → `gestion/models/{core,catalogo,...}.py`, etc.) y remitiendo a
   `docs/matriz_trazabilidad_pruebas.md` (mantenido activamente) como fuente de verdad actual.
   De paso se corrigió el orden de las secciones — "4.10 Descarga de Químicos" aparecía físicamente
   *antes* que "4.9 Seguridad y Multi-Tenancy" — y se anotó que la cifra "64/64 tests" de la Fase
   TDD de Mayo es histórica (Fase 6 de este barrido agregó 6 tests más a ese archivo).
2. **`docs/matriz_trazabilidad_pruebas.md`** — ya actualizado en la Fase 6 de este barrido (filas
   de Cliente + sección de cierre); no requirió cambios adicionales.
3. **`docs/arquitectura/COMANDOS_OPERACION.md`** — corregida la afirmación falsa de que los roles
   RBAC "se crean automáticamente"; ahora documenta que requiere `setup_permissions` o
   `seed_production_masters` explícito (confirmado leyendo ambos comandos).
4. **`docs/arquitectura/ARQUITECTURA_SISTEMA.md`** — la tabla de propietarios de
   `INTERNAL_JWT_PUBLIC_KEY` decía que `reporting_excel` ya no la usa. **Verificación cruzada
   contra `docker-compose.prod.yml` y `reporting_excel/src/main.py` mostró que esto era falso**
   (el propio documento se contradecía a sí mismo entre dos secciones): `reporting_excel` sí
   sigue requiriendo `INTERNAL_JWT_PUBLIC_KEY` — ahora para verificar el token que **Django** le
   manda al llamar `POST /generate` (el sentido se invirtió, no desapareció). Lo que sí dejó de
   necesitar es `SERVICE_NAME`/`SERVICE_SECRET` (autenticación saliente, que ya no hace). Se
   corrigieron las 3 menciones de este hecho en el documento (tabla de claves, nota de
   contenedor, bloque de variables de entorno de ejemplo — a este último le faltaba
   `INTERNAL_JWT_PUBLIC_KEY` y `AUDIT_DB_PATH`).
5. **`docs/arquitectura-bd/DICCIONARIO_ELIMINACION.md`** — múltiples correcciones verificadas
   contra los modelos reales:
   - `Producto→OrdenProduccion` es `PROTECT` (`producto_entrada`/`producto_salida`, ambas
     nullable), no `SET_NULL` — corregida la tabla resumen y el script de la sección B, que
     además usaba una columna inexistente (`producto_id`; son `producto_entrada_id`/
     `producto_salida_id`).
   - `FormulaColor→OrdenProduccion` es `CASCADE` real (no la descripción ambigua "SET_NULL u
     opcional a veces CASCADE"), y no hay FK directo `formula_color_id` en
     `gestion_detalleformula` — el camino real es `FormulaColor→FaseReceta (CASCADE)
     →DetalleFormula (CASCADE vía fase)`. El script de la sección C intentaba `DELETE FROM
     gestion_detalleformula WHERE formula_color_id = ...` (columna inexistente) y no advertía
     que omitir el paso de limpiar `formula_color_id` en `gestion_ordenproduccion` arrastraría
     esas órdenes por el CASCADE real. Reescrito completo.
   - Sección D (eliminar Bodega): mismo bug de columna inexistente (`bodega_id` en vez de
     `bodega_entrada_id`/`bodega_salida_id`) — corregido.
6. **`docs/arquitectura-bd/MODELO_DATOS.md`** — `saldo_pendiente` decía "sumando `DetallePedido`
   de órdenes no pagadas"; el código real (`ClienteManager.get_queryset`, anotación
   `saldo_calculado`) suma TODOS los `PedidoVenta` no anulados (pagados o no) menos los pagos —
   no filtra por `esta_pagado`. Corregida la descripción. Numeración de secciones duplicada
   ("## 4." y "## 5." aparecían dos veces) renumerada a 6 y 7.
7. **`docs/arquitectura/MICROSERVICIOS.md`** — la nota de auditoría decía que los routers viejos
   por-reporte (`exports.py`, `gerencial.py`, `produccion.py`, `vendedores.py`) "quedaron
   intactos pero sin uso real"; confirmado por `find`/`ls` que esos archivos **ya no existen**
   (commit `cfb5212`) — solo queda `generate.py`. Corregido.
8. **`reporting_excel/README.md`** — la sección "Autenticación con Backend (Fase 13)" describía
   el flujo viejo (reporting_excel llama a Django); reescrita para el flujo actual (Django llama
   `POST /generate` en reporting_excel, verificado por JWT). El ejemplo de "Patrón SOLID en los
   Routers" usaba `/kardex` de un router ya eliminado; reemplazado por el router real
   (`generate.py`, `POST /generate`).
   - **Hallazgo incidental relacionado, corregido de paso:** `reporting_excel/src/routers/generate.py`
     tenía en su propio docstring la misma afirmación desactualizada ("los routers por-reporte se
     mantienen por compatibilidad") — corregida en el mismo archivo, ya que es la fuente de la
     que el README derivaba el dato incorrecto.

## Verificación de cierre

- `python manage.py check --settings=TexCore.settings_test` → **0 issues** (tras los cambios de
  Fase 3 en `.py`).
- `python -m py_compile` sobre los 6 archivos Python tocados (Fase 3 + `generate.py` de Fase 4) →
  sin errores.
- Los cambios de Fase 4 son documentación pura (`.md`), no requieren verificación de test suite.
- `graphify update .` pendiente de correr junto con el cierre de Fase 5 (o al terminar la sesión).
- Brandon revisa el diff y decide cómo commitear — Claude no ejecuta `git commit`/`push`.
