# Diagramas de Secuencia — Usuarios Principales del Sistema TexCore

> Stack: Django 5 + React/TypeScript + FastAPI (servicios satélite) + SQL Server + Docker + Nginx
>
> Autenticacion usuario: SimpleJWT (access + refresh token via `/api/token/`)
> Autenticacion servicio-a-servicio: JWT RS256 — clave privada en backend Django, clave publica distribuida a servicios satélite
> Servicios Satélite: `scanning_service` (:8000), `reporting_excel` (:8002), `printing_service` (:8001)
> El `scanning_service` NO tiene acceso directo a SQL Server — consume la Internal API de Django vía JWT RS256

---

## 1. Administrador de Sistemas

```mermaid
sequenceDiagram
    actor Admin as Administrador de Sistemas
    participant FE as Frontend (AdminSistemasDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant DB as SQL Server
    participant Audit as AuditLog (modelo Django)

    Note over Admin,Audit: Gestion de Usuarios
    Admin->>FE: Accede al modulo de usuarios
    FE->>Nginx: GET /api/users/
    Nginx->>API: proxy → GET /api/users/
    API->>DB: SELECT CustomUser JOIN groups JOIN Sede
    DB-->>API: Lista de usuarios con roles y sede
    API-->>FE: 200 JSON [{id, username, groups, sede, bodegas_asignadas}]
    FE-->>Admin: Tabla de usuarios del sistema con roles

    Admin->>FE: Crea nuevo usuario (nombre, rol, sede, bodegas)
    FE->>Nginx: POST /api/users/ {username, password, groups, sede_id, bodegas_asignadas}
    Nginx->>API: proxy → POST /api/users/
    API->>DB: INSERT CustomUser
    API->>DB: INSERT UserGroups (asigna rol)
    API->>DB: INSERT UserBodega M2M (asigna bodegas)
    DB-->>API: OK
    API->>Audit: INSERT AuditLog {accion: "create_user", usuario, objeto_id}
    API-->>FE: 201 Created {id, username, ...}
    FE-->>Admin: Confirmacion + usuario en tabla

    Note over Admin,Audit: Gestion de Productos y Bodegas
    Admin->>FE: Crea producto nuevo
    FE->>Nginx: POST /api/productos/ {codigo, descripcion, tipo, unidad_medida, precio_base, stock_minimo}
    Nginx->>API: proxy → POST /api/productos/
    API->>DB: INSERT Producto
    DB-->>API: Producto creado
    API->>Audit: INSERT AuditLog {accion: "create_producto"}
    API-->>FE: 201 Created
    FE-->>Admin: Producto disponible en el sistema

    Admin->>FE: Crea bodega y asigna a sede
    FE->>Nginx: POST /api/bodegas/ {sede_id, nombre, tipo, descripcion}
    Nginx->>API: proxy → POST /api/bodegas/
    API->>DB: INSERT Bodega (sede_id, nombre, tipo)
    DB-->>API: Bodega creada
    API-->>FE: 201 Created
    FE-->>Admin: Bodega visible en inventario

    Note over Admin,Audit: Gestion de Inventario Global
    Admin->>FE: Accede al InventoryDashboard
    FE->>Nginx: GET /api/inventory/stock/
    Nginx->>API: proxy → GET /api/inventory/stock/
    API->>DB: SELECT StockBodega JOIN Bodega JOIN Sede (sin filtro — acceso total)
    DB-->>API: Stock de todas las sedes y bodegas
    API-->>FE: 200 JSON [{bodega, sede, producto, cantidad}]
    FE-->>Admin: Dashboard con metricas globales (Recharts)

    Admin->>FE: Realiza transferencia entre bodegas
    FE->>Nginx: POST /api/inventory/transferencias/ {producto_id, bodega_origen, bodega_destino, cantidad, lote, observaciones}
    Nginx->>API: proxy → POST /api/inventory/transferencias/
    API->>DB: BEGIN TRANSACTION
    API->>DB: SELECT StockBodega FOR UPDATE (bodega_origen)
    DB-->>API: Stock actual
    alt Stock insuficiente
        API-->>FE: 400 {error: "Stock insuficiente en bodega origen. Disponible: X"}
        FE-->>Admin: Alerta de stock insuficiente
    else Stock suficiente
        API->>DB: UPDATE StockBodega SET cantidad = cantidad - X WHERE bodega=origen
        API->>DB: UPDATE StockBodega SET cantidad = cantidad + X WHERE bodega=destino (o INSERT si no existe)
        API->>DB: INSERT MovimientoInventario (tipo=TRANSFERENCIA, bodega_origen, bodega_destino, cantidad)
        API->>DB: COMMIT
        DB-->>API: OK
        API->>Audit: INSERT AuditLog {accion: "transferencia_inventario"}
        API-->>FE: 200 {message: "Transferencia realizada con exito."}
        FE-->>Admin: Confirmacion de transferencia exitosa
    end

    Note over Admin,Audit: Gestion de Formulas de Color
    Admin->>FE: Elimina formula (cascade delete)
    FE->>Nginx: DELETE /api/formulas-color/{id}/
    Nginx->>API: proxy → DELETE /api/formulas-color/{id}/
    API->>DB: DELETE FormulaColor + DetalleFormula (cascade)
    DB-->>API: OK
    API->>Audit: INSERT AuditLog {accion: "delete_formula_color"}
    API-->>FE: 204 No Content
    FE-->>Admin: Formula eliminada del sistema

    Note over Admin,Audit: Auditoria del Sistema
    Admin->>FE: Solicita logs de auditoria con filtros
    FE->>Nginx: GET /api/audit-logs/?fecha_desde=X&fecha_hasta=Y&sede_id=Z
    Nginx->>API: proxy → GET /api/audit-logs/
    API->>DB: SELECT AuditLog WHERE fecha_hora >= X AND fecha_hora <= Y AND usuario__sede_id = Z ORDER BY -fecha_hora (paginated)
    DB-->>API: Registros de auditoria
    API-->>FE: 200 JSON {count, results: [{accion, usuario, objeto, fecha_hora, ip}]}
    FE-->>Admin: Tabla paginada de eventos auditados con filtros
```

---

## 2. Bodeguero

