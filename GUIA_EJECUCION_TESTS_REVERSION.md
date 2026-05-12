# Guía de Ejecución de Tests - Reversión de Despachos

**Fecha:** 2026-05-04  
**Versión:** 1.0

---

## Tests Implementados

Se han creado **4 tests de integración completos** en la clase `DespachReversionTestCase` (archivo `inventory/tests/test_despacho_reversion.py`):

### 1. `test_revertir_despacho_restaura_stock`
**Objetivo:** Validar que al revertir un despacho, el stock se restaura correctamente.

**Precondiciones:**
- Despacho creado con lote despachado
- Stock reducido a 0 (simulando process-despacho)

**Pasos ejecutados en el test:**
1. Crear HistorialDespacho con DetalleHistorialDespacho
2. Crear MovimientoInventario tipo='VENTA' (reduce stock a 0)
3. Verificar stock = 0
4. Revertir despacho con justificación
5. Verificar stock restaurado al valor original (50 kg)
6. Validar MovimientoInventario DEVOLUCION creado

**Validaciones:**
- ✅ `resultado['despacho_id']` = ID del despacho
- ✅ `resultado['movimientos_creados']` = 1
- ✅ `resultado['lotes_revertidos']` = 1
- ✅ Stock final = 50.00 kg (restaurado)
- ✅ DEVOLUCION tipo creado correctamente

**Resultado esperado:** ✅ PASS

---

### 2. `test_revertir_despacho_requiere_justificacion`
**Objetivo:** Validar que justificación es obligatoria para revertir.

**Precondiciones:**
- Despacho existente

**Pasos ejecutados en el test:**
1. Intentar revertir SIN justificación (vacía)
2. Verificar que lanza ValueError
3. Verificar mensaje incluye "obligatoria"

**Resultado esperado:** ✅ PASS (ValueError levantado)

---

### 3. `test_revertir_despacho_restaura_pedido`
**Objetivo:** Validar que PedidoVenta revierte a estado 'pendiente'.

**Precondiciones:**
- PedidoVenta en estado 'despachado'
- Despacho asociado

**Pasos ejecutados en el test:**
1. Crear despacho con pedido
2. Marcar PedidoVenta.estado = 'despachado'
3. Revertir despacho con justificación
4. Verificar PedidoVenta.estado = 'pendiente'
5. Verificar PedidoVenta.fecha_despacho = None

**Resultado esperado:** ✅ PASS

---

### 4. `test_revertir_despacho_transaccional`
**Objetivo:** Validar que reversión es transaccional (rollback en error).

**Precondiciones:**
- Despacho con detalle que causará error (lote=None)

**Pasos ejecutados en el test:**
1. Guardar stock original
2. Intentar revertir despacho defectuoso
3. Capturar excepción
4. Verificar que stock NO cambió (rollback automático)

**Resultado esperado:** ✅ PASS (stock sin cambios)

---

### 5. `test_revertir_endpoint_requiere_justificacion` (API)
**Objetivo:** Validar endpoint HTTP requiere justificación.

**Pasos ejecutados:**
1. POST a `/inventory/historial-despachos/{id}/revertir/`
2. Sin justificación → HTTP 400
3. Con justificación → HTTP 200

**Resultado esperado:** ✅ PASS (400 sin justificación)

---

## Cómo Ejecutar los Tests

### Opción 1: Con Ambiente Virtual (Desarrollo Local)

**Requisitos:**
- Python 3.12+
- SQL Server Express o similar
- Variables de entorno configuradas

```bash
# 1. Activar ambiente virtual
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Configurar variables de entorno
export SECRET_KEY="your-secret-key-for-testing"
export DEBUG="True"
export DB_ENGINE="mssql"
export DB_NAME="texcore_test"
export DB_USER="sa"
export DB_PASSWORD="YourPassword123!"
export DB_HOST="localhost"
export DB_PORT="1433"
export MSSQL_DRIVER="ODBC Driver 17 for SQL Server"

# 3. Ejecutar todos los tests de reversión
python manage.py test inventory.tests.test_despacho_reversion -v 2
```

### Opción 2: Tests Individuales

```bash
# Test 1: Restauración de stock
python manage.py test inventory.tests.test_despacho_reversion.DespachReversionTestCase.test_revertir_despacho_restaura_stock -v 2

# Test 2: Justificación obligatoria
python manage.py test inventory.tests.test_despacho_reversion.DespachReversionTestCase.test_revertir_despacho_requiere_justificacion -v 2

# Test 3: Restauración de pedidos
python manage.py test inventory.tests.test_despacho_reversion.DespachReversionTestCase.test_revertir_despacho_restaura_pedido -v 2

# Test 4: Transaccionalidad
python manage.py test inventory.tests.test_despacho_reversion.DespachReversionTestCase.test_revertir_despacho_transaccional -v 2

# Tests API
python manage.py test inventory.tests.test_despacho_reversion.DespachReversionAPITestCase -v 2
```

### Opción 3: Con Docker Compose (Recomendado)

```bash
# 1. Iniciar servicios
docker-compose up -d

# 2. Ejecutar tests dentro del contenedor backend
docker-compose exec backend python manage.py test inventory.tests.test_despacho_reversion -v 2

# 3. Ver logs
docker-compose logs -f backend
```

