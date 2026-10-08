# Matriz de Trazabilidad de Pruebas — TexCore

> **Última actualización:** 5-oct-2026, tras la Etapa 4 de Ruff (Django, simplificaciones y complejidad).
> Backend: **1530 pruebas** (SQLite local, `settings_test_local`), cobertura **91,8 %** (`fail_under = 90`); la última
> corrida en SQL Server 2022 fue la del 1-oct (1441). Frontend: **1888 pruebas** en 129 archivos, cobertura
> 95,67 / 90,16 / 93,62 / 96,61 % (statements / branches / functions / lines).

> **Estándares aplicados:** PMBOK (Gestión de la Calidad — *Planificar / Gestionar /
> Controlar la Calidad* y *Matriz de Trazabilidad de Requisitos*) e ISTQB
> (técnicas de diseño de pruebas de caja negra y caja blanca).

Este documento vincula cada **módulo/requisito** con los **casos de prueba** que lo
verifican y la **técnica ISTQB** aplicada, sirviendo como evidencia de control de
calidad y como guía de mantenimiento de la suite.

## Cómo ejecutar la suite

```bash
bash scripts/run_backend_tests.sh            # toda la suite + cobertura (SQL Server vía Docker)
bash scripts/run_backend_tests.sh gestion.tests.test_kpi_views   # subconjunto
```

El harness levanta un SQL Server de prueba en contenedor, instala dependencias con
el driver ODBC 18 y ejecuta `coverage` sobre `gestion` e `inventory`
(configuración en `.coveragerc`, con `branch = True`).

## Leyenda de técnicas ISTQB

| Sigla | Técnica |
|-------|---------|
| EP  | Partición de Equivalencia (caja negra) |
| BVA | Análisis de Valores Límite (caja negra) |
| TD  | Tabla de Decisión (caja negra) |
| STT | Prueba de Transición de Estados (caja negra) |
| CB-D | Caja Blanca — Cobertura de Decisiones/Ramas |
| RND | Prueba no funcional de rendimiento (eficiencia de desempeño, ISO/IEC 25010 — comportamiento temporal) |

## Matriz

### Seguridad y autenticación

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Autenticación JWT por cookie (válida/expirada/ausente) | `gestion/tests/test_cookie_jwt_auth.py` | EP, CB-D | ✅ |
| Auditoría: extracción segura de IP / anti-spoofing X-Forwarded-For | `gestion/tests/test_audit_middleware.py` | EP, BVA, CB-D | ✅ |
| Relay de logs de frontend (mapeo de severidad RFC 5424) | `gestion/tests/test_system_views.py` | EP, BVA, CB-D | ✅ |
| Grupos RBAC: solo admin_sistemas los lista; anónimo, admin_sede y vendedor → rechazados; **solo lectura** (renombrar o crear → 404/405; los crean los comandos de semilla). Cierra el hallazgo C-1 | `gestion/tests/test_core_views.py` (`GroupViewSetTestCase`) | EP | ✅ |
| Permiso por defecto `IsAuthenticated` (falla en cerrado) y toda vista del proyecto declara sus permisos | `gestion/tests/test_permisos_por_defecto.py` | CB-D, EP | ✅ |

### Vistas / API (RBAC y contratos)

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Bodegas: filtrado por rol y sede, escritura restringida | `gestion/tests/test_inventory_views.py` | TD, EP, CB-D | ✅ |
| KPIs de área y ejecutivos (autorización + contrato JSON) | `gestion/tests/test_kpi_views.py` | TD, EP, CB-D | ✅ |
| Catálogo (químicos/productos/proveedores), filtro de seguridad vendedor | `gestion/tests/test_catalog_views.py` | EP, TD, CB-D | ✅ |
| Áreas: lista plana sin paginación, filtro por sede_id; el listado se acota a la sede del usuario (admin_sistemas ve todas) | `gestion/tests/test_catalog_views.py` (`AreaViewSetTestCase`), `gestion/tests/test_alcance_indicadores.py` | EP, CB-D | ✅ |
| Fórmulas: dosificación, duplicar, exportar, RBAC por acción | `gestion/tests/test_formula_views.py` | EP, TD, CB-D | ✅ |
| Inventario: stock, transferencia, alertas, kardex | `inventory/tests/test_views_endpoints.py` | EP, BVA, CB-D | ✅ |
| Matriz RBAC de endpoints de inventario | `inventory/tests/test_roles_rbac.py` | TD | ✅ |
| Órdenes de producción: aislamiento por sede (jefe_planta, bodeguero, tintorero, admin_sede solo su sede; admin_sistemas y ejecutivo todas; detalle de otra sede → 404) | `gestion/tests/test_production_views_extra.py` (`OrdenProduccionAislamientoSedeTestCase`) | TD, EP | ✅ |
| Producción: máquinas, OP (completar/update/destroy/requisitos/stock-quimicos), lotes (genealogía/ZPL/costeo/corrección/rechazo) | `gestion/tests/test_production_views.py` | TD, EP, BVA, CB-D, STT | ✅ |
| Movimientos de inventario: entradas (AJUSTE) / salidas + edición auditada; la COMPRA genérica se rechaza (va por la recepción F0-001) | `inventory/tests/test_movimiento_views.py`, `inventory/tests/test_alcance_escrituras_inventario.py` | EP, BVA, CB-D | ✅ |
| Cliente: justificación de auditoría exigida en UPDATE, no en CREATE | `gestion/tests/test_cliente_auditoria_justificacion.py` | CB-D | ✅ |
| Cliente: filtrado multi-tenant por sede (admin ve todas, vendedor solo sus asignados) | `gestion/tests/test_cliente_sede_filtering.py` | EP | ✅ |
| Recetas tintorería F1: `GET/POST /procesos-tintoreria/` (operario 403, tintorero/admin 201, codigo único por sede, multi-tenant, `?activo=`) | `gestion/tests/test_procesos_tintoreria.py` (`ProcesoTintoreriaApiTestCase`) | TD, EP | ✅ |
| Recetas tintorería F1: `GET /maquinas/{id}/procesos/` (operario 403; tintorero y Jefe de Planta ven solo los asignados) y `volumen_bano_litros` expuesto | `gestion/tests/test_procesos_tintoreria.py` (`MaquinaProcesosApiTestCase`), `gestion/tests/test_ordenes_edicion_y_asignacion.py` | TD | ✅ |
| Recetas tintorería F1: `OrdenProduccion.formula_color` PROTECT → 409 «órdenes de producción asociadas»; carga diferida sin recursión en `AuditableModelMixin` | `gestion/tests/test_procesos_tintoreria.py` (`FormulaColorProtectTestCase`) | CB-D | ✅ |
| Recetas tintorería F2: `POST /formula-colors/{id}/aprobar/` (motivo ≥ 10, ya aprobada → 400, operario 403); editar aprobada exige motivo y crea vN+1 oficial; `estado` no se cambia por PUT/POST; `version` de solo lectura; historial, detalle y diff de versiones (PUT/DELETE → 405); `duplicar` = variante en pruebas con la sede de la original | `gestion/tests/test_versionado_formula.py` (`VersionadoFormulaApiTestCase`) | STT, TD, EP, BVA | ✅ |
| Recetas tintorería F2: un PUT que omite `fases` (p. ej. solo renombrar) conserva la receta; `fases: []` explícito la vacía | `gestion/tests/test_versionado_formula.py` (`VersionadoFormulaApiTestCase`) | EP, CB-D | ✅ |
| Recetas tintorería F2 (reglas 4-5) vía API: PATCH a `en_proceso` con fórmula sin versión oficial → 400 y la OP sigue pendiente; con versión → expone `version_formula`; `version_formula` en el payload se ignora (solo lectura) | `gestion/tests/test_versionado_formula.py` (`CongeladoVersionOrdenApiTestCase`) | STT, EP | ✅ |

