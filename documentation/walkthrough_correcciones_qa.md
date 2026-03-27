# 🚀 Walkthrough: Corrección de Defectos QA (TexCore ERP)

> **Estado:** Finalizado & Validado ✅  
> **Fecha:** 2026-03-27  
> **Responsable:** Senior SDET / QA Lead  
> **Referencia:** [Plan de Pruebas Técnico](plan_pruebas_texcore.md)

---

## 📅 Control de Cambios

| Versión | Fecha | Autor | Descripción |
| :--- | :--- | :--- | :--- |
| 1.0 | 2026-03-27 | QA Team | Implementación de correcciones críticas (D-01 a D-06) tras auditoría técnica. |

---

## 🛠️ Detalle de Correcciones Implementadas

Este documento resume las correcciones técnicas aplicadas para resolver los 6 defectos identificados durante la auditoría de QA, asegurando la integridad de los datos y la robustez de los procesos de negocio.

### 1. Módulo de Gestión (`gestion`)
- **D-01 (CRÍTICO): NameError en Proveedores**
  - **Ubicación:** `gestion/views.py` -> `ProveedorViewSet.get_queryset()`.
  - **Problema:** Intento de filtrar por `sede_id` sin haber definido la variable en el contexto del método.
  - **Corrección:** Se inicializó la variable capturando el parámetro desde `self.request.query_params`.
  
- **D-02 (MEDIO): Código Inalcanzable en Pedidos**
  - **Ubicación:** `gestion/serializers.py` -> `PedidoVentaSerializer`.
  - **Problema:** Existía una definición de `read_only_fields` dentro de un método `get_fecha_pedido` después de la sentencia `return`.
  - **Corrección:** Limpieza de código muerto para mejorar el mantenimiento y legibilidad.

- **D-03 (MEDIO): Fallo de Relación en Reversión de Lotes**
  - **Ubicación:** `gestion/views.py` -> Acción `rechazar` de LoteProduccion.
  - **Problema:** El ORM fallaba al intentar acceder a `detalleformula_set` desde el modelo `FormulaColor` (relación no definida por defecto).
  - **Corrección:** Se ajustó la consulta para filtrar `DetalleFormula` directamente por la relación `fase__formula`.

### 2. Lógica Financiera y Reconciliación
- **D-05 (MEDIO): Inconsistencia en Reconciliación FIFO**
  - **Ubicación:** `gestion/utils.py` -> `PaymentReconciler`.
  - **Problema:** La amortización de pagos ignoraba el IVA (15%) y las retenciones, calculando saldos erróneos.
  - **Corrección:** Se sincronizó con la lógica de facturación real usando el campo desnormalizado `total_con_iva` y restando la `valor_retencion` del pedido.

### 3. Inventario y Motor de Producción (MRP)
- **D-04 (BAJO): Error de Atributo en Historial de Despacho**
  - **Ubicación:** `inventory/models.py` -> `DetalleHistorialDespachoPedido`.
  - **Problema:** El método `__str__` referenciaba un campo inexistente en el modelo de detalle.
  - **Corrección:** Se mapeó correctamente hacia el objeto padre: `self.historial.fecha_despacho`.

- **D-06 (BAJO): Selección Arbitraria de Fórmulas en MRP**
  - **Ubicación:** `inventory/services/mrp_engine.py`.
  - **Problema:** El motor tomaba la primera fórmula aprobada globalmente, lo cual es arriesgado en entornos multi-fórmula.
  - **Corrección:** Se implementó una selección determinista por el ID más reciente (`-id`) y se documentó la necesidad de un mapeo Producto <-> Fórmula para futuras fases.

---

## 🧪 Validación Técnica (QA Pass)

La suite de pruebas de TexCore ha sido ejecutada en su totalidad para garantizar que estas correcciones no introdujeron regresiones en los flujos críticos (Ventas, Crédito, Producción).

### Resultados del Test Suite:
- **Pruebas Totales:** 73
- **Exitosas (PASS):** 73
- **Fallidas (FAIL):** 0
- **Entorno de Validación:** SQL Server (Producción/Staging) vía ODBC.

> [!IMPORTANT]
> **Ajuste de Pruebas de Reconciliación:** Debido a la corrección **D-05** (activación de IVA en reconciliación), los montos de prueba en `UnifiedBusinessLogicTestCase` fueron actualizados (de $50 a $80) para reflejar la carga impositiva real y permitir que las facturas se marquen como "Pagadas" correctamente.

---
**TexCore ERP - Aseguramiento de Calidad**