```mermaid
sequenceDiagram
    actor Bod as Bodeguero
    participant FE as Frontend (BodegueroDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant DB as SQL Server
    participant Proxy as ReportingProxyView (Django)
    participant Report as reporting_excel :8002

    Note over Bod,Report: Inicio de Sesion y Vista General
    Bod->>FE: Accede al dashboard
    FE->>Nginx: GET /api/inventory/alertas-stock/?sede_id=X
    Nginx->>API: proxy → GET /api/inventory/alertas-stock/
    API->>DB: SELECT StockBodega WHERE cantidad < producto__stock_minimo AND bodega_id IN bodegas_asignadas
    DB-->>API: Productos con stock bajo
    API-->>FE: 200 JSON [{bodega, producto, stock_actual, stock_minimo, faltante}]
    FE-->>Bod: Panel de alertas con productos criticos

    FE->>Nginx: GET /api/inventory/stock/?bodega_ids=X,Y
    Nginx->>API: proxy → GET /api/inventory/stock/
    API->>DB: SELECT StockBodega WHERE bodega_id IN bodegas_asignadas_usuario
    DB-->>API: Niveles de stock actuales
    API-->>FE: 200 JSON stock de bodegas asignadas
    FE-->>Bod: Visualizacion de niveles de inventario

    Note over Bod,Report: Registro de Movimientos de Inventario
    Bod->>FE: Registra entrada de mercancia (recepcion)
    FE->>Nginx: POST /api/inventory/movimientos/ {tipo_movimiento: "COMPRA", producto_id, cantidad, bodega_destino_id, proveedor_id, documento_ref}
    Nginx->>API: proxy → POST /api/inventory/movimientos/
    API->>DB: BEGIN TRANSACTION
    API->>DB: INSERT o UPDATE StockBodega (bodega_destino, cantidad += entrada)
    API->>DB: INSERT MovimientoInventario (COMPRA, saldo_resultante)
    API->>DB: COMMIT
    DB-->>API: OK
    API-->>FE: 201 Created {movimiento_id, saldo_resultante}
    FE-->>Bod: Stock actualizado + movimiento registrado

    Bod->>FE: Edita movimiento COMPRA existente con justificacion
    FE->>Nginx: PUT /api/inventory/movimientos/{id}/ {cantidad: nueva, razon_cambio: "justificacion"}
    Nginx->>API: proxy → PUT /api/inventory/movimientos/{id}/
    API->>DB: BEGIN TRANSACTION
    API->>DB: SELECT StockBodega FOR UPDATE (bodega_destino del movimiento)
    alt Reduccion deja stock negativo
        API-->>FE: 400 {error: "No se puede reducir la entrada en X porque el stock actual es insuficiente"}
        FE-->>Bod: Alerta de error — operacion cancelada
    else Cambio valido
        API->>DB: UPDATE StockBodega SET cantidad += (nueva - anterior)
        API->>DB: INSERT AuditoriaMovimiento {campo: "cantidad", valor_anterior, valor_nuevo, razon_cambio}
        API->>DB: UPDATE MovimientoInventario SET cantidad=nueva, editado=true, fecha_ultima_edicion=now()
        API->>DB: COMMIT
        DB-->>API: OK
        API-->>FE: 200 {message: "Movimiento actualizado con exito", cambios: ["cantidad"]}
        FE-->>Bod: Historial de auditoria actualizado
    end

    Note over Bod,Report: Consulta de Kardex
    Bod->>FE: Solicita Kardex de bodega por fecha y producto
    FE->>Nginx: GET /api/inventory/bodegas/{id}/kardex/?producto_id=X&fecha_inicio=Y&fecha_fin=Z
    Nginx->>API: proxy → GET /api/inventory/bodegas/{id}/kardex/
    API->>DB: SELECT MovimientoInventario WHERE (bodega_origen=id OR bodega_destino=id) AND producto=X AND fecha BETWEEN Y AND Z ORDER BY fecha
    DB-->>API: Movimientos ordenados cronologicamente
    API-->>FE: 200 JSON [{fecha, tipo, documento_ref, entrada, salida, saldo_resultante, lote, usuario}]
    FE-->>Bod: Tabla kardex con entradas, salidas y saldo progresivo

    Note over Bod,Report: Generacion de Reportes Excel via JWT Bearer
    Bod->>FE: Solicita reporte de movimientos en Excel
    FE->>Nginx: GET /api/inventory/reportes/export/movimientos/?bodega_id=X&fecha_desde=Y&fecha_hasta=Z
    Nginx->>API: proxy → GET /api/inventory/reportes/export/movimientos/
    Note over API,Proxy: ReportingProxyView valida sesion usuario y permisos de bodega
    Proxy->>DB: SELECT Bodega WHERE id=X (verifica acceso del bodeguero)
    DB-->>Proxy: Bodega encontrada
    alt Bodega no asignada al usuario
        Proxy-->>FE: 403 {detail: "No tiene permiso para acceder a esta bodega"}
        FE-->>Bod: Alerta de acceso denegado
    else Acceso autorizado
        Proxy->>Proxy: JWTServiceAuthentication.generate_token(service_name="backend-proxy", scopes=["reports:read"], expires_in=300)
        Note right of Proxy: Firma JWT RS256 con clave privada del backend
        Proxy->>Report: GET /export/movimientos/?bodega_id=X&fecha_desde=Y&fecha_hasta=Z<br/>Authorization: Bearer {JWT RS256}
        Report->>Report: Valida JWT RS256 (clave publica distribuida)
        Report->>Report: Verifica scope "reports:read"
        Report->>API: GET /api/internal/v1/reports/kardex/?bodega_id=X&fecha_desde=Y&fecha_hasta=Z<br/>Authorization: Bearer {JWT RS256}
        API->>DB: SELECT MovimientoInventario con filtros aplicados
        DB-->>API: Dataset completo
        API-->>Report: 200 JSON dataset
        Report->>Report: Genera DataFrame Pandas → openpyxl → .xlsx
        Report-->>Proxy: Blob application/vnd.openxmlformats-officedocument.spreadsheetml.sheet + Content-Disposition
        Proxy-->>FE: HttpResponse con binario Excel
        FE->>FE: URL.createObjectURL(blob) → click automatico → revoke
        FE-->>Bod: Descarga automatica del reporte .xlsx
    end

    Note over Bod,Report: Consulta de Trazabilidad de Lotes
    Bod->>FE: Busca lote por codigo de barras
    FE->>Nginx: GET /api/inventory/lotes/{codigo}/movimientos/
    Nginx->>API: proxy → GET /api/inventory/lotes/{codigo}/movimientos/
    API->>DB: SELECT LoteProduccion WHERE codigo_lote=codigo
    API->>DB: SELECT MovimientoInventario WHERE lote=lote ORDER BY fecha
    DB-->>API: Movimientos del lote con bodegas y usuarios
    API-->>FE: 200 JSON {lote_codigo, producto, historial: [{fecha, tipo, bodega_origen, bodega_destino, cantidad}]}
    FE-->>Bod: Historial completo de trazabilidad del lote
```

