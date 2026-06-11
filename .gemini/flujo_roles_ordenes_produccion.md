# Nuevo Flujo de Órdenes de Producción por Roles

## Overview

El flujo de órdenes de producción se ha restructurado para separar responsabilidades:

- **Jefe de Planta**: Crea órdenes básicas (planificación)
- **Jefe de Área**: Completa detalles (ejecución)
- **Operarios**: Ejecutan el trabajo asignado

---

## 1. Jefe de Planta - Crear Orden Básica

### Responsabilidades
- ✅ Crear orden con información mínima
- ✅ Especificar qué área la ejecutará
- ✅ Definir peso/cantidad requerida
- ✅ Opcionalmente establecer prioridad

### Datos Requeridos
```
{
  "codigo": "OP-2026-001",           // Código único de orden
  "area": 1,                          // ID del área responsable
  "peso_neto_requerido": 100.50,     // Peso a producir
  "prioridad": "normal",              // baja|normal|alta|urgente
  "observaciones": "..."              // Opcional
}
```

### Datos Opcionales (No completa)
- `producto_entrada` - NULL (el jefe de área lo selecciona)
- `producto_salida` - NULL
- `bodega_entrada` - NULL
- `bodega_salida` - NULL
- `maquina_asignada` - NULL
- `operario_asignado` - NULL
- `formula_color` - NULL
- `bodega_quimicos` - NULL

### Endpoint
```
POST /api/ordenes-produccion/
```

### Permisos Requeridos
- Jefe de Planta ✅
- Admin Sistemas ✅
- Admin Sede ✅

### Flujo
```
Jefe Planta crea OP
         ↓
    OP creada
   estado: pendiente
         ↓
Jefe Área completa detalles
```

---

## 2. Jefe de Área - Completar Detalles

### Responsabilidades
- ✅ Seleccionar producto entrada (materia prima)
- ✅ Seleccionar producto salida (resultado)
- ✅ Elegir bodega de donde tomar material
- ✅ Elegir bodega destino para producto final
- ✅ Asignar máquinas
- ✅ Asignar operarios (distribución de carga)
- ✅ Definir fórmula química (si aplica)

### Acción: Completar Detalles
```
PATCH /api/ordenes-produccion/{id}/completar_detalles/
```

### Datos a Completar
```json
{
  "producto_entrada": 5,              // ID del producto a procesar
  "producto_salida": 6,               // ID del resultado
  "bodega_entrada": 2,                // Bodega fuente
  "bodega_salida": 3,                 // Bodega destino
  "maquina_asignada": 1,              // ID de máquina
  "operario_asignado": 15,            // ID del operario
  "formula_color": null,              // ID formula (si aplica)
  "bodega_quimicos": null             // Bodega de químicos (si usa fórmula)
}
```

### Permisos Requeridos
- Jefe de Área de la orden ✅
- Admin Sistemas ✅

### Validaciones
- ✅ Usuario es jefe del área asignada
- ✅ Producto entrada existe en bodega origen
- ✅ Operario asignado pertenece al área
- ✅ Máquina asignada existe y está disponible

### Flujo Después de Completar
```
OP con detalles completos
         ↓
Descarga automática de químicos
(si tiene fórmula y bodega_quimicos)
         ↓
Operario puede empezar a trabajar
```

---

## 3. Operario - Ejecutar Orden

### Responsabilidades
- Registrar lotes producidos
- Reportar mermas
- Actualizar estado del lote

### Ver Órdenes Asignadas
```
GET /api/ordenes-produccion/?estado=en_proceso
```

### Registrar Lote
```
POST /api/ordenes-produccion/{id}/registrar-lote/
```

---

## Estados y Transiciones

```
CREADA (Jefe Planta)
  ↓
DETALLES COMPLETOS (Jefe Área)
  ↓
EN PROCESO (Operario inicia trabajo)
  ↓
FINALIZADA (Se completa cantidad o se cancela)
```

---

## Casos de Uso Típicos

### Caso 1: Producción Textil
```
Jefe Planta: OP-2026-001, Teñidurería, 500kg
    ↓
Jefe Área Tintorería:
  - Producto: Hilo Blanco
  - Bodega entrada: Almacén MP
  - Máquina: Tinturadora 3
  - Operario: Juan García
  - Fórmula: Azul Reactivo
  - Bodega Químicos: Química Central
    ↓
Juan inicia teñido
```

