# Diseño: Producción Flexible con Mezclas, Transformación y Merma Vendible

**Fecha:** 2026-06-01  
**Autor:** Brandon Arellano  
**Estado:** Aprobado  
**Controles:** ISO 27001 A.9.4, A.12.4 | COBIT DSS06, MEA01

---

## 1. Contexto y Objetivo

TexCore es un ERP textil multi-tenant donde cada empresa configura sus propias áreas, máquinas, bodegas y productos. El modelo actual de `OrdenProduccion` asume que el producto consumido y el producto generado son el mismo (solo cambia el lote), lo cual no refleja la realidad: cada máquina **transforma** un producto de entrada en uno de salida diferente, puede mezclar múltiples lotes de entrada, y genera merma vendible específica por máquina.

**Objetivo:** Extender el modelo quirúrgicamente (Opción A) para soportar:
1. `producto_entrada` → `producto_salida` en cada OP
2. Mezcla de múltiples lotes de entrada (ej: 50% algodón + 50% poliéster)
3. Merma como producto vendible, configurable por máquina
4. CRUD completo en dashboards por rol con auditoría total
5. Tests TDD con técnicas ISTQB (EP, BVA, STT)

---

## 2. Arquitectura — Cuatro Sub-proyectos

```
SP-1: Modelos + Migraciones (backend)
  └─ SP-2: Service Layer (backend)
       └─ SP-3: API / Views (backend)
            └─ SP-4: Frontend CRUD Dashboards
```

Cada sub-proyecto se implementa con TDD: tests primero (RED), luego implementación (GREEN), luego refactor.

---

## 3. Sub-proyecto 1: Modelos y Migraciones

### 3.1 `OrdenProduccion` — Campos modificados

| Campo actual | Campo nuevo | Tipo | Notas |
|---|---|---|---|
| `producto` | `producto_entrada` | FK → Producto | `RenameField` — sin pérdida de datos |
| `bodega` | `bodega_entrada` | FK → Bodega | `RenameField` |
| *(nuevo)* | `producto_salida` | FK → Producto | `AddField`, nullable en migración → not null tras backfill |
| *(nuevo)* | `bodega_salida` | FK → Bodega | `AddField`, nullable en migración → not null tras backfill |

### 3.2 `ComponenteMezclaOP` — NUEVO

Representa la **receta de mezcla** definida por el Jefe de Área para una OP. Si la OP no tiene mezcla, este modelo queda vacío y se usa solo `producto_entrada`.

```python
class ComponenteMezclaOP(AuditableModel):
    orden       = ForeignKey(OrdenProduccion, on_delete=CASCADE, related_name='componentes_mezcla')
    producto    = ForeignKey(Producto, on_delete=PROTECT)
    bodega      = ForeignKey(Bodega, on_delete=PROTECT)          # bodega de origen de este componente
    porcentaje  = DecimalField(max_digits=5, decimal_places=2)   # ej: 50.00
    cantidad_kg = DecimalField(max_digits=12, decimal_places=3)  # calculado: (porcentaje/100) * peso_neto_requerido

    class Meta:
        unique_together = [('orden', 'producto')]
        # ISO 27001 A.12.4 — auditoría habilitada via AuditableModel
```

**Constraint de negocio (COBIT DSS06):** `SUM(porcentaje) == 100` por OP. Validado en serializer Y en service. En DB: `CheckConstraint` en migración.

### 3.3 `ConsumoLoteDetalle` — NUEVO

Registra la **ejecución real** de consumo al momento de registrar un lote. Vincula qué lote origen se usó y cuánto.

```python
class ConsumoLoteDetalle(AuditableModel):
    lote_produccion    = ForeignKey(LoteProduccion, on_delete=CASCADE, related_name='consumos_detalle')
    lote_origen        = ForeignKey(LoteProduccion, on_delete=PROTECT, related_name='usos_como_input')
    cantidad_consumida = DecimalField(max_digits=12, decimal_places=3)
    genera_nuevo_lote  = BooleanField(default=True)
    # Si False: el output mantiene el código de lote del origen (sin transformación)

    class Meta:
        # ISO 27001 A.12.4 — INMUTABLE: no se permite UPDATE, solo DELETE con reversión justificada
```

**Regla de inmutabilidad (ISO 27001 A.12.4):** `ConsumoLoteDetalle` no tiene endpoint PATCH/PUT. Las correcciones se hacen únicamente mediante el endpoint `rechazar` del lote, que revierte todo de forma atómica con justificación obligatoria en AuditLog.

### 3.4 `Maquina` — Campos nuevos

