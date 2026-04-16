# Diagramas de Secuencia - Usuarios Principales del Sistema

## 1. Administrador de Sistemas

```mermaid
sequenceDiagram
    actor Admin as Administrador de Sistemas
    participant FE as Frontend (AdminSistemasDashboard)
    participant API as Django REST API
    participant DB as Base de Datos
    participant Audit as Audit Trail

    Note over Admin,Audit: Gestión de Usuarios
    Admin->>FE: Accede al módulo de usuarios
    FE->>API: GET /api/users/
    API->>DB: SELECT CustomUser WHERE all
    DB-->>API: Lista de usuarios
    API-->>FE: JSON usuarios
    FE-->>Admin: Tabla de usuarios del sistema

    Admin->>FE: Crea nuevo usuario (nombre, rol, sede, bodega)
    FE->>API: POST /api/users/
    API->>DB: INSERT CustomUser + assign group
    DB-->>API: Usuario creado
    API->>Audit: Registra acción de creación
    API-->>FE: 201 Created
    FE-->>Admin: Confirmación + usuario en tabla

    Note over Admin,Audit: Gestión de Productos y Bodegas
    Admin->>FE: Crea producto nuevo
    FE->>API: POST /api/productos/
    API->>DB: INSERT Producto
    DB-->>API: Producto creado
    API-->>FE: 201 Created
    FE-->>Admin: Producto disponible en el sistema

    Admin->>FE: Crea bodega y asigna a sede
    FE->>API: POST /api/bodegas/
    API->>DB: INSERT Bodega (sede_id, nombre, tipo)
    DB-->>API: Bodega creada
    API-->>FE: 201 Created
    FE-->>Admin: Bodega visible en inventario

    Note over Admin,Audit: Gestión de Inventario Global
    Admin->>FE: Accede al InventoryDashboard
    FE->>API: GET /api/inventory/stock/?all_sedes=true
    API->>DB: SELECT StockBodega JOIN Bodega JOIN Sede
    DB-->>API: Stock de todas las sedes
    API-->>FE: JSON stock global
    FE-->>Admin: Dashboard con métricas globales

    Admin->>FE: Realiza transferencia entre bodegas
    FE->>API: POST /api/inventory/movimientos/
    API->>DB: INSERT MovimientoInventario (tipo=transferencia)
    API->>DB: UPDATE StockBodega origen (decremento)
    API->>DB: UPDATE StockBodega destino (incremento)
    DB-->>API: OK
    API->>Audit: Registra movimiento con justificación
    API-->>FE: 201 Created
    FE-->>Admin: Confirmación de transferencia

    Note over Admin,Audit: Gestión de Fórmulas de Color
    Admin->>FE: Elimina fórmula (cascade delete)
    FE->>API: DELETE /api/formulas-color/{id}/
    API->>DB: DELETE FormulaColor + DetalleFormula (cascade)
    DB-->>API: OK
    API->>Audit: Registra eliminación
    API-->>FE: 204 No Content
    FE-->>Admin: Fórmula eliminada del sistema

    Note over Admin,Audit: Reportes y Auditoría
    Admin->>FE: Solicita reporte de auditoría
    FE->>API: GET /api/audit-logs/?fecha_inicio=X&fecha_fin=Y
    API->>DB: SELECT AuditLog WHERE fecha BETWEEN X AND Y
    DB-->>API: Registros de auditoría
    API-->>FE: JSON logs
    FE-->>Admin: Tabla de eventos auditados con filtros
```

---

## 2. Bodeguero

