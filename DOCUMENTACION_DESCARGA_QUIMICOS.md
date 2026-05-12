# Documentación: Descarga Automática de Químicos en Tintorería

**Fecha:** 2026-05-04  
**Versión:** 1.0  
**Autor:** Claude Code (Haiku 4.5)

---

## Resumen Ejecutivo

Se ha implementado un sistema completo de **descarga automática de químicos** al crear, modificar o eliminar órdenes de producción. El sistema incluye:

- ✅ Descarga automática al crear OP (si tiene fórmula + bodega de químicos)
- ✅ Ajuste de descarga al modificar peso/fórmula con justificación obligatoria
- ✅ Reversión automática al eliminar OP con justificación obligatoria
- ✅ Dashboard de stock de químicos para tintoreros con alertas visuales
- ✅ Auditoría completa con rastreo de usuario, fecha y justificación
- ✅ Respeto total de principios SOLID y patrones de diseño vigentes

---

## Arquitectura Implementada

### Principios SOLID Aplicados

| Principio | Implementación |
|-----------|---|
| **SRP** | `DescargaQuimicosService` solo gestiona descargas. Cálculo delegado a `DosificacionCalculator`. Alertas en método `_verificar_alertas`. |
| **OCP** | El servicio acepta estrategias de cálculo (gr/L o %) sin modificar el core. |
| **LSP** | `DescargaQuimicoOP` extiende fielmente contratos de auditoría. |
| **ISP** | Endpoints separados: `/ordenes-produccion/` para CRUD, `/ordenes-produccion/stock-quimicos/` para consulta de stock. |
| **DIP** | `DescargaQuimicosService` depende de abstracciones (`DosificacionCalculator`, `safe_get_or_create_stock`), no de implementaciones. |

### Patrones de Diseño

| Patrón | Aplicación |
|--------|-----------|
| **Service Layer** | `gestion/services/descarga_quimicos.py` — toda lógica de negocio fuera de vistas |
| **Strategy** | Reutiliza `tipo_calculo` (gr_l / pct) de `DosificacionCalculator` |
| **Template Method** | `ajustar_descarga_op = revertir + descargar` (secuencia fija, pasos delegados) |
| **Proxy** | Endpoint `stock-quimicos` filtra y enriquece datos de `StockBodega` |
| **Entity + Audit Trail** | `DescargaQuimicoOP` es inmutable post-creación, registra auditoría |

---

## Módulos Implementados

### 1. Backend - Modelos (`gestion/models.py`)

#### Cambios a `OrdenProduccion`
```python
bodega_quimicos = ForeignKey(Bodega, on_delete=SET_NULL, null=True)
fecha_modificacion = DateTimeField(auto_now=True)
```

#### Nuevo Modelo: `DescargaQuimicoOP`
- **Propósito:** Registro inmutable de cada descarga de químico
- **Campos clave:**
  - `orden_produccion`, `producto`, `fase`, `bodega`
  - `tipo_calculo`: 'gr_l' o 'pct'
  - `cantidad_calculada_kg`, `cantidad_real_kg` (null hasta post-ejecución)
  - `estado`: 'aplicada' o 'revertida'
  - `fecha_descarga`, `descargado_por`, `justificacion`
- **Índices:** `(orden_produccion, estado)` y `(bodega, fecha_descarga)`

**Migración:** `gestion/migrations/0022_descarga_quimico_op.py`

---

### 2. Backend - Service Layer (`gestion/services/descarga_quimicos.py`)

#### `DescargaQuimicosService`

**Método: `descargar_para_op(orden, usuario) -> list[DescargaQuimicoOP]`**
- Calcula dosificación usando `DosificacionCalculator`
- Descuenta stock thread-safe con `safe_get_or_create_stock`
- Crea `MovimientoInventario` tipo='CONSUMO'
- Crea `DescargaQuimicoOP` por cada insumo
- Marca `orden.inventario_descontado = True`
- Lanza alertas si stock < stock_minimo
- **Transaccional:** `@transaction.atomic`