### Servicios de negocio

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Dosificación química (gr/L, %, fallbacks, tipo desconocido) | `gestion/tests/test_services_formula.py` | EP, BVA, CB-D | ✅ |
| Descarga de químicos: validaciones de configuración + stock | `gestion/tests/test_descarga_quimicos_validaciones.py`, `test_descarga_quimicos_stock_p0.py`, `test_descarga_quimicos_tdd.py` | EP, BVA, CB-D, STT | ✅ |
| Costeo de lote y margen | `gestion/tests/test_costeo_f0_002.py` | EP, BVA | ✅ |
| Consumo de mezcla (tolerancia, stock) | `gestion/tests/test_consumo_mezcla_service.py` | EP, BVA | ✅ |
| Materia prima: entrada, consumo, trazabilidad | `gestion/tests/test_materia_prima_f0_001.py` | EP, BVA, STT | ✅ |
| Merma vendible | `gestion/tests/test_merma_stock_service.py` | EP | ✅ |
| Reversión de pago de cliente | `gestion/tests/test_pago_reversion.py` | STT | ✅ |
| KPIs de producción | `gestion/tests/test_produccion_kpi_service.py` | EP | ✅ |
| Registro de lote (mezcla, merma, estados de OP) | `gestion/tests/test_registro_lote_*.py` | EP, BVA, STT | ✅ |
| Registro de lote y reglas 4-5: congela la versión oficial al lanzar; fórmula sin versión → error y se revierte todo (lote, stock, estado); OP sin peso requerido (producción continua) no se finaliza sola | `gestion/tests/test_registro_lote_estado_op.py` | STT, EP | ✅ |
| Versionado de fórmulas (`VersionadoFormulaService`): snapshot §5.5, aprobar (regla 2), versionar (regla 3), `asegurar_version_oficial` idempotente (seeders / migración de datos), producto renombrado o de baja sigue legible | `gestion/tests/test_versionado_formula.py` (`VersionadoFormulaServiceTestCase`) | STT, EP, BVA | ✅ |
| Corrección de peso de lote y rechazo (`LoteStockAdjustmentService`): salida / materia prima / químicos, stock justo en 0 vs negativo, stock de salida inexistente (log), OP finalizada ↔ en_proceso, OP sin peso requerido | `gestion/tests/test_lote_stock_adjustment.py` | EP, BVA, STT, CB-D | ✅ |
| Despacho de reportes (`resolve_report`): cada ruta → función de datos + nombre de archivo; `dias` del aging y `producto_id` del kardex; ruta no soportada → ValueError | `internal_api/tests/test_report_dispatch.py` | TD, EP, BVA | ✅ |
| Equivalencias de empaque configurables por sede (baño→fundas→conos) | `gestion/tests/test_configuracion_empaque_sede.py` | EP, CB-D | ✅ |
| MRP (requerimientos y sugerencias de compra) | `inventory/tests/test_mrp.py` | EP | ✅ |
| Reversión de despacho (cascada, FK/fallback) | `inventory/tests/test_despacho_reversion.py` | STT, CB-D | ✅ |
| Transición de bodega (protocolo 3 fases) | `inventory/tests/test_transicion_3_fase_p1.py` | STT | ✅ |
| KPIs ejecutivos | `inventory/tests/test_executive_kpi_service.py` | EP | ✅ |

### Modelos y migraciones

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Recetas tintorería F1: `ProcesoTintoreria` codigo único por sede, `MaquinaProceso` (par único, misma sede), `Maquina.volumen_bano_litros`, `FaseReceta.proceso` PROTECT + `ciclo` | `gestion/tests/test_procesos_tintoreria.py` | EP, BVA, CB-D | ✅ |
| Migraciones unificadas (1-oct-2026): `gestion/migrations/0001_initial.py` + `0002_fix_token_blacklist_mssql.py` e `inventory/migrations/0001_initial.py` crean la base de SQL Server desde cero; la suite completa corre sobre esa base. Las pruebas de las migraciones de datos históricas (0014 fases → procesos; enlace de compras con su lote de MP) se retiraron junto con esas migraciones | `scripts/run_backend_tests.sh` (base nueva) | — | ✅ |
| Recetas tintorería F2: `VersionFormula` inmutable salvo `es_oficial` (update/delete rechazados), número único por fórmula, una sola oficial (restricción de BD), motivo 9/10 caracteres | `gestion/tests/test_versionado_formula.py` (`VersionFormulaModelTestCase`) | TD, CB-D, BVA | ✅ |
| Recetas tintorería F2 (reglas 4-5): `OrdenProduccion.version_formula` se congela al salir de `pendiente` (también `update_fields=['estado']`, pendiente → finalizada y creada ya en proceso); sin versión oficial se rechaza; una OP lanzada no cambia de fórmula ni de versión; OPs legacy ya en proceso no se bloquean; OP pendiente sí puede cambiar de fórmula | `gestion/tests/test_versionado_formula.py` (`CongeladoVersionOrdenTestCase`) | STT, CB-D | ✅ |

### Requisitos no funcionales — RNF-03 Rendimiento y Tiempo de Respuesta

Cada prueba afirma dos cosas: **reloj** (`time.perf_counter()` contra la cifra
formal del backlog) y, en Django, **techo de consultas** fijo (determinista entre
máquinas; detecta el N+1 que degrada el umbral con volumen real en SQL Server).
Son pisos de referencia *in-process* — sin red, sin Nginx, sin SQL Server —: su
valor es detectar regresiones. La medición end-to-end bajo carga, con fila y fallo
explícito propios para los tres umbrales, está en `scripts/loadtest/locustfile.py`
(lista para ejecutar cuando haya entorno).