---

## 3. Operario

```mermaid
sequenceDiagram
    actor Op as Operario
    participant FE as Frontend (OperarioDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant DB as SQL Server

    Note over Op,DB: Inicio y Vista de Ordenes Asignadas
    Op->>FE: Accede al dashboard
    FE->>Nginx: GET /api/ordenes-produccion/?estado=en_proceso
    Nginx->>API: proxy → GET /api/ordenes-produccion/
    API->>DB: SELECT OrdenProduccion WHERE operario_asignado=current_user AND estado='en_proceso'
    DB-->>API: Ordenes activas del operario con detalles
    API-->>FE: 200 JSON [{id, codigo, producto_salida, maquina, estado, prioridad}]
    FE-->>Op: Tarjetas de ordenes activas asignadas

    Note over Op,DB: Registro de Lote de Produccion
    Op->>FE: Selecciona orden y abre formulario de registro
    FE->>Nginx: GET /api/ordenes-produccion/{id}/
    Nginx->>API: proxy → GET /api/ordenes-produccion/{id}/
    API->>DB: SELECT OrdenProduccion WHERE id=id AND operario_asignado=current_user
    DB-->>API: Detalle de orden (maquina asignada, producto_salida, bodega_entrada, bodega_salida)
    API-->>FE: 200 JSON detalle orden
    FE-->>Op: Formulario pre-cargado con maquina, producto y bodegas

    Op->>FE: Completa datos del lote (peso, unidades, turno, hora_inicio, hora_final)
    FE->>Nginx: POST /api/ordenes-produccion/{id}/registrar-lote/ {peso_neto_producido, unidades_empaque, turno, hora_inicio, hora_final}
    Nginx->>API: proxy → POST /api/ordenes-produccion/{id}/registrar-lote/
    API->>DB: BEGIN TRANSACTION
    API->>DB: INSERT LoteProduccion {codigo_lote: auto, peso_neto_producido, operario=current_user, maquina, turno, hora_inicio, hora_final, orden_produccion_id}
    API->>DB: INSERT MovimientoInventario (tipo=PRODUCCION, lote, producto_salida, bodega_destino=bodega_salida_maquina)
    API->>DB: INSERT o UPDATE StockBodega (bodega_salida, producto, lote, cantidad += peso_producido)
    API->>DB: COMMIT
    DB-->>API: Lote registrado con ID
    API-->>FE: 201 Created {codigo_lote, lote_id}
    FE-->>Op: Confirmacion con codigo de lote generado

    Note over Op,DB: Consulta de Historial de Produccion Personal
    Op->>FE: Ve su historial de lotes producidos
    FE->>Nginx: GET /api/lotes-produccion/?operario=current_user&ordering=-hora_inicio
    Nginx->>API: proxy → GET /api/lotes-produccion/
    API->>DB: SELECT LoteProduccion WHERE operario_id=current_user ORDER BY hora_inicio DESC
    DB-->>API: Lista de lotes historicos del operario
    API-->>FE: 200 JSON [{codigo_lote, peso_neto_producido, producto, hora_inicio, hora_final, turno}]
    FE-->>Op: Timeline de produccion personal

    Note over Op,DB: Consulta de Metricas de Desempeno
    Op->>FE: Accede a sus metricas de rendimiento
    FE->>Nginx: GET /api/users/{id}/desempeno/
    Nginx->>API: proxy → GET /api/users/{id}/desempeno/
    API->>DB: SELECT SUM(peso_neto_producido), COUNT(*), AVG per turno FROM LoteProduccion WHERE operario=current_user
    DB-->>API: KPIs calculados
    API-->>FE: 200 JSON {peso_total_kg, lotes_registrados, promedio_por_turno, lotes_por_dia}
    FE-->>Op: Dashboard personal con indicadores de desempeno (Recharts)

    Note over Op,DB: Consulta de Stock de Materia Prima (Solo Lectura)
    Op->>FE: Consulta disponibilidad de materia prima
    FE->>Nginx: GET /api/inventory/alertas-stock/
    Nginx->>API: proxy → GET /api/inventory/alertas-stock/
    API->>DB: SELECT StockBodega WHERE cantidad < producto__stock_minimo AND bodega_id IN bodegas_asignadas
    DB-->>API: Alertas de stock bajo
    API-->>FE: 200 JSON alertas
    FE-->>Op: Vista de productos con stock critico (solo lectura, sin edicion)
```

---

## 4. Ejecutivo

