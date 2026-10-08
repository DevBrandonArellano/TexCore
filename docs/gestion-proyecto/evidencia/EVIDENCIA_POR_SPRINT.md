# Evidencia de pruebas por sprint — TexCore

> Generado por `scripts/evidencia/evidencia_sprints.py`. No editar a mano: volver a ejecutar el script.
>
> **Fecha:** 2026-10-08 10:34 -05 · **Commit:** `dec016c` con cambios sin commitear · **Rama:** `MES`
> **Backend:** `TexCore.settings_test` (SQL Server 2022)
> Reportes JUnit crudos en `junit/`. Las historias sin prueba automatizada se demuestran con
> `CHECKLIST_EVIDENCIA_MANUAL.md`.

## Resumen

| Sprint | Historias | Con prueba automatizada | Pruebas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 5 | 0 | 0 | 0 | 0 | 0 | ✅ + 📋 manual |
| 1 | 5 | 5 | 53 | 53 | 0 | 0 | ✅ |
| 2 | 7 | 7 | 444 | 444 | 0 | 0 | ✅ |
| 3 | 6 | 6 | 151 | 151 | 0 | 0 | ✅ |
| 4 | 6 | 6 | 209 | 209 | 0 | 0 | ✅ |
| 5 | 7 | 7 | 80 | 80 | 0 | 0 | ✅ |
| 6 | 7 | 7 | 268 | 268 | 0 | 0 | ✅ |
| 7 | 5 | 5 | 199 | 199 | 0 | 0 | ✅ |
| 8 | 6 | 5 | 1651 | 1651 | 0 | 0 | ✅ + 📋 manual |

Una prueba citada por varias historias se cuenta en cada una (ej. `test_production_views.py`).
Las omitidas llevan su motivo en el reporte JUnit (ej. permisos POSIX que solo existen en Linux).

## Sprint 0

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-01** Orquestación de contenedores con Docker Compose | — | 0 | 0 | 0 | 0 | 📋 evidencia manual |
| **TEX-02** Red de contenedores aislada y comunicación entre servicios | — | 0 | 0 | 0 | 0 | 📋 evidencia manual |
| **TEX-03** API Gateway con Nginx como punto único de entrada | — | 0 | 0 | 0 | 0 | 📋 evidencia manual |
| **TEX-04** Pipeline de CI con Quality Gates | — | 0 | 0 | 0 | 0 | 📋 evidencia manual |
| **TEX-05** Estructura base del repositorio y estándares de desarrollo | — | 0 | 0 | 0 | 0 | 📋 evidencia manual |

## Sprint 1

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-06** Autenticación con JWT en cookies HttpOnly | `gestion/tests/test_cookie_jwt_auth.py` | 6 | 6 | 0 | 0 | ✅ |
| **TEX-07** Control de acceso basado en roles para los once roles | `inventory/tests/test_roles_rbac.py` | 8 | 8 | 0 | 0 | ✅ |
| **TEX-08** Aislamiento multi-sede de la información | `gestion/tests/test_cliente_sede_filtering.py` | 4 | 4 | 0 | 0 | ✅ |
| **TEX-09** Registro de auditoría inmutable en operaciones críticas | `gestion/tests/test_audit_middleware.py`<br>`gestion/tests/test_auditlog_inmutable.py` | 31 | 31 | 0 | 0 | ✅ |
| **TEX-10** Justificación obligatoria en modificación de datos maestros | `gestion/tests/test_cliente_auditoria_justificacion.py` | 4 | 4 | 0 | 0 | ✅ |

