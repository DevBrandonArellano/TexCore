# Flujo de Producción Multi-Etapas y Multi-Área

## Overview

El sistema ahora soporta procesos de manufactura en cascada donde:
- Cada **Área** tiene múltiples **Etapas** de producción
- Cada **Etapa** usa una máquina específica
- Hay **Bodegas Intermedias** entre etapas dentro del mismo área
- Las áreas se conectan mediante **Transferencias Interárea**
- Cada área tiene su propia **Orden de Producción**

---

## Conceptos Clave

### 1. Etapa de Producción (EtapaProduccion)

Define un paso de procesamiento dentro de un área.

```
EtapaProduccion {
  - área: "Tintura"
  - nombre: "Teñido"
  - orden: 1
  - máquina: "Tinturadora #1"
  - bodega_entrada: "Bodega MP Tintura"
  - bodega_salida: "Bodega Secado"
  - tiempo_estimado: 120 minutos
}
```

### 2. Transferencia Interárea (TransferenciaInterarea)

Registra cuándo se transfiere producto entre áreas.

```
TransferenciaInterarea {
  - orden_origen: OP-Tintura-001
  - orden_destino: OP-Empaque-001
  - bodega_origen: "Bodega Final Tintura"
  - bodega_destino: "Bodega MP Empaque"
  - cantidad: 95.50 kg
  - fecha: 2026-06-11 15:30
}
```

---

## Arquitectura de Flujo

### Flujo Completo de Manufactura

```
JEFE PLANTA crea orden básica
            ↓
JEFE ÁREA TINTURA completa detalles
            ├─ Configura etapas (si no existen)
            ├─ Asigna máquinas y bodegas
            └─ Inicia producción
            ↓
OPERARIO ejecuta lotes
            ↓
JEFE ÁREA TINTURA transferencia producto
            ↓
JEFE ÁREA EMPAQUE crea nueva orden para su área
            ├─ Bodega entrada = Bodega final Tintura
            └─ Producto entrada = Producto salida Tintura
            ↓
OPERARIO EMPAQUE ejecuta empaques
            ↓
JEFE ÁREA EMPAQUE transferencia a Bodega Final
```

### Ejemplo: Producción de Textil

```
┌─────────────────────────────────────┐
│ ÁREA: TINTURA                       │
│ Orden: OP-TINT-2026-001             │
│ Peso requerido: 500 kg              │
├─────────────────────────────────────┤
│ Etapa 1: Teñido                     │
│   Máquina: Tinturadora #1           │
│   Entrada: Bodega MP → Tintura      │
│   Salida: Bodega MP → Secado        │
│   Duración: 120 min                 │
├─────────────────────────────────────┤
│ Etapa 2: Secado                     │
│   Máquina: Secadora Industrial      │
│   Entrada: Bodega Secado            │
│   Salida: Bodega Final Tintura      │
│   Duración: 60 min                  │
└─────────────────────────────────────┘
            ↓ Transferencia
         480 kg OK
            ↓
┌─────────────────────────────────────┐
│ ÁREA: EMPAQUE                       │
│ Orden: OP-EMP-2026-001              │
│ Peso requerido: 480 kg              │
├─────────────────────────────────────┤
│ Etapa 1: Empaque Automático         │
│   Máquina: Empaquetadora            │
│   Entrada: Bodega Final Tintura     │
│   Salida: Bodega Final Empaque      │
│   Duración: 45 min                  │
└─────────────────────────────────────┘
```

---

## Configuración de Etapas por Área

### Para cada Área, Jefe define:

**POST** `/api/etapas-produccion/`

```json
{
  "area": 2,                          // ID Tintura
  "nombre": "Teñido",
  "orden": 1,                         // Primera etapa
  "maquina": 5,                       // Tinturadora #1
  "bodega_entrada": 10,               // Bodega MP Tintura
  "bodega_salida": 11,                // Bodega Secado
  "tiempo_procesamiento_minutos": 120
}
```

### Ejemplo Completo - Área Tintura

```
Etapa 1:
  Nombre: "Teñido"
  Orden: 1
  Máquina: Tinturadora #1
  Entrada: Bodega MP Tintura
  Salida: Bodega Secado
  Tiempo: 120 min

Etapa 2:
  Nombre: "Secado"
  Orden: 2
  Máquina: Secadora Industrial
  Entrada: Bodega Secado
  Salida: Bodega Final Tintura
  Tiempo: 60 min
```

---

## Flujo de Transferencia Interárea

### 1. Área A Termina Producción

```
OP-Área-A:
  - Lote 1: 250 kg ✓ Completado
  - Lote 2: 230 kg ✓ Completado
  - Total: 480 kg en Bodega Final Área A
```

### 2. Jefe Área A Transfiere a Área B

**POST** `/api/transferencias-interarea/`

```json
{
  "orden_area_origen": 5,             // OP de Área A (Tintura)
  "orden_area_destino": 6,            // OP de Área B (Empaque)
  "bodega_origen": 11,                // Bodega Final Tintura
  "bodega_destino": 12,               // Bodega MP Empaque
  "cantidad_transferida": 480.00,
  "observaciones": "Teñido completado, sin defectos"
}
```

