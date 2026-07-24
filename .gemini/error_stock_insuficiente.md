# Error: Stock Insuficiente

## El Error

```
ValidationError: Stock insuficiente en Bodega de Materia Prima.
Disponible: 300 kg
Requerido: 500 kg
```

---

## ¿Por Qué Ocurre?

Estás intentando registrar un lote de **500 kg**, pero en la bodega de entrada solo hay **300 kg** disponibles.

### Ejemplo
```
Bodega de Materia Prima (Entrada):
├─ Stock actual: 300 kg
└─ Intentas registrar: 500 kg ❌

Resultado: ERROR - No hay suficiente inventario
```

---

## Soluciones

### Solución 1: Registra Solo lo Disponible (300 kg)

**Paso 1**: No intentes registrar 500 kg
```
Peso Neto: 300 kg ✅ (Disponible)
Unidades: (lo que corresponda)
```

**Paso 2**: Después de agotar stock, carga más materia prima
```
1. Jefe de Área compra 200 kg más
2. Se agrega a Bodega de Materia Prima
3. Ahora tienes 200 kg disponibles nuevamente
4. Registra el siguiente lote
```

### Solución 2: Verifica la Bodega de Entrada

**Pregunta**: ¿La orden tiene bodega de entrada asignada?

```
Si NO tiene:
❌ Jefe de Planta no asignó bodega
✅ Jefe de Área debe completar detalles via completar_detalles

Si SÍ tiene:
✅ Bodega asignada correctamente
⚠️ Pero stock insuficiente en esa bodega
```

### Solución 3: Chequea el Inventario Real

**Verificar stock disponible**:
1. Ve a "Inventario" (si tienes acceso)
2. Busca la bodega: "Bodega de Materia Prima"
3. Verifica disponibilidad real
4. Si es bajo, solicita reabastecimiento

---

## Flujo Correcto

```
┌─ JEFE DE PLANTA
│  └─ Crea orden (código, peso, área)
│
├─ JEFE DE ÁREA  
│  ├─ Completa detalles (bodega_entrada, producto)
│  ├─ Verifica que bodega tenga stock suficiente
│  └─ Autoriza a operario a producir
│
└─ OPERARIO
   └─ Registra lote
      ├─ Si hay stock: ✅ Registra correctamente
      └─ Si NO hay: ❌ Error "Stock insuficiente"
```

---

## Cómo Resolver en Tu Caso

### Paso 1: Verifica el Stock
```
Bodega de Materia Prima: 300 kg disponibles
Necesitas: 500 kg
Diferencia: -200 kg (falta)
```

### Paso 2: Opción A - Registra Solo 300 kg
```
1. Registra: Peso Neto = 300 kg
2. Resto (200 kg) lo registras después
3. O solicita compra de 200 kg más
```

### Paso 3: Opción B - Compra/Traslada Stock
```
1. Jefe de Área compra 200 kg más
2. Se agrega al inventario
3. Ahora registras 500 kg normalmente
```

---

## Mensaje de Error Mejorado

Ahora el error debería aparecer más claro:

```
❌ "Stock insuficiente en Bodega de Materia Prima. 
   Disponible: 300 kg
   Requerido: 500 kg"
```

Este es un error **HTTP 400 (Bad Request)** normal, no un 500 (Internal Server Error).

---

## Prevención para el Futuro

### Checklist Antes de Registrar

- [ ] ¿Tiene la orden bodega_entrada asignada?
- [ ] ¿El stock en esa bodega es >= al peso que vas a registrar?
- [ ] ¿Hay merma previsible? (sumar al peso total)

**Ejemplo:**
```
Quiero registrar: 500 kg
Merma estimada: 5 kg
Stock necesario real: 505 kg

Bodega disponible: 300 kg ❌ Insuficiente
```

---

## Resumen

| Problema | Causa | Solución |
|----------|-------|----------|
| Error 500 | Stock insuficiente | Registra menos o compra más |
| 300 kg disponibles | Bodega vacía | Solicita reabastecimiento |
| No puedo registrar 500 | Falta 200 kg | Registra en dos veces |

---

## Archivos Modificados

**gestion/views/production_views.py**:
- ✅ Mejorado manejo de errores de ValidationError
- ✅ Ahora retorna HTTP 400 en lugar de 500
- ✅ Mensaje de error más claro

---

## Notas Técnicas

El servicio `RegistroLoteService` valida que exista suficiente stock en la bodega antes de registrar el lote. Esto es correcto y necesario para mantener la integridad del inventario.

Si intentas registrar un peso mayor al disponible:
1. El servicio lanza `ValidationError`
2. Ahora se retorna como HTTP 400 (Bad Request)
3. Mensaje claro: "Stock insuficiente"
4. El lote NO se registra

Esto es un comportamiento esperado y correcto.