| Requisito | Historia | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|---|
| RNF-03: consulta de kárdex < 3000 ms — 5000 movimientos del producto en la bodega (+2000 de ruido), rango de fechas con saldo inicial, **última página** (peor caso del OFFSET); techo de 6 consultas | TEX-22 CA-3 | `inventory/tests/test_views_endpoints.py` (`KardexBodegaRendimientoTestCase`) | RND, CB-D | ✅ |
| RNF-03 / TEX-22 CA-1: `KardexService` — saldo inicial con un `SUM` en la base, saldo corrido con `SUM() OVER (ORDER BY fecha, id)` que sobrevive a la paginación, desempate por id, transferencias entrantes/salientes, `fecha_fin` incluye todo el día (23:59:59 dentro, 00:00 del siguiente fuera), `fecha_inicio` a las 00:00 entra al rango, filtro por tipo sin alterar el saldo, sin producto no hay saldo, fecha inválida | TEX-22 CA-1, CA-3 | `inventory/tests/test_kardex_service.py` | EP, BVA, CB-D | ✅ |
| TEX-22 CA-1: contrato paginado de `GET /bodegas/{id}/kardex/` — `count`/`results`/`saldo_inicial`, el saldo de la página 2 continúa el de la 1, `page_size` 500 respetado y 501 recortado, fecha o tipo inválidos → 400, usuario con nombre completo o «Sistema» | TEX-22 CA-1 | `inventory/tests/test_views_endpoints.py` (`KardexBodegaAPIViewTestCase`) | EP, BVA, CB-D | ✅ |
| TEX-22 CA-2: export Excel del kárdex con la misma consulta que la pantalla — saldo que incluye lo previo a `fecha_desde` sin fila virtual, entrada/salida/bodega destino, sin producto sin columna saldo, filtro por tipo | TEX-22 CA-2 | `internal_api/tests/test_reporting_data_kardex.py`, `internal_api/tests/test_report_dispatch.py` | EP, CB-D, TD | ✅ |
| RNF-03: listado `/inventory/movimientos/` sin N+1 (4 consultas para 34 filas; antes 258) y `page_size` 2/500/501 | TEX-22 CA-3 | `inventory/tests/test_kardex_filters.py` | CB-D, BVA | ✅ |
| TEX-22: filtro de kárdex inválido (fecha imposible como mes 13, fecha sin formato, tipo desconocido) → 400 con el motivo real en pantalla, export vía proxy y `internal_api`; `internal_api` acepta `tipo` | TEX-22 CA-1, CA-2 | `inventory/tests/test_kardex_service.py`, `inventory/tests/test_reporting_proxy_extra.py`, `internal_api/tests/test_reporting_views_extra.py` | EP, BVA | ✅ |
| RNF-03: panel de Jefe de Planta < 3000 ms con la sede completa cargada — las 9 peticiones de `JefePlantaDashboard.tsx` sobre 500 órdenes, 1500 lotes, 1000 componentes de mezcla, 60 productos, 15 máquinas, 42 usuarios; techo de 35 consultas (34 hasta la Fase B; +1 por el chequeo de sede de `/api/areas/`) | TEX-17 CA-3 | `gestion/tests/test_produccion_kpi_service.py` (`PanelJefePlantaRendimientoTest`, `OrdenPesoProducidoPrefetchTest`) | RND, CB-D, EP | ✅ |
| RNF-03: escaneo de lote < 2500 ms (gate del test en 1.0 s, deliberadamente más estricto: mide solo el overhead interno del microservicio) | TEX-44 CA-3 | `scanning_service/tests/integration/test_validate_latency.py` | RND | ✅ |
| Soporte RNF-03: el snapshot de `AuditableModelMixin` no consulta las FK auditables al cargar un modelo, y sigue detectando el cambio de bodega | TEX-22 CA-3 | `gestion/tests/test_auditable_mixin_consultas.py` | CB-D, EP | ✅ |

### Fase B — rutas sin consumidor y control de acceso (1-oct-2026)

Plan `docs/superpowers/plans/2026-10-01-fase-b-rutas-sin-consumidor.md`. Cada prueba de alcance se vio roja contra el
código anterior (los casos que ya se cumplían se indican en el CHANGELOG). Regla común: una referencia de otra sede o
fuera del alcance del usuario responde igual que una inexistente (400 «No encontrado.» o 404).

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Rutas retiradas (`quimicos/`, `detalle-formulas/`, `detalles-pedido/`, `area-process-steps/`, subprocesos) → 404; detalle REST sin uso (stock, auditoría, operaciones) → 404 con su listado vigente; GET de detalle de procesos de tintorería → 405 (la ruta solo admite PATCH); usuarios y catálogo con los helpers únicos de sede (un usuario sin sede no ve ni modifica lo global) | `gestion/tests/test_rutas_retiradas_y_alcance_catalogo.py` | EP, BVA | ✅ |
| Configuración de planta: etapas, transferencias interárea, máquinas, líneas y paros acotados por sede y área; escrituras con área, máquina, órdenes, bodegas y operarios de la misma sede; paros y transferencias sin edición ni borrado; transferencias: crea Jefe de Planta / Admin de Sistemas, lista también Admin de Sede | `gestion/tests/test_alcance_sede_configuracion_planta.py` | EP, TD, BVA | ✅ |
| Ventas: pedidos y pagos sin edición ni borrado genérico (`modificar`, `anular`, `revertir`); detalles anidados validados al crear (precio ≥ costo base, peso > 0, producto global o de la sede del cliente); venta de contado sin pago registrado permitida (decisión del usuario) | `gestion/tests/test_sales_views_extra.py` (`PagoClienteRevertirExtraTestCase`, `VentaDeContadoTestCase`), `gestion/tests/test_control_acceso_sede.py`, `gestion/tests_integrados.py` | EP, BVA, TD | ✅ |
| MRP: requerimientos y sugerencias para bodeguero, ejecutivo y admins; `ejecutar-mrp` sin rol → 403 sin lanzar el motor; sugerencias sin edición | `inventory/tests/test_views_extra.py` | TD, EP | ✅ |
| Escrituras de stock (movimientos, transferencias, transformaciones): solo bodegas operables, destino en la sede del origen, lotes de la sede, transformaciones con rol de inventario, sin entradas fantasma en el kárdex; 500 sin detalle interno (CWE-209) | `inventory/tests/test_alcance_escrituras_inventario.py`, `inventory/tests/test_transform_view.py` | EP, TD, CB-D | ✅ |
| Recepción de MP F0-001 como única vía de compra: bodega operable, producto y proveedor de la sede; COMPRA enlazada a su lote (editar no baja de lo consumido, borrar exige lote sin consumos); listado por sede y bodega, paginado | `gestion/tests/test_recepcion_materia_prima_alcance.py` | EP, BVA, STT | ✅ |
| Stock a fecha de corte: solo bodegas visibles, fecha (fin del día local) o fecha y hora (instante exacto), bodegas homónimas en sedes distintas, consultas constantes | `inventory/tests/test_stock_a_fecha.py` | EP, BVA, RND | ✅ |
| Órdenes: edición genérica solo Jefe de Planta y admins; `completar_detalles` del Jefe de Área (su área, referencias de la sede, `iniciar` atómico con transición válida); vista previa de dosificación y procesos por máquina para el Jefe de Planta | `gestion/tests/test_ordenes_edicion_y_asignacion.py` | TD, EP, STT | ✅ |
| Catálogo de procesos de producción: lectura para todos, escritura solo admin_sistemas, nombre único, proceso en uso → 409; `proceso_id` en la operación MES | `gestion/tests/test_catalogo_procesos.py`, `gestion/tests/test_produccion_continua.py` | TD, EP | ✅ |
| Lotes: editar y rechazar solo el operario dueño, jefes y admins; sin DELETE; costo F0-002 para los roles de costos; transformaciones y trazabilidad de otra sede → 404; consumos por lote y componentes de mezcla acotados por sede | `gestion/tests/test_alcance_lotes_y_transformaciones.py`, `gestion/tests/test_transformacion_api.py` | TD, EP | ✅ |
| Indicadores: reporte de eficiencia del área (Jefe de Área solo su área, Jefe de Planta y admins); desempeño del operario (el propio, su Jefe de Área, Jefe de Planta y admins de su sede) | `gestion/tests/test_alcance_indicadores.py` | TD, EP | ✅ |
| Auditoría reproducible de rutas sin consumidor en el frontend (debe devolver 0) | `scripts/auditar_rutas_frontend.py` | — | ✅ |