```python
producto_merma = ForeignKey(Producto, null=True, blank=True, on_delete=SET_NULL,
                            related_name='maquinas_generadoras')
bodega_merma   = ForeignKey(Bodega, null=True, blank=True, on_delete=SET_NULL)
```

Configura qué producto se genera como desperdicio y dónde se almacena. Cada empresa configura esto en el dashboard de Jefe de Área.

### 3.5 Matriz de permisos por modelo (ISO 27001 A.9.4)

| Modelo | Crear | Editar | Eliminar | Ver |
|---|---|---|---|---|
| `ComponenteMezclaOP` | `jefe_area` | `jefe_area` | `jefe_area` + justificación | Autenticados |
| `ConsumoLoteDetalle` | Sistema (service) | ❌ Inmutable | Via `rechazar` + justificación | `jefe_area`, `admin_sistemas` |
| `Maquina` (merma config) | `jefe_area` | `jefe_area` | `jefe_area` | Autenticados |
| `OrdenProduccion` (nuevos campos) | `jefe_planta` | `jefe_planta` + justificación si hay descarga | `jefe_planta` + justificación | Autenticados |

### 3.6 Estrategia de migración

```
0001_rename_producto_to_producto_entrada       (RenameField)
0002_rename_bodega_to_bodega_entrada           (RenameField)
0003_add_producto_salida_bodega_salida         (AddField nullable)
0004_add_componente_mezcla_op                 (CreateModel)
0005_add_consumo_lote_detalle                 (CreateModel)
0006_add_maquina_merma_fields                 (AddField)
0007_backfill_producto_salida                 (RunPython — copia producto_entrada a producto_salida en registros existentes)
0008_make_producto_salida_not_null            (AlterField)
```

---

## 4. Sub-proyecto 2: Service Layer

### 4.1 `RegistroLoteService` — Actualizado

**Flujo actualizado (COBIT DSS06 — integridad transaccional):**

```
@transaction.atomic
registrar_lote(orden, lote_data, user):
  1. Validar orden.producto_entrada, orden.producto_salida, orden.bodega_entrada, orden.bodega_salida
  2. Calcular consumo_total = peso_neto_producido + peso_merma
  3. Si orden.componentes_mezcla.exists():
       → ConsumoMezclaService.consumir(orden, lote_data['consumos'], consumo_total, user)
     Sino:
       → Consumo simple: StockBodega(bodega_entrada, producto_entrada) -= consumo_total
       → MovimientoInventario(CONSUMO, producto_entrada, bodega_origen=bodega_entrada)
  4. Si peso_merma > 0:
       → MermaStockService.registrar(lote, user)
  5. Crear LoteProduccion
  6. StockBodega(bodega_salida, producto_salida, lote=nuevo_lote) += peso_neto_producido
  7. MovimientoInventario(PRODUCCION, producto_salida, bodega_destino=bodega_salida)
  8. Actualizar estado de OP
  9. AuditLog estructurado (RFC 5424)
```

### 4.2 `ConsumoMezclaService` — NUEVO (SRP)

```
consumir(orden, consumos_data, consumo_total, user):
  # consumos_data: [{lote_origen_id, cantidad_kg, genera_nuevo_lote}, ...]
  
  Validar: SUM(consumos_data.cantidad_kg) == consumo_total (BVA: tolerancia ±0.01 kg)
  
  Para cada componente:
    1. select_for_update() en StockBodega(bodega_componente, producto_componente, lote=lote_origen)
    2. Validar stock disponible >= cantidad_kg
    3. Descontar stock
    4. Crear MovimientoInventario(CONSUMO, producto, lote_origen=lote_origen)
    5. Crear ConsumoLoteDetalle(lote_produccion=nuevo_lote, lote_origen, cantidad, genera_nuevo_lote)
    
  AuditLog con sd: {componentes: [...], total_consumido: X}
```

### 4.3 `MermaStockService` — NUEVO (SRP)

```
registrar(lote, user):
  maquina = lote.maquina
  Si NOT maquina.producto_merma: return  # máquina sin merma configurada
  
  safe_get_or_create_stock(maquina.bodega_merma, maquina.producto_merma)
  stock.cantidad += lote.peso_merma
  
  MovimientoInventario(
    tipo=PRODUCCION,               # entra al inventario como producto
    producto=maquina.producto_merma,
    lote=lote,
    bodega_destino=maquina.bodega_merma,
    cantidad=lote.peso_merma,
    documento_ref=f"MERMA-{lote.codigo_lote}"
  )
  
  AuditLog (ISO 27001 A.12.4)
```