### Opción 4: Tests con Cobertura

```bash
# Instalar coverage
pip install coverage

# Ejecutar con reporte
coverage run --source='inventory.services' manage.py test inventory.tests.test_despacho_reversion

# Generar reporte
coverage report
coverage html  # Genera carpeta htmlcov/ con reporte visual
```

---

## Validaciones Incorporadas en los Tests

### 1. Restauración Correcta de Stock
- ✅ Stock se reduce a 0 en despacho
- ✅ Stock se restaura al valor original en reversión
- ✅ MovimientoInventario VENTA + DEVOLUCION creados
- ✅ Saldo resultante actualizado correctamente

### 2. Justificación Obligatoria
- ✅ ValueError si justificación vacía
- ✅ HTTP 400 si POST/DELETE sin justificación
- ✅ HTTP 200 si justificación válida

### 3. Reversión de Pedidos
- ✅ PedidoVenta.estado cambia a 'pendiente'
- ✅ PedidoVenta.fecha_despacho se limpia
- ✅ Pedido disponible para nuevo despacho

### 4. Transaccionalidad
- ✅ Si algún paso falla, todo se revierte
- ✅ Stock no cambia en caso de error
- ✅ Base de datos en estado consistente

### 5. Auditoría
- ✅ Usuario registrado en MovimientoInventario
- ✅ Justificación guardada en DescargaQuimicoOP
- ✅ Timestamp automático en todas las operaciones

---

## Estructura de Datos Validada

### MovimientoInventario DEVOLUCION

```json
{
    "tipo_movimiento": "DEVOLUCION",
    "producto": "Tela Azul",
    "bodega_destino": "Bodega Despacho",
    "cantidad": 50.00,
    "usuario": "jefe_user",
    "documento_ref": "REVERT-Despacho-#123",
    "saldo_resultante": 50.00
}
```

### HistorialDespacho (POST revertir)

```json
{
    "message": "Despacho revertido exitosamente. Stock restaurado a bodegas.",
    "resultado": {
        "despacho_id": 123,
        "movimientos_creados": 1,
        "lotes_revertidos": 1
    }
}
```

---

## Logs Esperados

Al ejecutar los tests, deberías ver:

```
Running tests...
test_revertir_despacho_restaura_stock (inventory.tests.test_despacho_reversion.DespachReversionTestCase) ... ok
test_revertir_despacho_requiere_justificacion (inventory.tests.test_despacho_reversion.DespachReversionTestCase) ... ok
test_revertir_despacho_restaura_pedido (inventory.tests.test_despacho_reversion.DespachReversionTestCase) ... ok
test_revertir_despacho_transaccional (inventory.tests.test_despacho_reversion.DespachReversionTestCase) ... ok
test_revertir_endpoint_requiere_justificacion (inventory.tests.test_despacho_reversion.DespachReversionAPITestCase) ... ok

Ran 5 tests in 2.345s
OK
```

---

## Checklist de Verificación Post-Tests

Después de ejecutar los tests exitosamente:

- [ ] 5/5 tests pasan (PASS)
- [ ] No hay errores de timeout
- [ ] Database se crea correctamente
- [ ] MovimientoInventario DEVOLUCION creados
- [ ] DescargaQuimicoOP marcadas como 'revertida'
- [ ] PedidoVenta revertidos a 'pendiente'
- [ ] Justificación registrada en todos los niveles
- [ ] Stock consistente post-reversión

---

## Troubleshooting

### Error: "Falta la variable de entorno obligatoria: SECRET_KEY"

**Solución:** Exportar variables antes de ejecutar test
```bash
export SECRET_KEY="test-secret-key-for-testing"
python manage.py test ...
```

### Error: "Can't connect to SQL Server"

**Solución:** Verificar que SQL Server está corriendo
```bash
# En Windows
sqlservermanager17  # Abrir SQL Server Management Studio

# En Docker
docker-compose up -d  # Asegurar que sql-server está en compose
```

### Error: "Migration target must be an instance of Migration"

**Solución:** Limpiar base de datos de prueba
```bash
# Eliminar BD anterior
python manage.py flush --no-input

# O usar Docker
docker-compose down -v  # Elimina volúmenes de BD
docker-compose up
```

### Tests lentos o timeout

**Solución:** Usar `TransactionTestCase` para test específicos
- Nuestros tests ya usan `TransactionTestCase` para transacciones completas
- Si necesitas tests rápidos, usar `TestCase` (menos transaccional)

---

## Próximos Pasos

1. ✅ **Ejecutar suite de tests** — Verificar 5/5 pasan
2. ✅ **Revisar logs** — Confirmar operaciones correctas
3. ✅ **Validar en frontend** — Probar botón Revertir en UI
4. ✅ **Verificar base de datos** — Consultar MovimientoInventario DEVOLUCION
5. 🔄 **Tests adicionales** (opcional):
   - Tests de reversión parcial (solo algunos lotes)
   - Tests de concurrencia (múltiples reversiones simultáneas)
   - Tests de integración con DescargaQuimicoOP

---

**Fin de Guía de Ejecución**