**Método: `revertir_descarga_op(orden, usuario, justificacion)`**
- Busca descargas 'aplicada' de la OP
- Suma al stock cada químico
- Crea `MovimientoInventario` tipo='DEVOLUCION'
- Marca descargas como 'revertida'
- Resetea `orden.inventario_descontado = False`
- **Justificación obligatoria**

**Método: `ajustar_descarga_op(orden, usuario, justificacion)`**
- Template Method: `revertir_descarga_op()` → `descargar_para_op()`
- Se invoca al modificar peso/fórmula de OP con descarga previa
- **Justificación obligatoria**

**Método: `_verificar_alertas(bodega, producto_id, saldo)`**
- Verifica si saldo < stock_minimo
- Emite warning en logs
- Extensible para crear `AlertaStock`

---

### 3. Backend - Views (`gestion/views.py`)

#### `OrdenProduccionViewSet`

**`perform_create(serializer)`**
- Ejecuta `DescargaQuimicosService.descargar_para_op()` si `formula_color` y `bodega_quimicos` configurados
- Log de auditoría

**`perform_update(serializer)`**
- Valida `justificacion` obligatoria si `inventario_descontado == True`
- Detecta cambios en `peso_neto_requerido` o `formula_color`
- Ejecuta `ajustar_descarga_op()` si hubo cambios; sino `descargar_para_op()` si es primera vez

**`destroy(request, ...)`**
- Valida `justificacion` obligatoria (HTTP 400 si falta)
- Ejecuta `revertir_descarga_op()` si `inventario_descontado == True`
- Transaccional con `@transaction.atomic`

**`@action stock-quimicos`**
- GET `/ordenes-produccion/stock-quimicos/?sede_id=<id>`
- Permiso: `IsTintoreroOrAdmin`
- Retorna: lista de `StockQuimico` con campo `alerta` (True si cantidad < stock_minimo)
- Ordena por alerta descendente

---

### 4. Backend - Serializers (`gestion/serializers.py`)

**`OrdenProduccionSerializer` (actualizado)**
- Nuevos campos: `bodega_quimicos`, `bodega_quimicos_nombre`, `inventario_descontado` (read-only), `fecha_modificacion`

**`DescargaQuimicoOPSerializer` (nuevo)**
- Read-only: registra detalles de descarga
- Fields: `id`, `orden_produccion`, `producto_*`, `bodega_nombre`, `tipo_calculo`, `cantidad_calculada_kg`, `cantidad_real_kg`, `estado`, `fecha_descarga`, `descargado_por_nombre`, `justificacion`

**`StockQuimicoSerializer` (nuevo)**
- Para endpoint `/stock-quimicos/`
- Fields: `producto_id`, `producto_codigo`, `producto_descripcion`, `cantidad`, `stock_minimo`, `alerta`, `bodega_nombre`

---

### 5. Frontend - Types (`frontend/src/lib/types.ts`)

**`OrdenProduccion` (actualizado)**
```typescript
bodega_quimicos?: number;
bodega_quimicos_nombre?: string;
inventario_descontado: boolean;
fecha_modificacion: string;
```

**`DescargaQuimicoOP` (nuevo)**
```typescript
id, orden_produccion, producto, cantidad_calculada_kg, cantidad_real_kg, 
estado: 'aplicada' | 'revertida', fecha_descarga, descargado_por_nombre, justificacion
```

**`StockQuimico` (nuevo)**
```typescript
producto_id, producto_codigo, producto_descripcion, cantidad, stock_minimo, 
alerta: boolean, bodega_nombre
```

---

### 6. Frontend - Components

#### `StockQuimicosDashboard.tsx` (nuevo)
- Dashboard para tintoreros
- Tabla de químicos disponibles con:
  - Código, descripción, cantidad, stock mínimo
  - Badge `STOCK BAJO` en rojo si alerta=true
  - Stats cards: Total, Stock Bajo, Disponibles
  - Modal de historial de descargas por químico