```mermaid
sequenceDiagram
    actor Eje as Ejecutivo
    participant FE as Frontend (EjecutivosDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant DB as SQL Server

    Note over Eje,DB: Dashboard General — Vista Multi-Sede
    Eje->>FE: Accede al dashboard ejecutivo
    FE->>Nginx: GET /api/sedes/
    Nginx->>API: proxy → GET /api/sedes/
    API->>DB: SELECT Sede WHERE all (sin filtro — ejecutivo tiene acceso global)
    DB-->>API: Todas las sedes del sistema
    API-->>FE: 200 JSON [{id, nombre, ciudad}]
    FE-->>Eje: Selector de sede para filtrar vistas

    FE->>Nginx: GET /api/kpi-ejecutivo/?sede_id=X
    Nginx->>API: proxy → GET /api/kpi-ejecutivo/
    API->>API: ProduccionKPIService(sede_id=X).obtener_kpis()
    API->>DB: SELECT OrdenProduccion, LoteProduccion GROUP BY estado/fecha WHERE sede=X
    DB-->>API: Datos de produccion agregados
    API->>API: ExecutiveKPIService(sede_id=X).obtener_kpis()
    API->>DB: SELECT OrdenCompra, StockBodega (F() expr), PedidoVenta WHERE sede=X
    DB-->>API: Datos MRP, stock y cartera
    API-->>FE: 200 JSON {produccion: {ops_pendientes, kg_hoy, kg_semana, kg_mes}, mrp: {productos_bajo_minimo}, cartera: {vencida_total}}
    FE-->>Eje: Cards KPI: OPs por estado, kg producidos, productos bajo minimo, cartera vencida

    Note over Eje,DB: Analisis de Ventas
    Eje->>FE: Filtra reporte de ventas por vendedor y fechas
    FE->>Nginx: GET /api/pedidos-venta/?vendedor_id=X&fecha_inicio=Y&fecha_fin=Z
    Nginx->>API: proxy → GET /api/pedidos-venta/
    API->>DB: SELECT PedidoVenta WHERE vendedor_asignado_id=X AND fecha_pedido BETWEEN Y AND Z AND anulado=false
    DB-->>API: Ordenes de venta filtradas con cliente y sede
    API-->>FE: 200 JSON [{id, guia_remision, cliente, fecha_pedido, estado, esta_pagado}]
    FE-->>Eje: Tabla + grafico de barras de ventas por periodo (Recharts)

    Note over Eje,DB: KPIs de Produccion
    Eje->>FE: Accede a metricas de produccion por area
    FE->>Nginx: GET /api/lotes-produccion/?sede_id=X&fecha_inicio=Y
    Nginx->>API: proxy → GET /api/lotes-produccion/
    API->>DB: SELECT LoteProduccion JOIN OrdenProduccion JOIN Maquina JOIN Area WHERE sede=X AND hora_inicio >= Y
    DB-->>API: Lotes con datos de area y maquina
    API-->>FE: 200 JSON produccion agregada por area y maquina
    FE-->>Eje: Grafico de eficiencia por area productiva + pie chart de utilizacion de maquinas

    Note over Eje,DB: Gestion de Clientes (Vista Global)
    Eje->>FE: Consulta lista de clientes con estado de credito
    FE->>Nginx: GET /api/clientes/
    Nginx->>API: proxy → GET /api/clientes/
    API->>DB: SELECT Cliente WHERE all (ejecutivo sin restriccion de vendedor)
    DB-->>API: Todos los clientes del sistema con limite_credito y cartera_vencida
    API-->>FE: 200 JSON [{id, nombre_razon_social, limite_credito, cartera_vencida, vendedor_asignado}]
    FE-->>Eje: Tabla de clientes con estado de credito

    Note over Eje,DB: Alertas de Inventario Multi-Sede
    Eje->>FE: Revisa alertas de stock bajo (todas las sedes)
    FE->>Nginx: GET /api/inventory/alertas-stock/
    Nginx->>API: proxy → GET /api/inventory/alertas-stock/
    API->>DB: SELECT StockBodega WHERE cantidad < producto__stock_minimo (acceso global sin filtro de bodega)
    DB-->>API: Todas las alertas del sistema
    API-->>FE: 200 JSON [{bodega, sede, producto, stock_actual, stock_minimo, faltante}]
    FE-->>Eje: Dashboard de alertas con filtro por sede

    Note over Eje,DB: Auto-Refresh de Datos
    loop Cada N segundos (auto-refresh activo en dashboard)
        FE->>Nginx: GET /api/kpi-ejecutivo/?sede_id=X
        Nginx->>API: proxy → GET /api/kpi-ejecutivo/
        API->>DB: Queries KPI actualizadas
        DB-->>API: Datos frescos
        API-->>FE: 200 JSON KPIs actualizados
        FE-->>Eje: Dashboard refrescado automaticamente
    end
```

---

### CU-EJ-01: Ejecutivo consulta KPIs ejecutivos consolidados

```mermaid
sequenceDiagram
    actor Eje as Ejecutivo
    participant FE as EjecutivosDashboard (Tab Resumen)
    participant Nginx as Nginx
    participant API as Django REST API
    participant SvcP as ProduccionKPIService
    participant SvcE as ExecutiveKPIService
    participant DB as SQL Server

    Eje->>FE: Abre dashboard o cambia sede en selector
    FE->>Nginx: GET /api/kpi-ejecutivo/?sede_id=X
    Nginx->>API: proxy → GET /api/kpi-ejecutivo/?sede_id=X

    API->>SvcP: ProduccionKPIService(sede_id=X).obtener_kpis()
    SvcP->>DB: SELECT OrdenProduccion GROUP BY estado WHERE sede=X
    SvcP->>DB: SELECT SUM(peso_neto_producido) FROM LoteProduccion GROUP BY fecha WHERE sede=X
    DB-->>SvcP: Datos de produccion (OPs por estado, kg hoy/semana/mes)
    SvcP-->>API: ProduccionKPIs (frozen dataclass)

    API->>SvcE: ExecutiveKPIService(sede_id=X).obtener_kpis()
    SvcE->>DB: SELECT StockBodega WHERE cantidad < stock_minimo (F() expression) AND sede=X
    SvcE->>DB: SELECT SUM(cartera_vencida) FROM Cliente WHERE sede=X
    SvcE->>DB: SELECT OrdenCompra WHERE estado='pendiente' AND sede=X
    DB-->>SvcE: Datos MRP, stock y cartera
    SvcE-->>API: ExecutiveKPIs (frozen dataclass)

    API-->>FE: 200 JSON {produccion: {ops_pendientes, ops_en_proceso, ops_completadas, kg_hoy, kg_semana, kg_mes}, mrp: {productos_bajo_minimo}, stock: {valor_total_bodega}, cartera: {vencida_total, clientes_deudores}}
    FE-->>Eje: Cards KPI: OPs por estado, kg hoy/semana/mes, productos bajo minimo, cartera vencida
```

### CU-EJ-07: Ejecutivo descarga reporte gerencial Excel

