# Análisis del Rol de Vendedor - Sistema TexCore

Este documento detalla la implementación, lógica de negocio y medidas de seguridad aplicadas al rol de **Vendedor** en el sistema TexCore.

## 1. Responsabilidades del Rol
El Vendedor es responsable de la gestión de la relación con el cliente, desde la prospección hasta la cobranza. Sus funciones principales incluyen:
*   Registro y mantenimiento de Clientes.
*   Creación de Pedidos de Venta.
*   Registro de Cobros/Pagos de Clientes.
*   Seguimiento del estado de cuenta de sus clientes asignados.

## 2. Lógica de Negocio y Automatizaciones

### 2.1 Auto-asignación de Registros
Para garantizar que el vendedor mantenga el control sobre su cartera, el sistema implementa auto-asignación automática:
*   **Al crear un Cliente**: Si el usuario tiene el rol de `vendedor`, el sistema lo asigna automáticamente como `vendedor_asignado`.
*   **Al crear un Pedido**: Se asigna automáticamente al vendedor que realiza la transacción.

### 2.2 Reconciliación FIFO (First In, First Out)
El sistema utiliza un motor de reconciliación automática de pagos (`PaymentReconciler`):
*   Cuando se registra un nuevo pago, el sistema recorre los pedidos pendientes del cliente en orden cronológico.
*   El saldo del pago se aplica a los pedidos más antiguos primero.
*   Si un pedido se cubre totalmente, se marca automáticamente como `esta_pagado = True`.

### 2.3 Validaciones de Crédito y Precio
*   **Límite de Crédito**: No se permite la creación de nuevos pedidos si el saldo pendiente del cliente (incluyendo el nuevo pedido) excedería su `limite_credito`.
*   **Precio Base (Piso)**: Un vendedor no puede vender un producto por debajo de su `precio_base` establecido en el catálogo, protegiendo los márgenes de la empresa.

## 3. Seguridad y Aislamiento (Multi-tenancy a nivel de Vendedor)

### 3.1 Filtrado de Datos (QuerySet Filtering)
El sistema aplica un aislamiento estricto de datos en la API:
*   **Clientes**: Los vendedores solo pueden ver y editar clientes que tengan asignados.
*   **Pedidos**: Solo visualizan pedidos creados por ellos o de sus clientes.
*   **Pagos**: Solo visualizan el historial de pagos de sus clientes asignados.

### 3.2 Permisos de Granularidad
Aunque el vendedor tiene permisos de `view`, `add` y `change` sobre sus modelos, ciertas acciones críticas están restingidas:
*   **Beneficios Especiales**: Solo un Administrador puede activar el campo `tiene_beneficio` en un cliente (usado para descuentos globales o condiciones especiales).

### 3.3 Dashboard Integrado (Frontend)
El sistema proporciona una interfaz intuitiva para el vendedor que centraliza:
*   **KPIs de Cartera**: Visualización inmediata del monto total por cobrar y utilización del crédito.
*   **Gestión de Prospectos**: Formulario simplificado para alta de nuevos clientes con validación RUC.
*   **Punto de Venta**: Creación de pedidos con cálculo automático de totales y validación de margen (Precio Base).
*   **Centro de Cobranza**: Registro de abonos con soporte para múltiples métodos (Transferencia, Efectivo, Cheque).
*   **Generación de Documentos**: Descarga directa de notas de venta en PDF via microservicio de impresión.

## 4. Pruebas de Integración (Suite Unificada)
Las funcionalidades del vendedor están validadas mediante tests integrados en `gestion/tests_integrados.py` que cubren:
*   `test_salesman_filtering`: Aislamiento de cartera.
*   `test_credit_limit_validation`: Control de riesgo.
*   `test_dynamic_balance_calculation`: Integridad de saldos.
*   `test_payment_reconciliation_flow`: Automatización de cobranza.

## 5. Próximas Mejoras
*   Panel de metas y comisiones basado en pedidos facturados.
*   Alertas de morosidad automáticas.
*   Integración con WhatsApp para envío de notas de venta PDF.
