# Informe de Rendimiento — TexCore API
**Fecha:** 2026-03-31
**Entorno:** Docker Production (SQL Server 2022, Django 5.x, Gunicorn)
**Volumen de datos de prueba:** ~1,032,000 registros (stress test con `load_million`)

---

## Resumen Ejecutivo

| Endpoint | Estado | Tiempo (p50) | Prioridad |
|---|---|---|---|
| `GET /api/clientes/` | 🔴 CRÍTICO | ~2.2s (10K clientes) | P0 |
| `GET /api/ordenes-produccion/` | 🟠 ALTO | ~660ms (21K órdenes) | P1 |
| `GET /api/lotes-produccion/` | 🟢 OK | ~150ms (43K lotes) | — |
| `GET /api/productos/` | 🟢 OK | ~62ms (3.3K productos) | — |
| `GET /api/inventory/movimientos/` | ⚠ PENDIENTE | ~?ms (750K movs) | P1 |
| `GET /api/pedidos-venta/` | 🟢 OK | ~17ms (30K pedidos) | — |
| `GET /api/inventory/stock/` | 🟢 OK | ~7ms (9.9K stock) | — |

**Bugs confirmados:**
- BUG-01: `GET /api/pedidos/`, `GET /api/movimientos/`, `GET /api/stock/` → HTTP 500 (URLs incorrectas en el benchmark inicial — éstas no existen, son `/api/pedidos-venta/`, `/api/inventory/movimientos/`, `/api/inventory/stock/`).

---

## Hotspots Detallados

