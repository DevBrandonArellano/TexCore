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
| **Tintorero** | Gestión de Fórmulas Químicas | Laboratorio y Tintura | `TintoreroDashboard` |
| **Ejecutivo** | Análisis Estratégico | Reportes de Solo Lectura | `EjecutivosDashboard` |
| **Admin de Sede** | Administración Local | Aprobaciones y Gestión de Sede | `AdminSedeDashboard` |
| **Admin de Sistemas** | Administración Global | Configuración Maestro de Datos | `AdminSistemasDashboard` |

---

## 🛠 Detalle por Rol

### 1. Operario
**Función:** Ejecución de producción física — registro de lotes de producción y transformaciones máquina a máquina.
*   **¿Qué puede hacer?**
    *   Registrar entradas y salidas de inventario mediante formularios manuales.
    *   Consultar su propio historial de movimientos realizados.
    *   Vincular movimientos a productos y lotes específicos.
    *   **Registrar lotes de producción** para las OPs asignadas a su máquina y turno.
    *   **Registrar transformaciones máquina a máquina** (Fase 16): especifica producto de salida, máquina, peso de entrada/salida y observaciones. La merma se calcula automáticamente. Restricción: solo en órdenes de su área y sede.
    *   **Consultar trazabilidad**: visualiza el árbol completo de transformaciones de una orden (merma por etapa y acumulada total).

### 2. Empaquetado
**Función:** Estación final de producción donde el producto se pesa y etiqueta para su almacenamiento o venta.
*   **¿Qué puede hacer?**
    *   Registrar bultos/cajas vinculados a una **Orden de Producción** activa.
    *   Calcular automáticamente el **Peso Neto** (Peso Bruto - Tara).
    *   Generar e imprimir etiquetas — **Zebra Browser Print** (ZPL nativo) con fallback a
        **PDF universal** (cualquier impresora) y portapapeles como último recurso.
*   **Reimprimir** una etiqueta idéntica indicando un motivo obligatorio (etiqueta dañada,
        perdida, atasco de impresora, etc.) — queda registrado en auditoría, no requiere
        aprobación de supervisor.
    *   **Solicitar Reetiquetado in-situ (Supervisor Override)**: si necesita corregir el peso o la calidad de un lote ya registrado, puede solicitar la autorización in-situ de su **Jefe de Área** o Supervisor, quien ingresa su usuario y contraseña en el modal sin cerrar ni cambiar la sesión activa.
    *   **Control de Tolerancia de Pesaje**: recibe advertencia si el peso difiere más del 10% del esperado, requiriendo confirmación explícita.
    *   **Configurar Preferencia de Impresora**: seleccionar y guardar en `localStorage` el modo de impresión (Zebra Nativo, PDF Universal o Automático).
    *   **Buscar lotes** de otras fechas por rango de fechas, turno, código de lote o calidad.
    *   Seleccionar máquina y turno de producción.


### 3. Despacho
**Función:** Gestiona la salida física de mercancía hacia los clientes finales.
*   **¿Qué puede hacer?**
    *   Seleccionar múltiples pedidos pendientes para un mismo despacho.
    *   Validar la carga mediante **escaneo de códigos de barras**.
    *   Verificar en tiempo real el cumplimiento del pedido (Teórico vs. Escaneado).
    *   Finalizar despachos, lo cual rebaja automáticamente el stock y actualiza el pedido a "Despachado".
    *   **Consultar Historial**: Acceder al registro histórico de despachos realizados con detalles de lotes y pesos.
    *   **Gestionar Devoluciones**: Registrar el reingreso de mercancía previamente despachada.


### 4. Bodeguero
**Función:** Responsable de la integridad del stock y la organización de los almacenes.
*   **¿Qué puede hacer?**
    *   Visualizar stock en tiempo real filtrado por sede y bodega.
    *   Ejecutar **Transferencias** de stock entre bodegas.
    *   Monitorear **Alertas de Stock Bajo** (basado en el stock mínimo configurado).
    *   Consultar el **Kardex** detallado por producto.
    *   **Auditoría de Stock**: Realizar ajustes justificados a los movimientos de inventario.
    *   **MRP (Planificación de Requerimientos)**: Consultar insumos faltantes según las Órdenes de Producción activas y generar sugerencias de compra.


