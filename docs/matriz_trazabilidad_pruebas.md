# Matriz de Trazabilidad de Pruebas — TexCore (Backend)

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

## Matriz

### Seguridad y autenticación

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Autenticación JWT por cookie (válida/expirada/ausente) | `gestion/tests/test_cookie_jwt_auth.py` | EP, CB-D | ✅ |
| Auditoría: extracción segura de IP / anti-spoofing X-Forwarded-For | `gestion/tests/test_audit_middleware.py` | EP, BVA, CB-D | ✅ |
| Relay de logs de frontend (mapeo de severidad RFC 5424) | `gestion/tests/test_system_views.py` | EP, BVA, CB-D | ✅ |

### Vistas / API (RBAC y contratos)

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Bodegas: filtrado por rol y sede, escritura restringida | `gestion/tests/test_inventory_views.py` | TD, EP, CB-D | ✅ |
| KPIs de área y ejecutivos (autorización + contrato JSON) | `gestion/tests/test_kpi_views.py` | TD, EP, CB-D | ✅ |
| Catálogo (químicos/productos/proveedores), filtro de seguridad vendedor | `gestion/tests/test_catalog_views.py` | EP, TD, CB-D | ✅ |
| Fórmulas: dosificación, duplicar, exportar, RBAC por acción | `gestion/tests/test_formula_views.py` | EP, TD, CB-D | ✅ |
| Inventario: stock, transferencia, alertas, kardex | `inventory/tests/test_views_endpoints.py` | EP, BVA, CB-D | ✅ |
| Matriz RBAC de endpoints de inventario | `inventory/tests/test_roles_rbac.py` | TD | ✅ |
| Producción: máquinas, OP (completar/update/destroy/requisitos/stock-quimicos), lotes (genealogía/ZPL/costeo/corrección/rechazo) | `gestion/tests/test_production_views.py` | TD, EP, BVA, CB-D, STT | ✅ |
| Subprocesos de OP: máquina de estados (iniciar/completar/pausar/rechazar) | `gestion/tests/test_production_views.py` | STT | ✅ |
| Movimientos de inventario: entradas/salidas + edición auditada | `inventory/tests/test_movimiento_views.py` | EP, BVA, CB-D | ✅ |

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
| MRP (requerimientos y sugerencias de compra) | `inventory/tests/test_mrp.py` | EP | ✅ |
| Reversión de despacho (cascada, FK/fallback) | `inventory/tests/test_despacho_reversion.py` | STT, CB-D | ✅ |
| Transición de bodega (protocolo 3 fases) | `inventory/tests/test_transicion_3_fase_p1.py` | STT | ✅ |
| KPIs ejecutivos | `inventory/tests/test_executive_kpi_service.py` | EP | ✅ |

### Serializers (validación de entrada)

| Requisito / Módulo | Archivo de prueba | Técnicas | Estado |
|---|---|---|---|
| Nombre alfanumérico con acentos; dosificación > 0 | `gestion/tests/test_serializers.py` | EP, BVA | ✅ |
| Actualización de movimiento (cantidad > 0, razón ≥ 10) y transferencia | `inventory/tests/test_serializers.py` | BVA, caja negra | ✅ |

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

## Estado de cobertura

Cobertura medida sobre el **código de aplicación** (`gestion`, `inventory`). Los
comandos de management (`*/management/commands/*` — utilitarios operativos de
seed/stress de datos, ~1.232 líneas sin valor de prueba unitaria) se excluyen vía
`omit` en `.coveragerc`, práctica estándar de coverage.

| Hito | Cobertura | Tests |
|------|-----------|-------|
| Baseline (suite nunca ejecutada) | 58.0% | 220/243 (14 rojos) |
| Tras Fases 0–3 (seguridad, vistas, servicios, serializers) | 63.5% | 337 ✅ |
| Tras módulos grandes (production_views, movimientos) | **81.2%** | **379 ✅** |

Umbral mínimo `fail_under = 78` en `.coveragerc` (piso protegido con margen). Se
obtiene con el harness (`bash scripts/run_backend_tests.sh` → `coverage report`).
