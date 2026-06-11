# Guía: Cómo Registrar Lotes Correctamente

## El Problema

El usuario registró:
- **Peso Neto: 500 kg** ✅ Correcto
- **Unidades: 1** ❌ Por defecto (no cambió)

Y esperaba:
- **Peso Neto: 500 kg**
- **Unidades: 500**

## Entendiendo los Campos

### 🎯 Peso Neto (Kg) - OBLIGATORIO
```
Este es el peso TOTAL producido en el lote
Ejemplo: 500 kg
```

**Casos de uso:**
- ✅ Producción de textil: 500 kg de tela
- ✅ Producción de hilados: 250 kg de hilo
- ✅ Empaquetado: 100 kg de producto empaquetado

---

### 📦 Unidades (Bobinas/Conos) - OPCIONAL
```
El NÚMERO DE UNIDADES (bobinas, conos, cajas, etc.)
```

**Casos de uso:**

#### Caso 1: Textil (Tejeduría)
```
Producción: 500 kg de tela en 12 bobinas
└─ Peso Neto: 500 kg
└─ Unidades: 12 bobinas
```

#### Caso 2: Hilados (Tintorería)
```
Producción: 250 kg de hilo en 50 conos
└─ Peso Neto: 250 kg
└─ Unidades: 50 conos
```

#### Caso 3: Empaquetado
```
Producción: 100 kg empaquetado en 20 cajas
└─ Peso Neto: 100 kg
└─ Unidades: 20 cajas
```

#### Caso 4: No sabes el número de unidades
```
Producción: 500 kg de tela, sin contar bobinas
└─ Peso Neto: 500 kg
└─ Unidades: 1 (por defecto)
└─ Nota: Puedes editar después si lo sabes
```

---

## Merma / Desperdicio (Kg) - OPCIONAL

```
Pérdida o desperdicio durante el proceso
Ejemplo: 5 kg de merma
```

**Cuando registrar merma:**
- ✅ Rotura de tela
- ✅ Hilo defectuoso descartado
- ✅ Muestras/pruebas
- ✅ Pérdida en máquina

**Si hay merma, debes especificar el motivo:**
- 🔧 Falla Técnica / Máquina
- 🧪 Calidad de Hilo / Material
- ⚙️ Arranque / Setup
- ✂️ Corte / Empalme
- 📝 Otro

---

## Ejemplo Práctico: Correcto vs Incorrecto

### ❌ INCORRECTO (Lo que hiciste)
```
Peso Neto: 500 kg
Unidades: 1
Merma: (vacío)

Result en tabla: 500 kg | 1 unidad | Sin merma ❌
Problema: Parece que produciste 500 kg en 1 unidad
```

### ✅ CORRECTO
```
OPCIÓN A - Si sabes las unidades:
Peso Neto: 500 kg
Unidades: 12 (bobinas de tela)
Merma: (vacío)

Result: 500 kg | 12 unidades | Sin merma ✅

---

OPCIÓN B - Si NO sabes las unidades:
Peso Neto: 500 kg
Unidades: 1 (dejar por defecto)
Merma: (vacío)

Result: 500 kg | 1 unidad | Sin merma ✅
Nota: Significa 500 kg en 1 lote global
```

---

## Pasos para Registrar Correctamente

### Paso 1: Abre "Registrar Avance"
```
Ves el formulario con tres campos
```

### Paso 2: Llena "Peso Neto (Kg)"
```
Ingresa el peso TOTAL producido
Ejemplo: 500
```

### Paso 3: Llena "Unidades" (SI LO SABES)
```
Si la producción vino en 12 bobinas, ingresa: 12
Si NO sabes el número de unidades, deja en: 1
```

### Paso 4: Llena "Desperdicio" (SI HAY)
```
Si hubo 5 kg de merma, ingresa: 5
Si NO hay merma, deja vacío
```

### Paso 5: Si hay desperdicio, elige el motivo
```
Selecciona por qué ocurrió la merma
```

### Paso 6: Click en "Confirmar Registro"
```
✅ Lote registrado correctamente
```

---

## Editar Después (Si Cometiste un Error)

Si registraste mal, no hay problema:

1. Ve a "Últimos Ingresos" (abajo)
2. Busca tu lote
3. Click en el ✏️ (Editar)
4. Cambia los valores
5. Click en ✓ (Guardar)

**Ejemplo:**
```
Registraste: 500 kg | 1 unidad
Quieres: 500 kg | 12 unidades

1. Click en lápiz en la fila
2. Cambia Unidades de 1 a 12
3. Click en ✓
4. Listo ✅
```

---

## Tabla de Referencia: Cuándo Ingresar Qué

| Situación | Peso Neto | Unidades | Merma |
|-----------|-----------|----------|-------|
| Tela sin contar bobinas | 500 kg | 1 | Si hay |
| Tela con 12 bobinas | 500 kg | 12 | Si hay |
| Hilo en 50 conos | 250 kg | 50 | Si hay |
| Empaque en 20 cajas | 100 kg | 20 | Si hay |
| No sabes nada | 500 kg | 1 | Si hay |

---

## ¿Qué Aparece en la Tabla?

Después de registrar, verás en "Últimos Ingresos":

```
Lote | Orden | Peso Neto | Unidades | Merma | Fecha
L001 | OP-1  | 500.00 kg | 12       | ✓ Sin | 2026-06-11
```

**Significado:**
- **Peso Neto 500.00**: Produjiste 500 kg
- **Unidades 12**: En 12 unidades (bobinas, conos, etc.)
- **✓ Sin merma**: No hubo desperdicio
- **2026-06-11**: Fecha del registro

---

## Si Aparece "no se ha registrado merma"

Eso es CORRECTO si NO ingresaste merma:

```
Merma: ✓ Sin merma ← Significa "sin desperdicio" ✅
Merma: 5.00 kg ← Significa "5 kg de desperdicio" ⚠️
```

---

## Resumen

✅ **Siempre:**
- Ingresa el **Peso Neto** (obligatorio)

✅ **Si lo sabes:**
- Ingresa el **número de Unidades**

✅ **Si hubo desperdicio:**
- Ingresa la cantidad en **Desperdicio**
- Selecciona el **Motivo**

✅ **Si cometes error:**
- Usa el botón ✏️ para editar después

---

## Ejemplos de Entrada Correcta

### Ejemplo 1: Tintorería
```
Peso Neto: 250 kg
Unidades: 30 conos
Desperdicio: 5 kg
Motivo: Rotura de cono
```

### Ejemplo 2: Tejeduría
```
Peso Neto: 500 kg
Unidades: 10 rollos
Desperdicio: (vacío)
Motivo: (no aplica)
```

### Ejemplo 3: Sin información de unidades
```
Peso Neto: 150 kg
Unidades: 1
Desperdicio: (vacío)
Motivo: (no aplica)
```

---

## ¿Preguntas?

Si algo no es claro:
1. Edita el lote después (botón ✏️)
2. El Jefe de Área puede revisar y corregir
3. No te preocupes, los datos se pueden cambiar