### 5. Vendedor (Ejecutivo de Ventas)
**Función:** Motor comercial de la empresa. Gestiona la cartera de clientes y créditos.
*   **¿Qué puede hacer?**
    *   Registrar y editar clientes con perfiles de precio (Normal/Mayorista).
    *   Crear pedidos de venta validando automáticamente el **Límite de Crédito**.
    *   Registrar **Abonos** a cuentas por cobrar.
    *   **Revertir Abonos**: Deshacer un pago registrado con justificación obligatoria. La operación restaura automáticamente el `saldo_pendiente` del cliente al monto anterior y registra el evento en `AuditLog`. Endpoint: `POST /api/pagos-cliente/{id}/revertir/`. La reconciliación FIFO se re-ejecuta automáticamente post-reversión.
    *   Visualizar el estado financiero de cada cliente (Saldo Pendiente vs. Límite).
    *   **Beneficios Dinámicos**: Aplicar lógica de descuentos y precios mayoristas automáticamente.
    *   Descargar Notas de Venta en formato PDF.


### 6. Jefe de Planta
**Función:** Planificador central de la producción.
*   **¿Qué puede hacer?**
    *   Crear y gestionar el ciclo de vida de las **Órdenes de Producción**.
    *   Asignar órdenes a sedes específicas.
    *   Definir parámetros de producción y requerimientos de peso.
    *   **Consultar trazabilidad (solo lectura)**: desde el panel de detalle de cualquier OP, visualiza el árbol completo de transformaciones con merma acumulada %. No puede registrar transformaciones (esa responsabilidad corresponde a Jefes de Área y Operarios).

### 7. Jefe de Área
**Función:** Supervisor de la eficiencia operativa y calidad en una sección específica.
*   **¿Qué puede hacer?**
    *   Monitorear KPIs de calidad y rendimiento en tiempo real: **Producción Total (Kg)**, **Rendimiento (Yield)** = neto / (neto + merma), **First Pass Yield (FPY)** = kg de primera calidad / kg total (componente "Calidad" de OEE), **distribución por calidad** (primera/segunda/saldo) y **Tiempo Promedio** por lote. (Antes el Yield era un placeholder fijo en 100 %; ahora se calcula con la merma y la clasificación real de cada lote.)
    *   Controlar la carga y estado operativo de las máquinas.
    *   **Rechazar Lotes** de producción indicando un **motivo obligatorio** (ISO 9001: causa del rechazo trazable). Revierte automáticamente los movimientos de stock, consumo de mezcla y merma asociados.
    *   Recibir alertas críticas de insumos (químicos/hilos) para su área.
    *   **Registrar transformaciones máquina a máquina** (Fase 16): puede registrar y consultar la cadena de transformaciones de las órdenes de su área. Restricción: solo en órdenes de su misma área y sede (aislamiento RBAC).
    *   **Gestionar Líneas de Producción (Células de Manufactura Flexibles)**: crear, editar y eliminar líneas de producción en su área, asignando múltiples máquinas. Permite compartir máquinas rápidas entre líneas sin duplicar capacidad calculada a nivel de área (TOC / ISA-95).
    *   **Reetiquetar lotes** (exclusivo de supervisores, junto con Jefe de Planta y Admin): corregir peso neto o reclasificar la calidad de un lote ya registrado, con motivo obligatorio. Anula la etiqueta anterior y emite una nueva versión; si cambia el peso, ajusta el stock automáticamente. El código de lote y el QR de trazabilidad nunca cambian.


### 8. Tintorero
**Función:** Especialista en color y formulación química para los procesos de tintura y acabado.
*   **¿Qué puede hacer?**
    *   **Gestionar Fórmulas Químicas**: Crear, editar y versionar recetas de color por tipo de sustrato.
    *   **Calcular Pesajes (Laboratorio)**: Usar la calculadora integrada para determinar gramajes exactos de químicos según el volumen de tela y la relación de baño.
    *   **Sincronización Infotint**: Exportar las fórmulas en formato JSON listo para ser cargado en máquinas dosificadoras automáticas.
    *   **Monitorear Fórmulas en Pruebas**: Diferenciar fórmulas aprobadas de aquellas aún en fase de laboratorio.

