# Documentación: Relaciones y Eliminación de Registros en Base de Datos

Este documento describe las dependencias entre las distintas entidades del sistema TexCore y proporciona los scripts SQL necesarios para eliminar de manera segura y forzada registros directamente desde el motor de base de datos SQL Server, gestionando las restricciones de integridad referencial (Foreign Keys).

## 1. Entendiendo las Relaciones (Padres e Hijos)

El ORM de Django define cómo se comportan las claves foráneas al eliminar un padre:
- **CASCADE**: Si se borra el padre, automáticamente se borran los registros hijos.
- **SETT_NULL**: Si se borra el padre, el campo en el hijo se actualiza a `NULL` (no borra al hijo).
- **PROTECT**: La base de datos impide borrar al padre si existen hijos asociados. Se deben borrar o reasignar los hijos primero.

### Resumen de Relaciones

| Entidad Padre | Entidades Hijas (CASCADE) | Entidades Hijas (SET_NULL) | Entidades Hijas (PROTECT / Restrictivo) |
| --- | --- | --- | --- |
| **Sede** | Area, Bodega | CustomUser, PagoCliente, PedidoVenta, OrdenProduccion | Ninguno |
| **Area** | Ninguna | CustomUser, Maquina | **OrdenProduccion** (Impide el borrado) |
| **Bodega** | StockBodega | Usuarios Asignados (M2M) | **OrdenProduccion**, **MovimientoInventario** (Impide el borrado) |
| **Usuario** (`CustomUser`) | auth_user_groups, permisos | Cliente, LoteProduccion, OrdenProduccion, Movimientoinventario, Pedidos | Ninguno |
| **Producto** | Batch, DetalleFormula, DetallePedido, StockBodega | OrdenProduccion | **MovimientoInventario** (Impide el borrado) |
| **Formula de Color** | DetalleFormula | OrdenProduccion (SET_NULL u opcional a veces es CASCADE según Django pero en SQL es directo) | Ninguno |
| **Proveedor** | Ninguna | MovimientoInventario | Ninguno |
| **Cliente** | PagoCliente, PedidoVenta | Ninguna | Ninguno |

---

## 2. Scripts SQL de Eliminación Directa

Si se requiere eliminar información directamente en SQL Server mediante `sqlcmd` o SQL Server Management Studio (SSMS), es obligatorio limpiar las tablas interrelacionadas o utilizar los scripts en orden. A continuación, los scripts seguros para cada entidad.

### A. Eliminar un Usuario (CustomUser)
El usuario es referenciado en múltiples transacciones. Si el usuario ya tiene movimientos o producción asociada, al eliminarlo esas referencias quedarán en `NULL`. Las relaciones "Muchos a Muchos" deben borrarse primero.

```sql
DECLARE @UsuarioID INT = 1; -- Cambiar por el ID del usuario a eliminar

BEGIN TRAN;
    -- 1. Eliminar relaciones N:M
    DELETE FROM gestion_customuser_groups WHERE customuser_id = @UsuarioID;
    DELETE FROM gestion_customuser_user_permissions WHERE customuser_id = @UsuarioID;
    DELETE FROM gestion_customuser_bodegas_asignadas WHERE customuser_id = @UsuarioID;
    DELETE FROM gestion_customuser_superior WHERE from_customuser_id = @UsuarioID OR to_customuser_id = @UsuarioID;
    DELETE FROM gestion_maquina_operarios WHERE customuser_id = @UsuarioID;

    -- 2. Poner en NULL relaciones SET_NULL (SQL Server no siempre lo hace automático si no se configuró así)
    UPDATE gestion_cliente SET vendedor_asignado_id = NULL WHERE vendedor_asignado_id = @UsuarioID;
    UPDATE gestion_loteproduccion SET operario_id = NULL WHERE operario_id = @UsuarioID;
    UPDATE gestion_ordenproduccion SET operario_asignado_id = NULL WHERE operario_asignado_id = @UsuarioID;
    UPDATE gestion_pedidoventa SET vendedor_asignado_id = NULL WHERE vendedor_asignado_id = @UsuarioID;
    UPDATE inventory_movimientoinventario SET usuario_id = NULL WHERE usuario_id = @UsuarioID;
    UPDATE inventory_auditoriamovimiento SET usuario_modificador_id = NULL WHERE usuario_modificador_id = @UsuarioID;
    UPDATE inventory_historialdespacho SET usuario_id = NULL WHERE usuario_id = @UsuarioID;

    -- 3. Finalmente borrar al usuario
    DELETE FROM gestion_customuser WHERE id = @UsuarioID;
COMMIT TRAN;
```

---

### B. Eliminar un Producto
Un producto es altamente crítico. Tiene protección estricta (`PROTECT`) en los movimientos de inventario (`inventory_movimientoinventario`). Esto significa que **no puedes eliminar un producto si ya tiene movimientos de kardex asociados**. Tendrías que borrar primero esos movimientos, lo cual afecta el historial financiero.

*Si estás seguro de querer forzar su borrado completo (incluyendo su historial logístico e inventario):*