### Hallazgos de la revisión de manuales (2-oct-2026)

Plan `C:/Users/arebr/.claude/plans/vammos-a-generar-un-crispy-ember.md`. Cada prueba se vio en rojo antes del cambio.

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Eliminar una OP: justificación obligatoria (ausente o solo espacios → 400), se guarda recortada en el AuditLog del DELETE; fallo interno → 500 genérico sin detalle y la orden se conserva | `gestion/tests/test_ordenes_edicion_y_asignacion.py` (`EliminacionOrdenTestCase`) | EP | ✅ |
| Editar una OP con químicos descontados: justificación solo con espacios → 400 sin cambios | `gestion/tests/test_descarga_quimicos_tdd.py` | EP | ✅ |
| Componentes de mezcla: solo con la OP `pendiente` (crear, editar y borrar con la OP iniciada o finalizada → 400); suma ≤ 100 % (100 válido, 100,01 inválido; al editar no cuenta el propio); borrar exige justificación auditada; operario → 403 | `gestion/tests/test_componentes_mezcla_reglas.py` | STT, BVA, EP | ✅ |
| Procesos de tintorería: PATCH del tintorero y admin (código y sede inmutables, sin DELETE → 405); jefes de producción leen el catálogo y no lo escriben; otra sede → 404. Procesos de una máquina: PUT reemplaza el conjunto (Jefe de Área de esa área, Jefe de Planta, admin); procesos de otra sede, inactivos o inexistentes → 400 sin cambios; lista vacía limpia; otra área → 404 | `gestion/tests/test_procesos_tintoreria.py` (`ProcesoTintoreriaEdicionApiTestCase`, `AsignacionProcesosMaquinaApiTestCase`), `gestion/tests/test_rutas_retiradas_y_alcance_catalogo.py` | TD, EP | ✅ |
| Diálogo de justificación reutilizable: longitud mínima 10 (9 inválido, 10 válido), solo espacios inválido, texto recortado, no cierra si la acción falla | `frontend/src/components/shared/JustificacionDialog.test.tsx` | BVA, EP | ✅ |
| Jefe de Planta: eliminar OP con justificación (menú y detalle), litros de baño con químicos descontados piden justificación sin `window.prompt`, formulario con fórmula (solo con versión oficial) y bodega de químicos, justificación del cambio solo si hay químicos descontados | `frontend/src/components/jefe-planta/{JefePlantaDashboard,ManageOrdenesProduccion.crud,OrdenDetalleSheet,ordenUtils}.test.tsx` | EP, STT | ✅ |
| Jefe de Área: «Componentes de mezcla» en órdenes pendientes; quitar un componente pide justificación; procesos de cada máquina | `frontend/src/components/jefe-area/{OrdenesAsignacionPanel,ComponenteMezclaPanel,ProcesosMaquinaDialog,ManageMaquinas}.test.tsx` | EP, STT | ✅ |
| Fecha del pedido al frontend en ISO UTC con `Z`: datetime UTC, datetime de otra zona (se convierte), datetime sin zona (se asume UTC), date (medianoche UTC), None, texto | `gestion/tests/test_fecha_pedido_iso_utc.py` | EP | ✅ |
| Reversión de despacho: un fallo real después de restaurar el stock deshace todo (stock, DEVOLUCION, marca de devolución) | `inventory/tests/test_despacho_reversion.py` | STT | ✅ |
| printing_service: un error interno responde 500 genérico sin exponer el detalle de la excepción (CWE-209) | `printing_service/tests/unit/test_printing_endpoints.py` | EP | ✅ |
| Plan Maestro MTS: generar OP sin bodega de salida usa la primera bodega de la sede del plan (antes `FieldError` → 500) | `gestion/tests/test_produccion_stock.py` | EP | ✅ |
| Registro de lote y motor MES: sin máquina en el payload usa la asignada a la OP; sin ninguna, guarda el lote, no crea operación MES y lo registra en el log; OP bajo pedido sin máquina reserva igual el lote para su pedido (antes se perdía en silencio) | `gestion/tests/test_registro_lote_sincronizacion_mes.py` | EP | ✅ |
| Permiso por scope de la API interna: `HasScope('x')` es una clase de permiso; scopes distintos no comparten estado; `IsInternalService & HasScope` exige servicio y scope | `internal_api/tests/test_permissions.py` | EP | ✅ |
| Formulario único de máquina (5-oct): crear con POST y editar con PATCH con todos los campos; nombre solo con espacios, capacidad 0 o negativa y eficiencia fuera de [0, 1] (1,01 y −0,01 inválidos; 0 y 1 válidos) dejan Guardar deshabilitado; al editar conserva operarios y merma, y no envía la merma si la máquina no la trajo; error 400 muestra el mensaje del backend sin cerrar; guardar desde la tarjeta o desde Gestión de Máquinas refresca ambas vistas | `frontend/src/components/jefe-area/{MaquinaDialog,ManageMaquinas,JefeAreaDashboard}.test.tsx` | EP, BVA | ✅ |
| Tintorero: pestaña Procesos (crear, editar sin código, activar/desactivar, refresca las recetas) | `frontend/src/components/tintura/{ManageProcesosTintoreria,TintoreroDashboard}.test.tsx`, `frontend/src/lib/api/procesosTintoreriaApi.test.ts` | EP | ✅ |
| Mensajes de error: el sobre del backend `{success, error: {message}}` se muestra legible (antes «success: false \| error: [object Object]») | `frontend/src/lib/apiError.test.ts` | EP | ✅ |

### Ruff Etapa 4 — refactor con pruebas de caracterización (5-oct-2026)

Cada prueba de caracterización se ejecutó **también contra `HEAD`** (el código anterior al refactor) y pasó allí. Las marcadas con † fallan contra `HEAD`: documentan un defecto corregido, no comportamiento conservado.

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Sede de auditoría por atributos (`_get_object_sede_id`) para los modelos auditados por señal: prioridad Sede → `sede_id` → `sede` → `fase.formula` → bodega, OP, pedido, bodegas origen/destino, área, producto → `lote.orden_produccion`; la primera relación presente decide aunque su sede sea `None`; un atributo que falla se registra y devuelve `None` | `gestion/tests/test_sede_auditoria_fallback.py` | EP, CB-D | ✅ |
| Motor MES `registrar_operacion`: corrida inexistente, finalizada o anulada; sin máquina ni operario; ID inexistente de máquina, operario y proceso con su mensaje; número de secuencia explícito; merma 0 no crea registro; merma vendible sin producto o bodega; sin arista reflexiva en el DAG | `gestion/tests/test_ejecucion_produccion_service.py` (`EjecucionProduccionValidacionesTestCase`) | EP, BVA, CB-D | ✅ |
| Registro de lote: un error de BD en la sincronización MES no revierte el lote ni sus movimientos y no deja la corrida a medio crear (savepoint) † | `gestion/tests/test_registro_lote_sincronizacion_mes.py` | EP, CB-D | ✅ |
| Despacho: asignación de cada lote a un pedido (reserva MTO dentro o fuera de los pedidos elegidos; primer pedido con necesidad pendiente; excedente al primer pedido que lo pidió; producto que ningún pedido pidió); lote inexistente, sin stock o sin producto | `inventory/tests/test_despacho_asignacion.py` | EP, CB-D | ✅ |
| Transformación de stock: cantidad no numérica (`abc`, `NaN`, `Infinity`) → 400 sin movimientos (antes 500) † | `inventory/tests/test_transform_view.py` | EP | ✅ |
| Comando `stress_test_data`: 4 sedes con 3 bodegas, usuarios demo del login, ningún saldo negativo, OPs del operario demo con materia prima ≥ 50 000 kg, 120 pedidos generales y 80 del vendedor demo. El refactor se verificó con una huella determinista (`random.seed`) idéntica antes y después | `gestion/tests/test_stress_test_data.py` | Humo, invariantes | ✅ |
| Texto vacío sin `NULL` (DJ001): los formularios de producto, químico y línea envían `''` en los campos opcionales | `frontend/src/components/{bodeguero/BodegueroDashboard,admin-sistemas/AdminSistemasDashboard}.test.tsx` | EP | ✅ |
| Salud de `printing_service`: con las plantillas reales responde 200; con un directorio de plantillas vacío, 503 (antes se parcheaba `os.path.exists`) | `printing_service/tests/unit/test_printing_endpoints.py` | EP | ✅ |