```mermaid
sequenceDiagram
    actor Bod as Bodeguero
    participant FE as Frontend (BodegueroDashboard)
    participant API as Django REST API
    participant DB as Base de Datos
    participant Report as Microservicio Reportes

    Note over Bod,Report: Inicio de Sesión y Vista General
    Bod->>FE: Accede al dashboard
    FE->>API: GET /api/inventory/alertas-stock/
    API->>DB: SELECT StockBodega WHERE cantidad < stock_minimo AND bodega IN bodegas_asignadas
    DB-->>API: Productos con stock bajo
    API-->>FE: JSON alertas
    FE-->>Bod: Panel de alertas con productos críticos

    FE->>API: GET /api/inventory/stock/?bodega_ids=[X,Y]
    API->>DB: SELECT StockBodega WHERE bodega_id IN bodegas_asignadas
    DB-->>API: Niveles de stock actuales
    API-->>FE: JSON stock
    FE-->>Bod: Visualización de niveles de inventario

    Note over Bod,Report: Registro de Movimientos de Inventario
    Bod->>FE: Registra entrada de mercancía (recepción)
    FE->>API: POST /api/inventory/movimientos/
    Note right of FE: tipo=entrada, cantidad, producto, bodega, justificacion
    API->>DB: INSERT MovimientoInventario
    API->>DB: UPDATE StockBodega SET cantidad = cantidad + entrada
    DB-->>API: OK
    API-->>FE: 201 Created
    FE-->>Bod: Stock actualizado + movimiento registrado

    Bod->>FE: Edita movimiento existente con justificación
    FE->>API: PUT /api/inventory/movimientos/{id}/
    Note right of FE: nueva_cantidad, justificacion_auditoria requerida
    API->>DB: UPDATE MovimientoInventario
    API->>DB: Recalcula StockBodega afectado
    API->>DB: INSERT HistorialMovimiento (cambio, justificación, timestamp)
    DB-->>API: OK
    API-->>FE: 200 OK
    FE-->>Bod: Historial de auditoría actualizado

    Note over Bod,Report: Consulta de Kardex
    Bod->>FE: Solicita Kardex de bodega por fecha
    FE->>API: GET /api/inventory/bodegas/{id}/kardex/?fecha_inicio=X&fecha_fin=Y
    API->>DB: SELECT MovimientoInventario WHERE bodega_id=id AND fecha BETWEEN X AND Y ORDER BY fecha
    DB-->>API: Movimientos ordenados cronológicamente
    API-->>FE: JSON kardex con saldos acumulados
    FE-->>Bod: Tabla kardex con entradas, salidas y saldo

    Note over Bod,Report: Productos en Stock Cero
    Bod->>FE: Consulta productos con stock en 0
    FE->>API: GET /api/inventory/stock/?cantidad=0&bodega_ids=[X]
    API->>DB: SELECT StockBodega WHERE cantidad=0 AND bodega_id IN bodegas_asignadas
    DB-->>API: Productos sin stock
    API-->>FE: JSON productos en 0
    FE-->>Bod: Lista de productos agotados

    Note over Bod,Report: Generación de Reportes Excel
    Bod->>FE: Descarga reporte de movimientos en Excel
    FE->>Report: POST /reporting/excel/movimientos/
    Note right of FE: filtros: bodega, fechas, tipo movimiento
    Report->>DB: Consulta movimientos con filtros aplicados
    DB-->>Report: Dataset completo
    Report-->>FE: Archivo Excel (.xlsx) con formato
    FE-->>Bod: Descarga automática del reporte

    Note over Bod,Report: Consulta de Lotes de Producción
    Bod->>FE: Busca lote por código
    FE->>API: GET /api/inventory/lotes/{codigo}/movimientos/
    API->>DB: SELECT MovimientoInventario WHERE lote_codigo=codigo
    DB-->>API: Movimientos del lote
    API-->>FE: JSON trazabilidad del lote
    FE-->>Bod: Historial completo del lote de producción
```

---

## 3. Operario

