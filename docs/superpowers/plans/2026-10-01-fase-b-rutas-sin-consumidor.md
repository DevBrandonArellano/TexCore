# Fase B — rutas del backend sin consumidor en el frontend — Implementation Plan

**Estado:** Fase B completada el 1-oct-2026: B1 (8/8), B2 (9/9), B3 (7/7), B4 (6/6), B5 (6/6) y B6 (3/3). La auditoría de rutas devuelve 0.

**Goal:** que ninguna ruta `api/` del backend quede sin su llamada en el frontend. Cada una de las rutas que siguen sin consumidor termina **integrada en una pantalla** o **retirada del backend**, con pruebas.

**Spec:** `docs/superpowers/specs/2026-09-29-paginacion-lotes-y-cobertura-frontend-design.md` §7, aprobada por el usuario el 1-oct-2026 («continuemos con la fase B»).

**Auditoría reproducible:** `scripts/auditar_rutas_frontend.py`. Lista las rutas `api/` de Django y las cruza con `frontend/src` (sin tests). Excluye `internal/v1/*` (las consumen los microservicios), `health/` (lo consume Docker), `schema/`, `docs/` y la raíz del router. Al cerrar la Fase B debe devolver **0 rutas**. Inicio de la Fase B: 43 rutas; tras B1: 23; tras B2: 19; tras B3: 11; tras B4: 7; tras B5: 4; tras B6: **0**.

Cada paso: prueba primero (roja), implementación, prueba verde. En B1 las pruebas nuevas se verificaron rojas contra `HEAD` en un worktree temporal y verdes con el cambio. Backend en SQL Server (`scripts/run_backend_tests.sh`); frontend con `npx tsc --noEmit` y `npm test`.

## Global Constraints

- **NUNCA `git commit` ni `git push`** (el usuario hace los commits).
- Se retiran las **rutas** (vista, registro en el router y serializer si queda huérfano), **no los modelos**: siguen en uso en `seed_data`, en trazabilidad y en el admin, y retirarlos exigiría migraciones.
- Toda regla de sede usa los helpers únicos de `gestion/permissions.py` (`filtrar_por_sede`, `filtrar_catalogo_por_sede`, `ve_todas_las_sedes`, `validar_visible`, `validar_misma_sede`, `areas_gestionables`) e `inventory/permissions.py` (`bodegas_visibles`); no se reescribe la regla.
- Pruebas con la convención `test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]`.
- `gestion/tests/test_permisos_por_defecto.py` conserva sus 10 pruebas (6 de grupos y 4 de configuración); el documento de tesis las cita.

## Clasificación verificada (1-oct)

La revisión contra el código cambia dos propuestas del spec:

- **`process-steps/` no es código muerto.** `ProcessStep` es el catálogo de procesos que usan `OperacionProduccion.proceso` (MES), `maquinas/{id}/procesos/` y `ejecucion_produccion`. Pasa a *construir pantalla*: el catálogo, junto con los procesos por máquina (B3).
- **`maquinas/{id}/oee/` sí tiene consumidor** (`useJefeAreaData.ts` arma la URL con `${accion}`); el primer cruce del 29-sep no lo detectaba.

Huecos encontrados al verificar (OWASP A01 e integridad), todos cerrados en B1:

- `EtapaProduccionViewSet` y `TransferenciaInterareaViewSet` devolvían todas las sedes a `jefe_planta`, y las transferencias también a `admin_sede`. Las escrituras aceptaban área, máquina, órdenes y bodegas de otra sede. `MaquinaViewSet`, `LineaProduccionViewSet` y `ParoMaquinaViewSet` aceptaban área, bodegas, operarios o máquina de otra sede. `OrdenProduccionSubprocesoViewSet`, `AreaProcessStepViewSet` y `DetalleFormulaViewSet` (que esquivaba el versionado de fórmulas) tenían el mismo defecto y se retiran.
- `PATCH /pedidos-venta/{id}/` aceptaba `estado`, `esta_pagado`, `guia_remision` y `fecha_despacho`: marcaba un pedido como despachado o pagado sin despacho ni conciliación, esquivando `modificar`/`anular` (estado `pendiente`, motivo, auditoría). `DELETE` borraba el pedido. `PUT/PATCH /pagos-cliente/{id}/` cambiaba el monto sin conciliar, y `DELETE` duplicaba `revertir`.
- **Detalles de pedido sin validar en el flujo real:** la regla «precio ≥ costo base» vivía solo en `detalles-pedido/`, que el frontend no usa. `POST /pedidos-venta/` con detalles anidados (lo que envía el frontend) los guardaba sin validar: precio bajo el costo, peso negativo o producto de otra sede.
- MRP: `requerimientos-material/` y `sugerencias-compra/` solo exigían autenticación. Cualquier rol editaba o borraba sugerencias de compra y disparaba `ejecutar-mrp`, que recalcula todas las sedes. Además dejaban fuera al ejecutivo (que ve todas las sedes).
- Copias sueltas de la regla de sede que sobrevivieron al 29-sep (usuarios, máquinas, paros, líneas, MRP y catálogo) filtraban `sede=user.sede`: un usuario sin sede veía (o, en el catálogo, **escribía**) los registros sin sede.

