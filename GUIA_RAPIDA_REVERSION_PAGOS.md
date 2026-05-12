# Guía Rápida: Reversión de Pagos de Clientes

**Última actualización:** 2026-05-04

---

## 🎯 En 60 Segundos

El sistema ahora permite **deshacer pagos registrados** y restaurar automáticamente la deuda del cliente:

```
Vendedor ve Historial de Pagos
    → Haz clic en 🔄 (Revertir)
    → Ingresa justificación (mín 5 caracteres)
    → Confirma
    ↓
✅ Deuda restaurada + Auditoría registrada
```

---

## 📊 Qué se Restaura

Cuando reviertes un pago:

1. **Deuda del cliente**
   - Saldo_pendiente restaurado al monto anterior
   - Cálculo: saldo_anterior = saldo_actual + monto_pago

2. **Auditoría completa**
   - AuditLog creado en tabla de auditoría
   - Justificación guardada
   - Usuario y timestamp automáticos

3. **Reconciliación automática**
   - PaymentReconciler ejecutado post-reversión
   - FIFO automático se recalcula
   - Facturas vuelven a estado no pagado si es necesario

4. **Pago eliminado**
   - PagoCliente se elimina de la BD (soft-delete vía auditoría)
   - Ya no aparece en historial de pagos

---

## 🖥️ Interfaces

### Backend API

**Endpoint 1: POST (Recomendado)**
```bash
POST /pagos-cliente/{id}/revertir/
Content-Type: application/json

{
  "justificacion": "Pago duplicado registrado"
}

# Respuesta: 200 OK
{
  "message": "Pago revertido exitosamente. Deuda restaurada a $7500.00",
  "resultado": {
    "pago_id": 123,
    "cliente_id": 45,
    "cliente_nombre": "Cliente SA",
    "monto_revertido": "2500.00",
    "saldo_anterior_pago": "7500.00"
  }
}

# Error: 400 Bad Request
{
  "error": "Justificación obligatoria para revertir pago"
}
```

**Endpoint 2: DELETE (Alternativo)**
```bash
DELETE /pagos-cliente/{id}/
Content-Type: application/json

{
  "justificacion": "Pago registrado por error"
}

# Respuesta: 204 No Content (éxito)
```

### Frontend

**Ubicación:** Panel de Ventas → Cliente → Abonos/Recibos

**UI:**
1. Tabla con historial de pagos
2. Columna "Acciones" con botones:
   - 👁️ Ver (detalles si los hubiera)
   - 🔄 Revertir (rojo)

3. Modal al hacer clic en 🔄:
   - TextArea para justificación (mín. 5 caracteres)
   - Advertencia: "Se restaurará la deuda al monto anterior"
   - Muestra: Monto, fecha, método de pago
   - Botones: Cancelar | Confirmar Reversión

---

## ✅ Validaciones

### Justificación Obligatoria

```
❌ Vacía o < 5 caracteres → HTTP 400 / Botón deshabilitado
✅ ≥ 5 caracteres → HTTP 200 / Reversión exitosa
```

### Solo para Vendedores

- Rol requerido: `vendedor` o `admin`
- Sin permiso: HTTP 403 Forbidden
- Vendedor solo ve sus clientes asignados

### Transaccionalidad

- Si algo falla → todo se deshace (rollback)
- Deuda nunca queda inconsistente

---

## 🧪 Testing en Postman

### 1. Crear Pago (Setup)

```bash
POST /pagos-cliente/
{
  "cliente": 45,
  "monto": 2500.00,
  "metodo_pago": "transferencia",
  "comprobante": "TRANS-2026-001",
  "notas": "Pago del pedido GR-001"
}
```

Respuesta: `201 Created` + `id: 123`

### 2. Verificar Deuda ANTES

```bash
GET /clientes/45/

# Respuesta incluye: saldo_calculado (o saldo_pendiente)
```

### 3. Revertir Pago

```bash
POST /pagos-cliente/123/revertir/
{
  "justificacion": "Cliente reportó que pagó dos veces"
}

# Respuesta: 200 OK
```

