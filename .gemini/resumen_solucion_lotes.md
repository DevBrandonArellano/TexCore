# Solución: Registrar Lotes Correctamente

## Problema Identificado

El usuario registró:
- ✅ Peso Neto: 500 kg → Correcto
- ❌ Unidades: 1 → Por defecto, no cambió
- ❓ Merma: Vacío, pero aparece como "no se ha registrado merma"

### ¿Por qué pasó?
El formulario no era claro sobre la diferencia entre:
1. **Peso Neto** = kg totales producidos
2. **Unidades** = número de bobinas/conos/cajas (opcional)

---

## Cambios Realizados

### 1. ✅ Mejorado el Formulario de Registro

**Archivo**: `frontend/src/components/operario/OperarioDashboard.tsx`

#### Antes
```
Peso Neto (Kg): [input]
Unidades: [input]
```

#### Ahora
```
Peso Neto (Kg) * : [input placeholder="Ej: 500.00"]
                   (Obligatorio, en rojo)

Unidades (Bobinas/Conos): [input placeholder="Ej: 12 bobinas"]
                          Si no conoces el número, deja en 1
                          (Texto de ayuda más claro)

Desperdicio (Kg): [input placeholder="0.00 (Opcional)"]
```

**Mejoras:**
- ✅ Asterisco rojo en "Peso Neto" para indicar obligatorio
- ✅ Texto "(Bobinas/Conos)" para aclarar qué es Unidades
- ✅ Placeholder de ejemplo ("Ej: 500.00", "Ej: 12 bobinas")
- ✅ Explicación: "Si no conoces el número, deja en 1"

---

### 2. ✅ Mejorada la Tabla de Últimos Ingresos

**Archivo**: `frontend/src/components/operario/OperarioDashboard.tsx`

#### Antes
```
Peso Neto | Unidades | Merma
500.00   | 1        | —
```

#### Ahora
```
Peso Neto    | Unidades | Merma
500.00 (🟢)  | 1 (bold) | ✓ Sin merma (verde)
```

**Mejoras:**
- ✅ Peso Neto en VERDE Y BOLD para destacar producción
- ✅ Unidades en BOLD para que sea visible
- ✅ Merma muestra "✓ Sin merma" en VERDE si no hay
- ✅ Merma muestra cantidad en NARANJA si la hay
- ✅ Más visual y fácil de entender

---

### 3. 📚 Creada Guía Completa

**Archivo**: `.gemini/guia_registrar_lotes.md`

Incluye:
- ✅ Explicación clara de cada campo
- ✅ Ejemplos prácticos por industria (Textil, Hilados, Empaquetado)
- ✅ Tabla de referencia
- ✅ Cómo editar después si cometes error
- ✅ Ejemplos de entrada correcta

---

## Cómo Usar Ahora

### Escenario 1: Sabes las unidades
```
Peso Neto: 500 kg
Unidades: 12 bobinas ← Cambio del valor por defecto
Merma: (vacío) ← "✓ Sin merma"

Resultado en tabla:
500.00 | 12 | ✓ Sin merma ✅
```

### Escenario 2: No sabes las unidades
```
Peso Neto: 500 kg
Unidades: 1 ← Dejar por defecto
Merma: (vacío) ← "✓ Sin merma"

Resultado en tabla:
500.00 | 1 | ✓ Sin merma ✅
Nota: Significa 500 kg en 1 lote global
```

### Escenario 3: Hay desperdicio
```
Peso Neto: 500 kg
Unidades: 12
Merma: 5 kg ← Ingresa la cantidad
Motivo: Rotura (select)

Resultado en tabla:
500.00 | 12 | 5.00 (naranja) ⚠️
```

---

## Sobre "no se ha registrado merma"

✅ **Esto es CORRECTO:**
```
Si no ingresaste merma:
Merma: ✓ Sin merma

Si ingresaste merma:
Merma: 5.00 kg
```

El sistema distingue entre:
- **✓ Sin merma** = Producción perfecta sin desperdicio
- **Número en naranja** = Hubo desperdicio (ej. 5.00 kg)

---

## Editar Después

Si registraste mal, es FÁCIL corregir:

1. Ve a "Últimos Ingresos" (tabla abajo)
2. Busca tu lote
3. Click en ✏️ (Editar)
4. Cambia los valores que quieras
5. Click en ✓ (Guardar)

**Ejemplo:**
```
Registraste: 500 kg | 1 unidad | Sin merma
Quieres: 500 kg | 12 unidades | Sin merma

1. Click lápiz
2. Cambia "1" a "12"
3. Click ✓
4. Listo ✅
```

---

## Testing

### Test 1: Registra con Unidades Correctas
```
1. Click "Registrar Avance"
2. Peso Neto: 500
3. Unidades: 12 (CAMBIO DE 1 A 12)
4. Merma: (vacío)
5. Click "Confirmar Registro"
✅ Debe aparecer: 500.00 | 12 | ✓ Sin merma
```

### Test 2: Registra con Merma
```
1. Click "Registrar Avance"
2. Peso Neto: 500
3. Unidades: 12
4. Merma: 5
5. Motivo: Rotura
6. Click "Confirmar Registro"
✅ Debe aparecer: 500.00 | 12 | 5.00
```

### Test 3: Edita Después
```
1. Ve a tabla "Últimos Ingresos"
2. Click lápiz en la fila
3. Cambia Unidades: 1 → 12
4. Click ✓
✅ Se actualiza a: 500.00 | 12 | ✓ Sin merma
```

---

## Resumen de Cambios

| Elemento | Antes | Ahora |
|----------|-------|-------|
| Peso Neto | Normal | BOLD + Verde |
| Unidades | Normal | BOLD |
| Merma | Línea o número | Verde "✓" o Naranja |
| Ayuda | Ninguna | "Si no sabes, deja en 1" |
| Placeholders | Genéricos | Ejemplos específicos |
| Edición | Posible | Más obvio con ✏️ |

---

## Notas Importantes

1. **Peso Neto es obligatorio** - Sin esto no se puede registrar
2. **Unidades es opcional** - Puedes dejar en 1 si no la sabes
3. **Merma es opcional** - Solo si hay desperdicio
4. **Puedes editar después** - No es la última palabra
5. **El Jefe de Área puede revisar** - Si algo no está bien

---

## Para el Usuario

Si vuelves a registrar 500 kg:

### Opción A (si sabes unidades):
```
Peso: 500 kg
Unidades: 12 (bobinas, conos, etc.)
Merma: (vacío si no hay)
```

### Opción B (si NO sabes unidades):
```
Peso: 500 kg
Unidades: 1 (dejar por defecto)
Merma: (vacío si no hay)
```

Ambas son correctas. La diferencia es si especificas cuántas bobinas/conos/etc. produciste.