## Sprint 2

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-11** Creación de Órdenes de Producción | `gestion/tests/test_production_views.py`<br>`gestion/tests/test_descarga_quimicos_tdd.py` | 93 | 93 | 0 | 0 | ✅ |
| **TEX-12** Registro de lote de producción en un solo paso | `gestion/tests/test_registro_lote_estado_op.py`<br>`gestion/tests/test_registro_lote_lock.py`<br>`gestion/tests/test_registro_lote_merma.py`<br>`gestion/tests/test_registro_lote_sincronizacion_mes.py`<br>`gestion/tests/test_registro_lote_transformacion.py` | 15 | 15 | 0 | 0 | ✅ |
| **TEX-13** Asignación de máquina y operario a una orden | `gestion/tests/test_production_views.py` | 80 | 80 | 0 | 0 | ✅ |
| **TEX-14** Máquina de estados del ciclo de vida de la orden | `gestion/tests/test_production_views.py` | 80 | 80 | 0 | 0 | ✅ |
| **TEX-15** Gestión de maquinaria del área | `gestion/tests/test_production_views.py` | 80 | 80 | 0 | 0 | ✅ |
| **TEX-16** Rechazo de lote con reversión de inventario | `gestion/tests/test_production_views.py` | 80 | 80 | 0 | 0 | ✅ |
| **TEX-17** Monitoreo del avance de planta | `gestion/tests/test_produccion_kpi_service.py` | 16 | 16 | 0 | 0 | ✅ |

## Sprint 3

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-18** Kárdex transaccional con saldo en tiempo real | `inventory/tests/test_views_endpoints.py`<br>`gestion/tests/test_metros_tela_precision.py` | 33 | 33 | 0 | 0 | ✅ |
| **TEX-19** Entrada de materia prima con trazabilidad de lote | `gestion/tests/test_materia_prima_f0_001.py` | 9 | 9 | 0 | 0 | ✅ |
| **TEX-20** Transferencia de existencias entre bodegas | `inventory/tests/test_serializers.py`<br>`inventory/tests/test_views_endpoints.py` | 34 | 34 | 0 | 0 | ✅ |
| **TEX-21** Edición auditada de movimientos de inventario | `inventory/tests/test_movimiento_views.py` | 15 | 15 | 0 | 0 | ✅ |
| **TEX-22** Consulta y exportación del kárdex | `inventory/tests/test_views_endpoints.py`<br>`inventory/tests/test_kardex_service.py`<br>`internal_api/tests/test_reporting_data_kardex.py` | 52 | 52 | 0 | 0 | ✅ |
| **TEX-23** Filtrado de bodegas por rol y sede | `gestion/tests/test_inventory_views.py` | 8 | 8 | 0 | 0 | ✅ |

## Sprint 4

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-24** Transformación de productos con cálculo de merma | `gestion/tests/test_production_views.py` | 80 | 80 | 0 | 0 | ✅ |
| **TEX-25** Bloqueo de saldos negativos de inventario | `gestion/tests/test_descarga_quimicos_stock_p0.py`<br>`gestion/tests/test_consumo_mezcla_service.py` | 14 | 14 | 0 | 0 | ✅ |
| **TEX-26** Alertas de stock bajo | `inventory/tests/test_views_endpoints.py` | 27 | 27 | 0 | 0 | ✅ |
| **TEX-27** Motor MRP de cálculo de requerimientos | `inventory/tests/test_mrp.py` | 1 | 1 | 0 | 0 | ✅ |
| **TEX-28** Consulta de requisitos de materiales de una orden | `gestion/tests/test_production_views.py` | 80 | 80 | 0 | 0 | ✅ |
| **TEX-29** Registro de merma vendible | `gestion/tests/test_merma_stock_service.py` | 7 | 7 | 0 | 0 | ✅ |

## Sprint 5

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-30** Directorio de clientes con aislamiento de cartera | `gestion/tests/test_cliente_sede_filtering.py` | 4 | 4 | 0 | 0 | ✅ |
| **TEX-31** Registro de pedidos de venta | `gestion/tests/test_catalog_views.py` | 14 | 14 | 0 | 0 | ✅ |
| **TEX-32** Validación automática de límite de crédito | `gestion/tests/test_catalog_views.py` | 14 | 14 | 0 | 0 | ✅ |
| **TEX-33** Validación de precio mínimo de venta | `gestion/tests/test_serializers.py` | 7 | 7 | 0 | 0 | ✅ |
| **TEX-34** Reconciliación de pagos con criterio FIFO | `gestion/tests/test_pago_reversion.py` | 6 | 6 | 0 | 0 | ✅ |
| **TEX-35** Reversión auditada de pagos | `gestion/tests/test_pago_reversion.py` | 6 | 6 | 0 | 0 | ✅ |
| **TEX-36** Estado de cuenta del cliente | `gestion/tests/test_catalog_views.py`<br>`frontend/src/components/vendedor/VendedorDashboard.cliente.test.tsx` | 29 | 29 | 0 | 0 | ✅ |

