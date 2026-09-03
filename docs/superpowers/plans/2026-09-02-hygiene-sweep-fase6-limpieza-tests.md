# Barrido de Higiene — Fase 6: Limpieza de tests de `gestion/`

> **Estado: COMPLETA (2026-09-02), sin commitear.** Ejecutada por implementación
> directa en sesión, con una decisión explícita de Brandon a mitad de camino (ver
> "Decisión de alcance" abajo).

**Origen:** `docs/superpowers/specs/2026-09-01-backend-hygiene-sweep-design.md`,
sección "Fase 6 — Limpieza de tests de `gestion/`" (4 ítems).

## Decisión de alcance (2026-09-02)

El ítem 6.2 de la spec ("resolver la duplicación... conservar la versión con nombre
ISTQB correcto, eliminar el duplicado") asumía que `FormulaQuimicaTestCase`,
`TintoreroRBACTestCase` y `DescargaQuimicosOPTestCase` (en
`gestion/tests_integrados.py`) eran duplicados completos de archivos ISTQB-compliant
en `gestion/tests/`. La comparación línea por línea mostró que la superposición era
**parcial**: de los 20 tests en esas 3 clases, solo 8 eran duplicados reales; los
otros 12 cubrían comportamiento que no existía en ningún otro archivo (copiado de
insumos al duplicar fórmula, creación atómica con detalles anidados, filtro por
estado, BVA de parámetros inválidos de dosificación, tintorero crea/edita fórmula,
rama `%` de descarga de químicos además de `gr/L`, flujo de modificar-OP-con-
justificación, endpoint `/stock-quimicos/` con alertas, rastro de auditoría de la
descarga). Un borrado literal de las 3 clases habría perdido esa cobertura.

Se presentó el hallazgo a Brandon con 3 opciones (migrar todo con nombres ISTQB,
pausar Fase 6.2, o borrar solo duplicados sin migrar el resto) — eligió **migrar
todo con nombres ISTQB**: cero pérdida de cobertura a cambio de más trabajo de
migración. Eso es lo que se ejecutó.

## 6.1 — Tests sin asserts reales

- `UnifiedBusinessLogicTestCase.test_seguridad_permisos_operario` (`gestion/tests_integrados.py`,
  no llamaba a ningún `assert*`, el comentario decía literalmente "si falla es OK") —
  **eliminado**. Cobertura equivalente y correcta ya existía en
  `gestion/tests/test_production_views_extra.py::OrdenProduccionCreateTestCase::test_create_dado_usuario_sin_permiso_cuando_post_entonces_403`.
- `RBACMatrixTestCase.test_unauthenticated_access` (mismo archivo, hacía las
  requests pero nunca comparaba el status code) — **eliminado junto con toda la
  clase** (ver 6.2): `gestion/tests/test_production_views_extra.py::RBACMatrixTestCase`
  ya tiene una versión con asserts reales y 3 endpoints adicionales
  (`movimientos`, `transferencias`, `kardex`) que la vieja no cubría.

## 6.2 — De-duplicación `tests_integrados.py` vs. `gestion/tests/`

`gestion/tests_integrados.py` pasó de 2472 a 1518 líneas — queda solo
`UnifiedBusinessLogicTestCase` (el resto del archivo, comprobado por lectura
completa, no tenía más contenido después de la última clase eliminada).

**Eliminados por duplicado real** (8 tests, verificado semánticamente — misma
aserción o una versión estrictamente mejor ya existente):
- `RBACMatrixTestCase` completa (4 tests) → duplicado byte-a-byte, versión superior
  en `test_production_views_extra.py`.
- `FormulaQuimicaTestCase.test_calcular_dosificacion_gr_l` / `_pct` → matemática
  exacta ya cubierta a nivel unitario en `test_services_formula.py`
  (`DosificacionCalculatorTestCase`) + wiring de la vista ya cubierto en
  `test_formula_views.py`.
- `FormulaQuimicaTestCase.test_formula_detalle_duplicado_bloqueado` → la misma
  validación (`validate_fases`, insumo repetido) ya cubierta a nivel unitario en
  `test_serializers_extra.py::FormulaColorWriteSerializerValidateFasesTestCase`.
- `TintoreroRBACTestCase.test_tintorero_puede_listar_formulas` / `_no_puede_eliminar_formula`
  / `_puede_duplicar_formula` / `_puede_calcular_dosificacion`,
  `test_admin_puede_eliminar_formula` → ya cubiertos en
  `test_formula_views.py::FormulaColorViewSetTestCase` con el mismo rol y el mismo
  status code esperado.

**Migrados a `gestion/tests/test_formula_views.py`** (`FormulaColorViewSetTestCase`,
8 tests nuevos, nombres ISTQB):
`test_formula_dado_kg_tela_cero_cuando_calcula_dosificacion_entonces_400`,
`test_formula_dado_relacion_bano_negativa_cuando_calcula_dosificacion_entonces_400`,
`test_formula_dado_existente_cuando_duplica_entonces_copia_insumos_y_mantiene_original`,
`test_formula_dado_fases_con_detalles_cuando_crea_entonces_persiste_atomicamente`,
`test_formula_dado_filtro_estado_cuando_lista_entonces_filtra`,
`test_formula_dado_tintorero_cuando_crea_entonces_201`,
`test_formula_dado_tintorero_cuando_edita_entonces_200`,
`test_formula_dado_operario_cuando_crea_entonces_403`.

**Migrados a `gestion/tests/test_descarga_quimicos_tdd.py`** (`DescargaQuimicosTDDTestCase`,
6 tests nuevos, nombres ISTQB — 2 de ellos combinan varias aserciones de la MISMA
acción en vez de reproducir 1:1 los 5 tests viejos, para no duplicar setup):
`test_crear_op_dado_formula_con_gr_l_y_pct_cuando_descarga_entonces_ambos_calculados_y_registra_consumo_y_auditoria`
(cubre la rama `%` + `MovimientoInventario` CONSUMO + auditoría `descargado_por`/`fecha_descarga`, los 3 puntos que
faltaban en el test existente de 1 solo insumo),
`test_modificar_op_dado_sin_justificacion_cuando_cambia_peso_entonces_400`,
`test_modificar_op_dado_con_justificacion_cuando_cambia_peso_entonces_reajusta_descarga_y_registra_justificacion`,
`test_eliminar_op_dado_sin_justificacion_cuando_elimina_entonces_400`,
`test_eliminar_op_dado_con_justificacion_cuando_elimina_entonces_registra_movimiento_devolucion`,
`test_stock_quimicos_endpoint_dado_stock_bajo_minimo_cuando_consulta_entonces_marca_alerta`.

Imports quedaron huérfanos tras las eliminaciones y se limpiaron en
`gestion/tests_integrados.py`: `get_user_model`, `APIClient` (ya lo provee
`APITestCase.client`), `FaseReceta`, `DetalleFormula as DetalleFormulaModel`.

## 6.3 — Archivos sueltos movidos a `gestion/tests/`

- `gestion/tests_cliente_improvements.py` (3 tests, fixtures manuales) →
  `gestion/tests/test_cliente_auditoria_justificacion.py` (4 tests ISTQB, factories
  — se separó el caso "creación no exige justificación" del original en su propio
  test en vez de dejarlo implícito).
- `gestion/test_sede_filtering.py` (2 tests) →
  `gestion/tests/test_cliente_sede_filtering.py` (4 tests ISTQB, factories — se
  separaron los 2 sub-casos de `test_admin_filters_by_sede` en tests independientes
  por consistencia con el resto del archivo).

## 6.4 — Documentación

`docs/matriz_trazabilidad_pruebas.md`: se agregaron las 2 filas de Cliente
(auditoría/justificación y filtrado por sede) a la tabla "Vistas / API", y una
sección nueva "Fase 6 — Limpieza de `gestion/tests_integrados.py`" con el detalle
de qué se eliminó vs. migró. Las filas de "Fórmulas" y "Descarga de químicos" ya
apuntaban a los archivos correctos (`test_formula_views.py`,
`test_descarga_quimicos_tdd.py`) — no requirieron cambio.

**Nota incidental, fuera de alcance:** `.secrets.baseline` tiene una entrada para
`gestion/tests_cliente_improvements.py` (ruta ahora inexistente). No se tocó —
Brandon debe re-generar el baseline (`detect-secrets scan`) la próxima vez que
toque ese archivo, no es bloqueante.

## Verificación de cierre

- `python manage.py check --settings=TexCore.settings_test` → **0 issues**.
- `python manage.py test gestion inventory internal_api --settings=TexCore.settings_test`
  → descubrimiento e importación de **todos** los módulos de test completó sin
  `ImportError` (incluidos los 4 archivos nuevos/editados); falló recién al
  conectar a SQL Server real — mismo bloqueo conocido de siempre en esta máquina
  ([[no-docker-local]]), no un error introducido por estos cambios.
- No fue posible correr `pytest --collect-only` (exige variables de entorno de
  `TexCore.settings` — `SECRET_KEY`, `CORS_ALLOWED_ORIGINS` — no configuradas en
  esta sesión); se usó `manage.py test` con `--settings=TexCore.settings_test` en
  su lugar, que sí tiene defaults y llega más lejos (hasta la conexión real a BD).
- `graphify update .` pendiente de correr al cierre de la fase (ver checklist de
  sesión).
- Suite completa pendiente de que Brandon la corra con Docker/SQL Server real —
  ahí se confirma definitivamente que los 18 tests migrados/nuevos pasan (fueron
  verificados por lectura contra el código real de vistas/serializers/servicios,
  no por ejecución).
- Brandon revisa el diff y decide si commitea como un solo commit o lo separa por
  ítem (6.1/6.2/6.3/6.4) — Claude no ejecuta `git commit`/`push`.