**Nota:** La merma usa `tipo=PRODUCCION` (no `MERMA`) porque entra al stock como producto vendible. El `MovimientoInventario.documento_ref` con prefijo `MERMA-` permite filtrado en Kardex para reportes de eficiencia (COBIT MEA01).

### 4.4 Ajuste del endpoint `rechazar` — Actualizado

Al rechazar un lote con mezcla:
1. Reversa `ConsumoLoteDetalle` — devuelve stock a cada `lote_origen`
2. Reversa merma si existe en `bodega_merma`
3. Reversa producto de salida de `bodega_salida`
4. Justificación obligatoria → AuditLog
5. `ConsumoLoteDetalle.delete()` → solo permitido desde este flujo (ISO 27001 A.12.4)

---

## 5. Sub-proyecto 3: API / Views

### 5.1 Endpoints nuevos/modificados

| Endpoint | Método | Permiso | Descripción |
|---|---|---|---|
| `/ordenes-produccion/{id}/componentes-mezcla/` | GET/POST | `jefe_area` | CRUD de receta de mezcla |
| `/ordenes-produccion/{id}/componentes-mezcla/{id}/` | PATCH/DELETE | `jefe_area` + justificación | Editar/eliminar componente |
| `/lotes-produccion/{id}/consumos-detalle/` | GET | `jefe_area`, `admin_sistemas` | Ver consumos reales del lote |
| `/lotes-produccion/{id}/rechazar/` | POST | Existente | Actualizar para reversar mezcla y merma |
| `/lotes-produccion/{id}/genealogia/` | GET | Existente | Expandir con `ConsumoLoteDetalle` |

### 5.2 Serializers clave

**`OrdenProduccionSerializer`:**
- Agregar `producto_entrada_detail`, `producto_salida_detail` (read-only nested)
- Agregar `componentes_mezcla` (nested writable)
- Validar: si `componentes_mezcla` presente → `sum(porcentaje) == 100` (COBIT DSS06)

**`ComponenteMezclaOPSerializer`:**
- Validar `porcentaje` en rango (0, 100] — BVA
- Calcular `cantidad_kg` en `validate()` desde `orden.peso_neto_requerido`

**`RegistrarLoteSerializer` — actualizado:**
- Agregar campo `consumos` (lista de `{lote_origen_id, cantidad_kg, genera_nuevo_lote}`)
- Si OP tiene mezcla: `consumos` requerido
- Si OP sin mezcla: `consumos` ignorado

---

## 6. Sub-proyecto 4: Frontend CRUD Dashboards

### 6.1 `AdminSistemasDashboard` — Pestañas nuevas/mejoradas

**Pestaña "Áreas" (NUEVO):**
- Tabla con CRUD: nombre, descripción, sede, fecha creación
- Modal crear/editar con validación Zod
- DELETE con confirmación y justificación → AuditLog

**Pestaña "Bodegas" (MEJORAR):**
- Agregar campo `area` FK al formulario
- Agregar campo `tipo` (entrada_mp, produccion, merma, producto_terminado)

**Pestaña "Productos" (MEJORAR):**
- Agregar campo `tipo` (materia_prima, intermedio, terminado, merma, quimico)
- Filtro por tipo en tabla

### 6.2 `JefeAreaDashboard` — Pestañas nuevas/mejoradas

**Pestaña "Máquinas" (MEJORAR):**
- Agregar formulario de configuración de merma: `producto_merma` + `bodega_merma`
- Selector de producto filtrado por `tipo=merma`

**Pestaña "Mezclas" (NUEVO):**
- Al asignar una OP, si requiere mezcla: formulario para definir `ComponenteMezclaOP`
- Tabla de componentes con porcentajes (validación visual: barra que suma 100%)
- CRUD inline

### 6.3 `JefePlantaDashboard` — Formulario OP actualizado

**Modal "Nueva Orden de Producción":**
- Reemplazar selector `producto` único por:
  - `producto_entrada` + `bodega_entrada`
  - `producto_salida` + `bodega_salida`
- Checkbox "¿Requiere mezcla?" → si true, habilita tab de componentes en JefeArea

### 6.4 `OperarioDashboard` — Formulario de lote actualizado

**Modal "Registrar Lote":**
- Si la OP tiene `componentes_mezcla`:
  - Mostrar tabla de componentes esperados
  - Por cada componente: selector de `lote_origen` (autocomplete filtrado por producto/bodega) + campo `cantidad_kg`
  - Validación: suma de cantidades == consumo_total
- Campo `peso_merma` ya existe — agregar label dinámico del `producto_merma` de la máquina seleccionada