### Caso 2: Empaquetado
```
Jefe Planta: OP-2026-002, Empaquetado, 100kg
    ↓
Jefe Área Empaquetado:
  - Producto entrada: Tela teñida (del almacén)
  - Producto salida: Tela empaquetada
  - Bodega entrada: Semiterminados
  - Máquina: Empaquetadora Automática
  - Operario: María López
    ↓
María empieza empaque
```

---

## Búsquedas y Filtros

### Por Jefe de Planta
```
GET /api/ordenes-produccion/              # Ver todas sus órdenes
GET /api/ordenes-produccion/?estado=pendiente  # Sin completar
```

### Por Jefe de Área
```
GET /api/ordenes-produccion/              # Ver solo su área
GET /api/ordenes-produccion/?area=1       # Filtrar por área
GET /api/ordenes-produccion/?estado=en_proceso
```

### Por Operario
```
GET /api/ordenes-produccion/              # Ver asignadas a él
GET /api/ordenes-produccion/?operario_asignado=15
```

---

## Validaciones por Rol

### Jefe de Planta - Crear
- ✅ Código único por sede
- ✅ Área existe
- ✅ Peso > 0
- ❌ NO puede asignar producto/bodega/máquina

### Jefe de Área - Completar Detalles
- ✅ Pertenece al área de la orden
- ✅ Productos existen y son válidos
- ✅ Bodegas existen
- ✅ Máquina existe y opera en el área
- ✅ Operario pertenece al área
- ❌ NO puede cambiar código/peso/área

### Operario - Registrar Lote
- ✅ Orden asignada a él
- ✅ Orden tiene detalles completos
- ❌ NO puede modificar datos base

---

## API Endpoints

| Método | Endpoint | Rol | Descripción |
|--------|----------|-----|-------------|
| POST | `/api/ordenes-produccion/` | Jefe Planta | Crear orden básica |
| GET | `/api/ordenes-produccion/` | Todos | Listar órdenes |
| GET | `/api/ordenes-produccion/{id}/` | Todos | Ver detalle |
| PATCH | `/api/ordenes-produccion/{id}/completar_detalles/` | Jefe Área | Completar detalles |
| POST | `/api/ordenes-produccion/{id}/registrar-lote/` | Operario | Registrar lote |
| PUT | `/api/ordenes-produccion/{id}/` | Admin | Actualización completa |

---

## Ejemplos cURL

### 1. Jefe Planta Crea Orden
```bash
curl -X POST http://localhost:8000/api/ordenes-produccion/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo": "OP-001",
    "area": 1,
    "peso_neto_requerido": 100.50,
    "prioridad": "alta"
  }'
```

### 2. Jefe Área Completa Detalles
```bash
curl -X PATCH http://localhost:8000/api/ordenes-produccion/1/completar_detalles/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "producto_entrada": 5,
    "producto_salida": 6,
    "bodega_entrada": 2,
    "bodega_salida": 3,
    "maquina_asignada": 1,
    "operario_asignado": 15
  }'
```

### 3. Operario Registra Lote
```bash
curl -X POST http://localhost:8000/api/ordenes-produccion/1/registrar-lote/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "codigo_lote": "OP-001-L1",
    "peso_neto_producido": 100.00,
    "hora_inicio": "2026-06-11T08:00:00Z",
    "hora_final": "2026-06-11T10:00:00Z"
  }'
```

---

## Notas Importantes

1. **Auditoría**: Todos los cambios se registran en AuditLog con usuario y justificación
2. **Descarga Química**: Automática si la orden tiene fórmula asignada
3. **Stock**: Se valida disponibilidad al registrar lote
4. **Prioridad**: Visible en dashboard para planificación
5. **Área**: Filtrado automático para Jefes de Área

---

## Cambios Realizados

### Backend
- ✅ Nuevo endpoint `completar_detalles` en OrdenProduccionViewSet
- ✅ Permisos refinados por rol y acción
- ✅ Validaciones relajadas para creación
- ✅ Validaciones estrictas para actualización
- ✅ Serializer con campos opcionales

### Flujo
- ✅ Separación clara de responsabilidades
- ✅ Dos fases: Creación básica + Completar detalles
- ✅ Prevención de cambios no autorizados
- ✅ Auditoria de todos los cambios