## Sprint 6

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-37** Recetas de tintorería por fases | `gestion/tests/test_formula_views.py` | 15 | 15 | 0 | 0 | ✅ |
| **TEX-38** Versionamiento de fórmulas de color | `gestion/tests/test_formula_views.py` | 15 | 15 | 0 | 0 | ✅ |
| **TEX-39** Calculadora de dosificación asociada a la orden | `gestion/tests/test_services_formula.py` | 9 | 9 | 0 | 0 | ✅ |
| **TEX-40** Descarga automática de químicos al inventario | `gestion/tests/test_descarga_quimicos_validaciones.py`<br>`gestion/tests/test_descarga_quimicos_stock_p0.py` | 7 | 7 | 0 | 0 | ✅ |
| **TEX-41** Registro de pesaje en estación de empaquetado | `gestion/tests/test_configuracion_empaque_sede.py` | 17 | 17 | 0 | 0 | ✅ |
| **TEX-42** Emisión de etiqueta ZPL para impresoras Zebra | `printing_service/tests`<br>`gestion/tests/test_production_views.py` | 174 | 174 | 0 | 0 | ✅ |
| **TEX-43** Equivalencias de empaque configurables por sede | `gestion/tests/test_configuracion_empaque_sede.py`<br>`gestion/tests/test_configuracion_empaque_api.py` | 31 | 31 | 0 | 0 | ✅ |

## Sprint 7

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-44** Microservicio de escaneo de códigos QR y de barras | `scanning_service/tests` | 58 | 58 | 0 | 0 | ✅ |
| **TEX-45** Despacho atómico con descarga de inventario | `inventory/tests/test_despacho_reversion.py` | 8 | 8 | 0 | 0 | ✅ |
| **TEX-46** Panel ejecutivo de indicadores | `gestion/tests/test_kpi_views.py`<br>`inventory/tests/test_executive_kpi_service.py` | 31 | 31 | 0 | 0 | ✅ |
| **TEX-47** Microservicio de reportes en Excel | `reporting_excel/tests` | 76 | 76 | 0 | 0 | ✅ |
| **TEX-48** Drill-down sobre los indicadores | `gestion/tests/test_kpi_views.py` | 26 | 26 | 0 | 0 | ✅ |

## Sprint 8

