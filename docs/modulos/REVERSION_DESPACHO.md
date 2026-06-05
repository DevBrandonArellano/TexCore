# Documentación: Reversión de Despachos con Restauración de Stock

**Fecha:** 2026-05-04  
**Versión:** 1.0  
**Autor:** Claude Code (Haiku 4.5)

---

## Resumen Ejecutivo

Se ha implementado un sistema completo de **reversión de despachos** que permite deshacer envíos y restaurar automáticamente todo el stock de químicos a las bodegas de origen. El sistema incluye:

- ✅ Reversión de despachos con justificación obligatoria
- ✅ Restauración automática de stock en bodegas
- ✅ Reversión de registros DescargaQuimicoOP (marca como 'revertida')
- ✅ Creación de MovimientoInventario DEVOLUCION para auditoría completa
- ✅ Revertir estado de pedidos a 'pendiente'
- ✅ Interfaz de usuario con modal de confirmación
- ✅ Respeto total de SOLID + patrones establecidos

---

## Arquitectura Implementada

### Principios SOLID Aplicados

| Principio | Implementación |
|-----------|---|
| **SRP** | `DespachoReversionService` solo gestiona reversión. No contiene lógica de validation o presentación. |
| **OCP** | El servicio es extensible para diferentes estrategias de reversión sin modificar el core. |
| **LSP** | Los contratos de auditoría y stock se respetan fielmente. |
| **ISP** | Endpoints separados: `/historial-despachos/{id}/revertir/` (POST) y DELETE con justificación. |
| **DIP** | Depende de abstracciones (`safe_get_or_create_stock`, `MovimientoInventario`), no de implementaciones. |

### Patrones de Diseño

| Patrón | Aplicación |
|--------|-----------|
| **Service Layer** | `inventory/services/despacho_reversion.py` — toda lógica de negocio fuera de vistas |
| **Template Method** | `_revertir_descargas_quimicas()` sigue patrón de reversión base (buscar → restaurar → auditar) |
| **Proxy/Adapter** | El ViewSet actúa como intermediario entre HTTP y el servicio de reversión |
| **Audit Trail** | Registro inmutable en `MovimientoInventario` y `DescargaQuimicoOP` |

---

## Módulos Implementados

### 1. Backend - Service Layer (`inventory/services/despacho_reversion.py` - NUEVO)

#### `DespachoReversionService`

**Método: `revertir_despacho(historial, usuario, justificacion) → dict`**
- Restaura stock en cada bodega origen del despacho
- Revierte registros `DescargaQuimicoOP` asociados (marca como 'revertida')
- Crea `MovimientoInventario` tipo='DEVOLUCION'
- Revertir estado de `PedidoVenta` a 'pendiente'
- **Transaccional:** `@transaction.atomic`
- **Retorna:** `{'despacho_id': int, 'movimientos_creados': int, 'lotes_revertidos': int}`

**Método: `_revertir_descargas_quimicas(historial, usuario, justificacion)`**
- Busca OPs con descargas 'aplicada' asociadas al despacho
- Restaura stock de cada producto químico descargado
- Marca descargas como 'revertida' con justificación
- Registra auditoría completa

---

### 2. Backend - Views (`inventory/views.py`)

#### `HistorialDespachoViewSet` (actualizado)

**Cambio: ReadOnlyModelViewSet → ModelViewSet**
- Ahora soporta DELETE y acciones personalizadas

**`destroy(request, ...)`**
- Valida `justificacion` obligatoria (HTTP 400 si falta)
- Ejecuta `DespachoReversionService.revertir_despacho()`
- Elimina HistorialDespacho tras reversión exitosa
- Transaccional: `@transaction.atomic`

**`@action revertir`**
- POST `/historial-despachos/{id}/revertir/`
- Alternativa amigable a DELETE con body
- Idéntica lógica que destroy pero retorna datos del resultado
- Permiso: `IsDespachoWriter`

---

### 3. Frontend - HistorialDespachos Component (actualizado)

**Nuevos State Variables:**
- `showReversionModal: boolean` — visibilidad del modal
- `reversionDespacho: HistorialDespacho | null` — despacho siendo revertido
- `reversionJustificacion: string` — texto de justificación ingresado
- `reversionLoading: boolean` — estado durante petición API

**Nuevas Funciones:**
- `handleInitiateReversion(despacho)` — abre modal
- `handleConfirmReversion()` — envía POST a `/revertir/` con justificación

**Cambios en UI:**
- Tabla: columna "Acciones" con botones Ver (👁️) y Revertir (🔄)
- Modal de confirmación con:
  - TextArea obligatorio para justificación
  - Advertencia visual con cantidad de stock a restaurar
  - Botones Cancelar / Confirmar Reversión
  - Estado de carga con spinner

---

## Flujos de Negocio

### 1. Crear Despacho (SIN CAMBIOS)

```
Despacho Worker selecciona pedidos → escanea lotes
    → POST /inventory/process-despacho/
    → ProcessDespachoAPIView crea HistorialDespacho
    → Reduce stock (cantidad = 0)
    → Crea MovimientoInventario VENTA
    → Marca PedidoVenta como 'despachado'
✓ Despacho creado
```

### 2. Revertir Despacho (NUEVO)