Sin prueba nueva, porque las existentes ya cubrían el comportamiento: `resolve_report` (100 % de líneas y ramas con `internal_api/tests/test_report_dispatch.py`), `reporting_proxy.get` (63 pruebas del proxy), `get_queryset` de lotes y la transformación (100 pruebas de alcance y API). `generar_docx.convertir` se verificó generando el `.docx` del backlog antes y después: las 17 partes XML salieron idénticas.

### Simulación de operación y hallazgos (6-oct-2026)

Las marcadas con † fallan contra `HEAD`: documentan un defecto corregido.

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Despacho, escáner (`ValidateLoteAPIView`) y reserva MTO de un lote con merma vendible: se toma la fila de stock del producto del lote, no la de la merma que comparte el lote (con la merma creada antes y después del producto terminado) † | `inventory/tests/test_despacho_merma_mismo_lote.py` | EP, STT | ✅ |
| `reporting_excel` `POST /generate`: el 500 no expone el detalle interno (CWE-209) y la auditoría sí lo registra † | `reporting_excel/tests/test_generate_errores.py` | EP | ✅ |
| `reporting_excel` middleware JWT (sin Bearer, expirado, inválido, refresh, emisor ajeno, válido), `/health` (200, 503, inalcanzable) y `lifespan` | `reporting_excel/tests/test_main_middleware.py` | EP, CB-D | ✅ |
| Comando `simular_operacion`: stock = Kardex en cada bodega, ningún saldo negativo, fechas dentro del período simulado, una OP lanzada (con versión de fórmula) por lote, pedidos despachados completos desde PT, no se ejecuta dos veces | `gestion/tests/test_simular_operacion.py` | Humo, invariantes | ✅ |
| Caracterización de `_get_object_sede_id` reescrita con `SimpleTestCase` + `subTest`: con pytest no la corría `manage.py test` † | `gestion/tests/test_sede_auditoria_fallback.py` | EP | ✅ |
| Historial de despachos acotado a la sede de sus pedidos (OWASP A01): listar, consultar, revertir y borrar un despacho de otra sede → no visible / 404; el ejecutivo ve todas † | `inventory/tests/test_historial_despacho_por_sede.py` | EP | ✅ |
| `GET /api/inventory/stock/` no lista filas sin existencias (cantidad 0 y nada comprometido); sí las que tienen 0,001 kg o están comprometidas † | `inventory/tests/test_stock_sin_existencias.py` | EP, BVA | ✅ |

### Rendimiento de stock y auditoría, y lotes con varios productos (7-oct-2026)

Las marcadas con † fallan contra `HEAD`: documentan un defecto corregido o un cambio de contrato.

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| `GET /api/inventory/stock/` paginado (`PaginacionAcotada`, tope 500), filtros `bodega_id`/`producto_id`/`search` en servidor, id no numérico → 400, orden estable, sin ver bodegas ajenas (OWASP A01); `GET /stock/resumen/` totaliza por bodega en la base con consultas constantes y respeta permisos † | `inventory/tests/test_stock_paginado.py` | EP, BVA | ✅ |
| `AuditLog.usuario_sede_id`: guarda la sede del usuario al momento del cambio (con y sin usuario o sede, cambio de sede posterior, modelo auditable); relleno de 0005 por bloques sin pisar valores † | `gestion/tests/test_auditlog_usuario_sede.py` | EP, CB | ✅ |
| `GET /api/inventory/audit-logs/`: alcance por rol y sede, búsqueda por usuario/tabla/id, el `COUNT` no une con `gestion_customuser` † | `inventory/tests/test_audit_logs_sede.py` | EP, CB | ✅ |
| Despacho de un lote con un producto agregado a mano: vende cada fila con su producto (Kardex, detalle, pedido), deja en stock lo que nadie pide, nunca la merma (aunque se haya trasladado), no lo reporta incompleto y la reversión devuelve cada fila; el escáner informa todas las filas vendibles † | `inventory/tests/test_despacho_producto_manual.py` | EP, STT | ✅ |
| Filas que salen del lote escaneado (`_lote_y_filas`): principal primero, solo productos pedidos, lote sin OP † | `inventory/tests/test_despacho_asignacion.py` | Caracterización | ✅ |
| API interna de validación (escáner de producción vía `scanning_service`): no informa la merma, lista los productos agregados a mano y acepta un lote que solo tiene uno de ellos † | `internal_api/tests/test_scanning_views.py` | EP | ✅ |
| `scanning_service`: traduce y devuelve `productos` y `peso_total` † | `scanning_service/tests/test_django_client.py`, `scanning_service/tests/unit/test_validation_service.py` | EP | ✅ |
| Frontend: `StockView` paginado y con búsqueda en servidor; `useStockDeProductoEnBodega` (sin selección, error, respuesta tardía); `useStockEjecutivo` con el resumen; detalle por bodega paginado; `AuditLogViewer` codifica la búsqueda; el escáner de despacho cuenta cada producto del lote † | `StockView.test.tsx`, `useStockDeProductoEnBodega.test.ts`, `useStockEjecutivo.test.ts`, `DrillDownModals.test.tsx`, `AuditLogViewer.test.tsx`, `DespachoDashboard.test.tsx` | EP, STT | ✅ |

### Casos de uso pendientes del backlog (7-oct-2026)