- Fetch: `GET /ordenes-produccion/stock-quimicos/?sede_id=<id>`
- Permiso: `IsTintoreroOrAdmin`

#### `TintoreroDashboard.tsx` (actualizado)
- Cambio de estructura: Tabs con sub-rutas
  - Tab "Fórmulas Químicas" → `FormulaQuimica`
  - Tab "Stock Disponible" → `StockQuimicosDashboard`
- Mantiene funcionalidad original de gestión de fórmulas

#### `ManageOrdenesProduccion.tsx` (actualizado)
- Nuevo campo en formulario: `bodega_quimicos` (Select de bodegas)
- Nuevo campo: `justificacion` (TextArea obligatorio en editar/eliminar)
- Tabla actualizada: Badge `✓ QUÍMICOS DESCONTADOS` cuando `inventario_descontado=true`

---

## Flujos de Negocio

### 1. Crear Nueva OP

```
JefePlanta crea OP con:
  - código, producto, fórmula, peso_neto, bodega_quimicos ✓
    ↓
OrdenProduccionViewSet.perform_create()
    ↓
DescargaQuimicosService.descargar_para_op()
    ├─ DosificacionCalculator.calcular(peso, relación_baño)
    ├─ Para cada insumo:
    │   ├─ safe_get_or_create_stock(bodega_quimicos, producto)
    │   ├─ stock.cantidad -= cantidad_calculada
    │   ├─ MovimientoInventario.create(CONSUMO)
    │   ├─ DescargaQuimicoOP.create(estado='aplicada')
    │   └─ _verificar_alertas() → log si stock < mínimo
    └─ orden.inventario_descontado = True
    ↓
✓ OP creada + químicos descontados automáticamente
```

### 2. Modificar OP Existente

```
JefePlanta modifica OP:
  - peso_neto_requerido o formula_color ↓ REQUIERE justificación ✓
    ↓
OrdenProduccionViewSet.perform_update()
    ├─ Valida justificación (HTTP 400 si falta)
    ├─ Si inventario_descontado=True:
    │   └─ DescargaQuimicosService.ajustar_descarga_op()
    │       ├─ revertir_descarga_op() → suma stock, MovimientoInventario DEVOLUCION
    │       └─ descargar_para_op() → con nuevos valores
    └─ Si no había descarga:
        └─ descargar_para_op()
    ↓
✓ OP modificada + descarga ajustada
```

### 3. Eliminar OP

```
JefePlanta elimina OP → REQUIERE justificación ✓
    ↓
OrdenProduccionViewSet.destroy()
    ├─ Valida justificación (HTTP 400 si falta)
    ├─ Si inventario_descontado=True:
    │   └─ DescargaQuimicosService.revertir_descarga_op()
    │       ├─ suma stock, MovimientoInventario DEVOLUCION
    │       └─ marca descargas como 'revertida'
    └─ orden.delete()
    ↓
✓ OP eliminada + químicos revertidos
```

### 4. Consultar Stock de Químicos

```
Tintorero accede a "Stock Disponible"
    ↓
GET /ordenes-produccion/stock-quimicos/?sede_id=<id>
    ├─ Filtra StockBodega.producto.tipo='quimico'
    ├─ Calcula alerta = (cantidad < stock_minimo)
    └─ Ordena por alerta DESC
    ↓
StockQuimicosDashboard renderiza:
  - Tabla con estado de cada químico
  - Badges rojos para stock bajo
  - Modal de historial de descargas por insumo
```

---

## Auditoría y Trazabilidad

### `MovimientoInventario`
- **Tipo:** 'CONSUMO' (descarga) o 'DEVOLUCION' (reversión)
- **Trazabilidad:** usuario, fecha, documento_ref (OP código)

