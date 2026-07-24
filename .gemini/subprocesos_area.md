# Flujo de Subprocesos por Área

## Descripción General

Este módulo implementa un control granular de subprocesos en las órdenes de producción, permitiendo que cada área tenga subprocesos secuenciales o paralelos que son supervisados por el jefe de área.

## Flujo de Trabajo

### 1. Configuración de Subprocesos por Área (Admin/Jefe de Planta)

Primero, se deben definir qué subprocesos ejecuta cada área:

**Endpoint:** `POST /api/area-process-steps/`

```json
{
  "area": 1,
  "proceso": 1,
  "orden": 1,
  "tipo_flujo": "secuencial",
  "es_bloqueante": true
}
```

**Campos:**
- `area`: ID del área
- `proceso`: ID del proceso (ProcessStep)
- `orden`: Número de orden de ejecución (menor = primero)
- `tipo_flujo`: "secuencial" o "paralelo"
  - **Secuencial**: El siguiente subproceso espera a que este se complete
  - **Paralelo**: Este subproceso puede ejecutarse junto con otros
- `es_bloqueante`: Si true, los procesos siguientes esperan su completación

**Ejemplo de configuración para Tintorería:**
```
Orden 1: Pre-tratamiento (Secuencial, Bloqueante)
Orden 2: Teñido (Secuencial, Bloqueante)
Orden 3: Post-tratamiento (Secuencial, Bloqueante)
Orden 4: Control de calidad (Paralelo, No bloqueante)
```

### 2. Creación Automática de Subprocesos en una Orden

Cuando el Jefe de Planta crea una orden de producción asignada a un área, los subprocesos se crean automáticamente basados en la configuración del área.

**Endpoint:** `POST /api/ordenes-produccion/`

```json
{
  "codigo": "OP-2024-001",
  "producto_entrada": 1,
  "producto_salida": 2,
  "area": 1,
  "peso_neto_requerido": 100.50,
  ...
}
```

**Resultado:** Se crean registros de `OrdenProduccionSubproceso` para cada subproceso del área, todos en estado "pendiente".

### 3. Control de Subprocesos por Jefe de Área

El Jefe de Área supervisa y controla el progreso de cada subproceso en la orden:

#### Listar subprocesos de una orden:
**GET** `/api/ordenes-produccion-subprocesos/?orden_produccion=1`

```json
{
  "results": [
    {
      "id": 1,
      "orden_produccion": 1,
      "area_proceso": 1,
      "proceso_nombre": "Pre-tratamiento",
      "area_nombre": "Tintorería",
      "estado": "pendiente",
      "fecha_inicio_real": null,
      "fecha_fin_real": null,
      "usuario_responsable": null,
      "observaciones": null,
      "duracion_minutos": null
    }
  ]
}
```

#### Iniciar un subproceso:
**PATCH** `/api/ordenes-produccion-subprocesos/1/iniciar_subproceso/`

```json
{
  "observaciones": "Iniciando el pre-tratamiento con agua a 40°C"
}
```

**Efecto:** Cambia estado a "en_progreso", registra fecha_inicio_real y usuario_responsable

#### Completar un subproceso:
**PATCH** `/api/ordenes-produccion-subprocesos/1/completar_subproceso/`

```json
{
  "observaciones": "Pre-tratamiento completado sin problemas"
}
```

**Efecto:** Cambia estado a "completado", registra fecha_fin_real

#### Pausar un subproceso:
**PATCH** `/api/ordenes-produccion-subprocesos/1/pausar_subproceso/`

```json
{
  "observaciones": "Pausado por mantenimiento de máquina"
}
```

**Efecto:** Cambia estado a "pausado" sin cerrar la ejecución

#### Rechazar un subproceso:
**PATCH** `/api/ordenes-produccion-subprocesos/1/rechazar_subproceso/`

```json
{
  "motivo_rechazo": "Producto no cumple especificaciones de color",
  "observaciones": "Se requiere repetir el teñido"
}
```