Cierre de los criterios abiertos en `docs/gestion-proyecto/AUDITORIA_BACKLOG_VS_CODIGO.md`. Las marcadas con † fallan contra `HEAD`.

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| **TEX-43** Equivalencias de empaque por sede: CA-1 (la sede usa las suyas), CA-2 (dos sedes no interfieren), CA-3 (sin configuración: aviso en el lote y en el MRP, sin constante), valores límite y justificación obligatoria; relleno 15/15 de la migración 0006 † | `gestion/tests/test_configuracion_empaque_sede.py` | EP, BVA, CB | ✅ |
| **TEX-43** API `/api/configuracion-empaque/`: Admin de Sede (la suya, otra → 404), Admin de Sistemas (`sede_id`), roles sin permiso → 403, auditoría con justificación; aviso de sedes sin equivalencias en `ejecutar-mrp` † | `gestion/tests/test_configuracion_empaque_api.py` | EP, STT | ✅ |
| **TEX-43** Frontend: pestaña Configuración del Admin de Sede, componente de equivalencias y aviso del MRP † | `ConfiguracionEmpaqueView.test.tsx`, `configuracionEmpaqueApi.test.ts`, `EjecutivosDashboard.test.tsx`, `MRPDashboard.test.tsx` | EP, BVA | ✅ |
| **TEX-52 CA-1** Auditoría filtrable por fecha (registros de cualquier antigüedad) y tipo de operación; límites del rango; rango invertido y valores inválidos → 400; el Admin de Sede sigue acotado (CA-2) † | `inventory/tests/test_audit_logs_sede.py`, `AuditLogViewer.test.tsx` | EP, BVA | ✅ |
| **TEX-18 CA-4** Metros de tela con 4 decimales exactos; 5 decimales → rechazo; máximo de enteros † | `gestion/tests/test_metros_tela_precision.py` | BVA | ✅ |
| **TEX-09 CA-2** AuditLog inmutable en el modelo: editar, borrar, `update`/`delete` masivos lanzan; borrar el usuario deja el registro con usuario nulo † | `gestion/tests/test_auditlog_inmutable.py` | EP, STT | ✅ |
| **TEX-03 CA-3** (M-8) IP del log del frontend: la del cliente detrás de un proxy de confianza; `X-Forwarded-For` de una IP pública se ignora † | `gestion/tests/test_system_views.py` | EP | ✅ |
| **TEX-36 CA-1** Cupo disponible en la ficha del cliente; *Sin cupo* al superar el límite † | `VendedorDashboard.cliente.test.tsx` | EP, BVA | ✅ |

### Serializers (validación de entrada)

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Nombre alfanumérico con acentos; dosificación > 0 | `gestion/tests/test_serializers.py` | EP, BVA | ✅ |
| Recetas tintorería: fase por `proceso` (id); el `nombre` legacy ya no se acepta (compatibilidad de F1 retirada en F2) → 400; proceso de otra sede / sin proceso → 400; lectura con `proceso_*`/`ciclo` y sin `nombre`/`nombre_display`; duplicar y exportar-dosificador | `gestion/tests/test_procesos_tintoreria.py` (`FormulaFasesProcesoApiTestCase`) | EP | ✅ |
| PUT que omite un campo anulable de un unique_together (`sede`, `area`) lo conserva (DRF 3.16 le daba `default=None` y lo anulaba); enviarlo con valor o null explícito lo cambia; PATCH sin cambios | `gestion/tests/test_put_conserva_campos_omitidos.py` | EP | ✅ |
| Actualización de movimiento (cantidad > 0, razón ≥ 10) y transferencia | `inventory/tests/test_serializers.py` | BVA, caja negra | ✅ |

### Frontend (React)

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Dashboard Jefe Planta: Exportación a PDF (Avance y Balance), UI states, network fallbacks, Blob/URL createObjectURL | `frontend/src/components/jefe-planta/JefePlantaDashboard.test.tsx` | EP | ✅ |
| Fórmulas en el panel del Administrador: editar una **aprobada** envía la justificación también como `motivo` (10 caracteres aceptado, 9 rechazado en pantalla); en pruebas no envía motivo; nunca envía `fases` ni el campo legacy `detalles` | `frontend/src/components/admin-sistemas/ManageFormulas.test.tsx` | BVA, EP | ✅ |
| Kárdex (TEX-22): paginación en servidor — con bodega + producto usa el kárdex con saldo del servidor, si no el listado; cambiar de página o recargar usa los filtros consultados (no los editados sin consultar); export Excel del servidor con esos filtros (sin consulta o sin bodega → aviso); columna Saldo según la consulta hecha; total de movimientos | `frontend/src/components/admin-sistemas/useKardex.test.ts`, `KardexView.test.tsx`, `InventoryDashboard.test.tsx` | EP, STT | ✅ |
| Recetas tintorería F2 — fórmulas: columna de versión oficial; «Aprobar» solo en pruebas, motivo 9/10 caracteres; estado de solo lectura en el editor; motivo obligatorio al editar una aprobada (y no se envía en pruebas); crear variante con código/color; fases con el catálogo de procesos activos + ciclo; catálogo vacío exige proceso | `frontend/src/components/tintura/FormulaQuimica.test.tsx` | EP, BVA, STT | ✅ |
| Recetas tintorería F2 — historial y diff de versiones: lista (oficial, motivo, autor), sin versiones, error de API, comparación penúltima → última, misma versión no comparable, versiones idénticas | `frontend/src/components/tintura/VersionesFormulaPanel.test.tsx` | EP | ✅ |
| Recetas tintorería F2 — panel del tintorero: catálogo `?activo=true`, aprobar con motivo y mensaje del backend, crear variante con código/color | `frontend/src/components/tintura/TintoreroDashboard.test.tsx` | EP | ✅ |
| Fase B — Repositories (URLs y parámetros de cada endpoint): inventario, órdenes, fórmulas, procesos, indicadores y lotes | `frontend/src/lib/api/{inventarioApi,ordenesApi,formulasApi,procesosApi,indicadoresApi,lotesApi}.test.ts` | EP | ✅ |
| Fase B — Bodega: recepción F0-001 (obligatorios, multipart con certificado, error del servidor), lotes de MP (filtros, consumido), stock a fecha de corte; pestañas del inventario | `frontend/src/components/admin-sistemas/{RegistrarEntradaView,MateriaPrimaView,StockAFechaView,InventoryDashboard}.test.tsx` | EP, BVA | ✅ |
| Fase B — Tintorería y órdenes: dosificación de fórmula y de orden, derivadas, receta de una versión, asignación del Jefe de Área con `completar_detalles` | `frontend/src/components/tintura/{DosificacionFormulaPanel,DerivadasFormula,RecetaVersionDialog,FormulaDetalle,VersionesFormulaPanel}.test.tsx`, `frontend/src/components/jefe-planta/DosificacionOrdenPanel.test.tsx`, `frontend/src/components/jefe-area/JefeAreaDashboard.test.tsx` | EP, STT | ✅ |
| Fase B — Catálogo de procesos y selector en la operación MES | `frontend/src/components/admin-sistemas/{ManageProcesos,AdminSistemasDashboard}.test.tsx`, `frontend/src/components/produccion/CorridaContinuaDashboard.test.tsx` | EP | ✅ |
| Fase B — Ficha de lote (Consumos y Costo por rol), todos los registros de transformación, reporte de eficiencia y desempeño, filtro por vendedor | `frontend/src/components/lotes/{FichaLoteDialog,paneles/PanelesConsumoCosto}.test.tsx`, `frontend/src/components/produccion/{RegistrosTransformacion,TrazabilidadProducto}.test.tsx`, `frontend/src/components/jefe-area/ReporteEficienciaArea.test.tsx`, `frontend/src/components/ejecutivos/EjecutivosDashboard.test.tsx` | EP, TD | ✅ |

## Defectos detectados y corregidos durante el refuerzo

La primera ejecución de la suite contra SQL Server (nunca antes ejecutada) reveló
14 fallos preexistentes. Hallazgos relevantes:

1. **Bug de aplicación** — método `calcular_margen` ubicado en la clase incorrecta
   (`TransferenciaInterarea`) pese a operar sobre campos de `CostoLoteProduccion`.
   Reubicado a su clase correcta.
