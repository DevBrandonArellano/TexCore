---
description: Gestión de recetas de color, formulación química, dosificación y stock de insumos.
---

1. **Dashboard de Tintorería**: Acceso centralizado a la gestión de recetas de tintura y stock de insumos químicos (`TintoreroDashboard.tsx`).
2. **Formulación Química**: Crear, editar y consultar recetas de color (`FormulaQuimica.tsx`) especificando sustrato (algodón, poliéster, mezclas), fases (pre-tratamiento, tintura, aclarado, suavizado) e insumos con porcentajes o g/L.
3. **Calculadora de Dosificación**: Calcular el pesaje exacto de colorantes y auxiliares químicos ingresando la Relación de Baño y el peso bruto del lote de tela a teñir.
4. **Supervisión de Químicos**: Monitorear existencias, mermas y alertas de reabastecimiento de insumos químicos mediante `StockQuimicosDashboard.tsx`.
5. **Exportación de Recetas (Infotint)**: Descargar fórmulas aprobadas en formato JSON estructurado para su carga en cocinas de colorantes automáticas.