**Efecto:** Cambia estado a "rechazado" y registra motivo

## Estados del Subproceso

| Estado | Descripción | Transiciones Válidas |
|--------|-------------|-------------------|
| **pendiente** | Esperando iniciar | → en_progreso |
| **en_progreso** | En ejecución | → completado, pausado, rechazado |
| **completado** | Finalizado correctamente | (terminal) |
| **pausado** | Suspendido temporalmente | → en_progreso, rechazado |
| **rechazado** | Falló y requiere repetición | (terminal) |

## Datos Capturados

Para cada subproceso se registran:

1. **Tiempos:**
   - `fecha_inicio_planificada`: Cuándo se planeó que iniciara
   - `fecha_inicio_real`: Cuándo efectivamente inició
   - `fecha_fin_real`: Cuándo se completó
   - `duracion_minutos`: Duración calculada (solo lectura)

2. **Responsabilidad:**
   - `usuario_responsable`: Quién supervisó/ejecutó el subproceso
   - `fecha_creacion`: Cuándo se creó el registro
   - `fecha_modificacion`: Última actualización

3. **Observaciones:**
   - `observaciones`: Notas durante la ejecución
   - `motivo_rechazo`: Razón si fue rechazado

## Casos de Uso

### Caso 1: Orden Simple con Subprocesos Secuenciales

```
Orden de teñido:
1. Pre-tratamiento (10:00 - 10:30)
   ↓ (espera a 1)
2. Teñido (10:30 - 12:00)
   ↓ (espera a 2)
3. Escurrido (12:00 - 12:15)
   ✓ Orden completa
```

### Caso 2: Subprocesos Paralelos con Control

```
Orden de transformación:
1. Corte (9:00 - 10:00) ─┐
2. Empalme (9:00 - 10:00) ├→ Ambos en paralelo
3. Control QA (10:00 - 11:00) ─ Espera ambos
```

### Caso 3: Rechazo y Reintento

```
1. Teñido (en_progreso)
   ↓
   ✗ Control color falla (rechazado)
   ↓
2. Nuevo teñido (pendiente) → se crea automáticamente
```

## Filtros Disponibles

```
GET /api/ordenes-produccion-subprocesos/?estado=en_progreso
GET /api/ordenes-produccion-subprocesos/?usuario_responsable=5
GET /api/ordenes-produccion-subprocesos/?area_proceso__area=2
GET /api/ordenes-produccion-subprocesos/?orden_produccion=1&estado=completado
```

## Permisos

- **Admin Sistemas**: Acceso total
- **Jefe de Planta**: Puede ver y crear órdenes con subprocesos
- **Jefe de Área**: Puede ver y actualizar subprocesos de su área
- **Operario**: Puede ver subprocesos asignados a su área
- **Bodeguero, Vendedor**: Solo lectura de subprocesos

## Notas Técnicas

### Relaciones de Datos

```
Area (1) ←→ (M) AreaProcessStep (M) ↔ (1) ProcessStep
              ↓
         OrdenProduccionSubproceso (M) ←→ (1) OrdenProduccion
```

### Índices de Performance

Se han creado índices en:
- `(orden_produccion, estado)` - Para filtros comunes
- `(usuario_responsable, estado)` - Para dashboards de jefes
- `orden_produccion_id` - Para joins rápidos

### Cálculo de Duración

```python
duracion_minutos = (fecha_fin_real - fecha_inicio_real).total_seconds() / 60
```

Solo está disponible si ambas fechas existen (subproceso completado).

## Futuros Enhancements

1. **Validaciones de Secuencia**: Impedir iniciar subproceso bloqueante si previos no están completos
2. **SLA Tracking**: Alertas si se excede tiempo planificado
3. **Escalations**: Notificar automáticamente si subproceso se detiene > X minutos
4. **Análisis de Performance**: Reportes de tiempo promedio por subproceso/área
5. **Reporte Automático**: Generar PDF de trazabilidad del flujo