## B1 — Backend: retiro y alcance de sede ✅

1. [x] **Retirar rutas muertas** (vista + router + serializer huérfano + pruebas de esas rutas): `quimicos/` (alias de `chemicals/`), `detalle-formulas/`, `detalles-pedido/`, `area-process-steps/` y `ordenes-produccion-subprocesos/` con sus 4 acciones. Test: `test_rutas_retiradas_y_alcance_catalogo.py` (404 en GET y POST; `chemicals/` sigue disponible).
2. [x] **`groups/`** queda en solo `list`. Tests adaptados en `test_permisos_por_defecto.py` (mismo número de pruebas) y `test_core_views.py`.
3. [x] **`paros-maquina/` y `transferencias-interarea/`** quedan en `list` + `create`: son registros históricos (OEE, cadena de trazabilidad y KPI de área). Tests: edición y borrado → 404 y el registro se conserva.
4. [x] **Alcance de sede en la configuración de planta** (etapas, transferencias, máquinas, líneas y paros): lectura con `filtrar_por_sede`; escrituras con `validar_visible`, `validar_misma_sede` y `areas_gestionables`. Tests: `test_alcance_sede_configuracion_planta.py` (27 pruebas).
5. [x] **Ventas:** `pedidos-venta/` y `pagos-cliente/` quedan en `list`/`create` y sus acciones de negocio. Los detalles anidados del pedido se validan con `DetallePedidoEntradaSerializer` (precio ≥ costo base, peso > 0, producto global o de la sede del cliente). Tests en `test_sales_views_extra.py`, `test_control_acceso_sede.py` y `tests_integrados.py`. Los de anticipos, anulación y destroy de pagos se migraron al flujo real (pedido con detalles anidados, listado, `revertir`).
6. [x] **MRP:** permiso `IsMRPRole` (bodeguero, ejecutivo, admin_sistemas, admin_sede), alcance con `filtrar_por_sede`; `requerimientos-material/` en `list` y `sugerencias-compra/` en `list` + `ejecutar-mrp`. Tests en `inventory/tests/test_views_extra.py`.
7. [x] **Copias de la regla de sede:** usuarios, máquinas, paros, líneas, MRP y catálogo pasan a los helpers únicos. El catálogo lee con `filtrar_catalogo_por_sede` (ítems globales + su sede) y escribe con `filtrar_por_sede`.
8. [x] Script `scripts/auditar_rutas_frontend.py`.

## B2 — Bodega ✅

**Decisión del usuario (1-oct):** la recepción se unifica en F0-001. La pestaña «Entrada» registraba las compras como un movimiento `COMPRA` genérico, sin lote de MP, costo ni lote del proveedor; eso las dejaba fuera de la trazabilidad. Ahora usa `materia-prima/registrar-entrada/`, y `inventory/movimientos/` rechaza `COMPRA`.

Hallazgos de la verificación (se cierran en B2):

