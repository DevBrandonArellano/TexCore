# Guía Rápida: Reversión de Despachos

**Última actualización:** 2026-05-04

---

## 🎯 En 60 Segundos

El sistema ahora permite **deshacer despachos** y restaurar automáticamente todo el stock:

```
Usuario ve Historial de Despachos
    → Haz clic en 🔄 (Revertir)
    → Ingresa justificación
    → Confirma
    ↓
✅ Stock restaurado + Auditoría registrada
```

---

## 📦 Qué se Restaura

Cuando reviertes un despacho:

1. **Stock en bodegas**
   - Cantidad restaurada a valor original
   - Registrado en `MovimientoInventario` (tipo=DEVOLUCION)

2. **Descargas de químicos**
   - `DescargaQuimicoOP.estado` → 'revertida'
   - Stock químico también restaurado

3. **Pedidos**
   - `PedidoVenta.estado` → 'pendiente'
   - Disponible para nuevo despacho

4. **Auditoría**
   - Usuario registrado
   - Justificación guardada
   - Timestamp automático

---

## 🖥️ Interfaces

### Backend API

**Endpoint 1: POST (Recomendado)**
```bash
POST /inventory/historial-despachos/{id}/revertir/
Content-Type: application/json

{
  "justificacion": "Error en selección de lotes"
}

# Respuesta: 200 OK
{
  "message": "Despacho revertido exitosamente...",
  "resultado": {
    "despacho_id": 123,
    "movimientos_creados": 2,
    "lotes_revertidos": 2
  }
}

# Error: 400 Bad Request
{
  "justificacion": "Justificación obligatoria para revertir despacho"
}
```

**Endpoint 2: DELETE (Alternativo)**
```bash
DELETE /inventory/historial-despachos/{id}/
Content-Type: application/json

{
  "justificacion": "Cliente rechazó mercadería"
}

# Respuesta: 204 No Content (éxito)
```

### Frontend

**Ubicación:** Panel de Despacho → Historial de Despachos

**UI:**
1. Tabla con despachos
2. Columna "Acciones" con botones:
   - 👁️ Ver (detalles)
   - 🔄 Revertir (rojo)

3. Modal al hacer clic en 🔄:
   - TextArea para justificación
   - Advertencia: "Se restaurarán X kg"
   - Botones: Cancelar | Confirmar Reversión

---

## ✅ Validaciones

### Justificación Obligatoria

```
❌ Vacía → HTTP 400 / Botón deshabilitado
✅ No vacía → HTTP 200 / Reversión exitosa
```

### Solo para Despachadores

- Rol requerido: `despacho` o `admin`
- Sin permiso: HTTP 403 Forbidden

### Transaccionalidad

- Si algo falla → todo se deshace (rollback)
- Stock nunca queda inconsistente

---

## 🧪 Testing en Postman

### 1. Crear Despacho (Setup)

```bash
POST /inventory/process-despacho/
{
  "pedidos": [1, 2],
  "lotes": ["LOTE-001", "LOTE-002"],
  "observaciones": "Despacho de prueba"
}
```

Respuesta: `201 Created` + `despacho_id: 123`

### 2. Verificar Stock ANTES

```bash
GET /inventory/stock/?bodega_id=5

# Respuesta: cantidad = 0 (despachado)
```

### 3. Revertir Despacho

```bash
POST /inventory/historial-despachos/123/revertir/
{
  "justificacion": "Error en el pesaje"
}

# Respuesta: 200 OK
```

### 4. Verificar Stock DESPUÉS

```bash
GET /inventory/stock/?bodega_id=5

# Respuesta: cantidad = 50.00 (restaurado)
```

### 5. Verificar Auditoría

```bash
GET /inventory/bodegas/5/kardex/?producto_id=10

# Buscar MovimientoInventario tipo='DEVOLUCION'
```

---

## 🐛 Troubleshooting

### Error: "Justificación obligatoria"

**Causa:** Campo vacío  
**Solución:** Ingresa motivo de reversión en el TextArea

### Error: 404 Not Found

**Causa:** Despacho no existe  
**Solución:** Verificar ID del despacho

### Error: 403 Forbidden

**Causa:** No tienes permisos  
**Solución:** Contacta administrador para rol `despacho`

### Stock no se restauró

**Causa:** Transacción falló (log interno)  
**Solución:** Revisar logs backend: `python manage.py logs`

---

## 📊 Flujo Completo

```
┌─────────────────────────────────────┐
│ HistorialDespachos Component        │
│ - Tabla de despachos                │
│ - Botón 🔄 Revertir                 │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ Modal de Reversión                  │
│ - TextArea: justificación            │
│ - Botón: Confirmar                  │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ API POST /revertir/                 │
│ + justificacion                      │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ HistorialDespachoViewSet.revertir() │
│ - Valida justificación              │
│ - Llama DespachoReversionService    │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ DespachoReversionService            │
│ @transaction.atomic                  │
│ - Restaura stock                    │
│ - Revierte descargas químicas       │
│ - Actualiza pedidos                 │
│ - Crea auditoría                    │
└────────────┬────────────────────────┘
             │
             ↓
┌─────────────────────────────────────┐
│ ✅ Despacho Revertido               │
│ - Stock restaurado                  │
│ - Pedido: pendiente                 │
│ - Auditoría: DEVOLUCION registrado  │
└─────────────────────────────────────┘
```

---

## 📁 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `inventory/views.py` | HistorialDespachoViewSet: ReadOnly → ModelViewSet + destroy + revertir action |
| `frontend/.../HistorialDespachos.tsx` | State + Modal + Botón revert + API call |
| `inventory/services/despacho_reversion.py` | **NUEVO** - DespachoReversionService |
| `inventory/tests/test_despacho_reversion.py` | **NUEVO** - 4 tests de integración |
| `DOCUMENTACION_REVERSION_DESPACHO.md` | **NUEVA** - Documentación técnica |
| `RESUMEN_IMPLEMENTACION_REVERSION_DESPACHO.md` | **NUEVO** - Resumen ejecutivo |

---

## 🔗 Documentación Relacionada

- [DOCUMENTACION_REVERSION_DESPACHO.md](DOCUMENTACION_REVERSION_DESPACHO.md) — Especificación técnica
- [DOCUMENTACION_DESCARGA_QUIMICOS.md](DOCUMENTACION_DESCARGA_QUIMICOS.md) — Descarga automática (relacionado)
- `/inventory/services/despacho_reversion.py` — Código del servicio
- `/inventory/tests/test_despacho_reversion.py` — Tests

---

## 💡 Tips Importantes

1. **Justificación es OBLIGATORIA** — sin ella, la reversión falla (HTTP 400)
2. **Reversión es ATÓMICA** — si algo falla, todo se deshace
3. **Stock se restaura AUTOMÁTICAMENTE** — no hay pasos manuales
4. **Descargas químicas también se revierten** — si existían
5. **Pedidos vuelven a PENDIENTE** — pueden ser despachados nuevamente

---

## 🆘 Soporte

Para problemas o preguntas:
1. Revisar **logs backend:** `python manage.py logs`
2. Consultar **test cases:** `inventory/tests/test_despacho_reversion.py`
3. Leer **documentación técnica:** `/DOCUMENTACION_REVERSION_DESPACHO.md`

---

**Última actualización:** 2026-05-04 | **Versión:** 1.0