```mermaid
sequenceDiagram
    actor Op as Operario
    participant FE as Frontend (OperarioDashboard)
    participant API as Django REST API
    participant DB as Base de Datos

    Note over Op,DB: Inicio y Vista de Órdenes Asignadas
    Op->>FE: Accede al dashboard
    FE->>API: GET /api/ordenes-produccion/?estado=en_proceso
    API->>DB: SELECT OrdenProduccion WHERE operario_asignado=current_user AND estado='en_proceso'
    DB-->>API: Órdenes activas del operario
    API-->>FE: JSON órdenes con detalles (producto, máquina, turno)
    FE-->>Op: Tarjetas de órdenes activas asignadas

    Note over Op,DB: Registro de Lote de Producción
    Op->>FE: Selecciona orden y abre formulario de registro
    FE->>API: GET /api/ordenes-produccion/{id}/
    API->>DB: SELECT OrdenProduccion WHERE id=id AND operario_asignado=current_user
    DB-->>API: Detalle de orden (máquina asignada, producto, especificaciones)
    API-->>FE: JSON detalle orden
    FE-->>Op: Formulario pre-cargado con máquina y producto

    Op->>FE: Completa datos del lote (peso, unidades, turno, hora inicio/fin)
    FE->>API: POST /api/ordenes-produccion/{id}/registrar-lote/
    Note right of FE: codigo_lote (auto), peso_neto_producido, unidades_empaque, turno, hora_inicio, hora_final
    API->>DB: INSERT LoteProduccion
    API->>DB: INSERT MovimientoInventario (tipo=produccion, lote_id)
    API->>DB: UPDATE StockBodega SET cantidad = cantidad + peso_producido
    DB-->>API: Lote registrado
    API-->>FE: 201 Created + codigo_lote generado
    FE-->>Op: Confirmación con código de lote asignado

    Note over Op,DB: Consulta de Historial de Producción
    Op->>FE: Ve su historial de lotes producidos
    FE->>API: GET /api/lotes-produccion/?operario=current_user&ordering=-fecha
    API->>DB: SELECT LoteProduccion WHERE operario_id=current_user ORDER BY fecha DESC
    DB-->>API: Lista de lotes históricos
    API-->>FE: JSON historial
    FE-->>Op: Timeline de producción personal

    Note over Op,DB: Consulta de Métricas de Desempeño
    Op->>FE: Accede a sus métricas de rendimiento
    FE->>API: GET /api/users/{id}/desempeno/
    API->>DB: SELECT agregados de LoteProduccion (peso total, lotes por turno, eficiencia)
    DB-->>API: KPIs calculados
    API-->>FE: JSON métricas (peso_total, lotes_registrados, promedio_por_turno)
    FE-->>Op: Dashboard personal con indicadores de desempeño

    Note over Op,DB: Consulta de Stock (Solo Lectura)
    Op->>FE: Consulta disponibilidad de materia prima
    FE->>API: GET /api/inventory/alertas-stock/
    API->>DB: SELECT StockBodega WHERE cantidad < stock_minimo
    DB-->>API: Alertas de stock bajo
    API-->>FE: JSON alertas
    FE-->>Op: Vista de productos con stock crítico (solo lectura)
```

---

## 4. Ejecutivo