2. **Bug de aplicación** — `DetalleFormulaViewSet.get_queryset` usaba un
   `select_related('formula_color')` inexistente (la relación real es `fase__formula`),
   causando HTTP 500 en todo listado. Corregido.
3. **Comportamiento restaurado** — la descarga automática de químicos al crear una OP
   con fórmula + bodega de químicos.
4. **Código muerto eliminado** — `empaque_service.py` (importaba modelos suprimidos
   `BultoEmpaque`/`ConfiguracionEmpaque`) y su test asociado.
5. Ajustes de tests desactualizados (precisión decimal a 3 lugares, envelope de
   respuesta, configuración de entorno `INTERNAL_JWT_*` / proxy de reportes).

Una segunda iteración sobre los módulos grandes (vistas de producción/inventario)
reveló **3 bugs reales adicionales** — referencias residuales de la Fase 14
(renombrado `producto`→`producto_entrada/salida`, `bodega`→`bodega_entrada/salida`):

6. **Bug de aplicación** — `OrdenProduccionViewSet.requisitos_materiales` usaba
   `orden.producto` (campo inexistente) → HTTP 500. Corregido a `producto_entrada`.
7. **Bug de aplicación** — `LoteProduccionViewSet.perform_update` usaba `orden.bodega`
   y `orden.producto` → HTTP 500 en toda corrección de lote con cambio de peso.
   Corregido a `bodega_salida`/`bodega_entrada`/`producto_salida`/`producto_entrada`.
8. **Bug de aplicación** — `OrdenProduccionViewSet.completar_detalles` asignaba FKs
   por instancia (`setattr(orden, 'formula_color', <id>)`) → `ValueError`. Corregido
   a asignación por `<campo>_id`.

El cierre de RNF-03 (2026-09-28) reveló **N+1 reales** al sembrar volumen:

9. **Rendimiento** — `AuditableModelMixin.__init__` tomaba el snapshot de las FK
   auditables con `getattr(self, fk)`, que consulta la base antes de que Django
   pueble la caché de `select_related`: una consulta por fila en **todo** listado
   de un modelo auditable. El kárdex de 5000 movimientos hacía 5005 consultas;
   ahora 5. Corregido leyendo la columna `<fk>_id` (mismo valor guardado).
10. **Rendimiento** — el panel de Jefe de Planta hacía 302 consultas: órdenes sin
    `producto_salida` en `select_related`, `peso_producido` con un `aggregate()`
    por orden que ignoraba el `prefetch_related('lotes')` ya cargado, mezcla sin
    prefetch; máquinas sin sus 4 FK de bodega/merma ni `operarios`; usuarios sin
    `superior`. Ahora 33, idéntico con 50 y con 500 órdenes.
11. **Datos incorrectos + rendimiento** — la pantalla del kárdex no usaba
    `KardexBodegaAPIView`: pedía `/inventory/movimientos/` (paginado a 50), leía solo
    la primera página y acumulaba el saldo en el navegador desde 0. Con más de 50
    movimientos mostraba un saldo **incorrecto** y exportaba un CSV truncado; además
    ese listado hacía 258 consultas por página (N+1). El export Excel del servidor
    usaba `saldo_resultante` (foto del stock por lote, no saldo de kárdex) y no
    distinguía entradas de salidas. Ahora pantalla y Excel comparten `KardexService`
    (saldo en la base con `SUM` + `SUM() OVER`, paginación en servidor) y el costo
    por petición no crece con el historial de la bodega.
12. **Seguridad (OWASP A01)** — `OrdenProduccionViewSet` solo acotaba a jefe_area y
    operario: jefe_planta, admin_sede, bodeguero y tintorero listaban y abrían
    órdenes de **otras sedes**. Ahora aplica la regla de todo el sistema
    (superuser, admin_sistemas y ejecutivo ven todas; el resto solo la suya).
13. **Manejo de errores** — una fecha imposible (`2026-13-45`) en el kárdex daba
    500 en `internal_api` y «Ruta de reporte no permitida» en el export: `parse_date`
    lanza su propio `ValueError` y el proxy trataba todo `ValueError` como ruta no
    soportada. Ahora `FiltroKardexInvalido` → 400 con el motivo real.
14. **Pérdida de datos** — `FormulaColorWriteSerializer.fases` tenía `default=list`: un
    PUT que no enviaba `fases` (renombrar una fórmula) borraba **toda la receta**. El
    mixin que conserva campos omitidos solo cubre defaults `None`. Ahora sin default:
    omitida se conserva, `[]` explícito la vacía.
15. **Regresión Fase 2 cerrada** — el panel del Administrador no podía editar fórmulas
    aprobadas (400 por falta de `motivo`). Ahora envía la justificación como motivo
    (≥ 10) y deja de enviar el campo legacy `detalles`.
16. **Transacción expuesta** (Ruff Etapa 4, 5-oct-2026) — la sincronización MES de
    `RegistroLoteService.registrar_lote` atrapaba cualquier excepción sin savepoint: un error
    de BD dejaba la corrida a medio crear dentro de la transacción del lote. Ahora corre en su
    propio `transaction.atomic()`.
17. **Manejo de errores** — `POST /api/inventory/transformaciones/` con una `cantidad` no
    numérica caía en el `except` genérico y respondía 500. Ahora responde 400.
18. **Bucle infinito** — `docs/gestion-proyecto/generar_docx.py` no avanzaba con una línea
    `| x` sin separador de tabla. El párrafo ahora siempre consume su primera línea.
19. **Texto nulo** — 32 campos de texto aceptaban `NULL` y `''` como vacío; la auditoría
    guardaba `None` y el frontend enviaba `null`. Migración propia `NULL → ''`
    (`docs/arquitectura/ADR/ADR_008_TEXTO_VACIO_SIN_NULL.md`).
20. **Inventario** (simulación de operación, 6-oct-2026) — un lote con merma vendible tiene
    dos filas de stock con el mismo lote (producto terminado y merma). El despacho, el
    escáner y la reserva MTO buscaban el stock solo por lote: al escanear el lote se
    despachaba la merma, el Kardex registraba una VENTA del producto terminado desde la
    bodega de merma y el pedido quedaba en `despachado_parcial`. Helper único
    `inventory.utils.stock_del_lote` (lote + producto del lote) en los cuatro lugares.
21. **CWE-209** — `reporting_excel` devolvía `str(exc)` en el 500 de `/generate`, y el
    backend (`reporting_proxy`) lo reenviaba al navegador. Ahora el mensaje es genérico y el
    detalle queda en el log y la auditoría (el mismo criterio que `printing_service`).
22. **Prueba que no corría** — `test_sede_auditoria_fallback.py` importaba pytest: el CI
    (`manage.py test`, sin pytest instalado) fallaba al importarla y, con pytest, unittest
    no ejecuta sus funciones `parametrize`.
23. **Comando roto** — `load_million` usaba campos de `OrdenProduccion` que ya no existen
    (`producto`, `bodega`), una unidad inválida (`litros`) y `None` en `pais`/`calidad`.
24. **OWASP A01** (prueba de carga con 4 empresas, 6-oct-2026) — `HistorialDespachoViewSet`
    no acotaba por sede: el despachador de una empresa listaba, revertía y hasta borraba los
    despachos de las demás (se observó un despacho de la empresa 3 revertido por el de la 1).
    Ahora `filtrar_por_sede(..., campo='pedidos__sede')`.