- Las tres escrituras de stock de `inventory` no validan la bodega: `POST /inventory/movimientos/` (un bodeguero suma stock o lo descuenta con VENTA/MERMA en cualquier bodega de cualquier sede), `POST /inventory/transferencias/` (saca stock de una bodega de otra sede) y `POST /inventory/transformaciones/`, que además solo exige **autenticación**: cualquier rol consume stock de cualquier bodega y genera producto en otra.
- Con `lote_codigo` (movimientos) o `nuevo_lote_codigo` (transformaciones) se hace `get_or_create` de un **`LoteProduccion`**: una compra crea un «lote de producción» falso o se engancha a un lote existente con el mismo código, aunque sea de otra sede. El `lote` por id tampoco se acota a la sede.
- Editar o borrar un movimiento `COMPRA` no toca el lote de MP que lo originó: tras la unificación, la cantidad del lote y el stock se desincronizarían.
- CWE-209: tres respuestas devuelven el texto de la excepción (`movimiento_views` crear y borrar, `transferencia_views`).
- `MateriaPrimaLoteViewSet`: `admin_sede` ve todas las sedes, y `create`/`update`/`destroy` genéricos esquivan `MateriaPrimaService` (stock + movimiento COMPRA). `registrar-entrada` no valida bodega, producto ni proveedor contra el alcance del usuario. (Una recepción duplicada ya respondía 400: el modelo valida `unique_together` al guardar.)
- `retro-kardex`: suma el stock de bodegas no visibles (la contraparte de una transferencia), la fecha de corte excluye ese mismo día (`fecha__lte` contra las 00:00), agrupa por **nombre** de bodega (se repite entre sedes) y recorre todos los movimientos en Python.
- `components/operario/InventoryForm.tsx` e `InventoryHistory.tsx` son código muerto: ningún componente los importa.
- `transformaciones/` guardaba el CONSUMO con una `bodega_destino` «informativa» y la PRODUCCION con una `bodega_origen` «informativa». El kárdex lee `bodega_destino` como entrada y `bodega_origen` como salida, así que cada transformación dejaba una **entrada fantasma** del producto de origen en la bodega de destino (y una salida fantasma del producto destino en la de origen).

Pasos:

1. [x] **Escrituras de stock** (movimientos, transferencias, transformaciones): la bodega donde sale o entra el stock está en `bodegas_visibles` (helper único `validar_bodega_operable`); el destino de una transferencia o transformación es de la sede del origen; transformaciones con `IsInventoryWriterOrAdmin`. Lotes: el `lote` por id se acota con `filtrar_lotes_por_sede`; se retira la creación por `lote_codigo` en movimientos; en transformaciones, un `nuevo_lote_codigo` existente debe ser visible. `COMPRA` genérico → 400 con aviso de usar la recepción F0-001. CWE-209 en `movimiento_views` y `transferencia_views`.
1b. [x] **Vínculo movimiento ↔ lote de MP:** FK `MovimientoInventario.materia_prima_lote` (migración con enlace de los existentes por `documento_ref`). Editar la COMPRA ajusta `cantidad_kg` del lote y no puede bajar de lo consumido; borrarla exige que el lote no tenga consumos y elimina el lote.
2. [x] **Materia prima:** `materia-prima/` queda en `list` + `registrar-entrada`; alcance por sede y por bodegas visibles. En la recepción se validan la bodega (visible), el producto y el proveedor (globales o de la sede de la bodega), cantidad > 0 y costo ≥ 0. País y calidad pasan al movimiento COMPRA.
3. [x] **Stock a fecha de corte:** `KardexService.stock_a_fecha` con agregación en SQL; solo bodegas visibles; fecha (fin del día local) o fecha y hora (instante exacto); filas por bodega con id, nombre y sede.
4. [x] **Frontend — Repository** `lib/api/inventarioApi.ts`: `listarMateriaPrima(params)`, `registrarEntradaMateriaPrima(datos)` (multipart con certificado) y `stockAFecha(params)`.
5. [x] **Frontend — Recepción F0-001:** la pestaña «Entrada» pasa a `registrar-entrada` (proveedor y lote del proveedor obligatorios, costo, fecha, n.º de documento, certificado, país y calidad).
6. [x] **Frontend — Lotes de MP:** pestaña «Materia prima» del inventario con los lotes recibidos (disponible, consumido, proveedor, costo) y filtros por proveedor y «solo disponibles».
7. [x] **Frontend — Stock a fecha:** consulta dentro de la pestaña Kárdex (producto, fecha de corte, bodega opcional).
8. [x] Retirar `InventoryForm.tsx` e `InventoryHistory.tsx` (código muerto); transformaciones sin bodegas «informativas». Suites completas, auditoría de rutas, CHANGELOG, `graphify update .`.

