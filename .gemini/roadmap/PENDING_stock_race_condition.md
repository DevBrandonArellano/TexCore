# Problema Pendiente: Race Condition en StockBodega con get_or_create

## Fecha: 2026-02-12
## Prioridad: Media
## Componente: Inventory / Stock Management

### Descripción del Problema

Existe una condición de carrera (race condition) en Django cuando se usa `get_or_create()` con SQL Server en transacciones atómicas, específicamente para registros de `StockBodega` donde `lote=NULL`.

### Síntomas

- `IntegrityError` al intentar crear registros duplicados de `StockBodega` con `(bodega_id, producto_id, lote_id=NULL)`
- El error ocurre incluso con:
  - Función helper con retry logic
  - Savepoints para aislar errores
  - Raw SQL MERGE statements
  - Unique constraints correctamente configurados

### Contexto Técnico

1. **Base de datos**: SQL Server trata NULL de manera especial en unique constraints
2. **Migración creada**: `inventory/migrations/0003_fix_unique_constraint_with_null.py`
   - Crea índices únicos filtrados para manejar NULL correctamente
   - `inventory_stockbodega_unique_without_lote`: Para registros con `lote_id IS NULL`
   - `inventory_stockbodega_unique_with_lote`: Para registros con `lote_id IS NOT NULL`

3. **Tests afectados**:
   - `gestion.tests_integrados.UnifiedBusinessLogicTestCase.test_rechazo_lote_reversion`
   - `gestion.tests_integrados.UnifiedBusinessLogicTestCase.test_precision_stock_update`

### Trabajo Realizado

1. ✅ Reinicio de base de datos de desarrollo (historial de migraciones corrupto)
2. ✅ Creación de unique constraints con manejo de NULL
3. ✅ Actualización de tests para filtrar por `lote=None`
4. ✅ Función helper `safe_get_or_create_stock()` con retry logic y savepoints
5. ✅ Eliminación de try-except que ocultaba errores en `LoteProduccionViewSet.rechazar`
6. ✅ **Estabilización Mayo 2026**: Verificación de la solución en la suite de 64 tests integrados pasando al 100% en SQL Server.

### Estado Actual (Mayo 2026)

El problema se considera **Mitigado y Estable**. La función `safe_get_or_create_stock()` junto con las correcciones de precisión decimal (`quantize`) en los servicios de descarga han eliminado los fallos en los tests y errores de integridad en SQL Server.

### Soluciones Propuestas (Largo Plazo)

#### Opción 1: Cambiar Diseño del Modelo (Sigue en pie)
- Eliminar uso de `lote=NULL`
- Usar un valor centinela (ej: `lote_id=-1` o crear un registro "STOCK_GENERICO")
- Ventajas: Evita problemas con NULL en unique constraints
- Desventajas: Requiere migración de datos y cambios en lógica de negocio

#### Opción 2: Usar Locking Explícito
- Implementar locking a nivel de aplicación antes de `get_or_create`
- Usar `select_for_update()` de manera más agresiva
- Ventajas: No requiere cambios en modelo
- Desventajas: Puede afectar performance

#### Opción 3: Raw SQL para Todas las Operaciones
- Reemplazar `get_or_create` con stored procedures o MERGE statements
- Ventajas: Control total sobre SQL
- Desventajas: Pierde portabilidad de Django ORM

### Próximos Pasos

1. Monitorear logs de producción en busca de `IntegrityError` residuales bajo carga real.
2. Evaluar la migración a la **Opción 1** si se decide realizar un refactor mayor del módulo de inventario.
3. Investigar si Django 5.x ofrece mejoras nativas para índices filtrados con NULL en MSSQL.

### Referencias

- Django Issue: https://code.djangoproject.com/ticket/13906
- SQL Server NULL behavior: https://docs.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql#filtered-indexes
- CHANGELOG.md (Mayo 2026): Estabilización de Suite de Integración.

### Notas Adicionales

Este problema NO afecta la funcionalidad en producción si:
- No hay concurrencia alta en creación de stock
- Los usuarios no ejecutan operaciones simultáneas sobre el mismo producto/bodega

El problema es más evidente en tests debido a la velocidad de ejecución y el uso de transacciones de test.