```mermaid
sequenceDiagram
    actor Eje as Ejecutivo
    participant FE as EjecutivosDashboard (Tab Reportes)
    participant Valid as Validacion Frontend
    participant Nginx as Nginx
    participant Proxy as ReportingProxyView (Django)
    participant InternalAPI as Django Internal API
    participant Report as reporting_excel :8002
    participant DB as SQL Server

    Eje->>FE: Selecciona rango de fechas y sede (opcional)
    Eje->>FE: Clic en boton de descarga (ej. "Ordenes de Produccion")

    FE->>Valid: Valida fecha_inicio <= fecha_fin
    alt Rango invalido
        Valid-->>FE: toast.error("La fecha de inicio no puede ser posterior a la fecha de fin")
        FE-->>Eje: Alerta de error — sin llamada al API
    else Rango valido
        FE->>FE: setDescargando(ruta) — deshabilita todos los botones de descarga
        FE->>Nginx: GET /api/inventory/reportes/produccion/ordenes?fecha_inicio=X&fecha_fin=Y&sede_id=Z
        Nginx->>Proxy: proxy → GET /api/inventory/reportes/produccion/ordenes

        Proxy->>Proxy: Valida sesion usuario (IsAuthenticated)
        Proxy->>Proxy: Valida path contra whitelist _ALLOWED_REPORT_PATH (previene Path Traversal)
        Proxy->>Proxy: JWTServiceAuthentication.generate_token(service_name="backend-proxy", scopes=["reports:read"], expires_in=300)
        Note right of Proxy: Firma JWT RS256 con INTERNAL_JWT_PRIVATE_KEY de settings

        Proxy->>Report: GET /produccion/ordenes?fecha_inicio=X&fecha_fin=Y&sede_id=Z<br/>Authorization: Bearer {JWT RS256 firmado}
        Report->>Report: Valida JWT RS256 (INTERNAL_JWT_PUBLIC_KEY distribuida al servicio satélite)
        Report->>Report: HasScope("reports:read") — verifica scope en payload

        Report->>InternalAPI: GET /api/internal/v1/produccion/ordenes/?fecha_desde=X&fecha_hasta=Y&sede_id=Z<br/>Authorization: Bearer {JWT RS256}
        InternalAPI->>InternalAPI: JWTServiceAuthentication + IsInternalService + HasScope("reports:read")
        InternalAPI->>InternalAPI: AuditLogger.log(service="backend-proxy", action="get_ordenes_produccion")
        InternalAPI->>DB: SELECT OrdenProduccion JOIN Producto JOIN Sede WHERE fecha BETWEEN X AND Y AND sede=Z
        DB-->>InternalAPI: Dataset de ordenes
        InternalAPI-->>Report: 200 JSON [{id, codigo, estado, prioridad, producto_descripcion, peso_neto_requerido, sede_nombre}]

        Report->>Report: Convierte JSON a Pandas DataFrame
        Report->>Report: ReportFactory.create("xlsx").generate(df, "ordenes_produccion.xlsx")
        Report-->>Proxy: Blob application/vnd.openxmlformats-officedocument.spreadsheetml.sheet + Content-Disposition: attachment

        Proxy-->>FE: HttpResponse con binario Excel (headers copiados)
        FE->>FE: URL.createObjectURL(blob) → click automatico → URL.revokeObjectURL
        FE->>FE: setDescargando(null) — rehabilita botones
        FE-->>Eje: toast.success("Reporte descargado") + descarga del archivo .xlsx
    end

    Note over FE,Report: El mismo flujo aplica para los reportes disponibles:<br/>gerencial/ventas, gerencial/top-clientes, gerencial/deudores,<br/>produccion/ordenes, produccion/lotes, produccion/tendencia
```

---

## 5. Ventas (Vendedor)

```mermaid
sequenceDiagram
    actor Ven as Vendedor
    participant FE as Frontend (VendedorDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant DB as SQL Server

    Note over Ven,DB: Gestion de Clientes
    Ven->>FE: Busca cliente existente por RUC o nombre
    FE->>Nginx: GET /api/clientes/?search=termino
    Nginx->>API: proxy → GET /api/clientes/?search=termino
    API->>DB: SELECT Cliente WHERE (ruc LIKE '%termino%' OR nombre_razon_social LIKE '%termino%') AND vendedor_asignado=current_user
    DB-->>API: Clientes encontrados
    API-->>FE: 200 JSON [{id, nombre_razon_social, ruc, limite_credito, cartera_vencida}]
    FE-->>Ven: Resultados de busqueda con estado de credito

    Ven->>FE: Crea nuevo cliente
    FE->>Nginx: POST /api/clientes/ {ruc, nombre_razon_social, direccion_envio, nivel_precio, limite_credito, plazo_credito_dias}
    Nginx->>API: proxy → POST /api/clientes/
    API->>DB: INSERT Cliente (vendedor_asignado=current_user, sede=user.sede)
    DB-->>API: Cliente creado con ID
    API-->>FE: 201 Created {id, nombre_razon_social}
    FE-->>Ven: Cliente disponible para crear pedidos

    Note over Ven,DB: Creacion de Pedido de Venta
    Ven->>FE: Inicia nuevo pedido de venta
    FE->>Nginx: GET /api/productos/?sede=current_user.sede
    Nginx->>API: proxy → GET /api/productos/
    API->>DB: SELECT Producto WHERE sede=current_user.sede AND activo=true
    DB-->>API: Catalogo de productos disponibles con precios por nivel
    API-->>FE: 200 JSON [{id, codigo, descripcion, precio_base, tipo, unidad_medida}]
    FE-->>Ven: Selector de productos con precios

    Ven->>FE: Agrega productos al pedido (cantidad/peso, precio)
    Ven->>FE: Aplica IVA y retencion si corresponde
    Ven->>FE: Ingresa numero de guia de remision
    FE->>Nginx: POST /api/pedidos-venta/ {cliente_id, detalles: [{producto_id, peso, precio_unitario}], iva_inclusivo, retencion, guia_remision}
    Nginx->>API: proxy → POST /api/pedidos-venta/
    API->>DB: INSERT PedidoVenta (vendedor_asignado=current_user, sede=user.sede, estado=pendiente)
    API->>DB: INSERT DetallePedido[] (producto, peso, precio_unitario, subtotal)
    API->>DB: Calcula total con IVA y retencion aplicables
    DB-->>API: Pedido creado con ID
    API-->>FE: 201 Created {id, guia_remision, total}
    FE-->>Ven: Pedido registrado con numero de orden

    Note over Ven,DB: Registro de Pagos
    Ven->>FE: Registra pago de cliente contra pedido
    FE->>Nginx: POST /api/pagos-cliente/ {pedido_id, monto, metodo_pago, comprobante, notas}
    Nginx->>API: proxy → POST /api/pagos-cliente/
    API->>DB: INSERT PagoCliente (pedido, monto, metodo, fecha=now())
    API->>DB: UPDATE PedidoVenta SET esta_pagado=true/partial segun monto acumulado
    API->>DB: Recalcula cartera_vencida del Cliente si corresponde
    DB-->>API: Pago registrado
    API-->>FE: 201 Created {pago_id, estado_pedido}
    FE-->>Ven: Estado de pago actualizado en el pedido

    Note over Ven,DB: Consulta de Mis Pedidos
    Ven->>FE: Ve sus pedidos del periodo con estado
    FE->>Nginx: GET /api/pedidos-venta/?fecha_inicio=X&fecha_fin=Y
    Nginx->>API: proxy → GET /api/pedidos-venta/
    API->>DB: SELECT PedidoVenta WHERE vendedor_asignado=current_user AND fecha_pedido BETWEEN X AND Y ORDER BY -fecha_pedido
    DB-->>API: Pedidos del vendedor en el periodo
    API-->>FE: 200 JSON [{id, cliente, total, estado, esta_pagado, fecha_pedido, guia_remision}]
    FE-->>Ven: Tabla de pedidos (pendientes, pagados, despachados)

    Note over Ven,DB: Generacion de Documentos PDF
    Ven->>FE: Descarga pedido como PDF
    FE->>Nginx: GET /api/pedidos-venta/{id}/download_pdf/
    Nginx->>API: proxy → GET /api/pedidos-venta/{id}/download_pdf/
    API->>DB: SELECT PedidoVenta + DetallePedido + Cliente + Sede + Vendedor WHERE id=id AND vendedor=current_user
    DB-->>API: Datos completos del pedido
    API->>API: Renderiza plantilla PDF con datos del pedido (WeasyPrint o similar)
    API-->>FE: application/pdf
    FE-->>Ven: Descarga o previsualizacion del PDF para imprimir o enviar al cliente
```