## B3 — Tintorería, órdenes y catálogo de procesos ✅

Hallazgos de la verificación (se cierran en B3):

- `PATCH /ordenes-produccion/{id}/` solo exigía **autenticación**. Cualquier rol de la sede (vendedor, despacho, operario, empaquetado) cambiaba peso, fórmula o bodega de químicos de una orden, y eso **dispara descargas de químicos del stock**. En la UI solo editan órdenes el Jefe de Planta (`JefePlantaDashboard`, `OrdenDetalleSheet`) y el Jefe de Área (`OrdenesAsignacionPanel`, que asigna máquina y operario e inicia la orden).
- `completar_detalles` (la acción del Jefe de Área, sin consumidor) asignaba los ids del payload sin validar la sede: máquina, operario, bodegas, productos o fórmula de otra sede. Un Jefe de Área **sin área** se saltaba el control de área.
- `ordenes-produccion/{id}/calcular-dosificacion/` y `maquinas/{id}/procesos/` solo admiten tintorero y administradores, pero los litros de baño los fija el Jefe de Planta en `OrdenDetalleSheet`.

Pasos:

1. [x] **Edición de órdenes:** `update`/`partial_update` con `IsJefePlantaOrAdmin`. `completar_detalles`: el Jefe de Área solo en su área (sin área → 403); máquina del área de la orden; operario, bodegas, productos y fórmula de su sede (globales permitidos en productos y fórmulas); ids inválidos → 400; `iniciar: true` pasa la orden a `en_proceso` en la misma transacción con la validación de transición de `OrdenProduccionEstadoSerializer`.
2. [x] **Vista previa de dosificación y procesos por máquina** para el Jefe de Planta: permiso de lectura `IsDosificacionRole` (tintorero, jefe de planta, admins).
3. [x] **Frontend — Asignación del Jefe de Área** vía `completar_detalles` con `iniciar` (consume la ruta de B4).
4. [x] **Frontend — `OrdenDetalleSheet`:** vista previa de la dosificación con los litros propuestos (`ordenes-produccion/{id}/calcular-dosificacion/`) y procesos de tintorería de la máquina asignada (`maquinas/{id}/procesos/`).
5. [x] **Frontend — `FormulaDetalle`:** pestaña «Dosificación» (peso y litros → `formula-colors/{id}/calcular-dosificacion/` sobre la fórmula guardada), fórmulas derivadas (`derivadas/`) y receta congelada de una versión (`versiones/{n}/`). La calculadora en vivo de `FormulaQuimica` se mantiene: calcula sobre la fórmula que se está editando, aún sin guardar.
6. [x] **Catálogo de procesos** (`process-steps/`): pantalla en Administración de Sistemas y selector opcional «Proceso» al registrar una operación MES (el backend ya acepta `proceso_id`).
7. [x] Suites completas, auditoría de rutas, CHANGELOG, `graphify update .`.

## B4 — Producción ✅

Hallazgos de la verificación (se cierran en B4):

- `transformaciones/`, `trazabilidad/` (consumida por `TrazabilidadProducto`) y `registrar-transformacion/` cargan la orden **sin acotar por sede** (`get_object_or_404(OrdenProduccion, pk=pk)`), y `_puede_operar_area` deja pasar a Jefe de Planta y Admin de Sede **de cualquier sede**.
- **Lotes:** toda acción no listada en `get_permissions` (`update`, `partial_update`, `destroy`, `rechazar`, `obtener_costo`) solo exige autenticación si el usuario es operario, empaquetado, jefe de área o de planta, o admin.
  - `rechazar` **borra el lote y revierte su stock**; cualquier operario o empaquetado lo hace sobre cualquier lote de la sede, no solo los suyos. En la UI rechazan el operario (los suyos) y el Jefe de Área.
  - `PATCH` cambia el peso y ajusta stock; en la UI solo lo usa el operario sobre sus lotes.
  - `DELETE` no lo usa nadie.
  - `obtener-costo` expone costos de materia prima y químicos al operario y al empaquetado, pero no a los roles que ven los costos de MP (bodeguero, ejecutivo).