```
Despacho Worker / Manager ve HistorialDespachos
    → Haz clic en botón Revertir (🔄)
    → Modal pide justificación (OBLIGATORIA)
    → Confirma reversión
    ↓
POST /inventory/historial-despachos/{id}/revertir/
    ↓
HistorialDespachoViewSet.revertir()
    ↓
DespachoReversionService.revertir_despacho()
    ├─ Para cada detalle del despacho:
    │   ├─ Busca MovimientoInventario VENTA original
    │   ├─ Restaura stock en bodega_origen
    │   ├─ Crea MovimientoInventario DEVOLUCION
    │   └─ Log de restauración
    ├─ Revierte DescargaQuimicoOP asociadas:
    │   ├─ Busca OPs con lotes despachados
    │   ├─ Restaura cantidad_calculada_kg de stock
    │   ├─ Marca como 'revertida'
    │   └─ Crea MovimientoInventario DEVOLUCION
    └─ Revierte PedidoVenta a estado 'pendiente'
    ↓
✓ Despacho revertido + Stock restaurado + Auditoría completa
✓ Descargas químicas revertidas
```

---

## Validaciones Incorporadas

| Validación | Nivel | Acción |
|------------|-------|--------|
| Justificación obligatoria | API (HTTP 400) | Bloquear reversión sin motivo |
| Justificación en Frontend | UI (TextArea) | Deshabilitar botón si vacío |
| Stock restaurado correctamente | Service Layer | Verificar movimiento VENTA original |
| DescargaQuimicoOP marcadas 'revertida' | Service Layer | Auditoría inmutable |
| Transaccionalidad | @transaction.atomic | Rollback si algún paso falla |
| Pedidos vuelven a estado 'pendiente' | Service Layer | Permitir nuevos despachos |

---

## Auditoría y Trazabilidad

### MovimientoInventario (DEVOLUCION)

```
tipo_movimiento = 'DEVOLUCION'
bodega_destino = bodega origen del despacho original
cantidad = peso restaurado
documento_ref = 'REVERT-Despacho-#{historial.id}' (para VENTA original)
              = 'REVERT-DESC-OP-{op.codigo}' (para descargas químicas)
usuario = usuario que ejecuta reversión
saldo_resultante = stock actualizado en bodega
```

### DescargaQuimicoOP (REVERTIDA)

```
estado = 'revertida'
justificacion = razón de reversión ingresada por usuario
cantidad_calculada_kg = sigue inmutable (auditoría histórica)
```

---

## Restricciones y Reglas

1. **Justificación obligatoria:** No se puede revertir sin explicar el motivo (HTTP 400)
2. **Reversión idempotente:** Marcar detalles con `es_devolucion=True` previene reversiones dobles
3. **Stock restaurado correctamente:** Busca el movimiento VENTA original para identificar bodega
4. **Transaccionalidad garantizada:** Si algún paso falla, todo se revierte automáticamente
5. **Pedidos disponibles:** Al revertir a 'pendiente', pueden ser despachados nuevamente

---

## Testing

### Tests de Integración Sugeridos

```python
# Caso 1: Revertir despacho restaura stock correctamente
def test_revertir_despacho_restaura_stock()
    # Crear despacho → verificar stock = 0
    # Revertir con justificación
    # Verificar stock = valores originales
    # Verificar MovimientoInventario DEVOLUCION creado

# Caso 2: Reversión sin justificación falla
def test_revertir_despacho_requiere_justificacion()
    # Intentar revertir sin justificación → HTTP 400
    # Con justificación → HTTP 200

# Caso 3: DescargaQuimicoOP se revierten
def test_revertir_despacho_revierte_descargas_quimicas()
    # Crear OP con descarga química + despacho
    # Revertir despacho
    # Verificar DescargaQuimicoOP.estado = 'revertida'
    # Verificar stock químico restaurado

# Caso 4: Pedidos vuelven a estado pendiente
def test_revertir_despacho_restaura_estado_pedido()
    # Crear despacho → PedidoVenta.estado = 'despachado'
    # Revertir
    # Verificar PedidoVenta.estado = 'pendiente'
```

---

## Comandos para Ejecutar

### Backend

```bash
# Aplicar migraciones (si hay cambios a modelos)
python manage.py migrate inventory

# Ejecutar tests de reversión (cuando se creen)
python manage.py test inventory.tests.test_despacho_reversion -v 2

# Verificar endpoint en shell
python manage.py shell
> from inventory.models import HistorialDespacho
> despacho = HistorialDespacho.objects.first()
> # Verificar que se puede acceder a /historial-despachos/{id}/revertir/
```

### Frontend

```bash
# El componente HistorialDespachos.tsx se actualiza automáticamente
# Se renderiza modal de reversión al hacer clic en botón 🔄

# Tests TypeScript (si aplica)
npm run test -- HistorialDespachos
```

---

## Verificación Funcional

✅ **Reversión de despacho con justificación obligatoria**  
✅ **Restauración automática de stock en bodegas**  
✅ **Reversión de DescargaQuimicoOP asociadas**  
✅ **Creación de MovimientoInventario DEVOLUCION**  
✅ **Pedidos revertidos a estado pendiente**  
✅ **Auditoría completa (usuario, fecha, justificación)**  
✅ **Integridad transaccional (@transaction.atomic)**  
✅ **Interface amigable con modal de confirmación**  
✅ **Permiso IsDespachoWriter en acciones de reversión**  

---

## Extensiones Futuras

1. **Reversión Parcial:** Revertir solo algunos lotes del despacho
2. **Notificaciones:** Alertar al cliente si su despacho fue revertido
3. **Reportes de Reversión:** Dashboard con tendencias de reversiones
4. **Auto-reversión:** Revertir automáticamente si se detectan errores (ej: peso inconsistente)
5. **Sincronización con TMS:** Notificar transportista si despacho es revertido

---

## Referencias

- **Plan maestro:** `/home/Adminbrandon/.claude/plans/cheerful-wiggling-blum.md`
- **Servicio de Descarga Química:** `gestion/services/descarga_quimicos.py`
- **Service Layer existente:** `inventory/services/`
- **Modelo HistorialDespacho:** `inventory/models.py`
- **Thread-safe utility:** `inventory/utils.py::safe_get_or_create_stock`

---

**Fin de Documentación**