```mermaid
sequenceDiagram
    actor Eje as Ejecutivo
    participant FE as Frontend (EjecutivosDashboard)
    participant API as Django REST API
    participant DB as Base de Datos
    participant Report as Microservicio Reportes

    Note over Eje,Report: Dashboard General - Vista Multi-Sede
    Eje->>FE: Accede al dashboard ejecutivo
    FE->>API: GET /api/sedes/
    API->>DB: SELECT Sede WHERE all (sin filtro de sede)
    DB-->>API: Todas las sedes
    API-->>FE: JSON sedes disponibles
    FE-->>Eje: Selector de sede para filtrar vistas

    FE->>API: GET /api/inventory/stock/
    API->>DB: SELECT StockBodega JOIN Bodega JOIN Sede (acceso global)
    DB-->>API: Stock de todas las sedes
    API-->>FE: JSON inventario global
    FE-->>Eje: Gráficos de distribución de inventario (Recharts)

    Note over Eje,Report: Análisis de Ventas
    Eje->>FE: Filtra reporte de ventas por vendedor y fecha
    FE->>API: GET /api/pedidos-venta/?vendedor_id=X&fecha_inicio=Y&fecha_fin=Z
    API->>DB: SELECT PedidoVenta WHERE vendedor_asignado=X AND fecha BETWEEN Y AND Z
    DB-->>API: Órdenes de venta filtradas
    API-->>FE: JSON pedidos con totales y estados
    FE-->>Eje: Tabla + gráfico de barras de ventas por período

    Eje->>FE: Consulta lista de vendedores disponibles
    FE->>API: GET /api/users/vendedores/
    API->>DB: SELECT CustomUser WHERE group='vendedor'
    DB-->>API: Lista de vendedores
    API-->>FE: JSON vendedores
    FE-->>Eje: Dropdown de vendedores para filtro

    Note over Eje,Report: KPIs de Producción
    Eje->>FE: Accede a métricas de producción
    FE->>API: GET /api/lotes-produccion/?sede_id=X&fecha_inicio=Y
    API->>DB: SELECT LoteProduccion JOIN OrdenProduccion JOIN Area (todas sedes)
    DB-->>API: Lotes con datos de área y máquina
    API-->>FE: JSON producción agregada por área
    FE-->>Eje: Gráfico de eficiencia por área productiva

    FE->>API: GET /api/ordenes-produccion/?estado=completada
    API->>DB: SELECT OrdenProduccion GROUP BY area, maquina con métricas
    DB-->>API: Utilización por máquina
    API-->>FE: JSON utilización máquinas
    FE-->>Eje: Pie chart de utilización de máquinas

    Note over Eje,Report: Gestión de Clientes
    Eje->>FE: Consulta lista de clientes
    FE->>API: GET /api/clientes/
    API->>DB: SELECT Cliente WHERE all (sin restricción de vendedor)
    DB-->>API: Todos los clientes del sistema
    API-->>FE: JSON clientes con nivel_precio y crédito
    FE-->>Eje: Tabla de clientes con estado de crédito

    Note over Eje,Report: Alertas de Inventario
    Eje->>FE: Revisa alertas de stock bajo (todas las sedes)
    FE->>API: GET /api/inventory/alertas-stock/
    API->>DB: SELECT StockBodega WHERE cantidad < stock_minimo (acceso global)
    DB-->>API: Todas las alertas del sistema
    API-->>FE: JSON alertas multi-sede
    FE-->>Eje: Dashboard de alertas con filtro por sede

    Note over Eje,Report: Generación de Reportes
    Eje->>FE: Exporta reporte de pedidos a PDF
    FE->>API: GET /api/pedidos-venta/{id}/download_pdf/
    API->>DB: SELECT PedidoVenta + DetallePedido + Cliente
    DB-->>API: Datos completos del pedido
    API-->>FE: PDF generado
    FE-->>Eje: Descarga automática del PDF

    Note over Eje,Report: Auto-Refresh de Datos
    loop Cada N segundos (auto-refresh activo)
        FE->>API: GET /api/inventory/stock/
        API->>DB: Query actualizada
        DB-->>API: Stock actual
        API-->>FE: JSON actualizado
        FE-->>Eje: Dashboard refrescado automáticamente
    end
```

---

> **[Sprint 6 — 2026-04-10]**

### CU-EJ-01: Ejecutivo consulta KPIs ejecutivos consolidados

```mermaid
sequenceDiagram
    actor Eje as Ejecutivo
    participant FE as EjecutivosDashboard (Tab Resumen)
    participant API as Django REST API
    participant SvcP as ProduccionKPIService
    participant SvcE as ExecutiveKPIService
    participant DB as SQL Server

    Eje->>FE: Abre dashboard / cambia sede
    FE->>API: GET /api/kpi-ejecutivo/?sede_id=X

    API->>SvcP: ProduccionKPIService(sede_id=X).obtener_kpis()
    SvcP->>DB: SELECT OPs, LoteProduccion GROUP BY estado/fecha
    DB-->>SvcP: Datos de producción
    SvcP-->>API: ProduccionKPIs (frozen dataclass)

    API->>SvcE: ExecutiveKPIService(sede_id=X).obtener_kpis()
    SvcE->>DB: SELECT OC, StockBodega (F() expr), PedidoVenta
    DB-->>SvcE: Datos MRP, stock y cartera
    SvcE-->>API: ExecutiveKPIs (frozen dataclass)

    API-->>FE: JSON { produccion, mrp, stock, cartera }
    FE-->>Eje: Cards KPI: OPs por estado, kg hoy/semana/mes,\nproductos bajo mínimo, cartera vencida
```