```sql
DECLARE @ProductoID INT = 1; -- Cambiar por el ID del producto

BEGIN TRAN;
    -- 1. Eliminar referencias CASCADE
    DELETE FROM gestion_batch WHERE producto_id = @ProductoID;
    DELETE FROM gestion_detalleformula WHERE producto_id = @ProductoID;
    DELETE FROM gestion_detallepedido WHERE producto_id = @ProductoID;
    DELETE FROM inventory_stockbodega WHERE producto_id = @ProductoID;
    DELETE FROM inventory_detallehistorialdespacho WHERE producto_id = @ProductoID;
    
    -- 2. Eliminar referencias PROTECT (Movimientos)
    -- ADVERTENCIA: Esto borra el rastro de auditoría del inventario
    DELETE FROM inventory_auditoriamovimiento 
           WHERE movimiento_id IN (SELECT id FROM inventory_movimientoinventario WHERE producto_id = @ProductoID);
    DELETE FROM inventory_movimientoinventario WHERE producto_id = @ProductoID;

    -- 3. SET_NULL
    UPDATE gestion_ordenproduccion SET producto_id = NULL WHERE producto_id = @ProductoID;

    -- 4. Borrar el producto
    DELETE FROM gestion_producto WHERE id = @ProductoID;
COMMIT TRAN;
```

---

### C. Eliminar una Fórmula de Color
Las fórmulas de color están atadas a `DetalleFormula` (los ingredientes) y a las órdenes de producción.

```sql
DECLARE @FormulaID INT = 1; -- Cambiar por el ID de la fórmula

BEGIN TRAN;
    -- 1. Borrar registros hijos en cascada
    DELETE FROM gestion_detalleformula WHERE formula_color_id = @FormulaID;
    
    -- 2. Quitar la referencia en las órdenes de producción (Evitar romper el historial de producción)
    UPDATE gestion_ordenproduccion SET formula_color_id = NULL WHERE formula_color_id = @FormulaID;

    -- 3. Borrar la fórmula
    DELETE FROM gestion_formulacolor WHERE id = @FormulaID;
COMMIT TRAN;
```

---

### D. Eliminar una Bodega
Las bodegas están protegidas (`PROTECT`) por Movimientos de Inventario y Órdenes de Producción. Si una bodega ya fue usada operativamente, borrarla implicaría destruir los registros relacionados o reasignarlos.

```sql
DECLARE @BodegaID INT = 1; -- Cambiar por el ID de la bodega
DECLARE @BodegaReemplazoID INT = 2; -- Si deseas reasignar movimientos en vez de borrarlos

BEGIN TRAN;
    -- Opción A: Reasignar los registros conflictivos (RECOMENDADO PARA DBs EN PRODUCCIÓN)
    UPDATE gestion_ordenproduccion SET bodega_id = @BodegaReemplazoID WHERE bodega_id = @BodegaID;
    UPDATE inventory_movimientoinventario SET bodega_origen_id = @BodegaReemplazoID WHERE bodega_origen_id = @BodegaID;
    UPDATE inventory_movimientoinventario SET bodega_destino_id = @BodegaReemplazoID WHERE bodega_destino_id = @BodegaID;

    -- 1. Eliminar relaciones M:M
    DELETE FROM gestion_customuser_bodegas_asignadas WHERE bodega_id = @BodegaID;

    -- 2. Eliminar hijos CASCADE
    DELETE FROM inventory_stockbodega WHERE bodega_id = @BodegaID;

    -- 3. Borrar bodega
    DELETE FROM gestion_bodega WHERE id = @BodegaID;
COMMIT TRAN;
```

---

### E. Eliminar un Área
El modelo de Área no tiene tantas restricciones, excepto en la tabla de Órdenes de Producción donde es `PROTECT`. 

```sql
DECLARE @AreaID INT = 1; -- ID de Área a borrar
DECLARE @AreaReemplazoID INT = 2; -- Opcional, para reasignar OP si quieres preservar data

BEGIN TRAN;
    -- 1. Reasignar o borrar registros protegidos (Órdenes de Producción)
    UPDATE gestion_ordenproduccion SET area_id = @AreaReemplazoID WHERE area_id = @AreaID;
    -- Opcional: DELETE FROM gestion_ordenproduccion WHERE area_id = @AreaID; -- (CUIDADO: Esto requerirá borrar Lotes hijos primero)

    -- 2. Hacer NULL las relaciones indirectas
    UPDATE gestion_customuser SET area_id = NULL WHERE area_id = @AreaID;
    UPDATE gestion_maquina SET area_id = NULL WHERE area_id = @AreaID;

    -- 3. Borrar Área
    DELETE FROM gestion_area WHERE id = @AreaID;
COMMIT TRAN;
```

---

### F. Consideraciones de Seguridad
1. **Nunca correr estos scripts en producción sin realizar un backup primero.**
2. En SQL Server, si una instrucción `DELETE` falla por violación de clave foránea (`FK Constraint`), el bloque completo se debe manejar con `ROLLBACK TRAN` (aunque el ejemplo utiliza `COMMIT TRAN`, asegúrate de verificar errores en la consola).
3. **Alternativa al borrado:** En muchos de estos módulos (como Máquinas, Sedes, Usuarios) la buena práctica es introducir un campo `estado = 'inactivo'` (Soft Delete) en lugar del `DELETE` puro (Hard Delete) para mantener inalterado el historial financiero e inventario.
