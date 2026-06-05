# Datos para Dashboard de Reportes Gerenciales (Ejecutivo)

Resumen de toda la información disponible en el apartado de Bodegueros, para usarla en el panel Ejecutivo.

---

## 1. APIs / Endpoints

### Django Backend (REST API)

| Endpoint | Método | Descripción | Parámetros | Respuesta |
|----------|--------|-------------|------------|-----------|
| `/api/inventory/alertas-stock/` | GET | Productos con stock bajo el mínimo | - | Lista de alertas |
| `/api/inventory/stock/` | GET | Stock actual por producto/bodega/lote | - | Lista de items de stock |
| `/api/inventory/bodegas/<bodega_id>/kardex/` | GET | Kardex de un producto en una bodega | `producto_id`, `fecha_inicio`, `fecha_fin`, `proveedor_id`, `lote_codigo` | Lista de movimientos |
| `/api/inventory/retro-kardex/` | GET | Stock a una fecha pasada | `producto_id`, `fecha_corte`, `bodega_id` (opcional) | Stock por bodega |
| `/api/inventory/lotes/<lote_codigo>/movimientos/` | GET | Trazabilidad de un lote | - | Historial de movimientos del lote |
| `/api/productos/` | GET | Catálogo de productos | - | Lista de productos |
| `/api/bodegas/` | GET | Lista de bodegas | - | Lista de bodegas |
| `/api/lotes-produccion/` | GET | Lotes de producción | - | Lista de lotes |
| `/api/proveedores/` | GET | Lista de proveedores | - | Lista de proveedores |

### Reporting Excel (microservicio puerto 8002)

| Endpoint | Método | Descripción | Parámetros |
|----------|--------|-------------|------------|
| `/api/reporting/export/kardex` | GET | Exportar Kardex a Excel/CSV | `bodega_id`, `producto_id`, `proveedor_id`, `fecha_inicio`, `fecha_fin`, `lote_codigo`, `format` |

---

## 2. Estructuras de datos

### AlertaStock (alertas-stock)

```typescript
interface AlertaStock {
  producto: string;
  producto_codigo: string;
  bodega: string;
  stock_actual: string;
  stock_minimo: string;
  faltante?: number;  // stock_minimo - stock_actual
}
```

### StockItem (stock actual)

```typescript
interface StockItem {
  id: number;
  producto: string;
  bodega: string;
  lote: string | null;
  cantidad: string;
}
```

### Movimiento (Kardex)

```typescript
interface Movimiento {
  id: number;
  fecha: string;
  tipo_movimiento: string;
  codigo_producto?: string;
  descripcion_producto?: string;
  lote: string | null;
  entrada?: string;
  salida?: string;
  saldo_resultante?: number;
  documento_ref: string | null;
  usuario: string;
  editado?: boolean;
  has_audit?: boolean;
}
```

### RetroKardex (stock a fecha pasada)

```typescript
interface RetroKardexRow {
  bodega: string;
  stock_calculado: number;
}
```

### Trazabilidad de Lote

```typescript
interface LoteTrazabilidad {
  lote_codigo: string;
  producto: string;
  historial: Array<{
    id: number;
    fecha: string;
    tipo_movimiento: string;
    bodega_origen: string;
    bodega_destino: string;
    cantidad: number;
    documento_ref: string;
    usuario: string;
  }>;
}
```

---

## 3. Componentes del Bodeguero (referencia)

### BodegueroDashboard
- **Stats Cards**: Productos count, Bodegas count, Lotes count
- **Tab Inventario**: usa `InventoryDashboard`
- **Tab Alertas**: usa `AlertasStockView`

### InventoryDashboard (6 tabs)
1. **Stock Actual** – tabla con búsqueda, paginación
2. **Entrada** – formulario Registrar Entrada (COMPRA)
3. **Transferencias** – formulario Transferir entre bodegas
4. **Transformación** – `TransformationView`
5. **Kardex** – filtros: bodega, producto, proveedor, fechas, lote. Tabla de movimientos. Export Excel.
6. **Reportes** – Retro-Kardex (stock a fecha) y Consulta de Lote (trazabilidad)

---

## 4. Permisos actuales (Backend)

- **StockBodegaViewSet**: admin_sistemas, admin_sede ven todo; otros solo bodegas asignadas
- **AlertasStockAPIView**: admin_sistemas, admin_sede ven todo; otros solo bodegas asignadas
- **KardexBodegaAPIView**: sin filtro por rol (usa bodega_id)
- **RetroKardexAPIView**: sin filtro por rol
- **MovimientosPorLoteAPIView**: sin filtro por rol

**Nota**: `ejecutivo` NO está en los grupos que ven todas las bodegas. Para el dashboard gerencial hay que:
- Añadir `ejecutivo` a los grupos que ven todo, O
- Crear endpoints específicos para ejecutivos que retornen datos de todas las bodegas.

---

## 5. Datos ideales para Reportes Gerenciales