---

## 6. Encargado de Despacho

```mermaid
sequenceDiagram
    actor ED as Encargado de Despacho
    participant FE as Frontend (EmpaquetadoDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant DB as SQL Server

    Note over ED,DB: Inicio de Sesion y Vista de Pedidos Pendientes
    ED->>FE: Accede al modulo de despacho
    FE->>Nginx: GET /api/pedidos-venta/?estado=pendiente
    Nginx->>API: proxy → GET /api/pedidos-venta/?estado=pendiente
    API->>DB: SELECT PedidoVenta JOIN DetallePedido JOIN Cliente WHERE estado='pendiente' AND anulado=false ORDER BY -fecha_pedido
    DB-->>API: Pedidos pendientes de despacho con sus detalles
    API-->>FE: 200 JSON [{id, cliente, guia_remision, detalles: [{producto, peso, precio_unitario}], fecha_pedido}]
    FE-->>ED: Tabla de pedidos pendientes de despacho con productos requeridos

    ED->>FE: Consulta historial de despachos anteriores
    FE->>Nginx: GET /api/inventory/despachos/?fecha_desde=X&fecha_hasta=Y
    Nginx->>API: proxy → GET /api/inventory/despachos/
    API->>DB: SELECT HistorialDespacho JOIN DetalleHistorialDespacho JOIN DetalleHistorialDespachoPedido WHERE fecha_despacho BETWEEN X AND Y ORDER BY -fecha_despacho
    DB-->>API: Historial de despachos con lotes y pedidos asociados
    API-->>FE: 200 JSON [{id, fecha_despacho, usuario, total_bultos, total_peso_kg, pedidos, lotes, items_no_despachados}]
    FE-->>ED: Tabla de historial de despachos con detalles
```

---

### CU-ED-01: Despacho con validacion de items incompletos

```mermaid
sequenceDiagram
    actor ED as Encargado de Despacho
    participant FE as Frontend (EmpaquetadoDashboard)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant ScanSvc as scanning_service :8001 (FastAPI)
    participant IntAPI as Django Internal API
    participant DB as SQL Server

    Note over ED,DB: Seleccion de Pedidos e Inicio de Modo Escaneo
    ED->>FE: Selecciona uno o varios pedidos pendientes mediante checkboxes
    FE->>FE: Estado local: pedidos_seleccionados = [id1, id2, ...]
    ED->>FE: Hace clic en "Iniciar Despacho" o "Modo Escaneo"
    FE->>FE: Activa modo escaneo — muestra input de codigo de barras y lista de lotes escaneados

    Note over ED,ScanSvc: Escaneo de Lotes via scanning_service
    loop Para cada lote escaneado (lectura de codigo de barras o entrada manual)
        ED->>FE: Escanea codigo de barras de lote (input onKeyDown Enter o evento scanner)
        FE->>FE: Extrae codigo del lote del input
        FE->>Nginx: POST /api/scanning/validate {codigo: "LOT-2025-001"}
        Note right of Nginx: Nginx rutea :8001 → scanning_service
        Nginx->>ScanSvc: POST /validate {codigo: "LOT-2025-001"}<br/>Authorization: Bearer {SimpleJWT del usuario}
        ScanSvc->>ScanSvc: LoteValidationService.validate(codigo)
        ScanSvc->>IntAPI: GET /api/internal/v1/lotes/LOT-2025-001/validate/<br/>Authorization: Bearer {JWT RS256 firmado por scanning_service}
        Note right of IntAPI: JWTServiceAuthentication valida RS256<br/>IsInternalService + HasScope("lotes:read")
        IntAPI->>IntAPI: AuditLogger.log(service="scanning_service", action="validate_lote", resource="LOT-2025-001")
        IntAPI->>DB: SELECT LoteProduccion WHERE codigo_lote="LOT-2025-001" + SELECT StockBodega WHERE lote AND cantidad > 0
        DB-->>IntAPI: {lote_id, codigo_lote, producto, estado_op, stock_id, peso_kg, bodega}
        IntAPI-->>ScanSvc: 200 JSON {lote_id, codigo_lote, producto: {id, descripcion}, peso_kg, bodega: {id, nombre}}

        alt Lote no encontrado o sin stock
            ScanSvc-->>FE: 200 JSON {valid: false, reason: "Lote no encontrado en el sistema"}
            FE-->>ED: Alerta visual + sonido error — lote rechazado, no se agrega a la lista
        else Lote ya fue escaneado (duplicado)
            FE->>FE: Verifica si codigo_lote ya esta en lotes_escaneados[]
            FE-->>ED: Alerta "Lote ya escaneado" — no se duplica
        else Lote valido con stock disponible
            ScanSvc-->>FE: 200 JSON {valid: true, lote: {codigo, producto_id, producto_nombre, peso, bodega_id, bodega_nombre}}
            FE->>FE: Agrega lote a lotes_escaneados[] con sus datos
            FE-->>ED: Lote aparece en tabla con producto, bodega y peso en kg
        end
    end

    Note over ED,DB: Confirmacion de Despacho (primera vez — sin confirmar_incompleto)
    ED->>FE: Revisa lista de lotes escaneados y hace clic en "Confirmar Salida"
    FE->>Nginx: POST /api/inventory/process-despacho/ {pedidos: [id1, id2], lotes: ["LOT-001", "LOT-002"], observaciones: "...", confirmar_incompleto: false}
    Nginx->>API: proxy → POST /api/inventory/process-despacho/
    API->>API: IsDespachoWriter — verifica permiso del usuario
    API->>API: ProcessDespachoAPIView._calcular_incompletos(pedidos_ids, lotes_codes)
    API->>DB: SELECT PedidoVenta + DetallePedido WHERE id IN pedidos_ids (requerimientos por producto)
    API->>DB: SELECT StockBodega WHERE lote__codigo_lote IN lotes_codes AND cantidad > 0 (disponible escaneado)
    DB-->>API: Datos de requerimientos y stock escaneado

    alt Todos los productos estan cubiertos (escaneado >= requerido)
        Note over API,DB: Despacho completo — procede directamente
        API->>DB: BEGIN TRANSACTION
        loop Para cada lote en lotes_codes
            API->>DB: SELECT StockBodega FOR UPDATE WHERE lote=lote AND cantidad > 0
            API->>DB: INSERT MovimientoInventario (tipo=VENTA, producto, cantidad=stock.cantidad, bodega_origen=stock.bodega, lote, documento_ref="Despacho #N")
            API->>DB: UPDATE StockBodega SET cantidad = 0
            API->>DB: INSERT DetalleHistorialDespacho (historial, lote, producto, peso)
        end
        API->>DB: INSERT HistorialDespacho (usuario, total_bultos, total_peso, observaciones, items_no_despachados={})
        API->>DB: INSERT DetalleHistorialDespachoPedido (historial, pedido_id) para cada pedido
        API->>DB: UPDATE PedidoVenta SET estado='despachado', fecha_despacho=today() WHERE id IN pedidos_ids
        API->>DB: COMMIT
        DB-->>API: Despacho registrado
        API-->>FE: 200 JSON {message: "Despacho procesado correctamente", despacho_id, pedidos_actualizados, lotes_procesados, items_no_despachados: {}}
        FE-->>ED: toast.success — despacho completado, lista de lotes limpiada

    else Hay productos con cantidad escaneada menor a la requerida
        API-->>FE: 409 Conflict {error: "despacho_incompleto", message: "Hay productos con cantidad despachada menor a la requerida.", items_incompletos: {"Hilo Rojo 30/2": {requerido: 500.0, escaneado: 320.0, faltante: 180.0}, ...}}
        FE->>FE: Abre modal de confirmacion de items faltantes
        FE-->>ED: Modal con tabla de items faltantes:<br/>| Producto | Requerido (kg) | Escaneado (kg) | Faltante (kg) |<br/>| Hilo Rojo 30/2 | 500.0 | 320.0 | 180.0 |

        alt ED decide seguir escaneando
            ED->>FE: Clic en "Cancelar — seguir escaneando"
            FE->>FE: Cierra modal — regresa al modo escaneo activo
            FE-->>ED: Input de escaneo listo para continuar agregando lotes
        else ED acepta despacho parcial
            ED->>FE: Clic en "Despachar de todas formas"
            FE->>Nginx: POST /api/inventory/process-despacho/ {pedidos: [id1, id2], lotes: ["LOT-001", "LOT-002"], observaciones: "Despacho parcial confirmado", confirmar_incompleto: true}
            Nginx->>API: proxy → POST /api/inventory/process-despacho/
            API->>API: _calcular_incompletos() — items_incompletos detectados de nuevo
            Note over API: confirmar_incompleto=true → no retorna 409, procede con transaccion
            API->>DB: BEGIN TRANSACTION
            loop Para cada lote en lotes_codes
                API->>DB: SELECT StockBodega FOR UPDATE WHERE lote=lote AND cantidad > 0
                API->>DB: INSERT MovimientoInventario (tipo=VENTA, cantidad=stock.cantidad, bodega_origen, lote)
                API->>DB: UPDATE StockBodega SET cantidad = 0
                API->>DB: INSERT DetalleHistorialDespacho (historial, lote, producto, peso)
            end
            API->>DB: INSERT HistorialDespacho (usuario, total_bultos, total_peso, observaciones, items_no_despachados={"Hilo Rojo 30/2": {requerido: 500.0, escaneado: 320.0, faltante: 180.0}})
            Note right of DB: items_no_despachados guardado como JSONField<br/>para trazabilidad del despacho parcial
            API->>DB: INSERT DetalleHistorialDespachoPedido para cada pedido
            API->>DB: UPDATE PedidoVenta SET estado='despachado', fecha_despacho=today()
            API->>DB: COMMIT
            DB-->>API: Despacho parcial registrado
            API-->>FE: 200 JSON {message: "Despacho procesado correctamente", despacho_id, pedidos_actualizados, lotes_procesados, items_no_despachados: {"Hilo Rojo 30/2": {requerido: 500.0, escaneado: 320.0, faltante: 180.0}}}
            FE-->>ED: toast.success con advertencia de items no despachados — despacho parcial registrado
        end
    end
```