### PERF-CRIT-01: `ClienteManager` — 3 subconsultas correlacionadas
**Ubicación:** [`gestion/models.py:476-516`](../gestion/models.py#L476)
**Tiempo medido:** ~2.2s para page=1 de 10,505 clientes
**Impacto:** Cada request a `/api/clientes/` ejecuta en SQL Server:

```sql
-- 3 subqueries correlacionadas ejecutadas UNA VEZ POR CLIENTE en el COUNT y luego en los 50 de la página
SELECT ...
  (SELECT SUM(d.total_con_iva) - SUM(p.valor_retencion)
   FROM gestion_pedidoventa p
   JOIN gestion_detallepedido d ON d.pedido_id = p.id
   WHERE p.cliente_id = c.id) AS saldo_calculado,
  ...
  (SELECT SUM(d.total_con_iva) - SUM(p.valor_retencion)
   FROM gestion_pedidoventa p
   JOIN gestion_detallepedido d ON d.pedido_id = p.id
   WHERE p.cliente_id = c.id AND p.esta_pagado = 0 AND p.fecha_vencimiento < TODAY) AS cartera_vencida
FROM gestion_cliente c
```

Con 10K clientes × 3 subqueries × (30K pedidos + 120K detalles): estimado 300-500 operaciones JOIN por request.

**Causa raíz:** `ClienteManager.get_queryset()` aplica las anotaciones en el manager base — se ejecutan en TODOS los querysets de `Cliente` incluido el `COUNT(*)` de paginación.

**Fix recomendado (P0):**
```python
# En ClienteViewSet.get_queryset(), agregar las anotaciones solo cuando se necesitan:
# Opción A: Mover anotaciones de ClienteManager a ClienteViewSet.get_queryset()
# Opción B: Usar un manager alternativo sin anotaciones para lookups internos

# ClienteViewSet.get_queryset():
queryset = Cliente._default_manager.all()  # bypassa ClienteManager
if self.action == 'list':
    queryset = queryset.annotate(
        saldo_calculado=...,
        cartera_vencida=...
    )
```

**Índices recomendados:**
```sql
CREATE INDEX ix_pedido_cliente ON gestion_pedidoventa (cliente_id) INCLUDE (esta_pagado, fecha_vencimiento, valor_retencion);
CREATE INDEX ix_detalle_pedido ON gestion_detallepedido (pedido_id) INCLUDE (total_con_iva);
```

---

### PERF-CRIT-02: `ClienteViewSet` — deep `prefetch_related` innecesario
**Ubicación:** [`gestion/views.py:654-658`](../gestion/views.py#L654)
**Problema:** Para LISTAR clientes se carga todo el árbol de pedidos en memoria:

```python
queryset = Cliente.objects.prefetch_related(
    'pedidoventa_set',              # 30K pedidos
    'pedidoventa_set__detalles',    # 120K detalles
    'pedidoventa_set__detalles__producto'  # 3.3K productos
)
```

Con 10K clientes y 30K pedidos: Django carga ~10K + 30K + 120K + 3.3K objetos Python en RAM por cada request de listado. Esto es innecesario si el serializer solo usa conteos o totales.

**Fix recomendado (P0):**
```python
def get_queryset(self):
    ...
    # Solo prefetch lo que el serializer realmente usa en list
    if self.action == 'list':
        return queryset.only('id', 'nombre_razon_social', 'ruc_cedula', 'sede_id', ...)
    # Para retrieve (detalle de un cliente), sí tiene sentido el prefetch
    return queryset.prefetch_related('pedidoventa_set__detalles__producto')
```

---

### PERF-03: `OrdenProduccionViewSet` — 660ms para 21K órdenes
**Ubicación:** [`gestion/views.py:728-730`](../gestion/views.py#L728)
**Tiempo:** ~660ms
**Causa probable:** `prefetch_related('lotes')` carga todos los lotes (43K) en memoria. Con 20K órdenes cada una con ~2 lotes: 40K objetos Python por request.

**Fix:** Agregar `only()` en el queryset o anotar conteo en lugar de prefetch:
```python
queryset = OrdenProduccion.objects.select_related(...).annotate(
    num_lotes=Count('lotes')
).all()
```

---

### PERF-04: `MovimientoInventarioViewSet` — sin `select_related`, sin ordering explícito
**Ubicación:** [`inventory/views.py:86-88`](../inventory/views.py#L86)

```python
class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.all()  # sin select_related
```

Con 750K movimientos:
- `COUNT(*)` sin índice optimizado → estimado 5-15s
- Sin `select_related('producto', 'bodega_origen', 'bodega_destino', 'lote')` → N+1: 50 registros por página × 4 FKs = 200 queries extra por request
- Sin `ordering` explícito → SQL Server hace full table scan con ORDER BY arbitrario

**Fix recomendado (P1):**
```python
class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    queryset = MovimientoInventario.objects.select_related(
        'producto', 'bodega_origen', 'bodega_destino', 'lote'
    ).order_by('-fecha')
```

**Índice recomendado:**
```sql
CREATE INDEX ix_movimiento_fecha ON inventory_movimientoinventario (fecha DESC)
  INCLUDE (tipo_movimiento, cantidad, producto_id, bodega_origen_id);
```

---

### PERF-05: `AuditableModelMixin.__init__` + `only()` — N+1 oculto
**Ubicación:** [`gestion/models.py:125-127`](../gestion/models.py#L125)
**Problema:** Cuando se usa `QuerySet.only('campo_a', 'campo_b')` en modelos auditables, el `__init__` llama `_get_auditable_data()` que hace `getattr(self, campo_auditable)` para cada campo en `campos_auditables`. Si ese campo fue diferido por `only()`, Django hace `SELECT campo FROM tabla WHERE id=X` por cada campo diferido, por cada instancia.

**Impacto:** Si `ClienteViewSet` usa `only()` con 50 instancias y 4 campos auditables diferidos → 50 × 4 = 200 queries extra invisibles.

**Fix recomendado:**
```python
def _get_auditable_data(self):
    data = {}
    campos = getattr(self, 'campos_auditables', [...])
    deferred = self.get_deferred_fields()  # disponible en Django
    for field in campos:
        if field in deferred:
            continue  # no forzar refresh de campos diferidos en init
        try:
            val = getattr(self, field)
            ...
```

---

### BUG-01: URLs inexistentes retornan `TemplateDoesNotExist: index.html`
**Ubicación:** [`TexCore/urls.py:41`](../TexCore/urls.py#L41)
**Descripción:** El catch-all `re_path(r'^.*', TemplateView.as_view(template_name='index.html'))` captura cualquier URL no registrada y devuelve HTTP 500 cuando `index.html` no existe en el directorio de templates del backend. En producción el frontend React se sirve desde nginx, no desde Django — el template nunca está presente.

**Impacto:** Errores engañosos en lugar de HTTP 404 para rutas API inexistentes. Durante el benchmarking inicial causó falsos positivos al usar `/api/pedidos/` en vez de `/api/pedidos-venta/`.

**Fix recomendado:**
```python
# TexCore/urls.py — en entorno sin templates (producción API-only):
from django.http import HttpResponseNotFound

def react_spa(request):
    # Solo sirve si el template existe; sino 404
    from django.template.loader import get_template
    from django.template.exceptions import TemplateDoesNotExist
    try:
        get_template('index.html')
        return TemplateView.as_view(template_name='index.html')(request)
    except TemplateDoesNotExist:
        return HttpResponseNotFound()
```

O simplemente eliminar el catch-all en la imagen Docker del backend (API-only).

---

## Resumen de Recomendaciones por Prioridad

| ID | Prioridad | Fix | Impacto esperado |
|---|---|---|---|
| FIX-01 | P0 | Mover anotaciones `saldo_calculado`/`cartera_vencida` fuera de `ClienteManager.get_queryset()` | `/api/clientes/` de 2.2s → <200ms |
| FIX-02 | P0 | Eliminar `prefetch_related` profundo en `ClienteViewSet.list` | Reduce RAM y latencia 50-80% |
| FIX-03 | P0 | Índices en `gestion_pedidoventa(cliente_id)` y `gestion_detallepedido(pedido_id)` | Acelera subqueries de saldo |
| FIX-04 | P1 | `select_related` + `order_by('-fecha')` en `MovimientoInventarioViewSet` | Elimina N+1, hace COUNT predecible |
| FIX-05 | P1 | Índice en `inventory_movimientoinventario(fecha DESC)` | COUNT/paginación en 750K rows |
| FIX-06 | P1 | `annotate(num_lotes=Count)` en lugar de `prefetch_related('lotes')` en órdenes | `/api/ordenes-produccion/` de 660ms → <150ms |
| FIX-07 | P2 | Guardar `get_deferred_fields()` en `AuditableModelMixin._get_auditable_data()` | Previene N+1 oculto con `only()` |
| FIX-08 | P2 | Eliminar o hacer condicional el catch-all `index.html` en backend Docker | Elimina 500 engañosos |

---

## Datos de Carga (stress test)

| Modelo | Registros | Método |
|---|---|---|
| Sede / Bodega / Máquina | ~150 | `bulk_create` |
| Producto | 1,000 | `bulk_create` |
| FormulaColor / FaseReceta / DetalleFormula | ~2,000 | `bulk_create` |
| Cliente | 10,000 | `bulk_create` |
| OrdenProduccion | 21,701 | `bulk_create` |
| LoteProduccion | 43,715 | `bulk_create` |
| PedidoVenta + DetallePedido | 30,753 + 121,851 | `bulk_create` |
| StockBodega | 9,944 | `bulk_create` |
| MovimientoInventario | 749,588 | `bulk_create` (en progreso) |
| **TOTAL** | **~989,702** | |

Todos los registros llevan el prefijo `STR-` para identificación y re-ejecución idempotente.
Las fechas fueron aleatorizadas en un rango de 12 meses via `DATEADD(second, -RAND*31536000, GETUTCDATE())`.