| Historia | Pruebas citadas en el backlog | Ejecutadas | Aprobadas | Fallidas | Omitidas | Estado |
|---|---|---:|---:|---:|---:|---|
| **TEX-49** Panel de Administrador de Sistemas | `gestion/tests/test_catalog_views.py` | 14 | 14 | 0 | 0 | ✅ |
| **TEX-50** Panel de Administrador de Sede | `inventory/tests/test_roles_rbac.py` | 8 | 8 | 0 | 0 | ✅ |
| **TEX-51** Gestión de catálogos maestros | `gestion/tests/test_catalog_views.py`<br>`gestion/tests/test_serializers.py` | 21 | 21 | 0 | 0 | ✅ |
| **TEX-52** Consulta del registro de auditoría | `inventory/tests/test_audit_logs_sede.py`<br>`frontend/src/components/shared/AuditLogViewer.test.tsx` | 38 | 38 | 0 | 0 | ✅ |
| **TEX-53** Persistencia del estado de navegación en la URL | `frontend/src/components/Layout.test.tsx`<br>`frontend/src/components/Login.test.tsx`<br>`frontend/src/components/admin-sede/AdminSedeDashboard.test.tsx`<br>`frontend/src/components/admin-sistemas/AdminSistemasDashboard.test.tsx`<br>`frontend/src/components/admin-sistemas/InventoryDashboard.reportes.test.tsx`<br>`frontend/src/components/admin-sistemas/InventoryDashboard.test.tsx`<br>`frontend/src/components/admin-sistemas/KardexView.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageAreas.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageBodegas.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageClientes.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageFormulas.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageProcesos.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageProductos.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageProveedores.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageQuimicos.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageSedes.test.tsx`<br>`frontend/src/components/admin-sistemas/ManageUsers.test.tsx`<br>`frontend/src/components/admin-sistemas/MateriaPrimaView.test.tsx`<br>`frontend/src/components/admin-sistemas/RegistrarEntradaView.test.tsx`<br>`frontend/src/components/admin-sistemas/ReportesView.test.tsx`<br>`frontend/src/components/admin-sistemas/StockAFechaView.test.tsx`<br>`frontend/src/components/admin-sistemas/StockView.test.tsx`<br>`frontend/src/components/admin-sistemas/TransformationView.test.tsx`<br>`frontend/src/components/bodeguero/AuditoriaDialog.test.tsx`<br>`frontend/src/components/bodeguero/BodegueroDashboard.test.tsx`<br>`frontend/src/components/bodeguero/EditarMovimientoDialog.test.tsx`<br>`frontend/src/components/bodeguero/EliminarMovimientoDialog.test.tsx`<br>`frontend/src/components/bodeguero/RegistrarMermaDialog.test.tsx`<br>`frontend/src/components/despacho/DespachoDashboard.test.tsx`<br>`frontend/src/components/despacho/GuiaRemisionModal.test.tsx`<br>`frontend/src/components/despacho/HistorialDespachos.test.tsx`<br>`frontend/src/components/ejecutivos/DrillDownModals.test.tsx`<br>`frontend/src/components/ejecutivos/EjecutivosDashboard.produccion-por-producto.test.tsx`<br>`frontend/src/components/ejecutivos/EjecutivosDashboard.reportes.test.tsx`<br>`frontend/src/components/ejecutivos/EjecutivosDashboard.test.tsx`<br>`frontend/src/components/ejecutivos/VentasTab.test.tsx`<br>`frontend/src/components/empaquetado/BuscadorLotes.test.tsx`<br>`frontend/src/components/empaquetado/EmpaquetadoDashboard.test.tsx`<br>`frontend/src/components/empaquetado/HistorialEtiquetasModal.test.tsx`<br>`frontend/src/components/empaquetado/ReetiquetarModal.test.tsx`<br>`frontend/src/components/figma/ImageWithFallback.test.tsx`<br>`frontend/src/components/jefe-area/ComponenteMezclaPanel.test.tsx`<br>`frontend/src/components/jefe-area/JefeAreaDashboard.test.tsx`<br>`frontend/src/components/jefe-area/ManageLineas.test.tsx`<br>`frontend/src/components/jefe-area/ManageMaquinas.test.tsx`<br>`frontend/src/components/jefe-area/MaquinaDialog.test.tsx`<br>`frontend/src/components/jefe-area/OrdenesAsignacionPanel.test.tsx`<br>`frontend/src/components/jefe-area/ProcesosMaquinaDialog.test.tsx`<br>`frontend/src/components/jefe-area/RechazarLoteDialog.test.tsx`<br>`frontend/src/components/jefe-area/RegistrarParoModal.test.tsx`<br>`frontend/src/components/jefe-area/ReporteEficienciaArea.test.tsx`<br>`frontend/src/components/jefe-planta/DosificacionOrdenPanel.test.tsx`<br>`frontend/src/components/jefe-planta/JefePlantaDashboard.test.tsx`<br>`frontend/src/components/jefe-planta/ManageOrdenesProduccion.crud.test.tsx`<br>`frontend/src/components/jefe-planta/ManageOrdenesProduccion.test.tsx`<br>`frontend/src/components/jefe-planta/OrdenDetalleSheet.test.tsx`<br>`frontend/src/components/jefe-planta/PlanProduccionMTS.test.tsx`<br>`frontend/src/components/jefe-planta/ordenUtils.test.tsx`<br>`frontend/src/components/lotes/FichaLoteDialog.test.tsx`<br>`frontend/src/components/lotes/TablaLotesPaginada.test.tsx`<br>`frontend/src/components/lotes/paneles/PanelGenealogia.test.tsx`<br>`frontend/src/components/lotes/paneles/PanelesConsumoCosto.test.tsx`<br>`frontend/src/components/operario/OperarioDashboard.test.tsx`<br>`frontend/src/components/produccion/CorridaContinuaDashboard.test.tsx`<br>`frontend/src/components/produccion/EtapasProduccion.test.tsx`<br>`frontend/src/components/produccion/FlujoProduccion.test.tsx`<br>`frontend/src/components/produccion/RegistrarTransformacion.test.tsx`<br>`frontend/src/components/produccion/RegistrosTransformacion.test.tsx`<br>`frontend/src/components/produccion/TransferenciasInterarea.test.tsx`<br>`frontend/src/components/produccion/TrazabilidadPorCodigoPage.test.tsx`<br>`frontend/src/components/produccion/TrazabilidadProducto.test.tsx`<br>`frontend/src/components/shared/AuditLogViewer.test.tsx`<br>`frontend/src/components/shared/ConfiguracionEmpaqueView.test.tsx`<br>`frontend/src/components/shared/ErrorBoundary.test.tsx`<br>`frontend/src/components/shared/JustificacionDialog.test.tsx`<br>`frontend/src/components/shared/MRPDashboard.test.tsx`<br>`frontend/src/components/shared/MovementApproval.test.tsx`<br>`frontend/src/components/shared/SharedKPIChart.test.tsx`<br>`frontend/src/components/tintura/DerivadasFormula.test.tsx`<br>`frontend/src/components/tintura/DescargasQuimicosTintoreria.test.tsx`<br>`frontend/src/components/tintura/DosificacionFormulaPanel.test.tsx`<br>`frontend/src/components/tintura/FormulaDetalle.test.tsx`<br>`frontend/src/components/tintura/FormulaQuimica.test.tsx`<br>`frontend/src/components/tintura/HistorialOrdenesTintoreria.test.tsx`<br>`frontend/src/components/tintura/ManageProcesosTintoreria.test.tsx`<br>`frontend/src/components/tintura/RecetaVersionDialog.test.tsx`<br>`frontend/src/components/tintura/StockQuimicosDashboard.test.tsx`<br>`frontend/src/components/tintura/TintoreroDashboard.test.tsx`<br>`frontend/src/components/tintura/VersionesFormulaPanel.test.tsx`<br>`frontend/src/components/ui/button.test.tsx`<br>`frontend/src/components/ui/controles-paginacion.test.tsx`<br>`frontend/src/components/ui/product-select.test.tsx`<br>`frontend/src/components/vendedor/EditarPedidoModal.test.tsx`<br>`frontend/src/components/vendedor/NuevaVentaDialog.test.tsx`<br>`frontend/src/components/vendedor/SeguimientoPedidoMTOModal.test.tsx`<br>`frontend/src/components/vendedor/VendedorDashboard.anulacion.test.tsx`<br>`frontend/src/components/vendedor/VendedorDashboard.cliente.test.tsx`<br>`frontend/src/components/vendedor/VendedorDashboard.cobranza.test.tsx`<br>`frontend/src/components/vendedor/VendedorDashboard.detalle.test.tsx`<br>`frontend/src/components/vendedor/VendedorDashboard.sinvendedor.test.tsx`<br>`frontend/src/components/vendedor/VendedorDashboard.test.tsx` | 1570 | 1570 | 0 | 0 | ✅ |
| **TEX-54** Congelamiento de código y despliegue en staging | Pipeline de CI/CD y `scripts/run_backend_tests.sh`. | 0 | 0 | 0 | 0 | 📋 evidencia manual |