### 4. Verificar Deuda DESPUÉS

```bash
GET /clientes/45/

# Respuesta: saldo_calculado = saldo_anterior (restaurado)
```

### 5. Verificar Auditoría

```bash
GET /audit-logs/?content_type=pagocliente&object_id=123

# Buscar AuditLog con accion='DELETE'
```

---

## 🐛 Troubleshooting

### Error: "Justificación obligatoria"

**Causa:** Campo vacío o < 5 caracteres  
**Solución:** Ingresa motivo válido (mínimo 5 caracteres)

### Error: 404 Not Found

**Causa:** Pago no existe  
**Solución:** Verificar ID del pago

### Error: 403 Forbidden

**Causa:** No tienes permisos  
**Solución:** Contacta administrador para rol `vendedor`

### Deuda no se restauró

**Causa:** Transacción falló (log interno)  
**Solución:** Revisar logs backend: `python manage.py shell` → buscar AuditLog

---

## 📊 Flujo Completo

```
┌──────────────────────────────────┐
│ VendedorDashboard Component      │
│ - Tabla de clientes              │
│ - Historial de pagos del cliente │
│ - Botón 🔄 Revertir              │
└────────┬──────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ Modal de Reversión               │
│ - TextArea: justificación (5+)   │
│ - Advertencia visual             │
│ - Botón: Confirmar               │
└────────┬──────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ API POST /revertir/              │
│ + justificacion                  │
└────────┬──────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ PagoClienteViewSet.revertir()    │
│ - Valida justificación           │
│ - Llama PagoReversionService     │
└────────┬──────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ PagoReversionService             │
│ @transaction.atomic              │
│ - Elimina PagoCliente            │
│ - Crea AuditLog                  │
│ - Trigger PaymentReconciler      │
└────────┬──────────────────────────┘
         │
         ↓
┌──────────────────────────────────┐
│ ✅ Pago Revertido                │
│ - Deuda restaurada               │
│ - Auditoría: DELETE registrado   │
│ - FIFO recalculado               │
└──────────────────────────────────┘
```

---

## 📁 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `gestion/services/pago_reversion.py` | **NUEVO** - PagoReversionService |
| `gestion/views.py` | PagoClienteViewSet: destroy + revertir action |
| `frontend/src/components/vendedor/VendedorDashboard.tsx` | Botón revert + Modal + handlers |
| `gestion/tests/test_pago_reversion.py` | **NUEVO** - 4 tests de integración |
| `GUIA_RAPIDA_REVERSION_PAGOS.md` | **NUEVO** - Este documento |

---

## 🔗 Documentación Relacionada

- [RESUMEN_IMPLEMENTACION_REVERSION_DESPACHO.md](RESUMEN_IMPLEMENTACION_REVERSION_DESPACHO.md) — Patrón similar para despachos
- [GUIA_RAPIDA_REVERSION_DESPACHO.md](GUIA_RAPIDA_REVERSION_DESPACHO.md) — Reversión de despachos
- `/gestion/services/pago_reversion.py` — Código del servicio
- `/gestion/tests/test_pago_reversion.py` — Tests de integración

---

## 💡 Tips Importantes

1. **Justificación es OBLIGATORIA** — sin ella, la reversión falla (HTTP 400)
2. **Reversión es ATÓMICA** — si algo falla, todo se deshace
3. **Deuda se restaura AUTOMÁTICAMENTE** — no hay pasos manuales
4. **FIFO se recalcula AUTOMÁTICAMENTE** — PaymentReconciler ejecutado post-reversión
5. **Auditoría es INMUTABLE** — todos los cambios registrados en AuditLog

---

## 🆘 Soporte

Para problemas o preguntas:
1. Revisar **logs backend:** Python shell → AuditLog.objects.filter(accion='DELETE')
2. Consultar **test cases:** `gestion/tests/test_pago_reversion.py`
3. Leer **documentación técnica:** Patrón idéntico a DespachoReversionService

---

**Última actualización:** 2026-05-04 | **Versión:** 1.0