---

### CU-ED-02: Reversion de Despacho

```mermaid
sequenceDiagram
    actor ED as Encargado de Despacho
    participant FE as Frontend (EmpaquetadoDashboard / HistorialDespachos)
    participant Nginx as Nginx (proxy inverso)
    participant API as Django REST API
    participant RevSvc as DespachoReversionService
    participant DB as SQL Server

    Note over ED,DB: Consulta del Historial para Identificar Despacho a Revertir
    ED->>FE: Accede a la tabla de historial de despachos
    FE->>Nginx: GET /api/inventory/despachos/?fecha_desde=X&fecha_hasta=Y
    Nginx->>API: proxy → GET /api/inventory/despachos/
    API->>DB: SELECT HistorialDespacho + DetalleHistorialDespacho + DetalleHistorialDespachoPedido ORDER BY -fecha_despacho
    DB-->>API: Historial de despachos con detalles de lotes y pedidos
    API-->>FE: 200 JSON [{id, fecha_despacho, usuario, total_bultos, total_peso, pedidos: [{guia_remision, cliente}], lotes: [{codigo, producto, peso}], items_no_despachados}]
    FE-->>ED: Tabla de historial con boton "Revertir" por fila

    Note over ED,DB: Inicio de Reversion con Justificacion Obligatoria
    ED->>FE: Selecciona un despacho y hace clic en "Revertir Despacho"
    FE->>FE: Muestra modal de confirmacion con campo de justificacion obligatoria
    ED->>FE: Escribe justificacion (ej: "Cliente rechazo mercaderia por defecto de calidad")
    ED->>FE: Confirma la reversion

    FE->>Nginx: POST /api/inventory/despachos/{id}/revertir/ {justificacion: "Cliente rechazo mercaderia por defecto de calidad"}
    Nginx->>API: proxy → POST /api/inventory/despachos/{id}/revertir/
    API->>API: IsDespachoWriter — verifica permiso del usuario
    API->>API: Extrae justificacion del body

    alt Justificacion vacia o ausente
        API-->>FE: 400 {justificacion: "Justificacion obligatoria para revertir despacho"}
        FE-->>ED: Alerta de campo requerido — modal permanece abierto
    else Justificacion presente
        API->>DB: BEGIN TRANSACTION
        API->>RevSvc: DespachoReversionService.revertir_despacho(historial, request.user, justificacion)

        RevSvc->>DB: SELECT DetalleHistorialDespacho WHERE historial=historial_id (lotes y pesos despachados)
        DB-->>RevSvc: Lista de lotes con producto y peso original despachado

        loop Para cada DetalleHistorialDespacho (lote despachado)
            RevSvc->>DB: INSERT o UPDATE StockBodega (bodega_origen_original, lote, cantidad += peso_despachado)
            Note right of DB: Restaura el stock del lote en la bodega de origen
            RevSvc->>DB: INSERT MovimientoInventario (tipo=DEVOLUCION, producto, cantidad=peso, bodega_destino=bodega_original, lote, usuario, documento_ref="Reversion Despacho #{id}: justificacion")
        end

        RevSvc->>DB: SELECT DetalleHistorialDespachoPedido WHERE historial=historial_id
        DB-->>RevSvc: Lista de pedidos asociados al despacho

        loop Para cada PedidoVenta asociado
            RevSvc->>DB: UPDATE PedidoVenta SET estado='pendiente', fecha_despacho=NULL WHERE id=pedido_id
            Note right of DB: Pedido regresa a estado pendiente para re-despacho
        end

        RevSvc-->>API: {lotes_revertidos: N, pedidos_restaurados: M}

        API->>DB: DELETE HistorialDespacho WHERE id=historial_id
        Note right of DB: CASCADE elimina DetalleHistorialDespacho y DetalleHistorialDespachoPedido
        API->>DB: COMMIT
        DB-->>API: Reversion completada

        API-->>FE: 200 {message: "Despacho revertido exitosamente", resultado: {lotes_revertidos: N, pedidos_restaurados: M}}
        FE-->>ED: toast.success — historial actualizado, pedidos vuelven a pendientes
    end
```