### 6.5 Patrón de CRUD en dashboards (consistente)

Todos los CRUD siguen el mismo patrón:
```
DataTable (shadcn) → columnas + acciones (editar/eliminar)
  ├─ Botón "Nuevo" → Dialog con Form (react-hook-form + Zod)
  ├─ Editar → mismo Dialog con datos pre-cargados
  ├─ Eliminar → AlertDialog con campo justificación (min 10 chars)
  └─ Toast notification (éxito/error)
Estado: TanStack Query (invalidateQueries post-mutación)
```

---

## 7. Estrategia de Tests (TDD + ISTQB)

### 7.1 Orden de implementación TDD

```
Para cada Service:
  RED   → escribir test que falla
  GREEN → implementar mínimo para pasar
  REFACTOR → limpiar sin romper tests
```

### 7.2 Suite de tests nuevos

**`gestion/tests/test_consumo_mezcla_service.py`**
```
EP:  mezcla válida 2 componentes | mezcla 1 componente (sin mezcla) | componente sin stock
BVA: sum_porcentaje=99.99 (falla) | sum_porcentaje=100.00 (pasa) | cantidad_kg=0 (falla)
STT: lote PENDIENTE → consumo → PRODUCIDO → rechazado → stock_revertido
```

**`gestion/tests/test_merma_stock_service.py`**
```
EP:  máquina con merma configurada | máquina sin merma | peso_merma=0 (no crea stock)
BVA: peso_merma=0.01 (crea) | peso_merma=0 (no crea)
STT: merma creada → lote rechazado → merma revertida
```

**`gestion/tests/test_registro_lote_transformacion.py`**
```
EP:  OP simple (sin mezcla) | OP con mezcla | OP con merma | OP con mezcla+merma
BVA: peso_neto=0 (falla) | stock_insuficiente (falla con rollback)
STT: OP pendiente → en_proceso → finalizada → lote rechazado → en_proceso
```

**`gestion/tests/test_componente_mezcla_serializer.py`**
```
EP:  porcentaje válido | porcentaje=0 (falla) | porcentaje>100 (falla)
BVA: sum=100 (pasa) | sum=100.01 (falla) | sum=99.99 (falla)
```

**Factories nuevas (`gestion/tests/factories.py`):**
```python
ComponenteMezclaOPFactory
ConsumoLoteDetalleFactory
MaquinaConMermaFactory   # con producto_merma y bodega_merma
OrdenProduccionConMezclaFactory
```

### 7.3 Controles de auditoría en tests (ISO 27001 A.12.4)

Cada test de service verifica:
- Que se creó `AuditLog` con usuario, timestamp, valores anterior/nuevo
- Que `ConsumoLoteDetalle` no tiene endpoint PUT/PATCH
- Que eliminar `ConsumoLoteDetalle` directamente retorna 405

---

## 8. Controles ISO 27001 y COBIT por capa

| Control | Capa | Implementación |
|---|---|---|
| ISO 27001 A.9.4 | API | `IsJefeArea`, `IsJefePlanta` en cada ViewSet nuevo |
| ISO 27001 A.12.4 | Modelos | `AuditableModel` en `ComponenteMezclaOP`, `ConsumoLoteDetalle` |
| ISO 27001 A.12.4 | Service | `AuditLogger` en cada operación de stock crítica |
| COBIT DSS06 | Service | `sum(porcentaje)==100` validado en serializer + service + DB constraint |
| COBIT DSS06 | Service | `@transaction.atomic` + `select_for_update()` en todo consumo de stock |
| COBIT DSS06 | API | `ConsumoLoteDetalle` inmutable: sin PATCH/PUT, DELETE solo via `rechazar` |
| COBIT MEA01 | Kardex | `documento_ref='MERMA-{codigo}'` para filtrado en reportes de eficiencia |
| COBIT MEA01 | Frontend | Dashboard de merma por máquina en `JefeAreaDashboard` |

---

## 9. Dependencias entre sub-proyectos

```
SP-1 (Modelos) → SP-2 (Services) → SP-3 (API) → SP-4 (Frontend)

No hay dependencias cruzadas entre SP. Cada uno se entrega y prueba
de forma independiente antes de pasar al siguiente.
```

---

## 10. Lo que NO cambia

- `DescargaQuimicosService` — autónomo, sin cambios
- `DosificacionCalculator` — sin cambios
- `DespachoReversionService` — sin cambios
- `PagoReversionService` — sin cambios
- `internal_api` JWT RS256 — sin cambios
- Pipeline CI/CD — sin cambios (nuevos tests se integran automáticamente)
