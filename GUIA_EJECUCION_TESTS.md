# Guía de Ejecución de Tests - Descarga Automática de Químicos

**Fecha:** 2026-05-04  
**Versión:** 1.0

---

## Tests Implementados

Se han creado **5 tests de integración completos** en la clase `DescargaQuimicosOPTestCase` (archivo `gestion/tests_integrados.py`):

### 1. `test_crear_op_descarga_automatica`
**Objetivo:** Validar que al crear una OP con fórmula y bodega_quimicos, se descuenten automáticamente los químicos.

**Precondiciones:**
- OP con código, producto, fórmula aprobada
- Bodega de químicos con stock inicial (100 kg soda, 50 kg tinte)

**Pasos ejecutados en el test:**
1. Crear OP con peso_neto_requerido = 100 kg
2. Verificar que `inventario_descontado = True`
3. Verificar que se crearon 2 `DescargaQuimicoOP` (soda + tinte)
4. Validar cálculos:
   - **Soda (gr/L):** volumen = 100 kg × 10 = 1000 L → cantidad = 1000 L × 10 gr/L = 10 kg ✓
   - **Tinte (%):** cantidad = 100 kg × 2% = 2 kg ✓
5. Verificar que stock fue descontado (100-10=90 soda, 50-2=48 tinte)
6. Verificar que se crearon 2 `MovimientoInventario` tipo='CONSUMO'

**Resultado esperado:** ✅ PASS

---

### 2. `test_modificar_op_ajusta_descarga`
**Objetivo:** Validar que modificar OP (peso/fórmula) requiere justificación y ajusta la descarga automáticamente.

**Precondiciones:**
- OP existente con descarga ya realizada
- Stock de químicos descontado

**Pasos ejecutados en el test:**
1. Intentar modificar OP SIN justificación → HTTP 400 (validación)
2. Modificar OP CON justificación = "Error en cálculo de peso, se corrige a 150 kg"
3. Verificar que `peso_neto_requerido` cambió a 150 kg
4. Validar que descarga se ajustó:
   - Descarga vieja (100 kg): soda 10 kg, tinte 2 kg → **revertida**
   - Descarga nueva (150 kg): soda 15 kg, tinte 3 kg → **aplicada**
   - Neto: stock descuento adicional (soda -5 kg, tinte -1 kg)
5. Verificar que existen 2 descargas 'revertida' y 2 'aplicada'
6. Verificar que stock final = (100-15) soda, (50-3) tinte

**Resultado esperado:** ✅ PASS

---

### 3. `test_eliminar_op_requiere_justificacion`
**Objetivo:** Validar que eliminar OP requiere justificación y revierte la descarga.

**Precondiciones:**
- OP existente con descarga ya realizada
- Stock de químicos descontado

**Pasos ejecutados en el test:**
1. Intentar eliminar OP SIN justificación → HTTP 400 (validación)
2. Eliminar OP CON justificación = "OP errónea"
3. Verificar que OP fue eliminada (OrdenProduccion.DoesNotExist)
4. Verificar que stock fue revertido (100 kg soda, 50 kg tinte - valores iniciales)
5. Verificar que se creó `MovimientoInventario` tipo='DEVOLUCION'

**Resultado esperado:** ✅ PASS

---

### 4. `test_stock_quimicos_endpoint_con_alertas`
**Objetivo:** Validar endpoint GET `/stock-quimicos/` retorna lista con alertas visuales.

**Precondiciones:**
- Soda: 100 kg (mínimo 5 kg) → sin alerta
- Tinte: 1.50 kg (mínimo 2 kg) → CON alerta

**Pasos ejecutados en el test:**
1. Bajar stock de tinte a 1.50 kg (por debajo del mínimo)
2. Consultar GET `/ordenes-produccion/stock-quimicos/?sede_id=<id>` como tintorero
3. Verificar HTTP 200
4. Validar respuesta contiene 2 químicos
5. Verificar que soda tiene `alerta=False`
6. Verificar que tinte tiene `alerta=True`

**Resultado esperado:** ✅ PASS

---

### 5. `test_auditoria_descarga_quimicos`
**Objetivo:** Validar que se registra auditoría completa (usuario, fecha, justificación).

**Precondiciones:**
- OP creada con descarga

**Pasos ejecutados en el test:**
1. Crear OP y verificar que `DescargaQuimicoOP.descargado_por = jefe_planta` ✓
2. Verificar que `fecha_descarga` no es null ✓
3. Modificar OP y verificar que descarga revertida registra `justificacion = "Ajuste por error de pesaje"` ✓

**Resultado esperado:** ✅ PASS

---

## Cómo Ejecutar los Tests

### Opción 1: Con Docker (Recomendado)

Si tienes Docker Compose con SQL Server:

```bash
# Desde el directorio raíz del proyecto
docker-compose up -d

# Ejecutar tests
cd /path/to/gestion
python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase -v 2
```

### Opción 2: Con SQL Express Local

**Requisitos:**
- SQL Server Express instalado en `localhost:1433`
- Driver ODBC configurado (ej: ODBC Driver 17 for SQL Server)
- Credenciales: `sa` / contraseña

```bash
export SECRET_KEY="test-secret-key"
export DEBUG="True"
export CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:5173"
export CSRF_TRUSTED_ORIGINS="http://localhost:3000,http://localhost:5173"
export DB_ENGINE="mssql"
export DB_NAME="test_texcore"
export DB_USER="sa"
export DB_PASSWORD="YourPassword123!"
export DB_HOST="localhost"
export DB_PORT="1433"
export MSSQL_DRIVER="ODBC Driver 17 for SQL Server"

python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase -v 2
```