| Dato | Fuente | Uso sugerido |
|------|--------|--------------|
| Alertas de stock bajo | `/inventory/alertas-stock/` | KPI / tabla / gráfico de barras |
| Stock total por bodega | `/inventory/stock/` (agregar en frontend) | Gráfico de barras, pie chart |
| Stock por producto | `/inventory/stock/` | Top productos, evolución |
| Movimientos por fecha | `/inventory/bodegas/<id>/kardex/` con fechas | Gráfico de líneas, tabla |
| Stock histórico | `/inventory/retro-kardex/` | Gráfico de evolución |
| Cantidad de productos | `/productos/` | KPI |
| Cantidad de bodegas | `/bodegas/` | KPI |
| Cantidad de lotes | `/lotes-produccion/` | KPI |

---

## 6. Filtros de fecha disponibles

- **Kardex**: `fecha_inicio`, `fecha_fin` (params GET)
- **Retro-Kardex**: `fecha_corte` (params GET)
- **Export Excel Kardex**: `fecha_inicio`, `fecha_fin` (params GET)

---

## 7. Tipos de movimiento (inventario)

Entradas: COMPRA, PRODUCCION, AJUSTE_POSITIVO, DEVOLUCION, AJUSTE  
Salidas: VENTA, CONSUMO, AJUSTE_NEGATIVO  
Otros: TRANSFERENCIA

---

> **[Sprint 6 — 2026-04-10]**

## 8. Endpoints Ejecutivos (nuevos — Sprint 6)

### Django Backend — Endpoints KPI y Producción

| Endpoint | Método | Descripción | Requiere |
|----------|--------|-------------|----------|
| `/api/kpi-ejecutivo/` | GET | KPIs consolidados: producción, MRP, stock, cartera | `?sede_id=` (opcional) |
| `/api/produccion/resumen/` | GET | Resumen de estado de órdenes de producción | `?sede_id=` (opcional) |
| `/api/produccion/tendencia/` | GET | Serie temporal diaria de kg producidos | `?sede_id=` (opcional) |

#### Respuesta: `/api/kpi-ejecutivo/`

```typescript
interface KpiEjecutivoResponse {
  produccion: {
    ops_pendiente: number;
    ops_en_proceso: number;
    ops_finalizada: number;
    kg_hoy: number;
    kg_semana: number;
    kg_mes: number;
    tiempo_promedio_lote_min: number;
  };
  mrp: {
    ocs_pendientes: number;
    ocs_aprobadas: number;
    ocs_rechazadas: number;
    productos_en_deficit: number;
  };
  stock: {
    productos_bajo_minimo: number;
  };
  cartera: {
    cuentas_por_cobrar: number;
    cartera_vencida: number;
    pedidos_pendientes: number;
    pedidos_despachados: number;
  };
}
```

#### Respuesta: `/api/produccion/resumen/`

```typescript
interface ProduccionResumenResponse {
  ops_por_estado: Array<{ estado: string; cantidad: number }>;
  kg_hoy: number;
  kg_semana: number;
  kg_mes: number;
  tiempo_promedio_lote_min: number;
}
```

#### Respuesta: `/api/produccion/tendencia/`

```typescript
// Array de puntos de la serie temporal
type TendenciaResponse = Array<{
  fecha: string;   // "YYYY-MM-DD"
  kg: number;      // kg producidos ese día (0 si no hubo producción)
}>;
```

**Nota**: Los endpoints usan el `ProduccionKPIService` y `ExecutiveKPIService` del Service Layer (`gestion/services/` e `inventory/services/`). El parámetro `sede_id` es derivado del perfil del usuario ejecutivo si no se pasa explícitamente.

---

## 9. Reporting Excel — Endpoints de Exportación (Sprint 6)

Microservicio `reporting_excel` (puerto 8003). Prefijo de ruta Nginx: `/reporting/`.

### Endpoints disponibles

| `data-testid` (frontend) | Ruta completa | SP SQL Server | Descripción |
|--------------------------|---------------|---------------|-------------|
| `btn-export-ventas` | `/reporting/gerencial/ventas` | — | Reporte de ventas del período |
| `btn-export-top-clientes` | `/reporting/gerencial/top-clientes` | — | Top clientes por monto |
| `btn-export-deudores` | `/reporting/gerencial/deudores` | — | Cartera y deudores |
| `btn-export-ordenes` | `/reporting/produccion/ordenes` | `sp_GetOrdenesProduccionGerencial` | Detalle de órdenes de producción |
| `btn-export-lotes` | `/reporting/produccion/lotes` | `sp_GetLotesProduccionGerencial` | Lotes producidos con métricas |
| `btn-export-tendencia` | `/reporting/produccion/tendencia` | `sp_GetTendenciaProduccionGerencial` | Serie temporal kg/día |

### Parámetros comunes (query string)

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `fecha_inicio` | `YYYY-MM-DD` | Inicio del período (requerido) |
| `fecha_fin` | `YYYY-MM-DD` | Fin del período (requerido) |
| `sede_id` | `integer` | ID de sede (opcional; `null` = todas) |
| `format` | `"xlsx"` \| `"csv"` | Formato de salida (default: `xlsx`) |

### Validación frontend (CU-EJ-07)

- Si `fecha_inicio > fecha_fin`: `toast.error('La fecha de inicio no puede ser posterior a la fecha de fin')` — sin llamada al API.
- Si hay descarga en curso (`descargando !== null`): todos los botones quedan `disabled`.
- Al completar: `toast.success('Reporte descargado')`.
- En error de red: `toast.error('Error al descargar el reporte')`.