### 9. Ejecutivo

> **[Sprint 6 — 2026-04-10]**

**Función:** Análisis estratégico y seguimiento gerencial multi-sede. Acceso de **solo lectura** a todos los módulos del sistema.

#### Casos de Uso implementados

| CU | Nombre | Tab | Endpoint(s) |
|----|--------|-----|-------------|
| CU-EJ-01 | Consultar KPIs ejecutivos consolidados | Resumen | `GET /api/kpi-ejecutivo/` |
| CU-EJ-02 | Ver resumen de producción | Producción | `GET /api/produccion/resumen/` |
| CU-EJ-03 | Ver tendencia de producción | Producción | `GET /api/produccion/tendencia/` |
| CU-EJ-04 | Consultar stock e inventario | Inventario | `GET /api/inventory/stock/`, `/alertas-stock/` |
| CU-EJ-05 | Consultar ventas y cartera | Ventas | `GET /api/pedidos-venta/`, `/clientes/` |
| CU-EJ-06 | Consultar estado MRP | MRP | incluido en `/kpi-ejecutivo/` |
| CU-EJ-07 | Descargar reportes gerenciales (Excel) | Reportes | 6 endpoints `/reporting/…` |

#### ¿Qué puede hacer?

*   **Tab Resumen**: Visualizar KPIs consolidados de producción, MRP, stock y cartera vencida en cards agrupadas. Los valores son calculados por `ProduccionKPIService` y `ExecutiveKPIService` (Service Layer).
*   **Tab Producción**: Ver el estado de las órdenes de producción por sede y la serie temporal de kg producidos por día.
*   **Tab Inventario**: Ver stock actual e historial de alertas de stock bajo mínimo de todas las sedes.
*   **Tab Ventas**: Ver pedidos, estado de cartera y lista de clientes sin restricción de vendedor.
*   **Tab MRP**: Consultar requerimientos de materiales y órdenes de compra sugeridas.
*   **Tab Reportes (CU-EJ-07)**: Descargar 6 reportes Excel gerenciales del período seleccionado:
    - **Ventas del período** — `/reporting/gerencial/ventas`
    - **Top clientes** — `/reporting/gerencial/top-clientes`
    - **Deudores / cartera** — `/reporting/gerencial/deudores`
    - **Órdenes de producción** — `/reporting/produccion/ordenes` (SP: `sp_GetOrdenesProduccionGerencial`)
    - **Lotes de producción** — `/reporting/produccion/lotes` (SP: `sp_GetLotesProduccionGerencial`)
    - **Tendencia de producción** — `/reporting/produccion/tendencia` (SP: `sp_GetTendenciaProduccionGerencial`)

#### Filtros disponibles

*   **Por sede**: Selector en la cabecera del dashboard. `sede_id = null` = vista global (todas las sedes).
*   **Por rango de fechas**: Inputs `fecha_inicio` / `fecha_fin` compartidos para producción y reportes.
*   Validación de rango: frontend rechaza `fecha_inicio > fecha_fin` antes de llamar al API.

#### Restricciones

*   Acceso de **solo lectura**. No puede crear, modificar ni eliminar ningún registro.
*   No puede ver datos de inventario filtrados por bodega asignada (ve todas las bodegas).
*   Durante una descarga de reporte: todos los botones de exportación quedan deshabilitados hasta que complete (prevención de descargas simultáneas).

### 10. Administrador de Sede
**Función:** Máxima autoridad operativa en una ubicación física.
*   **¿Qué puede hacer?**
    - **Aprobar Movimientos**: de inventario pendientes o críticos (e.g. ajustes manuales que superen un umbral).
    - **Supervisar Áreas**: Supervisar todas las áreas de su sede (Producción, Ventas, Bodega).
    - **Gestión Local**: Gestionar usuarios y áreas locales.

### 11. Administrador de Sistemas
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