---

## Resumen de Permisos por Rol

| Accion | Admin Sistemas | Bodeguero | Operario | Jefe Area | Ejecutivo | Vendedor | Encargado Despacho |
|--------|:--------------:|:---------:|:--------:|:---------:|:---------:|:--------:|:------------------:|
| Gestion de usuarios | CRUD | - | - | - | - | - | - |
| Gestion de sedes y areas | CRUD | - | - | Ver | Ver | - | - |
| Gestion de productos | CRUD | Ver | - | Ver | Ver | Ver | Ver |
| Gestion de bodegas | CRUD | Ver (asignadas) | - | - | - | - | - |
| Stock — Ver todas las sedes | CRUD | Ver (asignadas) | Ver (alertas) | Ver (sede) | Ver (todas) | - | Ver |
| Movimientos de inventario | CRUD | CRUD | - | Ver | - | - | - |
| Lotes de produccion | CRUD | Ver | Crear | Ver | Ver | - | Ver |
| Ordenes de produccion | CRUD | - | Ver (propias) | CRUD (sede) | Ver | - | - |
| Formulas de color | CRUD | - | - | Ver | - | - | - |
| Clientes | CRUD | - | - | - | Ver | CRUD | - |
| Pedidos de venta | CRUD | - | - | - | Ver | CRUD (propios) | Ver (pendientes) |
| Pagos de clientes | CRUD | - | - | - | - | Crear | - |
| Despacho — iniciar y confirmar | CRUD | - | - | - | - | - | CRUD |
| Despacho — revertir | CRUD | - | - | - | - | - | CRUD |
| Historial de despachos | CRUD | Ver | - | Ver | Ver | - | CRUD |
| Reportes Excel (via proxy JWT) | CRUD | Parciales (bodegas asignadas) | - | Ver (sede) | Ver (todas) | Ver (propios) | Ver |
| Auditoria | Ver | Ver (inventario propio) | - | - | - | - | - |

---

## Arquitectura de Autenticacion — Referencia Rapida

```mermaid
sequenceDiagram
    participant Browser as Navegador (React)
    participant Nginx as Nginx
    participant Django as Django REST API
    participant ScanSvc as scanning_service (FastAPI)
    participant Report as reporting_excel (FastAPI)
    participant IntAPI as Django Internal API

    Note over Browser,IntAPI: Flujo de autenticacion usuario (SimpleJWT)
    Browser->>Nginx: POST /api/token/ {username, password}
    Nginx->>Django: proxy
    Django->>Django: Autentica via SimpleJWT
    Django-->>Browser: {access: "eyJ...", refresh: "eyJ..."}
    Browser->>Browser: Guarda tokens en estado React (no localStorage)

    Note over Browser,IntAPI: Llamada normal del usuario al API Django
    Browser->>Nginx: GET /api/inventory/stock/ Authorization: Bearer {access_token}
    Nginx->>Django: proxy con header Authorization
    Django->>Django: SimpleJWT valida access_token
    Django-->>Browser: 200 JSON datos

    Note over Browser,IntAPI: Llamada usuario via scanning_service
    Browser->>Nginx: POST /api/scanning/validate Authorization: Bearer {access_token}
    Nginx->>ScanSvc: :8001 → /validate Authorization: Bearer {access_token_usuario}
    ScanSvc->>ScanSvc: Valida SimpleJWT del usuario
    ScanSvc->>ScanSvc: Genera JWT RS256 propio (service_name="scanning_service", scopes=["lotes:read"])
    ScanSvc->>IntAPI: GET /api/internal/v1/lotes/{codigo}/validate/ Authorization: Bearer {JWT RS256 scanning_service}
    IntAPI->>IntAPI: JWTServiceAuthentication valida RS256 con clave publica
    IntAPI->>IntAPI: IsInternalService + HasScope("lotes:read")
    IntAPI-->>ScanSvc: 200 JSON datos del lote
    ScanSvc-->>Browser: 200 JSON {valid, lote}

    Note over Browser,IntAPI: Llamada proxy Django → reporting_excel
    Browser->>Nginx: GET /api/inventory/reportes/kardex/?bodega_id=X Authorization: Bearer {access_token}
    Nginx->>Django: proxy
    Django->>Django: ReportingProxyView — SimpleJWT valida usuario
    Django->>Django: Verifica permisos de bodega del usuario
    Django->>Django: Genera JWT RS256 (service_name="backend-proxy", scopes=["reports:read"], expires_in=300)
    Django->>Report: GET /kardex/?bodega_id=X Authorization: Bearer {JWT RS256 backend-proxy}
    Report->>Report: Valida JWT RS256 con clave publica
    Report->>IntAPI: GET /api/internal/v1/reports/kardex/?bodega_id=X Authorization: Bearer {JWT RS256}
    IntAPI-->>Report: 200 JSON datos
    Report-->>Django: Blob Excel
    Django-->>Browser: HttpResponse Excel
```
