# 👥 Manual de Roles y Permisos - TexCore

Este documento detalla las funciones, responsabilidades y capacidades de cada tipo de usuario dentro de la plataforma TexCore. El sistema utiliza un control de acceso basado en roles (RBAC) para garantizar la seguridad y la integridad de los datos.

---

## 📋 Resumen de Roles

| Rol | Función Principal | Ámbito de Acción | Dashboard Principal |
| :--- | :--- | :--- | :--- |
| **Operario** | Registro de bodega | Movimientos e Historial | `OperarioDashboard` |
| **Empaquetado** | Registro de producto terminado | Pesaje y Etiquetado | `EmpaquetadoDashboard` |
| **Despacho** | Logística y Salida | Validación y Carga | `DespachoDashboard` |
| **Bodeguero** | Control de inventario | Stock, Transferencias y Alertas | `BodegueroDashboard` |
| **Vendedor** | Gestión Comercial | Clientes, Ventas y Abonos | `VendedorDashboard` |
| **Jefe de Planta** | Planificación | Órdenes de Producción | `JefePlantaDashboard` |
| **Jefe de Área** | Supervisión Técnica | KPIs, Máquinas y Rechazos | `JefeAreaDashboard` |
| **Ejecutivo** | Análisis Estratégico | Reportes de Solo Lectura | `EjecutivosDashboard` |
| **Admin de Sede** | Administración Local | Aprobaciones y Gestión de Sede | `AdminSedeDashboard` |
| **Admin de Sistemas** | Administración Global | Configuración Maestro de Datos | `AdminSistemasDashboard` |

---

## 🛠 Detalle por Rol

### 1. Operario
**Función:** Reporta movimientos directos de inventario (consumos de materia prima o ingresos manuales).
*   **¿Qué puede hacer?**
    *   Registrar entradas y salidas de inventario mediante formularios manuales.
    *   Consultar su propio historial de movimientos realizados.
    *   Vincular movimientos a productos y lotes específicos.

### 2. Empaquetado
**Función:** Estación final de producción donde el producto se pesa y etiqueta para su almacenamiento o venta.
*   **¿Qué puede hacer?**
    *   Registrar bultos/cajas vinculados a una **Orden de Producción** activa.
    *   Calcular automáticamente el **Peso Neto** (Peso Bruto - Tara).
    *   Generar e imprimir etiquetas en formato **ZPL** para impresoras Zebra.
    *   Seleccionar máquina y turno de producción.

### 3. Despacho
**Función:** Gestiona la salida física de mercancía hacia los clientes finales.
*   **¿Qué puede hacer?**
    *   Seleccionar múltiples pedidos pendientes para un mismo despacho.
    *   Validar la carga mediante **escaneo de códigos de barras**.
    *   Verificar en tiempo real el cumplimiento del pedido (Teórico vs. Escaneado).
    *   Finalizar despachos, lo cual rebaja automáticamente el stock y actualiza el pedido a "Despachado".

### 4. Bodeguero
**Función:** Responsable de la integridad del stock y la organización de los almacenes.
*   **¿Qué puede hacer?**
    *   Visualizar stock en tiempo real filtrado por sede y bodega.
    *   Ejecutar **Transferencias** de stock entre bodegas.
    *   Monitorear **Alertas de Stock Bajo** (basado en el stock mínimo configurado).
    *   Consultar el **Kardex** detallado por producto.

### 5. Vendedor (Ejecutivo de Ventas)
**Función:** Motor comercial de la empresa. Gestiona la cartera de clientes y créditos.
*   **¿Qué puede hacer?**
    *   Registrar y editar clientes con perfiles de precio (Normal/Mayorista).
    *   Crear pedidos de venta validando automáticamente el **Límite de Crédito**.
    *   Registrar **Abonos** a cuentas por cobrar.
    *   Visualizar el estado financiero de cada cliente (Saldo Pendiente vs. Límite).
    *   Descargar Notas de Venta en formato PDF.

### 6. Jefe de Planta
**Función:** Planificador central de la producción.
*   **¿Qué puede hacer?**
    *   Crear y gestionar el ciclo de vida de las **Órdenes de Producción**.
    *   Asignar órdenes a sedes específicas.
    *   Definir parámetros de producción y requerimientos de peso.

### 7. Jefe de Área
**Función:** Supervisor de la eficiencia operativa y calidad en una sección específica.
*   **¿Qué puede hacer?**
    *   Monitorear KPIs en tiempo real: Producción Total (Kg), Rendimiento (Yield) y Tiempos Promedio.
    *   Controlar la carga y estado operativo de las máquinas.
    *   **Rechazar Lotes** de producción (revirtiendo automáticamente los movimientos de stock asociados).
    *   Recibir alertas críticas de insumos (químicos/hilos) para su área.

### 8. Ejecutivo
**Función:** Perfil de consulta para gerencia (WIP).
*   **¿Qué puede hacer?**
    *   Visualizar tableros consolidados de indicadores clave.
    *   *Restricción:* Acceso de **solo lectura**. No puede alterar la integridad operacional.

### 9. Administrador de Sede
**Función:** Máxima autoridad operativa en una ubicación física.
*   **¿Qué puede hacer?**
    - **Aprobar Movimientos**: de inventario pendientes o críticos (e.g. ajustes manuales que superen un umbral).
    - **Supervisar Áreas**: Supervisar todas las áreas de su sede (Producción, Ventas, Bodega).
    - **Gestión Local**: Gestionar usuarios y áreas locales.

### 10. Administrador de Sistemas
**Función:** Configuración técnica y gestión de maestros globales.
*   **¿Qué puede hacer?**
    *   Gestionar el catálogo global de **Sedes, Áreas y Bodegas**.
    *   Configurar el maestro de **Productos y Químicos**.
    *   Administrar el catálogo de **Fórmulas de Color**.
    *   Gestión total de usuarios y grupos de permisos.

---

## 🔒 Reglas de Seguridad Transversales

1.  **Aislamiento de Sede:** Los usuarios solo interactúan con datos de su sede asignada.
2.  **Validación de Saldo:** No se permiten ventas si el cliente excede su límite de crédito configurado.
3.  **Transaccionalidad:** Los procesos críticos (Despacho, Transferencia, Rechazo) son **atómicos**; si un paso falla, se revierte todo el proceso para evitar descuadres.
4.  **Trazabilidad Máxima:** Cada movimiento de inventario registra el usuario, la hora y el documento de referencia.
5.  **Stock No Negativo:** El sistema impide realizar salidas de bodega si no hay existencia física validada en el sistema.