- `consumo-lote-detalle/` **no filtra por sede**: cualquier rol autenticado lista los consumos de todas las sedes.
- `componentes-mezcla/` copiaba la regla de sede a mano: un usuario **sin sede veía los componentes de todas las sedes**, y crear o editar un componente aceptaba orden, bodega o producto de otra sede.
- `transformaciones/` no duplica `trazabilidad/`: esta solo trae las transformaciones completadas, y aquella también las en curso y las rechazadas (intentos fallidos).

Pasos:

1. [x] **Órdenes:** `transformaciones`, `trazabilidad` y `registrar-transformacion` cargan la orden acotada por sede (`filtrar_por_sede`), además del control de área.
2. [x] **Lotes:** `update`/`partial_update` y `rechazar` solo para el operario dueño del lote, jefe de área (su área), jefe de planta y admins; sin empaquetado. `DELETE` se retira (el camino es `rechazar`). `obtener-costo` con `IsTrazabilidadCostosRole`.
3. [x] **Consumo por lote y mezcla:** `consumo-lote-detalle/` acotado con `filtrar_lotes_por_sede`; solo `list` (el `retrieve` no tiene uso). `componentes-mezcla/` con `filtrar_por_sede` y validación de orden, bodega y producto al escribir.
4. [x] **Frontend — ficha de lote:** pestañas «Consumos» (lotes de origen consumidos en la mezcla) y «Costo» (desglose F0-002 y margen) en el registro D6, con los roles de su endpoint.
5. [x] **Frontend — `TrazabilidadProducto`:** «Todos los registros» de la orden (incluye en curso y rechazados) desde `transformaciones/`.
6. [x] Suites completas, auditoría de rutas, CHANGELOG, `graphify update .`.

## B5 — Indicadores ✅

**Decisión del usuario (1-oct):** el desempeño de un operario lo ven el propio operario (solo el suyo), su Jefe de Área (solo los de su área) y el Jefe de Planta y los admins (los de su sede).

Hallazgos de la verificación (se cierran en B5):

- `AreaViewSet` no filtra por sede: cualquier usuario autenticado pide el `reporte-eficiencia` de un área de **otra sede**, con nombres y productividad de sus operarios, y el listado de áreas trae todas las sedes.
- `users/{id}/desempeno/` solo exige autenticación: cualquier usuario de la sede (un vendedor, otro operario) ve los lotes y la productividad de cualquier compañero.

Pasos:

1. [x] **Áreas:** listado y detalle con `filtrar_por_sede`. `reporte-eficiencia` para Jefe de Área (solo su área), Jefe de Planta y admins.
2. [x] **Desempeño:** regla del usuario (propio / su área / su sede).
3. [x] **Frontend — Repository** `lib/api/indicadoresApi.ts`: `reporteEficienciaArea`, `desempenoOperario` y `vendedores`.
4. [x] **Frontend — Jefe de Área:** reporte de eficiencia del día (máquinas y operarios); al elegir un operario se abre su desempeño.
5. [x] **Frontend — Ejecutivo:** filtro «por vendedor» en Ventas con `users/vendedores/` (el backend de pedidos ya acepta `vendedor_id`).
6. [x] Suites completas, auditoría de rutas, CHANGELOG, `graphify update .`.

## B6 — Detalle REST sin consumidor y cierre ✅

1. [x] Retirar el `retrieve` sin uso de `inventory/stock/`, `inventory/audit-logs/`, `procesos-tintoreria/` y `operaciones-produccion/` (verificando que ningún microservicio, script ni prueba de carga lo use).
2. [x] `scripts/auditar_rutas_frontend.py` devuelve 0 rutas.
3. [x] Suites completas, CHANGELOG, `graphify update .`; spec del 29-sep §7 marcada como cerrada.

## Pendiente de decisión del usuario (fuera del alcance de rutas)

- **Venta de contado (`esta_pagado: true`) sin pago registrado:** al crear un pedido marcado como pagado, `PedidoVentaSerializer.validate` omite el límite de crédito y el bloqueo por cartera vencida, aunque no exista un `PagoCliente`. La conciliación (`PaymentReconciler`) recalcula `esta_pagado` a partir de los pagos.
- **`admin_sede` y transferencias interárea:** puede crearlas (`IsJefePlantaOrAdmin`) pero no listarlas (`IsJefeAreaOrAdmin` no lo incluye).