### CU-EJ-07: Ejecutivo descarga reporte gerencial Excel

```mermaid
sequenceDiagram
    actor Eje as Ejecutivo
    participant FE as EjecutivosDashboard (Tab Reportes)
    participant Valid as Validación Frontend
    participant Report as reporting_excel :8003
    participant SP as SQL Server SP

    Eje->>FE: Selecciona rango de fechas y sede (opcional)
    Eje->>FE: Clic en botón de descarga (ej. "Órdenes de Producción")

    FE->>Valid: ¿fecha_inicio > fecha_fin?
    alt Rango inválido
        Valid-->>FE: toast.error("La fecha de inicio no puede ser posterior a la fecha de fin")
        FE-->>Eje: Alerta de error — sin llamada al API
    else Rango válido
        FE->>FE: setDescargando(ruta) — deshabilita todos los botones
        FE->>Report: GET /reporting/produccion/ordenes?fecha_inicio=X&fecha_fin=Y&sede_id=Z&format=xlsx

        Report->>SP: EXEC sp_GetOrdenesProduccionGerencial @FechaInicio, @FechaFin, @SedeID
        SP->>SP: JOIN OPs + Lotes + Producto + Sede + Máquina + Operario
        SP-->>Report: Resultset con avance_pct, kg, fechas de lote

        Report->>Report: execute_sp_to_dataframe() → Pandas DataFrame
        Report->>Report: generate_download_response(df, "xlsx", nombre_archivo)
        Report-->>FE: Blob application/vnd.openxmlformats-officedocument.spreadsheetml.sheet

        FE->>FE: URL.createObjectURL(blob) → click automático → revoke
        FE->>FE: setDescargando(null) — rehabilita botones
        FE-->>Eje: toast.success("Reporte descargado") + archivo .xlsx
    end

    Note over FE,Report: El mismo flujo aplica para los 6 reportes disponibles:\ngerencial/ventas, gerencial/top-clientes, gerencial/deudores,\nproduccion/ordenes, produccion/lotes, produccion/tendencia
```

---

## 5. Ventas (Vendedor)

