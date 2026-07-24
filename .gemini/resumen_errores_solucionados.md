# Resumen de Errores Solucionados

## Error 500 - Registrar Lote Fallaba

### 🔴 Problema Original
```
POST /ordenes-produccion/10004/registrar-lote/ → 500 Error
```

**Causa**: El servicio `RegistroLoteService` esperaba que la orden tuviera:
- `producto_entrada` asignado
- `bodega_entrada` asignado
- `bodega_salida` asignado

Pero como el **Jefe de Planta** solo crea órdenes básicas (código, peso, área), estos campos estaban **NULL**, causando un error al intentar acceder a propiedades como `.codigo`.

### ✅ Solución Aplicada

**Archivo**: `gestion/services/registro_lote.py`

#### Cambio 1: Validación Relajada (línea 48-55)
```python
# ANTES
if not getattr(orden, 'producto_entrada_id', None) and not getattr(orden, 'producto_id', None):
    raise ValidationError('La OP debe tener producto_entrada.')

# AHORA
producto_entrada_existe = getattr(orden, 'producto_entrada_id', None) or getattr(orden, 'producto_id', None)
if not producto_entrada_existe:
    logger.warning(f'OP {orden.codigo} sin producto_entrada. El Jefe de Área debe completar los detalles.')
```

**Resultado**: Permite registrar lotes aunque falta `producto_entrada`. Solo registra un warning.

---

#### Cambio 2: Consumo Condicional (línea 73)
```python
# ANTES
if not tiene_mezcla and bodega_entrada:

# AHORA
if not tiene_mezcla and bodega_entrada and producto_entrada:
    # Operaciones de consumo...
elif not bodega_entrada or not producto_entrada:
    logger.warning(f'OP {orden.codigo} sin bodega_entrada o producto_entrada...')
```

**Resultado**: Solo consume del stock si existen AMBOS bodega_entrada Y producto_entrada. Si falta uno, solo registra un warning.

---

#### Cambio 3: Entrada de Producto Condicional (línea 151)
```python
# ANTES
if bodega_salida:
    # Crear movimiento...

# AHORA
if bodega_salida and producto_salida:
    # Crear movimiento...
else:
    logger.warning(f'OP {orden.codigo} sin bodega_salida o producto_salida...')
```

**Resultado**: Solo registra entrada a stock si existen AMBOS bodega_salida Y producto_salida.

---

#### Cambio 4: Logging Seguro (línea 185-196)
```python
# ANTES
logger.info(extra={'sd': {
    'producto_entrada': producto_entrada.codigo,  # ← Error si es None
    'producto_salida': producto_salida.codigo,    # ← Error si es None
}})

# AHORA
logger.info(extra={'sd': {
    'producto_entrada': producto_entrada.codigo if producto_entrada else 'Sin asignar',
    'producto_salida': producto_salida.codigo if producto_salida else 'Sin asignar',
}})
```

**Resultado**: El logging no causa error si producto es None.

---

## Flujo Actualizado

```
┌─ JEFE DE PLANTA
│  └─ Crea Orden BÁSICA
│     ├─ Código: OP-TINT-001
│     ├─ Peso: 500 kg
│     └─ Área: Tintura
│        (SIN producto/bodega)
│
├─ JEFE DE ÁREA
│  └─ Completa Detalles vía completar_detalles
│     ├─ Producto Entrada
│     ├─ Bodega Entrada
│     ├─ Producto Salida
│     └─ Bodega Salida
│
└─ OPERARIO
   └─ Registra Lote
      ├─ Si orden TIENE detalles → Registra movimientos de inventario
      └─ Si orden SIN detalles → Solo registra lote (sin movimientos)
```

---

## Testing

### Test 1: Operario Registra Lote (Sin Completar Detalles)
```
1. Jefe de Planta crea: OP-TEST-001 (código, peso, área)
2. Operario intenta registrar lote
   ✅ Debe FUNCIONAR (error 500 solucionado)
   ✅ Registra el lote
   ⚠️  No actualiza stock (porque falta bodega/producto)
3. Jefe de Área completa detalles
4. Siguiente lote SÍ actualiza stock
```

### Test 2: Operario Registra Lote (Con Detalles Completados)
```
1. Jefe de Planta crea: OP-TEST-002 (código, peso, área)
2. Jefe de Área completa detalles (bodega, producto)
3. Operario registra lote
   ✅ Registra el lote
   ✅ Actualiza stock correctamente
```

---

## Cambios en Otros Archivos

### ✅ production_views.py (línea 121)
Actualizado permiso para crear órdenes:
```python
# ANTES
return [IsAuthenticated(), IsAdminSistemasOrSede()]

# AHORA
return [IsAuthenticated(), IsJefeAreaOrAdmin()]
# Permite: jefe_planta, jefe_area, admin_sistemas
```

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `gestion/services/registro_lote.py` | Validación relajada, consumo condicional, logging seguro |
| `gestion/views/production_views.py` | Permisos actualizados |
| `frontend/src/components/jefe-planta/ManageOrdenesProduccion.tsx` | Campos ocultados en creación |
| `frontend/src/components/jefe-area/JefeAreaDashboard.tsx` | Visualización mejorada |

---

## Notas Importantes

1. **Lotes sin Inventario**: Si un operario registra un lote antes de que el Jefe de Área complete detalles, el lote se crea pero sin movimientos de inventario. Esto es INTENCIONAL para permitir el nuevo flujo.

2. **Completar Detalles**: El Jefe de Área debe usar el endpoint:
   ```bash
   PATCH /api/ordenes-produccion/{id}/completar_detalles/
   ```
   Con los datos: producto_entrada, bodega_entrada, producto_salida, bodega_salida

3. **Workflow Recomendado**:
   - Jefe Planta: Crear orden
   - Jefe Área: Completar detalles
   - Operario: Registrar lotes (ahora funcionará)

---

## Verificación

✅ Error 500 solucionado
✅ Operario puede registrar lotes
✅ Logging no falla con productos NULL
✅ Flujo separado de responsabilidades funciona
✅ Stock se actualiza cuando hay detalles
✅ Stock NO se actualiza si faltan detalles (por ahora)