25. **Memoria** — `GET /api/inventory/stock/` (sin paginar) devolvía también las filas en cero
    que deja cada lote vendido: con 3 años, ~49 700 filas por petición del ejecutivo; los
    workers de gunicorn morían por memoria (SIGKILL) y nginx respondía 502.
26. **Prueba de carga desactualizada** — `locustfile.py` creaba pedidos sin `piezas`
    (obligatorio) y con precios por debajo del precio base: el 100 % de los pedidos fallaba.
27. **Rendimiento** (pendiente de la prueba de carga del 6-oct-2026) — `/api/inventory/stock/`
    sin paginar (28 799 filas, 8 MB por petición) y el `COUNT` de `/audit-logs/` uniendo con
    el usuario (75 % de la CPU de SQL Server). Stock paginado + resumen por bodega; la sede
    del usuario se guarda en el registro de auditoría con índices compuestos
    (`docs/arquitectura/ADR/ADR_010_RENDIMIENTO_STOCK_Y_AUDITORIA.md`).
28. **Búsqueda ignorada** — `AuditLogViewer` enviaba `?search=` (y sin codificar) y el
    backend no lo usaba.
29. **Escáner de producción** — `internal_api.ValidateLoteView`, la vista que consulta
    `scanning_service`, tomaba la primera fila de stock del lote y podía informar la merma: el
    defecto 20 solo se había corregido en la vista directa de Django.
30. **Stock sin vender** — un producto registrado a mano en un lote no se podía despachar y el
    Kardex vendía siempre el producto de la OP
    (`docs/arquitectura/ADR/ADR_009_LOTE_CON_VARIOS_PRODUCTOS.md`).
31. **Constante oculta** (TEX-43 CA-3) — sin `ConfiguracionEmpaqueSede`, el lote y el MRP
    convertían con 225/15 en silencio; la configuración no tenía API ni pantalla
    (`docs/arquitectura/ADR/ADR_011_EQUIVALENCIAS_EMPAQUE_SIN_CONSTANTE.md`).
32. **Auditoría limitada a 30 días** (TEX-52 CA-1, M-6) — no había filtros de fecha ni de tipo
    de operación; los registros más antiguos no se podían consultar.
33. **Pérdida de precisión** (TEX-18 CA-4, M-1) — la operación MES redondeaba los metros a 4
    decimales y el lote que generaba los guardaba con 2.
34. **Auditoría mutable** (TEX-09 CA-2, M-5) — un `AuditLog` se podía editar o borrar con el ORM.
35. **IP del proxy** (TEX-03 CA-3, M-8) — el relay de logs del navegador registraba la IP de
    Nginx en lugar de la del cliente.

## Fase 6 — Limpieza de `gestion/tests_integrados.py` (2026-09-02)

`gestion/tests_integrados.py` (2472 líneas, sin convención ISTQB) se redujo a solo
`UnifiedBusinessLogicTestCase` (1517 líneas). Se eliminaron o migraron 4 clases:

- `test_seguridad_permisos_operario` y `RBACMatrixTestCase` completa (4 tests, uno de
  ellos sin asserts reales) — **eliminados sin pérdida de cobertura**: ambos ya
  estaban duplicados con asserts correctos en `gestion/tests/test_production_views_extra.py`
  (`OrdenProduccionCreateTestCase` y `RBACMatrixTestCase`, esta última con 3 endpoints
  adicionales que la versión vieja no cubría).
- `FormulaQuimicaTestCase` (7 tests) y `TintoreroRBACTestCase` (8 tests) — 8 tests
  eran duplicados reales (dosificación exacta ya cubierta a nivel unitario en
  `test_services_formula.py` + wiring en `test_formula_views.py`; inserción duplicada
  ya cubierta en `test_serializers_extra.py`; listar/eliminar/duplicar/calcular por
  tintorero y admin ya cubiertos). Los 7 tests con cobertura única (copiado de
  insumos al duplicar, creación atómica con detalles anidados, filtro por estado,
  BVA de parámetros inválidos, tintorero crea/edita, operario no puede crear) se
  migraron a `gestion/tests/test_formula_views.py` con nombres ISTQB y factories.
- `DescargaQuimicosOPTestCase` (5 tests) — ninguno era duplicado real (cubrían la
  rama `%` además de `gr/L`, el flujo de modificar-OP-con-justificación, el
  endpoint `/stock-quimicos/` con alertas, y el rastro de auditoría). Los 5 se
  migraron a `gestion/tests/test_descarga_quimicos_tdd.py`.
- `gestion/tests_cliente_improvements.py` y `gestion/test_sede_filtering.py` (sueltos
  en la raíz de `gestion/`, sin convención ISTQB) se renombraron/movieron a
  `gestion/tests/test_cliente_auditoria_justificacion.py` y
  `gestion/tests/test_cliente_sede_filtering.py`.

Verificación: `python manage.py check` (0 issues) y descubrimiento de tests de
`gestion`/`inventory`/`internal_api` (`manage.py test`) importaron todos los módulos
sin error — solo fallaron al conectar a SQL Server real (sin Docker local). Detalle
completo en `docs/superpowers/plans/2026-09-02-hygiene-sweep-fase6-limpieza-tests.md`.

## Estado de cobertura

Cobertura medida sobre el **código de aplicación** (`gestion`, `inventory`). Los
comandos de management (`*/management/commands/*` — utilitarios operativos de
seed/stress de datos, ~1.232 líneas sin valor de prueba unitaria) se excluyen vía
`omit` en `.coveragerc`, práctica estándar de coverage.

| Hito | Cobertura | Tests |
|------|-----------|-------|
| Baseline (suite nunca ejecutada) | 58.0% | 220/243 (14 rojos) |
| Tras Fases 0–3 (seguridad, vistas, servicios, serializers) | 63.5% | 337 ✅ |
| Tras módulos grandes (production_views, movimientos) | 81.2% | 379 ✅ |
| Plan de testabilidad (27-ago-2026) | 91.2% | — |
| Auditoría de tesis C-1/C-2/M-4 (30-sep-2026, SQLite local) | 90.7% | 1329 ✅ |
| Fin de la Fase B y migraciones unificadas (1-oct-2026, SQL Server 2022, base nueva) | 91.1% | 1441 ✅ |
| Cierre de hallazgos de la revisión de manuales (2-oct-2026, SQLite local) | 91.2% | 1473 ✅ |
| Brechas del código nuevo y convención de nombres (2-oct-2026, SQLite local) | 91.3% | 1478 ✅ |
| CI/CD Fase 2 y Ruff Etapas 1-3 (5-oct-2026, SQLite local) | 91.2% | 1490 ✅ |
| Ruff Etapa 4: DJ001, DJ012 y C901 (5-oct-2026, SQLite local, igual que el CI con `.coveragerc`) | **91.8%** | **1530 ✅** |

Umbral mínimo `fail_under = 90` en `.coveragerc`. Se obtiene con el harness
(`bash scripts/run_backend_tests.sh` → `coverage report`).

Frontend (`npx vitest run --coverage`, umbrales en `frontend/vite.config.ts`: lines 95, functions 91, branches 89,
statements 94): **1888 pruebas** en 129 archivos, 95,67 / 90,16 / 93,62 / 96,61 % (statements / branches /
functions / lines).