### 3. Área B Recibe Producto

```
OP-Área-B:
  - Bodega entrada: Bodega MP Empaque
  - Producto entrada: mismo que salida de Área A
  - Comienza procesamiento
```

---

## Relación entre Órdenes

```
Orden Tintura (OP-TINT-001)
  ├─ Estado: en_proceso
  ├─ Etapas: 2
  ├─ Bodega Final: Bodega Final Tintura
  └─ transferencias_salida →
                            ↓
          TransferenciaInterarea
          480 kg de producto
                            ↓
                    Orden Empaque (OP-EMP-001)
                    ├─ Estado: pendiente → en_proceso
                    ├─ Bodega Entrada: Bodega Final Tintura
                    ├─ Producto Entrada: Producto Tintura
                    └─ transferencias_entrada
```

---

## APIs Disponibles

### Gestión de Etapas

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/etapas-produccion/` | Listar todas las etapas |
| POST | `/api/etapas-produccion/` | Crear etapa |
| GET | `/api/etapas-produccion/{id}/` | Ver detalle |
| PATCH | `/api/etapas-produccion/{id}/` | Actualizar etapa |

### Gestión de Transferencias

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/transferencias-interarea/` | Listar transferencias |
| POST | `/api/transferencias-interarea/` | Registrar transferencia |
| GET | `/api/transferencias-interarea/{id}/` | Ver detalle |

---

## Flujo Completo del Usuario

### 1. Configuración Inicial (Una sola vez por Área)

Jefe de Área configura las etapas de su área:
```bash
# Crear Etapa 1: Teñido
POST /api/etapas-produccion/
{
  "area": 2,
  "nombre": "Teñido",
  "orden": 1,
  "maquina": 5,
  "bodega_entrada": 10,
  "bodega_salida": 11,
  "tiempo_procesamiento_minutos": 120
}

# Crear Etapa 2: Secado
POST /api/etapas-produccion/
{
  "area": 2,
  "nombre": "Secado",
  "orden": 2,
  "maquina": 6,
  "bodega_entrada": 11,
  "bodega_salida": 12,
  "tiempo_procesamiento_minutos": 60
}
```

### 2. Jefe de Planta Crea Orden

```bash
POST /api/ordenes-produccion/
{
  "codigo": "OP-TINT-2026-001",
  "area": 2,                    # Tintura
  "peso_neto_requerido": 500,
  "prioridad": "alta"
}
```

### 3. Jefe de Área Completa Detalles

```bash
PATCH /api/ordenes-produccion/123/completar_detalles/
{
  "producto_entrada": 8,
  "producto_salida": 8,
  "bodega_entrada": 10,         # Bodega MP Tintura
  "bodega_salida": 12,          # Bodega Final Tintura
  "maquina_asignada": 5,        # Tinturadora (para 1ra etapa)
  "operario_asignado": 45
}
```

### 4. Operario Ejecuta Lotes

```bash
POST /api/ordenes-produccion/123/registrar-lote/
{
  "codigo_lote": "OP-TINT-2026-001-L1",
  "peso_neto_producido": 250,
  "hora_inicio": "2026-06-11T08:00:00Z",
  "hora_final": "2026-06-11T10:00:00Z"
}
```

### 5. Jefe de Área Transfiere a Siguiente Área

```bash
POST /api/transferencias-interarea/
{
  "orden_area_origen": 123,     # OP Tintura
  "orden_area_destino": 124,    # OP Empaque (ya debe estar creada)
  "bodega_origen": 12,          # Bodega Final Tintura
  "bodega_destino": 15,         # Bodega MP Empaque
  "cantidad_transferida": 480
}
```

### 6. Siguiente Área Continúa

Jefe de Área Empaque:
- Completa detalles de su orden
- Su bodega_entrada es automáticamente la bodega final del área anterior
- Configura sus propias etapas
- Inicia producción

---

## Validaciones

### Al crear Etapa
- ✅ Área existe
- ✅ Máquina existe y pertenece al área
- ✅ Bodegas existen
- ✅ Orden secuencial es único por área

### Al registrar Transferencia
- ✅ Ambas órdenes existen
- ✅ Bodegas coinciden (final origen = entrada destino)
- ✅ Cantidad ≤ producida en orden origen
- ✅ Producto coincide

---

## Filtros y Búsqueda

```bash
# Por área
GET /api/etapas-produccion/?area=2

# Por máquina
GET /api/etapas-produccion/?maquina=5

# Transferencias de una orden
GET /api/transferencias-interarea/?orden_area_origen=123

# Transferencias recibidas por un área
GET /api/transferencias-interarea/?orden_area_destino=124
```

---

## Notas Importantes

1. **Bodega Final = Bodega Entrada Siguiente**: La bodega_salida del última etapa de un área es la bodega_entrada del área siguiente

2. **Cada Área = Orden Separada**: No es una etapa dentro de una orden, es una orden completamente nueva

3. **Traza Completa**: Se registran todas las transferencias, bodegas y tiempos para auditoría

4. **Producto Fluye**: El producto va cambiando su ubicación de bodega en bodega, etapa a etapa

5. **Operario por Etapa**: Cada etapa puede tener un operario diferente asignado (si se configura)