### Opción 3: Ejecutar Tests Individuales

```bash
# Test 1: Crear OP con descarga automática
python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase.test_crear_op_descarga_automatica -v 2

# Test 2: Modificar OP ajusta descarga
python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase.test_modificar_op_ajusta_descarga -v 2

# Test 3: Eliminar OP requiere justificación
python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase.test_eliminar_op_requiere_justificacion -v 2

# Test 4: Stock de químicos endpoint
python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase.test_stock_quimicos_endpoint_con_alertas -v 2

# Test 5: Auditoría
python manage.py test gestion.tests_integrados.DescargaQuimicosOPTestCase.test_auditoria_descarga_quimicos -v 2
```

---

## Validaciones Incorporadas en los Tests

### 1. Cálculos de Dosificación
- ✅ Fórmula gr/L (gramos por litro de baño)
- ✅ Fórmula % (porcentaje sobre peso de tela)
- ✅ Relación de baño (volumen = peso × relación)

### 2. Lógica de Descarga
- ✅ Creación automática al crear OP
- ✅ Ajuste (reversión + nueva) al modificar
- ✅ Reversión al eliminar

### 3. Validaciones
- ✅ Justificación obligatoria al modificar/eliminar OP con descarga
- ✅ HTTP 400 si falta justificación
- ✅ HTTP 200 si todo es correcto

### 4. Auditoría
- ✅ Registro de usuario (descargado_por)
- ✅ Registro de fecha (fecha_descarga)
- ✅ Registro de justificación (para reversiones)
- ✅ Movimientos de inventario (CONSUMO/DEVOLUCION)

### 5. Stock y Alertas
- ✅ Descuento correcto del stock
- ✅ Bandera `alerta=True` si cantidad < stock_minimo
- ✅ Endpoint `/stock-quimicos/` accesible solo para tintorero

---

## Estructura de Datos Validada

### DescargaQuimicoOP
```python
{
    "id": int,
    "orden_produccion": OrdenProduccion,
    "producto": Producto (químico),
    "fase": FaseReceta,
    "bodega": Bodega,
    "tipo_calculo": "gr_l" | "pct",
    "cantidad_calculada_kg": Decimal(6 decimales),
    "cantidad_real_kg": None (hasta ejecución),
    "estado": "aplicada" | "revertida",
    "fecha_descarga": datetime (auto_now_add),
    "descargado_por": CustomUser,
    "justificacion": str (nullable, para reversiones)
}
```

### MovimientoInventario
```python
{
    "tipo_movimiento": "CONSUMO" | "DEVOLUCION",
    "producto": Producto,
    "bodega_origen": Bodega (CONSUMO) | None,
    "bodega_destino": None | Bodega (DEVOLUCION),
    "cantidad": Decimal,
    "usuario": CustomUser,
    "documento_ref": f"OP-{codigo}" | f"REVERT-OP-{codigo}",
    "saldo_resultante": Decimal (stock después de movimiento)
}
```

---

## Logs Esperados

Al ejecutar los tests, deberías ver en los logs:

```
[ALERTA STOCK] Soda Cáustica en bodega 'Bodega Tintorería': 85.00kg (mín: 5.00kg)
[ALERTA STOCK] Tinte Reactivo Azul en bodega 'Bodega Tintorería': 47.00kg (mín: 2.00kg)
...
Descarga exitosa OP-AZUL-001: 2 químicos descargados
Reversión exitosa OP-MOD-001: 2 químicos revertidos
Ajuste exitoso OP-MOD-001: reversión + nueva descarga
```

---

## Checklist de Verificación Post-Tests

Después de ejecutar los tests exitosamente:

- [ ] 5/5 tests pasan (PASS)
- [ ] No hay errores de indentación
- [ ] `DescargaQuimicoOP` tiene registros en DB
- [ ] `MovimientoInventario` tipo CONSUMO/DEVOLUCION creados
- [ ] Stock de químicos decrementado correctamente
- [ ] Endpoint `/stock-quimicos/` retorna datos con alertas
- [ ] Auditoría registra usuario y justificación
- [ ] Logs muestran alertas de stock bajo

---

## Troubleshooting

### Error: "TypeError: expected string or bytes-like object, got 'NoneType'"
**Causa:** Variable de entorno `MSSQL_DRIVER` no configurada  
**Solución:** Instalar `ODBC Driver 17 for SQL Server` o configurar variable de entorno

### Error: "Can't connect to SQL Server"
**Causa:** SQL Server no está corriendo  
**Solución:** Iniciar SQL Server o usar Docker Compose

### Error: "Falta la variable de entorno obligatoria: SECRET_KEY"
**Causa:** Variables de entorno no exportadas  
**Solución:** Usar script con `export` o archivo `.env`

---

## Próximos Pasos

1. **Ejecutar los tests** en tu ambiente de SQL Server
2. **Validar que los 5 tests pasen**
3. **Revisar los logs** para verificar alertas
4. **Consultar la BD** para ver registros de `DescargaQuimicoOP` y `MovimientoInventario`
5. **Probar el endpoint** `/stock-quimicos/` manualmente vía Postman o curl

---

**Fin de Guía**