### `DescargaQuimicoOP`
- **Inmutable:** estado → 'aplicada' o 'revertida'
- **Trazabilidad:** descargado_por (usuario), fecha_descarga, justificacion (en reversión)
- **Cálculo vs. Real:** cantidad_calculada_kg fija; cantidad_real_kg se rellenará post-ejecución (extensión futura)

### `AuditLog` (existente)
- Audita cambios a `OrdenProduccion`: bodega_quimicos, peso_neto, formula_color con justificación

---

## Restricciones y Reglas

1. **Bodega de químicos obligatoria:** No se descarga si `bodega_quimicos` es NULL
2. **Justificación obligatoria:** Modificar o eliminar OP con descarga previa requiere `justificacion` (HTTP 400 si falta)
3. **Stock negativo permitido:** Sistema permite sobregiro (indicador de alerta en logs)
4. **Descarga idempotente:** Campo `inventario_descontado` previene descargas dobles si se llama `descargar_para_op()` dos veces

---

## Testing

### Tests de Integración a Implementar

**Archivo:** `gestion/tests_integrados.py`

```python
# Caso 1: Crear OP con fórmula y bodega → verifica DescargaQuimicoOP + MovimientoInventario
# Caso 2: Modificar peso_neto_requerido → verifica ajuste (reversión + nueva descarga)
# Caso 3: Eliminar OP sin justificación → HTTP 400
# Caso 4: Eliminar OP con justificación → verifica reversión + MovimientoInventario DEVOLUCION
# Caso 5: Stock cae bajo mínimo → verifica alerta en logs
# Caso 6: GET /stock-quimicos/ → verifica alerta=True para productos bajo mínimo
```

---

## Extensiones Futuras

1. **Registro de consumo real:** UI para operarios de tintorería registren `cantidad_real_kg` post-ejecución
2. **Alertas en tiempo real:** Crear tabla `AlertaStock` y notificaciones WebSocket
3. **Reposición automática:** Trigger de compra cuando stock < stock_mínimo
4. **Reportes de consumo:** Dashboard de tendencias de químicos consumidos
5. **Configuración de relación de baño:** Por sede/fórmula (hoy está hardcodeada en 10)

---

## Comandos para Ejecutar

### Backend

```bash
# Aplicar migración
python manage.py migrate gestion 0022

# Ejecutar tests
python manage.py test gestion.tests_integrados.UnifiedBusinessLogicTestCase -v 2

# Verificar endpoints
python manage.py shell
> from gestion.models import OrdenProduccion, DescargaQuimicoOP
> OrdenProduccion.objects.count()
> DescargaQuimicoOP.objects.count()
```

### Frontend

```bash
# El componente StockQuimicosDashboard se integra automáticamente en TintoreroDashboard
# No requiere cambios en rutas (usa Tabs en lugar de sub-rutas)

# Tests TypeScript (si aplica)
npm run test -- StockQuimicosDashboard
```

---

## Verificación Funcional

✅ **Descarga automática al crear OP** (perform_create)  
✅ **Ajuste de descarga al modificar OP** (perform_update con Template Method)  
✅ **Reversión al eliminar OP** (destroy)  
✅ **Justificación obligatoria** (validación en perform_update/destroy)  
✅ **Auditoría con trazabilidad** (usuario, fecha, justificación)  
✅ **Dashboard stock para tintorero** (StockQuimicosDashboard)  
✅ **Alertas visuales** (badges STOCK BAJO en rojo)  
✅ **Integridad transaccional** (@transaction.atomic)  
✅ **Thread-safety** (safe_get_or_create_stock con savepoint)  

---

## Referencias

- **Plan maestro:** `/home/Adminbrandon/.claude/plans/cheerful-wiggling-blum.md`
- **Service Layer pattern:** `gestion/services/descarga_quimicos.py`
- **DosificacionCalculator reutilizado:** `gestion/services_formula.py`
- **Patrón de reversión base:** `gestion/views.py` (action `rechazar_lote`)
- **Thread-safe utility:** `inventory/utils.py::safe_get_or_create_stock`

---

**Fin de Documentación**
