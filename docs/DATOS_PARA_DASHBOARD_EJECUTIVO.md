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
