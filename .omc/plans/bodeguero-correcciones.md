# Plan: Corrección de Movimientos de Inventario (Bodeguero)

**Fecha:** 2026-04-20  
**Rama:** fixreportes  
**Alcance:** COMPRA + TRANSFERENCIA — editar cantidad, bodega, documento + historial modal

---

## Contexto del sistema (hallazgos del análisis)

| Elemento | Estado |
|---|---|
| `MovimientoInventario.editado` / `fecha_ultima_edicion` | ✅ Ya existe |
| `AuditoriaMovimiento` (tabla de historial con `razon_cambio`) | ✅ Ya existe |
| `PUT /api/inventory/movimientos/{id}/` | ✅ Existe, **solo COMPRA** (línea 232 inventory/views.py) |
| `GET /api/inventory/movimientos/{id}/auditoria/` | ✅ Existe |
| `MovimientoInventarioUpdateSerializer` (razon_cambio min 10 chars) | ✅ Existe |
| Soporte edición TRANSFERENCIA | ❌ Falta |
| UI de correcciones en frontend | ❌ Falta |

---

## Requisitos

1. El bodeguero puede editar entradas (COMPRA) y transferencias (TRANSFERENCIA)
2. Toda edición requiere `razon_cambio` (mínimo 10 caracteres)
3. El stock se recalcula atómicamente al editar (revertir anterior, aplicar nuevo)
4. Cada edición queda en `AuditoriaMovimiento` con usuario, fecha y motivo
5. El bodeguero puede ver el historial de cambios de cualquier movimiento en un modal
6. Los movimientos editados muestran badge "Editado" en la tabla

---

## Criterios de aceptación

- [ ] PATCH a `/movimientos/{id}/` con tipo TRANSFERENCIA y `razon_cambio` actualiza stock correctamente
- [ ] Si nueva cantidad > stock disponible en bodega origen, retorna 400
- [ ] `AuditoriaMovimiento` registra un registro por campo modificado
- [ ] `MovimientoInventario.editado = True` y `fecha_ultima_edicion` se actualizan
- [ ] Modal de edición bloquea submit si `razon_cambio` < 10 caracteres
- [ ] Modal de historial muestra: fecha, usuario, campo, valor anterior→nuevo, motivo
- [ ] La tabla de correcciones es filtrable por tipo (COMPRA/TRANSFERENCIA) y fecha

---

## Implementación

### FASE 1 — Backend: extender edición a TRANSFERENCIA

**Archivo:** `inventory/views.py` — método `update()` (línea 214)

**Lógica para TRANSFERENCIA:**
```
1. Obtener movimiento original (cantidad_orig, bodega_origen, bodega_destino)
2. Con select_for_update:
   a. Revertir: stock_origen += cantidad_orig, stock_destino -= cantidad_orig
   b. Validar: stock_origen_nuevo >= nueva_cantidad (evitar negativos)
   c. Aplicar: stock_origen -= nueva_cantidad, stock_destino += nueva_cantidad
3. Actualizar movimiento: cantidad, bodega_origen, bodega_destino, documento_ref, editado, fecha_ultima_edicion
4. Registrar en AuditoriaMovimiento por cada campo cambiado
```

**Campos editables por tipo:**

| Tipo | Campos editables |
|---|---|
| COMPRA | cantidad, documento_ref, observaciones |
| TRANSFERENCIA | cantidad, bodega_origen, bodega_destino, observaciones |

**Archivos a modificar:**
- `inventory/views.py`: quitar restricción línea 232, agregar rama TRANSFERENCIA en `update()`
- `inventory/serializers.py`: extender `MovimientoInventarioUpdateSerializer` con campos opcionales `bodega_origen_id`, `bodega_destino_id`

---

### FASE 2 — Frontend: tab "Correcciones" en BodegueroDashboard

**Archivo:** `frontend/src/components/bodeguero/BodegueroDashboard.tsx`

**Nuevo tab:** `correcciones` (icono: `FileEdit` de lucide-react)

**Componente `CorreccionesView`:**
- Tabla con filtros: tipo (COMPRA/TRANSFERENCIA), fecha desde/hasta
- Columnas: ID, Fecha, Tipo, Producto, Cantidad, Bodega, Estado (badge "Editado"), Acciones
- Acciones por fila:
  - `Pencil` → abre `EditarMovimientoModal`
  - `History` → abre `HistorialMovimientoModal`

**`EditarMovimientoModal`:**
- Campos según tipo (ver tabla arriba)
- `razon_cambio` (textarea, required, min 10 chars, contador de caracteres)
- Validación client-side antes de submit
- On success: refresh tabla + toast "Movimiento corregido"

**`HistorialMovimientoModal`:**
- GET `/api/inventory/movimientos/{id}/auditoria/`
- Tabla: Fecha | Usuario | Campo | Anterior → Nuevo | Motivo
- Estado vacío si no hay modificaciones

**Archivos a crear/modificar:**
- `frontend/src/components/bodeguero/BodegueroDashboard.tsx` — agregar tab + componentes
- (Opcional) `frontend/src/components/bodeguero/CorreccionesView.tsx` — si el componente crece

---

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Stock negativo al editar transferencia | Validar `stock_origen >= nueva_cantidad` dentro de `select_for_update` antes de aplicar |
| Edición de transferencia con bodega cambiada | Revertir stock en bodegas ORIGINALES antes de aplicar en bodegas NUEVAS |
| Concurrencia (dos ediciones simultáneas) | `select_for_update()` en todo el bloque de stock |
| Usuario sin permiso edita vía API | Permiso ya validado en `update()` (bodeguero, jefe_area, etc.) |

---

## Pasos de verificación

1. `PUT /movimientos/{id}/` con tipo TRANSFERENCIA retorna 200 y stocks actualizados
2. `PUT /movimientos/{id}/` con cantidad > stock disponible retorna 400
3. `GET /movimientos/{id}/auditoria/` muestra los cambios registrados
4. En frontend: modal de edición con `razon_cambio` vacío no permite submit
5. Badge "Editado" aparece en la fila después de la corrección
6. Modal de historial muestra el cambio recién aplicado

---

## Orden de implementación sugerido

1. `inventory/views.py` — extender `update()` para TRANSFERENCIA
2. `inventory/serializers.py` — campos opcionales de bodega
3. `BodegueroDashboard.tsx` — tab + tabla de correcciones
4. `EditarMovimientoModal` — formulario con validación
5. `HistorialMovimientoModal` — visualización de auditoría
