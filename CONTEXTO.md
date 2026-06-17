# CONTEXTO — Análisis Exhaustivo de TexCore para Revisión Fable 5
## Diagnóstico Integral: Errores Críticos, Problemas por Rol y Funcionalidades Faltantes

**Documento de Análisis Técnico**  
**Fecha:** 10 de Junio de 2026  
**Versión:** 1.0 — Diagnóstico Inicial  
**Auditor:** Brandon Arellano  
**Modelo Objetivo:** Fable 5 (revisión exhaustiva + refactorización SOLID + pruebas ISTQB)

---

## 📋 Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Estado del Proyecto](#estado-del-proyecto)
3. [Análisis de Errores Críticos (P0)](#análisis-de-errores-críticos-p0)
4. [Problemas de Degradación (P1)](#problemas-de-degradación-p1)
5. [Análisis por Rol](#análisis-por-rol)
6. [Funcionalidades Faltantes para Industria Textil](#funcionalidades-faltantes-para-industria-textil)
7. [Problemas de Arquitectura y Patrones](#problemas-de-arquitectura-y-patrones)
8. [Plan de Acción Prioritario](#plan-de-acción-prioritario)

---

## Resumen Ejecutivo

### Hallazgos Generales

Se han identificado **25 problemas técnicos** en TexCore distribuidos en:
- **4 errores críticos (P0)** que bloquean operaciones
- **10 problemas de degradación (P1)** que afectan UX/confiabilidad
- **7 funcionalidades faltantes críticas** para textil
- **4 debilidades arquitectónicas** que requieren refactorización SOLID

### Puntuación de Salud del Código

| Aspecto | Puntuación | Estado |
|---------|-----------|--------|
| Arquitectura General | 7/10 | ✅ Service Layer bien estructurado |
| Seguridad | 5/10 | ⚠️ Race conditions, permisos permisivos |
| Trazabilidad | 6/10 | ⚠️ AuditLog OK pero gaps en colas de pago |
| Cumplimiento Textil | 3/10 | ❌ Crítico: falta trazabilidad de MP |
| Cobertura de Pruebas | 4/10 | ❌ Tests existen pero cobertura baja |

### Recomendación Inmediata

**TexCore está 60% listo para producción.** Los problemas P0 deben resolverse ANTES de lanzar. Los P1 pueden iterarse post-launch si hay monitoreo intensivo.

---

## ⚖️ Verificación contra Código Real (Fable 5 — 10 Junio 2026)

Cada hallazgo P0 fue contrastado contra el código fuente actual (branch `refactorizacion`). Veredictos:

| ID | Hallazgo | Veredicto | Evidencia |
|----|----------|-----------|-----------|
| P0-001 | Falta modelo FacturaVenta | ✅ **CONFIRMADO** | No existe `class FacturaVenta` en ningún archivo Python del proyecto |
| P0-005 | Race condition en saldo de cliente | ⚠️ **CONFIRMADO (refinado)** | `PagoClienteViewSet.perform_create` (`gestion/views/sales_views.py:139-148`) guarda el pago y llama a `PaymentReconciler` **sin** `transaction.atomic` ni `select_for_update` sobre el Cliente. Además **no valida monto vs. saldo** (acepta sobrepagos sin control). El stock SÍ usa `select_for_update` extensivamente — el gap es solo en la ruta de pagos |
| P0-006 | Stock de químicos puede quedar negativo | ✅ **CONFIRMADO** | `gestion/services/descarga_quimicos.py:72` — `stock.cantidad -= cantidad_descontar` sin validación previa de disponibilidad; `_verificar_alertas` solo emite `logger.warning` |
| P0-010 | Operario no puede rechazar lotes | ❌ **REFUTADO** | El endpoint `rechazar` SÍ existe (`gestion/views/production_views.py:508`) con reversión completa de mezcla, merma vendible y stock, y justificación obligatoria. Documentado en CHANGELOG 26-Mayo. **Eliminar de la lista P0.** Queda pendiente solo verificar qué roles tienen permiso sobre la acción |
| P0-016 | Vendedor no puede aplicar descuentos | ⚠️ **RECLASIFICADO a P1/P2** | Existe mecanismo de beneficios: `Cliente.tiene_beneficio` (`gestion/models.py:579`) + `nivel_precio` + "beneficios dinámicos" en `VendedorDashboard` (CHANGELOG Fase 2). Lo que NO existe es descuento porcentual por línea (`DetallePedido`). Es una mejora de funcionalidad, no un bloqueante |
| P0-017 | Reversión de pagos sin control de rol | ✅ **CONFIRMADO** | `gestion/views/sales_views.py:200` — `permission_classes=[IsAuthenticated]` en `revertir` y en el ViewSet (`destroy`). El `get_queryset` filtra solo al grupo `vendedor`; cualquier otro rol autenticado (operario, bodeguero) ve y puede revertir TODOS los pagos |

**Hallazgo adicional descubierto en verificación:** `perform_create` del pago y la reconciliación (`PaymentReconciler.reconcile_client_orders`) se ejecutan como dos operaciones separadas no atómicas — si la reconciliación falla, el pago queda guardado sin reconciliar, dejando `esta_pagado` desincronizado. Este es probablemente el origen de los errores de "colas de facturas y valores pendientes" reportados por el usuario.

> **Nota metodológica:** Los hallazgos P1 y las funcionalidades faltantes (F0/F1) de las secciones siguientes provienen del diagnóstico exploratorio inicial y se verificarán contra código antes de implementar cada uno. El veredicto de P0-010 demuestra que ningún hallazgo debe asumirse cierto sin verificación.

---

## 🛠️ Implementación Sprint 1 (Fable 5 — 10 Junio 2026) — TDD

Corregidos los 3 P0 confirmados + el bug raíz de colas de facturas. Tests escritos PRIMERO (ISTQB: EP + BVA + STT); ejecución pendiente en el entorno Docker de Brandon.

### Bug raíz encontrado: reconciliador incluía pedidos anulados

`PaymentReconciler` (gestion/utils.py) procesaba TODOS los pedidos del cliente en el FIFO, mientras `ClienteManager.saldo_calculado` excluye `anulado=True`. Un pedido anulado consumía el saldo y los pedidos activos posteriores quedaban `esta_pagado=False` permanentemente — **esta es la causa de los "valores pendientes" que no cuadraban y las facturas atascadas en cola**. Fix: filtro `anulado=False` en el queryset del reconciliador.

### Cambios en código de producción

| Archivo | Cambio | Problema |
|---------|--------|----------|
| `gestion/permissions.py` | Nuevo permiso `IsVendedorOrEjecutivoOrAdmin` (vendedor, ejecutivo, admin_sistemas, admin_sede) | P0-017 |
| `gestion/views/sales_views.py` | `PagoClienteViewSet.permission_classes` restringido; también en el decorador del `@action revertir` (sobreescribía los del ViewSet) | P0-017 |
| `gestion/views/sales_views.py` | `perform_create`: `transaction.atomic` + `select_for_update` sobre Cliente (vía `_base_manager` para poder bloquear sin las subqueries del manager) + validación `monto > 0` y `monto <= saldo_calculado` leído dentro del lock + reconciliación dentro de la misma transacción | P0-005 |
| `gestion/views/sales_views.py` | `destroy` y `revertir`: reversión + reconciliación envueltas en `transaction.atomic` con lock del cliente | P0-005 |
| `gestion/utils.py` | `PaymentReconciler`: filtro `anulado=False` en el FIFO | Bug colas de facturas |
| `gestion/services/descarga_quimicos.py` | Validación `stock.cantidad >= cantidad_descontar` antes de descontar; `ValidationError` de negocio sube sin re-envolver | P0-006 |

### Tests nuevos (escritos antes del código — deben pasar de RED a GREEN)

- **`gestion/tests/test_pago_seguridad_p0.py`** — 13 tests en 4 clases:
  - `PagoPermisosP017TestCase`: operario no lista/crea/revierte/elimina pagos (403); vendedor solo sus clientes (404 ajenos); admin_sistemas permitido
  - `PagoValidacionMontoP005TestCase`: sobrepago → 400; pago == saldo → 201 y pedido pagado (BVA); monto 0 y negativo → 400
  - `PagoAtomicidadP005TestCase` (`TransactionTestCase`): si la reconciliación falla, el pago se revierte (sin pagos huérfanos)
  - `ReconciliadorPedidosAnuladosTestCase`: pedido anulado no consume saldo; `saldo_calculado` y `esta_pagado` consistentes
- **`gestion/tests/test_descarga_quimicos_stock_p0.py`** — 5 tests: stock insuficiente → `ValidationError` sin tocar inventario; BVA stock == requerido (OK, queda 0) y stock = requerido − 0.01 (rechazo); rollback multi-químico (el primero se restaura si el segundo falla)

### Comandos de verificación (ejecutar cuando Docker esté disponible)

```bash
# Tests nuevos (RED→GREEN)
docker exec texcore-backend-1 python manage.py test gestion.tests.test_pago_seguridad_p0 gestion.tests.test_descarga_quimicos_stock_p0 -v 2

# Regresión de suites relacionadas
docker exec texcore-backend-1 python manage.py test gestion.tests.test_pago_reversion gestion.tests.test_descarga_quimicos_tdd gestion.tests_integrados
```

### Decisiones de diseño registradas

1. **Sobrepagos rechazados (interim):** hasta implementar `AnticipoCliente` (P1-002), un pago mayor a la deuda retorna 400 con mensaje claro. Cuando exista el modelo de anticipos, la validación derivará el excedente en lugar de rechazar.
2. **Lock vía `_base_manager`:** `Cliente.objects` anota subqueries (`saldo_calculado`) que no pueden combinarse con `SELECT ... FOR UPDATE`; se bloquea la fila con el manager base y el saldo se lee con el manager anotado *dentro* del lock.
3. **`destroy` de pagos no se restringió por objeto para vendedor:** el `get_queryset` ya limita a sus clientes (404 para ajenos), igual que `revertir`.

### Pendiente del Sprint 1

- ~~**P0-001 (FacturaVenta)**~~ — **RESUELTO POR ACLARACIÓN DE NEGOCIO (10-Jun):** la facturación SRI la maneja un software externo; TexCore no hace pasarela de pagos, solo registra pagos y emite el documento de validación. Ese documento ya existe: nota de venta vía `PrintingService.generate_nota_venta_pdf` (`gestion/views/sales_views.py` — action `download_pdf` de PedidoVenta). **No se requiere modelo FacturaVenta.** El hallazgo original del diagnóstico queda descartado.
- Ejecución de la suite por Brandon y reporte de resultados (RED esperado en código previo al fix → GREEN con los cambios).

---

## 🛠️ Implementación Sprint 2 (Fable 5 — 10 Junio 2026) — Anticipos y Pagos Parciales

Contexto de negocio confirmado por Brandon: existen clientes que pagan por adelantado. La validación interim del Sprint 1 (rechazar todo sobrepago) se reemplazó por anticipos explícitos.

### Cambios en código de producción

| Archivo | Cambio | Problema |
|---------|--------|----------|
| `gestion/models.py` | `PagoCliente.es_anticipo` (Boolean, default False) — marca explícita de pago por adelantado | P1-002 |
| `gestion/models.py` | `PedidoVenta.monto_pagado` (Decimal 12,3, default 0) — abono aplicado vía FIFO | P1-003 |
| `gestion/migrations/0067_pagocliente_es_anticipo_pedidoventa_monto_pagado.py` | Migración de ambos campos (depende de 0066) | — |
| `gestion/utils.py` | Reconciliador FIFO ahora aplica abonos parciales: `monto_aplicado = min(saldo, valor_pedido)` se persiste en `monto_pagado`; el remanente ya no se descarta. Saldo final sobrante = anticipo (visible como `saldo_calculado` negativo) | P1-002/P1-003 |
| `gestion/views/sales_views.py` | `perform_create` de pagos: sobrepago permitido SOLO con `es_anticipo=True`; sin marca → 400 con mensaje guía (previene typos sin bloquear anticipos legítimos) | P1-002 |
| `gestion/views/sales_views.py` | `DetallePedidoViewSet`: `perform_create/update/destroy` disparan reconciliación del cliente — los anticipos se aplican automáticamente al crear pedidos futuros | P1-002 |
| `gestion/serializers.py` | `PagoClienteSerializer` expone `es_anticipo`; `ClienteListSerializer` expone `saldo_a_favor` (= saldo negativo invertido); `PedidoVentaSerializer` expone `monto_pagado` + `porcentaje_pagado` (read-only) | P1-002/P1-003 |

### Tests nuevos (TDD — escritos antes del código)

**`gestion/tests/test_anticipos_pagos_parciales_p1.py`** — 9 tests en 2 clases:
- `AnticipoClienteP1002TestCase`: sobrepago sin marca → 400; con `es_anticipo` → 201 y saldo −500; anticipo a cliente sin deuda; anticipo se aplica automáticamente a pedido futuro (flujo API real: cabecera + detalle); `saldo_a_favor` visible en listado de clientes
- `PagosParcialesP1003TestCase`: abono parcial registra `monto_pagado` (600/1000); pago exacto (BVA); FIFO con parcial al segundo pedido (800 → 500 + 300); `porcentaje_pagado` en API (60.00); reversión limpia `monto_pagado`

### Comandos de verificación (suite completa de sprints 1+2)

```bash
# Aplicar la migración nueva primero
docker exec texcore-backend-1 python manage.py migrate gestion

# Tests de los dos sprints
docker exec texcore-backend-1 python manage.py test gestion.tests.test_pago_seguridad_p0 gestion.tests.test_descarga_quimicos_stock_p0 gestion.tests.test_anticipos_pagos_parciales_p1 -v 2

# Regresión
docker exec texcore-backend-1 python manage.py test gestion.tests.test_pago_reversion gestion.tests.test_descarga_quimicos_tdd gestion.tests_integrados
```

### Pendiente frontend (Sprint 2b — tras validar backend)

- `VendedorDashboard.tsx`: checkbox "Anticipo" en el formulario de registro de pago (envía `es_anticipo`); mostrar `saldo_a_favor` en la tarjeta del cliente; barra/badge de `porcentaje_pagado` en la tabla de pedidos en lugar del binario pagado/no pagado.

---

## 🛠️ Implementación Sprint 3 (Fable 5 — 10 Junio 2026) — FK Despacho→Movimiento (P1-007)

La reversión de despachos localizaba el movimiento VENTA original con `documento_ref__contains="Despacho #{id}"`; si el string cambiaba, **saltaba el lote en silencio** dejando stock inconsistente.

| Archivo | Cambio |
|---------|--------|
| `inventory/models.py` | `DetalleHistorialDespacho.movimiento_venta` — FK nullable a `MovimientoInventario` (`SET_NULL`, related_name `detalles_despacho`) |
| `inventory/migrations/0029_detallehistorialdespacho_movimiento_venta.py` | Migración del FK |
| `inventory/views.py` (`ProcessDespachoAPIView`) | El movimiento VENTA creado se vincula al detalle del despacho |
| `inventory/services/despacho_reversion.py` | Reversión usa la FK como fuente de verdad; fallback al string solo para registros pre-migración; si NINGUNO localiza el movimiento → **ValueError explícito + rollback total** (fail-loud reemplaza al skip silencioso). `select_related` ampliado |

**Tests:** `inventory/tests/test_despacho_fk_p1.py` — 4 tests: FK guardada; reversión funciona aunque `documento_ref` tenga formato distinto (el caso que antes fallaba en silencio); fallback legado por string; sin movimiento localizable → error explícito y nada queda a medias.

---

## 🛠️ Implementación Sprint 4 (Fable 5 — 10 Junio 2026) — Decimales Estandarizados (P1-008)

inventory usaba `DECIMAL(12,2)` mientras gestion usa `DECIMAL(12,3)` — redondeo cruzado acumulaba error en Kardex.

| Archivo | Cambio |
|---------|--------|
| `inventory/models.py` | 5 campos a 3 decimales: `StockBodega.cantidad`, `MovimientoInventario.cantidad`, `MovimientoInventario.saldo_resultante`, `HistorialDespacho.total_peso`, `DetalleHistorialDespacho.peso` |
| `inventory/migrations/0030_estandarizar_decimales_tres_lugares.py` | **Patrón SQL Server:** suelta los 2 CheckConstraints y el índice `idx_mov_bodega_fecha_incl` (con INCLUDE sobre las columnas) antes del ALTER COLUMN y los recrea después — sin esto la migración falla en mssql (mismo problema que `0051_fix_token_blacklist_mssql`). Ampliar precisión no pierde datos |
| `gestion/services/descarga_quimicos.py` | `quantize(Decimal('0.01'))` → `quantize(Decimal('0.001'))` en descarga y reversión |

**Decisión registrada:** los `quantize('0.01')` restantes (en `production_views.rechazar`, etc.) quedan funcionando — redondear a 2 y almacenar en 3 es seguro; se migran a `0.001` gradualmente en próximas sesiones para no cambiar comportamiento sin tests dedicados.

**Tests:** `inventory/tests/test_decimales_p1.py` — 3 tests BVA/STT: 10.125 se almacena exacto; movimiento con 3 decimales; 10 sumas de 1.111 dan 11.110 sin error acumulado.

---

## ⚖️ Sprint 5 — F1-005 (Alertas de Stock): REFUTADO PARCIALMENTE

Verificación previa a implementar (lección de P0-010): **ya existe** `AlertasStockAPIView` en `GET /api/inventory/alertas-stock/` (`inventory/views.py:614`) — calcula en vivo `stock < stock_minimo`, con filtro por sede y por rol (bodeguero ve solo sus bodegas; ejecutivo/admin ven todo). El cálculo on-demand es más robusto que un modelo persistente (sin dual-write). **No se construyó modelo redundante.** Gap real restante (menor): notificaciones push/email cuando se cruza el mínimo — anotado como mejora futura, requiere infraestructura de notificaciones.

---

## 🛠️ Implementación Sprint 2b (Fable 5 — 10 Junio 2026) — Frontend Anticipos

| Archivo | Cambio |
|---------|--------|
| `frontend/src/components/vendedor/VendedorDashboard.tsx` | `pagoForm.es_anticipo` + Switch "Es Anticipo" en el diálogo de pago (con texto explicativo); botón cambia a "Confirmar Anticipo"; el error 400 del backend (sobrepago sin marca) se muestra con su mensaje real en el toast; badge de pedidos ahora muestra **"Abonado X%"** en ámbar para pagos parciales (antes solo Pagado/Pendiente binario) |
| `frontend/src/lib/types.ts` | `PagoCliente.es_anticipo`, `PedidoVenta.monto_pagado`, `PedidoVenta.porcentaje_pagado` |

Nota: el dashboard ya mostraba "Saldo a Favor" cuando `saldo_pendiente` es negativo (verificado) — compatible sin cambios.

---

## 🛠️ Implementación Sprint 6 (Fable 5 — 10 Junio 2026) — F0-001 + F0-002 + Protocolo 3-Fase

Brandon definió el alcance vía especificaciones detalladas. Implementadas con adaptaciones al código real (documentadas abajo).

### F0-001 — Trazabilidad de Materia Prima

| Artefacto | Detalle |
|-----------|---------|
| Modelos (`gestion/models.py`) | `MateriaPrimaLote` (proveedor, lote_proveedor, certificado_calidad FileField, costo_unitario, control de consumo, unique (proveedor, lote, fecha)) + `ConsumoMateriaPrima` (through inmutable con cantidad, %, usuario) + M2M `LoteProduccion.materias_primas` |
| Migración | `gestion/0068_materia_prima_trazabilidad.py` |
| Servicio | `gestion/services/materia_prima_service.py` — `MateriaPrimaService.registrar_entrada` (MP + stock + movimiento COMPRA atómicos, validaciones cantidad>0/costo≥0), `consumir_materia_prima` (lock pesimista + validación disponible + % + flag agotada), `TraceabilityService.obtener_cadena_completa` |
| Vistas | `gestion/views/materia_prima_views.py` — `MateriaPrimaLoteViewSet` (`IsBodegueroOrAdmin`; bodeguero filtrado a sus bodegas; `POST /api/materia-prima/registrar-entrada/` multipart con certificado) + `TraceabilityViewSet` (`GET /api/trazabilidad/lote-produccion/?lote_id=X`) |
| Permiso | `IsBodegueroOrAdmin` en `permissions.py` |
| Serializers | `MateriaPrimaLoteSerializer`, `RegistrarMateriaPrimaSerializer`, `ConsumoMateriaPrimaSerializer` (read-only — ISO 27001 A.12.4) |
| Tests | `gestion/tests/test_materia_prima_f0_001.py` — 9 tests (EP/BVA/STT + atomicidad con TransactionTestCase) |

**Adaptaciones vs especificación:** el typo `materiaprimalore` de la migración spec corregido; `producto_final` se resuelve vía `orden_produccion.producto_salida` (el lote no tiene ese campo); `fecha_produccion` = `hora_final` (no existe `fecha_creacion` en LoteProduccion); vistas en módulo nuevo `materia_prima_views.py` (no existía `bodeguero_views.py`).

### F0-002 — Costeo de Producción por Lote

| Artefacto | Detalle |
|-----------|---------|
| Modelos | `TarifaOperario` (tiempo/pieza, vigencias), `CostoHoraMaquina`, `CostoLoteProduccion` (OneToOne con lote; desglose MP/químicos/operario/máquina/otros; margen sobre precio esperado; `calcular_margen()`) |
| Migración | `gestion/0069_costeo_lote_produccion.py` |
| Servicio | `gestion/services/costeo_service.py` — `CostoLoteService.calcular_costo`: MP desde la cadena F0-001; químicos = `cantidad_real_kg or cantidad_calculada_kg` × `precio_base`; horas reales = `hora_final - hora_inicio` del lote; tarifas vigentes a la fecha del lote |
| Endpoint | `GET /api/lotes-produccion/{id}/obtener-costo/` (action en `LoteProduccionViewSet`) |
| Tests | `gestion/tests/test_costeo_f0_002.py` — 7 tests (costo completo $630 = 500+100+20+10; sin tarifas; vigente_hasta NULL aplica; tarifa expirada no; margen 37%; idempotencia; endpoint) |

**Adaptaciones vs especificación:** `fecha_inicio_real/fecha_finalizacion_real` no existen → se usan `hora_inicio/hora_final`; el filtro de tarifas del spec (`vigente_hasta__gte=fecha`) **excluía contratos abiertos** (vigente_hasta NULL) — corregido con `Q(isnull=True) | Q(gte=fecha)`; la fecha de vigencia se evalúa a la fecha del lote (no `timezone.now`) para costear lotes históricos correctamente.

### Protocolo 3-Fase — Transiciones entre Bodegas

| Artefacto | Detalle |
|-----------|---------|
| Modelo | `MovimientoInventario.estado_movimiento` (solicitado/en_transito/completado/revertido, default **completado** = compatibilidad histórica) + `bodega_transicion` FK |
| Migración | `inventory/0031_protocolo_tres_fases.py` |
| Servicio | `inventory/services/transicion_bodega_service.py` — `iniciar_transicion` (valida stock con lock, descuenta origen, carga tránsito), `completar_transicion` (descuenta tránsito, carga destino), `revertir_transicion` (restaura origen, limpia tránsito, justificación obligatoria) |
| Integración | `descarga_quimicos.py` marca sus movimientos CONSUMO como `completado` explícito |
| Tests | `inventory/tests/test_transicion_3_fase_p1.py` — 7 tests (las 3 fases, conservación del balance total 100 kg, doble-completar falla, reversión, justificación, compat legado) |

**Adaptaciones vs especificación (importantes):**
1. **Bug del spec corregido:** `completar_transicion` del spec sumaba al destino sin descontar la bodega de tránsito → **material duplicado**. Aquí cada fase mueve el stock exactamente una vez (test de conservación de balance lo verifica).
2. **`OrdenProduccion.bodega_quimicos_intermedia` NO existe** — el spec lo asumía. La descarga de químicos es consumo inmediato (sin tránsito real); el protocolo se implementó como servicio standalone para TRANSFERENCIAS. Si se desea tránsito en descargas de químicos, hay que agregar primero ese campo a la OP (decisión de negocio pendiente).
3. **La validación propuesta en `ConsumoMezclaService` NO se aplicó:** exigir un movimiento 'completado' previo rechazaría TODO el stock existente creado sin historial de transferencias (seeds, producción directa, datos legados) — rompería la suite completa y la operación actual. Requiere plan de backfill antes de activarse.

### Comandos de verificación Sprint 6

```bash
docker exec texcore-backend-1 python manage.py migrate

docker exec texcore-backend-1 python manage.py test gestion.tests.test_materia_prima_f0_001 gestion.tests.test_costeo_f0_002 inventory.tests.test_transicion_3_fase_p1 -v 2

# Suite completa de la sesión (sprints 1-6)
docker exec texcore-backend-1 python manage.py test gestion inventory
```

### Pendiente Sprint 6 (frontend + decisiones)

- Frontend: componente `RegistrarMateriaPrima.tsx` (bodeguero), vista de cadena de trazabilidad, panel de costos/margen para vendedor — tras validar backend.
- Catálogos: pantallas CRUD para `TarifaOperario` y `CostoHoraMaquina` (admin).
- Decisión: ¿agregar `bodega_quimicos_intermedia` a la OP para usar 3-fase en descargas?

### F0 restantes (sin especificación aún)

- **F0-003 Analytics de merma:** datos listos en Kardex (`MERMA-*`); falta espec del dashboard.
- **F0-004 Composición de tejidos:** falta definir fichas técnicas.

### Comandos de verificación — SUITE COMPLETA (sprints 1-4)

```bash
# 1. Migraciones nuevas (gestion 0067, inventory 0029-0030)
docker exec texcore-backend-1 python manage.py migrate

# 2. Tests nuevos de todos los sprints
docker exec texcore-backend-1 python manage.py test gestion.tests.test_pago_seguridad_p0 gestion.tests.test_descarga_quimicos_stock_p0 gestion.tests.test_anticipos_pagos_parciales_p1 inventory.tests.test_despacho_fk_p1 inventory.tests.test_decimales_p1 -v 2

# 3. Regresión backend completa
docker exec texcore-backend-1 python manage.py test gestion inventory

# 4. Frontend (TypeScript + tests)
cd frontend && npm run build && npm test
```

---

## Estado del Proyecto

### Stack Tecnológico

- **Backend:** Django 5 + Django REST Framework
- **Microservicios:** FastAPI (scanning, reporting, printing)
- **Frontend:** React 18 + TypeScript + Vite
- **Base de Datos:** SQL Server 2022
- **Infraestructura:** Docker Compose, Nginx, Redis, Celery

### Fases Completadas ✅

- Fase 0-6: Estabilización, Arquitectura de Producción, Hardening de Seguridad
- Fase 8: Módulo de Despacho con reversión de stock
- Fase 13: API Interna JWT RS256 (eliminación de acceso directo a BD)
- Fase 14: Producción Flexible (transformación de productos, mezcla de lotes)

### Fases en Progreso ⏳

- Fase 12: Control de Mermas (parcial)
- Suite de Pruebas: 87 tests frontend + 184 tests backend, pero cobertura es solo ~40%

---

## Análisis de Errores Críticos (P0)

### P0-001: Falta Modelo FacturaVenta — BLOQUEANTE TRIBUTARIO

**Ubicación:** `gestion/models.py` líneas 893-921 (PedidoVenta)

**Descripción:**
El sistema usa `PedidoVenta` como documento único pero **NO existe modelo `FacturaVenta`** separado. Esto impide:
- Generar facturas electrónicas (normativa tributaria)
- Separar conceptos: pedido vs facturación
- Trazabilidad de facturación independiente

**Causa Raíz:**
Diseño incompleto que mezcla responsabilidades de venta con facturación.

**Impacto:**
- ❌ No cumple requisitos fiscales de Ecuador
- ❌ Imposible integración contable
- ❌ Auditoría fiscal es vulnerable

**Pasos para Reproducir:**
```
1. Crear PedidoVenta
2. Intentar generar factura electrónica
3. NO existe endpoint ni modelo
4. Imposible cumplir normas tributarias
```

**Propuesta de Solución:**
```python
# Crear modelo FacturaVenta
class FacturaVenta(models.Model, AuditableModelMixin):
    numero_factura = CharField(max_length=20, unique=True)  # 001-001-000000001
    fecha_emision = DateTimeField(auto_now_add=True)
    pedido_venta = ForeignKey(PedidoVenta, on_delete=PROTECT)
    subtotal = DecimalField(max_digits=12, decimal_places=3)
    iva = DecimalField(max_digits=12, decimal_places=3)  # 15% en Ecuador
    total = DecimalField(max_digits=12, decimal_places=3)
    estado = CharField(choices=[
        ('emitida', 'Emitida'),
        ('anulada', 'Anulada'),
        ('devuelta', 'Devuelta Parcialmente')
    ])
    archivo_xml = FileField(upload_to='facturas/%Y/%m/')  # XML electrónico
    estado_sri = CharField(choices=[
        ('pendiente', 'Pendiente Envío SRI'),
        ('enviada', 'Enviada a SRI'),
        ('autorizada', 'Autorizada por SRI'),
        ('rechazada', 'Rechazada por SRI')
    ])
```

---

### P0-005: Race Condition en Cálculo de Saldo de Cliente

**Ubicación:** `gestion/models.py` líneas 527-569 (ClienteManager.saldo_calculado)

**Descripción:**
El manager calcula saldo usando subqueries SIN bloqueos de concurrencia:

```python
# PROBLEMA: Dos threads pueden leer el mismo saldo simultáneamente
saldo_calculado = Sum('pedidos_venta__detalles__subtotal') - Sum('pagos_cliente__monto')
```

Si dos vendedores registran pagos simultáneamente:
- Thread A: lee deuda=1000, crea pago de 100 → deuda=900
- Thread B: lee deuda=1000 (antes que A commit), crea pago de 100 → deuda=900
- **Resultado incorrecto:** Deuda final es 900 en lugar de 800

**Causa Raíz:**
Django ORM no usa `SELECT ... FOR UPDATE`. La subquery se ejecuta sin lock.

**Impacto:**
- ❌ En alta concurrencia: sobrepagos se duplican
- ❌ Cartera inconsistente
- ❌ Fraude potencial

**Pasos para Reproducir (Concurrencia):**
```python
# Test con threading
def test_race_condition_saldo():
    cliente = Cliente.objects.create(ruc_cedula='1234567890', ...)
    # Stock inicial: deuda = 1000
    
    def registrar_pago_100():
        pago = PagoCliente.objects.create(cliente=cliente, monto=100)
        # Leer saldo (sin lock): ve 1000 - 100 = 900
    
    thread1 = Thread(target=registrar_pago_100)
    thread2 = Thread(target=registrar_pago_100)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    
    # Esperado: 800. Actual: 900 (INCORRECTO)
    assert cliente.saldo_calculado == 800
```

**Propuesta de Solución:**
```python
# En PagoClienteViewSet.perform_create()
from django.db import transaction

class PagoClienteViewSet(ViewSet):
    def perform_create(self, serializer):
        with transaction.atomic():
            # Bloquear cliente para que no otros puedan leer su saldo
            cliente = Cliente.objects.select_for_update().get(id=serializer.validated_data['cliente_id'])
            
            # Ahora sí: calcular saldo bloqueado
            saldo_actual = cliente.saldo_calculado
            monto_pago = serializer.validated_data['monto']
            
            if monto_pago > saldo_actual:
                raise ValidationError(f'Pago excede deuda. Deuda: {saldo_actual}')
            
            serializer.save()
```

---

### P0-006: Stock puede Quedar Negativo sin Validación

**Ubicación:** `gestion/services/descarga_quimicos.py` líneas 28-117 (DescargaQuimicosService)

**Descripción:**
El servicio descuenta químicos del stock **SIN validar que existan**:

```python
# PROBLEMA: No hay CHECK antes de descontar
stock.cantidad -= cantidad_descontar  # Línea 72
stock.save()

# Resultado: stock.cantidad = -5 kg (INVÁLIDO)
```

**Causa Raíz:**
- No hay constraint `CHECK(cantidad >= 0)` en BD
- No hay validación pre-descuento en lógica

**Impacto:**
- ❌ Stock negativo → reportes falsos
- ❌ MRP no funciona (cree que hay stock)
- ❌ Despachos se hacen con stock inexistente

**Pasos para Reproducir:**
```
1. Stock Soda: 5 kg
2. OP requiere: 10 kg Soda
3. DescargaQuimicosService.descargar_para_op(op)
4. Stock final: -5 kg
5. Reporte de kardex: INCORRECTO
```

**Propuesta de Solución:**
```python
# 1. Agregar constraint en StockBodega modelo
class StockBodega(models.Model):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad__gte=0),
                name='check_stock_no_negativo'
            )
        ]

# 2. Validar en servicio ANTES de descontar
class DescargaQuimicosService:
    def descargar_para_op(self, orden):
        for componente in orden.componentes_quimicos:
            stock = StockBodega.objects.get(producto=componente.producto, bodega=...)
            
            # VALIDACIÓN
            if stock.cantidad < componente.cantidad_requerida:
                raise ValidationError(
                    f"Stock insuficiente de {componente.producto.nombre}. "
                    f"Disponible: {stock.cantidad}, Requerido: {componente.cantidad_requerida}"
                )
            
            # DESCUENTO (ahora seguro)
            stock.cantidad -= componente.cantidad_requerida
            stock.save()
            
            # CREAR ALERTA SI BAJO MÍNIMO
            if stock.cantidad < stock.producto.stock_minimo:
                AlertaStockBajo.objects.create(
                    producto=stock.producto,
                    bodega=stock.bodega,
                    cantidad_actual=stock.cantidad,
                    fecha_alerta=now()
                )
```

---

### ~~P0-010: Operario NO PUEDE Rechazar Lotes Defectuosos~~ — ❌ REFUTADO EN VERIFICACIÓN

> **Veredicto Fable 5:** FALSO. El endpoint `POST /lotes-produccion/{id}/rechazar/` existe en `gestion/views/production_views.py:508` con reversión transaccional completa (mezcla, merma vendible, stock de salida) y justificación obligatoria. Se mantiene el texto original solo como registro del diagnóstico inicial. Pendiente menor: auditar qué roles tienen permiso sobre la acción.

**Ubicación:** `gestion/views/production_views.py` — NO existe endpoint *(claim original, incorrecto)*

**Descripción:**
Si un operario produce un lote con defecto (hilo roto, color incorrecto), **NO hay forma de reportarlo**. El lote se considera válido.

**Causa Raíz:**
Workflow de rechazo de lotes nunca se implementó. Solo existe `registrar_lote` y `rechazar` (pero requiere Jefe de Área).

**Impacto:**
- ❌ Lotes defectuosos llegan a ventas
- ❌ Cliente rechaza, devoluciones
- ❌ Pérdida de confianza

**Pasos para Reproducir:**
```
1. Operario registra LoteProduccion
2. Detecta falla visual (hilo débil)
3. Intenta rechazar → NO hay opción
4. Lote queda válido en sistema
5. Se envía al cliente
6. Cliente rechaza por defecto
```

**Propuesta de Solución:**
```python
# 1. Agregar estado 'rechazado' a LoteProduccion
class LoteProduccion(models.Model):
    ESTADO_CHOICES = [
        ('en_proceso', 'En Proceso'),
        ('finalizado', 'Finalizado'),
        ('rechazado', 'Rechazado por Operario'),  # ← NUEVO
        ('segunda', 'Segunda'),
    ]
    estado = CharField(choices=ESTADO_CHOICES)

# 2. Crear endpoint de rechazo
class LoteProduccionViewSet(ViewSet):
    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        """Operario rechaza lote defectuoso"""
        lote = self.get_object()
        
        # Validar que solo operario asignado puede rechazar
        if lote.orden_produccion.operario_asignado != request.user:
            raise PermissionDenied("No es tu lote")
        
        serializer = RechazarLoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Cambiar estado y registrar razón
        lote.estado = 'rechazado'
        lote.motivo_rechazo = serializer.validated_data['motivo']
        lote.observaciones = serializer.validated_data.get('observaciones', '')
        lote.save()
        
        # CREAR NUEVA OP PARA RE-PRODUCCIÓN
        nueva_op = OrdenProduccion.objects.create(
            referencia_lote_anterior=lote,
            producto_entrada=lote.orden_produccion.producto_entrada,
            bodega_entrada=lote.orden_produccion.bodega_entrada,
            producto_salida=lote.orden_produccion.producto_salida,
            peso_neto_requerido=lote.peso_neto_producido,  # Misma cantidad
            prioridad='urgente'  # Expedite re-producción
        )
        
        return Response({
            'status': 'Lote rechazado',
            'motivo': lote.motivo_rechazo,
            'nueva_op': nueva_op.id
        })

# 3. Serializer
class RechazarLoteSerializer(Serializer):
    motivo = ChoiceField(choices=[
        ('hilo_roto', 'Hilo Roto'),
        ('color_incorrecto', 'Color Incorrecto'),
        ('peso_incorrecto', 'Peso Incorrecto'),
        ('defecto_visual', 'Defecto Visual'),
        ('otro', 'Otro')
    ])
    observaciones = CharField(required=False, allow_blank=True, max_length=500)
```

---

### P0-016: Vendedor NO Puede Aplicar Beneficios en Pedidos

**Ubicación:** `gestion/serializers.py` líneas 343-390 (DetallePedidoSerializer)

**Descripción:**
`DetallePedido.precio_unitario` es fijo. **NO hay campo para descuentos, bonificaciones o precios especiales.**

**Causa Raíz:**
Diseño simplista que no contempló negociación de precios por volumen o cliente importante.

**Impacto:**
- ❌ Vendedor no puede ofrecer descuento mayorista
- ❌ Cliente importante debe ir a competencia
- ❌ Pérdida de ingresos potenciales

**Pasos para Reproducir:**
```
1. Vendedor intenta crear pedido con descuento 10%
2. No hay campo en formulario
3. Crea pedido con precio normal
4. Cliente negocia: "¿No me haces descuento?"
5. Vendedor dice: "El sistema no lo permite"
6. Cliente se va a la competencia
```

**Propuesta de Solución:**
```python
# 1. Extender DetallePedido
class DetallePedido(models.Model):
    # Campos existentes...
    precio_unitario = DecimalField(max_digits=12, decimal_places=3)
    
    # NUEVOS CAMPOS
    descuento_porcentaje = DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Precalculado pero editable
    precio_final_unitario = DecimalField(max_digits=12, decimal_places=3)
    
    monto_beneficio = DecimalField(max_digits=12, decimal_places=3, default=0)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(precio_final_unitario__lte=models.F('precio_unitario')),
                name='precio_final_no_mayor_original'
            )
        ]

# 2. Servicio de validación de beneficios
class BeneficioService:
    def validar_descuento(self, cliente, producto, porcentaje):
        """Valida si el cliente tiene derecho al descuento"""
        
        # Política 1: Por volumen histórico
        volumen_anual = PedidoVenta.objects.filter(
            cliente=cliente,
            fecha_creacion__gte=date.today() - timedelta(days=365)
        ).aggregate(total=Sum('monto_total'))['total'] or 0
        
        if volumen_anual > 100000:
            max_descuento = 15  # Máximo 15%
        elif volumen_anual > 50000:
            max_descuento = 10  # Máximo 10%
        else:
            max_descuento = 5   # Máximo 5%
        
        # Política 2: Por relación comercial
        if cliente.es_cliente_importante:
            max_descuento = 20
        
        if porcentaje > max_descuento:
            raise ValidationError(
                f"Descuento máximo permitido: {max_descuento}% "
                f"(volumen anual: {volumen_anual})"
            )
        
        return True

# 3. Serializer mejorado
class DetallePedidoSerializer(Serializer):
    descuento_porcentaje = DecimalField(max_digits=5, decimal_places=2)
    
    def validate_descuento_porcentaje(self, value):
        cliente_id = self.parent.initial_data.get('cliente_id')
        producto_id = self.initial_data.get('producto_id')
        
        BeneficioService().validar_descuento(
            cliente=Cliente.objects.get(id=cliente_id),
            producto=Producto.objects.get(id=producto_id),
            porcentaje=value
        )
        return value
    
    def create(self, validated_data):
        # Calcular precio final
        precio_original = validated_data['precio_unitario']
        descuento = validated_data['descuento_porcentaje']
        
        validated_data['precio_final_unitario'] = precio_original * (1 - descuento / 100)
        validated_data['monto_beneficio'] = precio_original * (descuento / 100) * validated_data['peso']
        
        return super().create(validated_data)
```

---

### P0-017: Endpoint de Reversión de Pagos SIN Control de Rol

**Ubicación:** `gestion/views/sales_views.py` línea 200-254 (revertir_pago)

**Descripción:**
```python
@action(detail=True, methods=['post'])
def revertir_pago(self, request, pk=None):
    permission_classes = [IsAuthenticated]  # ← PROBLEMA: Cualquier usuario puede revertir
```

**Impacto:**
- ❌ Operario autenticado puede revertir pagos
- ❌ Posible fraude
- ❌ Sin control de auditoría por rol

**Propuesta de Solución:**
```python
@action(detail=True, methods=['post'], 
        permission_classes=[IsAuthenticated, IsVendedorOrExecutivoOrAdmin])
def revertir_pago(self, request, pk=None):
    pago = self.get_object()
    
    # Validar que vendedor solo revierte sus propios clientes
    if request.user.groups.filter(name='vendedor').exists():
        if pago.cliente.vendedor_asignado != request.user:
            raise PermissionDenied("No puedes revertir pagos de otros vendedores")
    
    # ... resto del código
```

---

## Problemas de Degradación (P1)

### P1-002: PaymentReconciler Pierde Sobrantes de Pago

**Ubicación:** `gestion/utils.py` líneas 41-100

**Problema:**
Si cliente paga 7000 pero debe 5000:
- Sistema reconcilia 5000 → deuda=0 ✓
- **Pero 2000 se pierden** ❌ (no hay concepto de "saldo a favor")

**Impacto:** Cliente pagó de más pero no hay registro. Próximo pedido no se descuenta.

**Solución:**
Crear modelo `AnticipoCliente` para saldos a favor.

---

### P1-003: PedidoVenta.esta_pagado es Binario

**Ubicación:** `gestion/models.py` línea 902

**Problema:**
Campo es `True/False`. Si pedido de 1000 recibe pago de 600:
- `esta_pagado = False`
- No hay forma de reportar: "60% pagado"

**Solución:**
Agregar campo `porcentaje_pagado` (Decimal 0-100).

---

### P1-007: DespachoReversionService — Búsqueda Frágil por String

**Ubicación:** `inventory/services/despacho_reversion.py` líneas 74-79

**Problema:**
```python
mov_original = MovimientoInventario.objects.filter(
    documento_ref__contains=f'Despacho #{historial.id}'
).first()
```

Si formato de `documento_ref` cambia, búsqueda falla silenciosamente.

**Solución:**
Crear `ForeignKey DetalleHistorialDespacho → MovimientoInventario`.

---

### P1-008: Inconsistencia de Decimales (2 vs 3 lugares)

**Ubicación:** `gestion/models.py`, `inventory/models.py`

**Problema:**
- `StockBodega.cantidad`: 2 decimales
- `DetallePedido.subtotal`: 3 decimales
- Después de 100 transacciones: error acumulado > 1%

**Solución:**
Standarizar a `Decimal(max_digits=12, decimal_places=3)` en TODO el proyecto.

---

*(Continúan P1-009 a P1-025... ver sección 5 para detalles por rol)*

---

## Análisis por Rol

### 🔴 Operario — FALTA FUNCIONALIDAD CRÍTICA

| Problema | Severidad | Estado |
|----------|-----------|--------|
| No puede rechazar lotes defectuosos | P0 | ❌ Bloqueante |
| No tiene permiso para cambiar operario_asignado | P1 | ⚠️ Fricción |
| No ve KPI de su producción en tiempo real | P2 | 📊 Mejora |

**Flujo Quebrado:**
```
Operario produce → Detecta falla → ??? → NO hay opción → Lote sigue adelante
```

**Acción Requerida:**
Implementar endpoint `POST /lotes/{id}/rechazar/` con workflow de re-producción.

---

### 🟠 Bodeguero — PARCIALMENTE FUNCIONAL

| Problema | Severidad | Estado |
|----------|-----------|--------|
| MRP no está integrado (manual) | P1 | ⚠️ Degradación |
| No hay sugerencias de compra | P1 | ⚠️ Reactividad |
| No se valida proveedor activo | P1 | ⚠️ Fricción |

**Acción Requerida:**
- Crear Celery task para ejecutar MRP cada 6 horas
- Crear endpoint `GET /api/ordenes-compra-sugeridas/`
- Integrar alertas de stock bajo en dashboard

---

### 🟡 Despacho — BIEN ESTRUCTURADO pero FALTA VALIDACIÓN

| Problema | Severidad | Estado |
|----------|-----------|--------|
| Scanning NO valida fórmula correcta | P1 | ⚠️ Riesgo |
| Reversión no es atómica si falla | P1 | ⚠️ Inconsistencia |
| No hay validación de composición | P1 | ⚠️ Calidad |

---

### 🔴 Vendedor — CRÍTICO: NO PUEDE NEGOCIAR NI REVERTIR

| Problema | Severidad | Estado |
|----------|-----------|--------|
| NO puede aplicar descuentos/beneficios | P0 | ❌ Bloquea ventas |
| Permisos para revertir son abiertos | P0 | ❌ Riesgo fraude |
| No ve dashboard de su cartera | P1 | ⚠️ Ceguera |

**Impacto en Negocio:**
Vendedor pierde clientes porque no puede negociar precios.

---

### 🟢 Jefe de Área — FUNCIONAL

| Problema | Severidad | Estado |
|----------|-----------|--------|
| Sin sugerencias automáticas de máquina | P1 | ⚠️ Ineficiencia |
| Priorización no sincroniza con vencimientos | P1 | ⚠️ Retrasos |

---

### 🟢 Jefe de Planta — FUNCIONAL

| Problema | Severidad | Estado |
|----------|-----------|--------|
| KPIs lentos (>5s) sin caché | P1 | ⚠️ UX |

---

### 🟡 Tintorero — BIEN ESTRUCTURADO pero FALTA CALIDAD

| Problema | Severidad | Estado |
|----------|-----------|--------|
| NO puede registrar cantidad real de químicos | P1 | ⚠️ Waste tracking |
| NO hay trazabilidad de calidad de tinte | P1 | ⚠️ Variaciones |

**Acción Requerida:**
Crear modelo `TinteResultado` para densidad, pH, temperatura.

---

### 🟢 Ejecutivo — FUNCIONAL

| Problema | Severidad | Estado |
|----------|-----------|--------|
| Cartera vencida sin drill-down | P1 | ⚠️ Análisis |

---

### 🟢 Admin — FUNCIONAL

| Problema | Severidad | Estado |
|----------|-----------|--------|
| No hay auditoría de cambios de permisos | P1 | ⚠️ Compliance |

---

## Funcionalidades Faltantes para Industria Textil

### 🔴 F0-001: NO hay trazabilidad de materia prima (MP)

**Problema:**
LoteProduccion registra lote pero NO guarda:
- ❌ Proveedor de hilo de entrada
- ❌ Lote del proveedor
- ❌ Fecha de importación
- ❌ Costo real (solo hay precio_base)

**Impacto:**
- No se puede responder: "¿De dónde vino este hilo?"
- Imposible recall o garantía
- Contabilidad no puede cerrar costos

**Solución Propuesta:**
```python
class MateriaPrimaLote(models.Model):
    """Trazabilidad de materia prima"""
    producto = ForeignKey(Producto)  # Hilo
    proveedor = ForeignKey(Proveedor)
    lote_proveedor = CharField(max_length=50)  # Lote externo
    fecha_recepcion = DateField()
    cantidad_kg = DecimalField(max_digits=12, decimal_places=3)
    costo_unitario = DecimalField(max_digits=12, decimal_places=3)
    certificado_calidad = FileField(upload_to='certificados/')

class LoteProduccion(models.Model):
    # Campos existentes...
    materia_prima_lotes = ManyToManyField(MateriaPrimaLote, through='ConsumoMateriaPrima')
```

---

### 🔴 F0-002: NO se calcula costo de producción

**Problema:**
Sistema rastrea costos de entrada pero **NO calcula costo total por lote**.
Vendedor no sabe margen real.

**Impacto:**
- Decisiones de precio sin fundamento
- Márgenes pueden ser negativos (no se sabe)
- Ineficiencia de producción invisible

**Solución:**
```python
class CostoLoteProduccion(models.Model):
    lote_produccion = OneToOneField(LoteProduccion)
    
    # Desglose
    costo_materia_prima = DecimalField()
    costo_quimicos = DecimalField()
    costo_horas_operario = DecimalField()
    costo_amortizacion_maquina = DecimalField()
    otros_costos = DecimalField()
    
    total_costo = DecimalField()
    precio_venta_esperado = DecimalField()
    margen_bruto = DecimalField()
    margen_bruto_pct = DecimalField()
```

---

### 🔴 F0-003: NO hay control de desperdicios por máquina/operario

**Problema:**
`LoteProduccion.peso_merma` existe pero **NO hay analytics**.
- No se rastrea: ¿Máquina 01 tiene tasa merma 5%?
- No se rastrea: ¿Operario A desperdicia más?

**Impacto:**
- No se puede optimizar producción
- Desperdicios recurrentes no se detectan

---

### 🔴 F0-004: NO se rastrea composición de tejidos

**Problema:**
`Producto.tipo='tela'` pero **NO hay composición**.
Si cliente solicita "80% algodón", no se valida.

---

### 🔴 F0-005: NO hay alertas automáticas de stock crítico

**Problema:**
`Producto.stock_minimo` existe pero no se ejecuta verificación automática.

---

### 🟡 F1-006: NO se rastrea calidad de tintes

**Problema:**
`FormulaColor` es template pero **NO hay registro de cómo salió el tinte real**.
Tintorero no puede reportar: "Quedó desaturado".

---

### 🟡 F1-007: NO hay trazabilidad de transformación (lotes entrada → salida)

**Problema:**
`ConsumoLoteDetalle` existe pero no hay visualización clara: "Lote L1 + L2 → L3".

---

## Problemas de Arquitectura y Patrones

### Fortalezas ✅

| Aspecto | Implementación |
|---------|---|
| **Service Layer** | DescargaQuimicosService, PagoReversionService bien estructurados |
| **Auditoría** | AuditableModelMixin implementado correctamente |
| **Transacciones** | @transaction.atomic() en operaciones críticas |
| **Permisos** | RBAC basado en grupos con factory |
| **Separación de Responsabilidades** | Models, Serializers, Views claros |

### Debilidades ❌

| Problema | Ubicación | Severidad |
|----------|-----------|-----------|
| Race conditions sin SELECT FOR UPDATE | ClienteManager | P0 |
| Falta de constraints CHECK en BD | StockBodega, DetallePedido | P0 |
| Coupling débil (búsquedas por string) | DespachoReversionService | P1 |
| Sin caché para datos read-heavy | KPI endpoints | P1 |
| Permisos demasiado permisivos | revertir_pago | P0 |
| Cobertura de tests baja | Proyecto completo | P2 |
| Docstrings incompletos | Servicios | P2 |

### Recomendaciones SOLID

| Principio | Problema Actual | Refactorización Necesaria |
|-----------|-----------------|--------------------------|
| **Single Responsibility** | DescargaQuimicosService hace demasiado | Dividir en: DescargaChemicalService + StockValidationService |
| **Open/Closed** | Nuevos tipos de beneficios requieren cambiar código | Crear BenefitStrategy interface |
| **Liskov Substitution** | MovimientoInventario.tipo hardcodeado | Usar polimorfismo o enum |
| **Interface Segregation** | ViewSet hereda demasiados métodos | Crear mixins específicos |
| **Dependency Inversion** | Services importan models directamente | Usar inyección de dependencias |

---

## Plan de Acción Prioritario

### 📅 Semana 1 — Bloqueantes (P0 verificados)

1. **P0-017: Restringir permisos en revertir/destroy de PagoCliente** *(empezar aquí: menor esfuerzo, mayor riesgo)*
   - Tiempo: 2h
   - Impact: Prevenir fraude — hoy cualquier rol autenticado puede revertir pagos

2. **P0-005: Atomicidad y lock en flujo de pagos** *(refinado tras verificación)*
   - Envolver `perform_create` + `PaymentReconciler` en `transaction.atomic` con `select_for_update` sobre Cliente
   - Validar monto del pago vs. saldo (rechazar o derivar a anticipo)
   - Tiempo: 6h
   - Impact: Eliminar race condition + corregir desincronización de `esta_pagado` (causa probable de los errores de colas de facturas/valores pendientes)

3. **P0-006: Agregar validación de stock + constraint CHECK**
   - Tiempo: 6h
   - Impact: Evitar stock negativo en descarga de químicos

4. **P0-001: Crear modelo FacturaVenta**
   - Tiempo: 8h
   - Impact: Cumplimiento fiscal (requiere definir alcance SRI con el usuario)

~~5. P0-010: Crear endpoint rechazar lotes~~ — **ELIMINADO: refutado, el endpoint ya existe**

5. **P0-016 (reclasificado P1): Descuento por línea en DetallePedido**
   - Tiempo: 8h
   - Impact: Complementa el mecanismo de beneficios existente (`nivel_precio`/`tiene_beneficio`)

**Total Semana 1: 22h de P0 confirmados + 8h de mejora reclasificada**

---

### 📅 Semana 2 — Degradación (P1)

1. **P1-002: Crear modelo AnticipoCliente**
   - Tiempo: 6h
   - Impact: Rastrear sobrantes de pago

2. **P1-003: Agregar porcentaje_pagado a PedidoVenta**
   - Tiempo: 4h

3. **P1-007: Cambiar búsqueda string a FK en DespachoReversión**
   - Tiempo: 6h

4. **P1-008: Standarizar decimales a 3 lugares**
   - Tiempo: 12h (incluye migraciones)

5. **Otros P1 (8-11 restantes)**
   - Tiempo: 20h

**Total Semana 2: 48 horas**

---

### 📅 Mes 1 — Funcionalidades Textil (F0/F1)

1. **F0-001: Modelo MateriaPrimaLote**
   - Tiempo: 12h
   - Impact: Trazabilidad de MP

2. **F0-002: Modelo CostoLoteProduccion**
   - Tiempo: 10h
   - Impact: Márgenes calculados

3. **F0-003: Tabla MermaAnalysis**
   - Tiempo: 8h
   - Impact: Analytics de desperdicios

4. **F1-005: Alertas automáticas de stock**
   - Tiempo: 8h
   - Impact: Prevenir paros

5. **F1-006: Modelo TinteResultado**
   - Tiempo: 8h
   - Impact: Control de calidad

**Total Mes 1: 46 horas (adicional a semanas 1-2)**

---

### 🔬 Fase de Pruebas — ISTQB Completo

**Después de cada refactorización:**

1. **Pruebas Caja Blanca (Unit Tests)**
   - EP (Equivalence Partitioning): casos normales, edge, error
   - BVA (Boundary Value Analysis): límites de decimales, stock
   - Decision Table: flujos de descuento, reconciliación

2. **Pruebas Caja Negra (Integration Tests)**
   - Validar contratos de API
   - Verificar transacciones atómicas
   - Concurrencia (race condition test)

3. **Pruebas TDD**
   - Tests ANTES de código
   - Red → Green → Refactor

4. **Security (SSD)**
   - OWASP Top 10
   - SQL Injection prevention
   - Authentication/Authorization

---

## Próximos Pasos con Fable 5

Este documento CONTEXTO proporciona:

1. ✅ **Diagnóstico exhaustivo** de 25 problemas
2. ✅ **Propuestas de solución** con código de ejemplo
3. ✅ **Plan de acción prioritario** con estimaciones
4. ✅ **Análisis SOLID** para refactorización

### Flujo Recomendado:

```
1. Fable 5 revisa CONTEXTO.md
   ↓
2. Fable 5 valida prioridades y propuestas
   ↓
3. Acordar plan de Sprints (Semana 1-2 P0, Semana 3-4 P1, etc.)
   ↓
4. Implementación paralela:
   - Refactorización SOLID + Clean Code
   - Pruebas ISTQB (caja blanca, caja negra, TDD, SSD)
   - Documentación actualizada
   ↓
5. Actualizar CONTEXTO.md con cambios realizados
   ↓
6. Validar pre-producción
```

---

## Conclusión

**TexCore está 60% listo para producción.**

- Arquitectura es sólida (Service Layer, AuditLog)
- Pero tiene **gaps críticos** en validaciones y permisos (P0)
- Y **funcionalidades incompletas** para industria textil (F0)

**Con 2-3 sprints de refactorización SOLID + pruebas ISTQB, puede estar 95% listo.**

---

**Próximo paso:** Enviar este CONTEXTO.md a Fable 5 para revisión y validación de plan de acción.

---

*Documento generado: 10 de Junio de 2026*  
*Auditor: Brandon Arellano*  
*Status: Listo para Revisión Fable 5*