```mermaid
sequenceDiagram
    actor Ven as Vendedor
    participant FE as Frontend (VendedorDashboard)
    participant API as Django REST API
    participant DB as Base de Datos
    participant PDF as Generador PDF

    Note over Ven,PDF: Gestión de Clientes
    Ven->>FE: Busca cliente existente por RUC/nombre
    FE->>API: GET /api/clientes/?search=término
    API->>DB: SELECT Cliente WHERE ruc ILIKE '%term%' OR razon_social ILIKE '%term%'
    DB-->>API: Clientes encontrados
    API-->>FE: JSON clientes
    FE-->>Ven: Resultados de búsqueda con estado de crédito

    Ven->>FE: Crea nuevo cliente
    FE->>API: POST /api/clientes/
    Note right of FE: ruc, razon_social, direccion_envio, nivel_precio, limite_credito, plazo_credito_dias
    API->>DB: INSERT Cliente
    DB-->>API: Cliente creado con ID
    API-->>FE: 201 Created
    FE-->>Ven: Cliente disponible para crear pedidos

    Ven->>FE: Actualiza información del cliente
    FE->>API: PUT /api/clientes/{id}/
    API->>DB: UPDATE Cliente
    DB-->>API: OK
    API-->>FE: 200 OK
    FE-->>Ven: Datos actualizados del cliente

    Note over Ven,PDF: Creación de Pedido de Venta
    Ven->>FE: Inicia nuevo pedido de venta
    FE->>API: GET /api/productos/
    API->>DB: SELECT Producto WHERE sede=current_user.sede AND activo=true
    DB-->>API: Catálogo de productos disponibles
    API-->>FE: JSON productos con precios por nivel
    FE-->>Ven: Selector de productos con precios

    Ven->>FE: Agrega productos al pedido (cantidad/peso, precio)
    Ven->>FE: Aplica IVA, retención si corresponde
    Ven->>FE: Ingresa guía de remisión
    FE->>API: POST /api/pedidos-venta/
    Note right of FE: cliente_id, detalles[], iva_inclusivo, retencion, guia_remision, vendedor=auto
    API->>DB: INSERT PedidoVenta (vendedor_asignado=current_user, sede=user.sede)
    API->>DB: INSERT DetallePedido[] (producto, cantidad, precio_unitario, subtotal)
    API->>DB: Calcula total con IVA y retención
    DB-->>API: Pedido creado
    API-->>FE: 201 Created + pedido_id
    FE-->>Ven: Pedido registrado con número de orden

    Note over Ven,PDF: Registro de Pagos
    Ven->>FE: Registra pago de cliente
    FE->>API: POST /api/pagos-cliente/
    Note right of FE: pedido_id, monto, metodo_pago (transferencia/efectivo/cheque), comprobante, notas
    API->>DB: INSERT PagoCliente
    API->>DB: UPDATE PedidoVenta SET esta_pagado=true/parcial
    API->>DB: Actualiza cartera_vencida del cliente si aplica
    DB-->>API: Pago registrado
    API-->>FE: 201 Created
    FE-->>Ven: Estado de pago actualizado en el pedido

    Note over Ven,PDF: Consulta de Mis Pedidos
    Ven->>FE: Ve sus pedidos del período
    FE->>API: GET /api/pedidos-venta/?fecha_inicio=X&fecha_fin=Y
    API->>DB: SELECT PedidoVenta WHERE vendedor_asignado=current_user AND fecha BETWEEN X AND Y
    DB-->>API: Pedidos del vendedor en el período
    API-->>FE: JSON pedidos con estado de pago
    FE-->>Ven: Tabla de pedidos (pendientes, pagados, vencidos)

    Note over Ven,PDF: Generación de Documentos
    Ven->>FE: Imprime/descarga pedido como PDF
    FE->>API: GET /api/pedidos-venta/{id}/download_pdf/
    API->>DB: SELECT PedidoVenta + DetallePedido + Cliente + Sede
    DB-->>API: Datos completos
    API->>PDF: Renderiza plantilla PDF con datos del pedido
    PDF-->>API: PDF generado
    API-->>FE: Archivo PDF
    FE-->>Ven: Descarga o previsualización del PDF para imprimir/enviar

    Note over Ven,PDF: Seguimiento de Crédito de Clientes
    Ven->>FE: Revisa estado de crédito de cliente
    FE->>API: GET /api/clientes/{id}/
    API->>DB: SELECT Cliente + SUM(pedidos pendientes) + cartera_vencida
    DB-->>API: Cliente con estado de cuenta
    API-->>FE: JSON cliente con saldo y límite de crédito
    FE-->>Ven: Panel con disponible de crédito y facturas vencidas
```

---

## Resumen de Permisos por Rol

| Acción | Admin Sistemas | Bodeguero | Operario | Ejecutivo | Ventas |
|--------|:--------------:|:---------:|:--------:|:---------:|:------:|
| Gestión de usuarios | CRUD | - | - | - | - |
| Gestión de sedes/áreas | CRUD | - | - | Ver | - |
| Gestión de productos | CRUD | Ver | - | Ver | Ver |
| Gestión de bodegas | CRUD | Ver | - | - | - |
| Stock - Ver (todas las sedes) | CRUD | Ver (asignadas) | Ver | Ver (todas) | - |
| Movimientos de inventario | CRUD | CRUD | - | - | - |
| Lotes de producción | CRUD | Ver | Crear | Ver | - |
| Órdenes de producción | CRUD | - | Ver (propias) | Ver | - |
| Fórmulas de color | CRUD | - | - | - | - |
| Clientes | CRUD | - | - | Ver | CRUD |
| Pedidos de venta | CRUD | - | - | Ver | CRUD (propios) |
| Pagos de clientes | CRUD | - | - | - | Crear |
| Reportes globales | CRUD | Parciales | - | Ver | Ver (propios) |
| Auditoría | Ver | Ver (inventario) | - | - | - |
