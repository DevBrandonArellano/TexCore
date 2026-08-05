-- =============================================================================
-- TEXCORE DATABASE OPTIMIZATION SCRIPT - SQL SERVER 2022
-- Sistema de Control de Producción Textil (Ecosistema Híbrido: Django + SQLAlchemy)
-- Autor: Principal Database Architect & SQL Server 2022 Expert
-- =============================================================================

USE [texcore_db];
GO

-- -----------------------------------------------------------------------------
-- 1. CONFIGURACIONES DE BASE DE DATOS Y CONCURRENCIA (RCSI)
-- -----------------------------------------------------------------------------
-- Habilitar Read Committed Snapshot Isolation (RCSI) para eliminar bloqueos entre lecturas y escrituras
IF EXISTS (SELECT 1 FROM sys.databases WHERE name = 'texcore_db' AND is_read_committed_snapshot_on = 0)
BEGIN
    PRINT 'Habilitando Read Committed Snapshot Isolation (RCSI)...';
    ALTER DATABASE [texcore_db] SET READ_COMMITTED_SNAPSHOT ON WITH ROLLBACK IMMEDIATE;
END
GO

ALTER DATABASE [texcore_db] SET ALLOW_SNAPSHOT_ISOLATION ON;
GO

-- -----------------------------------------------------------------------------
-- 2. REGLAS DE NEGOCIO TEXTIL (CHECK CONSTRAINTS EN SQL SERVER)
-- -----------------------------------------------------------------------------

-- A. Validar equivalencias de empaquetado textil en LoteProduccion (1 baño = 15 fundas = 225 conos)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_lote_empaque_bano_225')
BEGIN
    ALTER TABLE [dbo].[gestion_loteproduccion] WITH CHECK
    ADD CONSTRAINT [CK_lote_empaque_bano_225]
    CHECK ([presentacion] IS NULL OR LOWER([presentacion]) <> 'baño' OR [unidades_empaque] = 225);
    PRINT 'Constraint CK_lote_empaque_bano_225 creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_lote_empaque_funda_15')
BEGIN
    ALTER TABLE [dbo].[gestion_loteproduccion] WITH CHECK
    ADD CONSTRAINT [CK_lote_empaque_funda_15]
    CHECK ([presentacion] IS NULL OR LOWER([presentacion]) <> 'funda' OR [unidades_empaque] = 15);
    PRINT 'Constraint CK_lote_empaque_funda_15 creado.';
END
GO

IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_lote_empaque_cono_1')
BEGIN
    ALTER TABLE [dbo].[gestion_loteproduccion] WITH CHECK
    ADD CONSTRAINT [CK_lote_empaque_cono_1]
    CHECK ([presentacion] IS NULL OR LOWER([presentacion]) <> 'cono' OR [unidades_empaque] = 1);
    PRINT 'Constraint CK_lote_empaque_cono_1 creado.';
END
GO

-- B. Validar mermas no negativas en transformaciones de producto (peso_entrada >= peso_salida)
IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name = 'CK_transf_merma_no_negativa')
BEGIN
    ALTER TABLE [dbo].[gestion_transformacionproducto] WITH CHECK
    ADD CONSTRAINT [CK_transf_merma_no_negativa]
    CHECK ([peso_entrada] >= [peso_salida]);
    PRINT 'Constraint CK_transf_merma_no_negativa creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 3. ESTRATEGIA DE ÍNDICES AVANZADOS MULTI-ORM
-- -----------------------------------------------------------------------------

-- A. Índice Filtrado para Pedidos de Venta Activos (Reporting Excel / Gerencial)
-- Corregido: 'vendedor_id' no existe (el FK real es vendedor_asignado ->
-- columna 'vendedor_asignado_id'); 'total_con_iva' no existe en PedidoVenta
-- (vive en DetallePedido, una tabla distinta) — ambos hacían fallar el CREATE
-- INDEX con "Invalid column name".
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_pv_activos_gerencial' AND object_id = OBJECT_ID('gestion_pedidoventa'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_pv_activos_gerencial]
    ON [dbo].[gestion_pedidoventa] ([sede_id], [fecha_pedido])
    INCLUDE ([cliente_id], [vendedor_asignado_id], [monto_pagado], [valor_retencion], [estado])
    WHERE ([anulado] = 0);
    PRINT 'Índice filtrado idx_pv_activos_gerencial creado.';
END
GO

-- B. Índice Filtrado para Órdenes de Producción en Ejecución (Planta)
-- Corregido: OrdenProduccion no tiene 'producto_id' (son 'producto_entrada_id'/
-- 'producto_salida_id') ni 'cliente_id' (ese FK vive en PedidoVenta, no en OP);
-- el peso real se llama 'peso_neto_requerido', no 'peso_neto_programado_kg'.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_op_activas_planta' AND object_id = OBJECT_ID('gestion_ordenproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_op_activas_planta]
    ON [dbo].[gestion_ordenproduccion] ([sede_id], [estado], [fecha_creacion])
    INCLUDE ([producto_entrada_id], [producto_salida_id], [peso_neto_requerido], [area_id])
    WHERE ([estado] <> 'cancelada');
    PRINT 'Índice filtrado idx_op_activas_planta creado.';
END
GO

-- C. (Eliminado) Índice para "scan_audit_log" — esa tabla NO vive en esta base
-- de datos. scanning_service persiste su auditoría en un SQLite propio
-- (scanning_service/src/database/engine.py, sqlite+aiosqlite:///{AUDIT_DB_PATH}),
-- separado del SQL Server de Django. Un CREATE INDEX contra
-- [dbo].[scan_audit_log] aquí falla con "Invalid object name": la tabla no
-- existe en texcore_db. Si scanning_service necesita esa optimización, debe
-- vivir en una migración/optimización propia de su SQLite, no en este script.

-- D. Índice Covering para Movimientos de Inventario Entrantes / Destino
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_mov_destino_fecha_incl' AND object_id = OBJECT_ID('inventory_movimientoinventario'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_mov_destino_fecha_incl]
    ON [dbo].[inventory_movimientoinventario] ([bodega_destino_id], [fecha])
    INCLUDE ([producto_id], [cantidad], [tipo_movimiento], [saldo_resultante]);
    PRINT 'Índice covering idx_mov_destino_fecha_incl creado.';
END
GO

-- E. Índice Covering para Transformaciones Máquina a Máquina
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_transf_op_secuencia_incl' AND object_id = OBJECT_ID('gestion_transformacionproducto'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_transf_op_secuencia_incl]
    ON [dbo].[gestion_transformacionproducto] ([orden_produccion_id], [numero_secuencia])
    INCLUDE ([producto_entrada_id], [producto_salida_id], [maquina_id], [peso_entrada], [peso_salida], [merma], [estado]);
    PRINT 'Índice covering idx_transf_op_secuencia_incl creado.';
END
GO

-- F. Non-Clustered Columnstore Index (NCCI) para Reportes Masivos de Inventario
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'ncci_movimiento_inventario' AND object_id = OBJECT_ID('inventory_movimientoinventario'))
BEGIN
    CREATE NONCLUSTERED COLUMNSTORE INDEX [ncci_movimiento_inventario]
    ON [dbo].[inventory_movimientoinventario]
    ([fecha], [producto_id], [bodega_origen_id], [bodega_destino_id], [tipo_movimiento], [cantidad], [saldo_resultante]);
    PRINT 'Columnstore Index ncci_movimiento_inventario creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 4. MITIGACIÓN DE CONTENCIÓN Y LATERALIDAD (SQL SERVER 2022 OPTIMIZE_FOR_SEQUENTIAL_KEY)
-- -----------------------------------------------------------------------------

DECLARE @pk_name NVARCHAR(256);

-- (scan_audit_log eliminado de este bloque — no vive en texcore_db, ver nota
-- en la sección 3.C más arriba)

-- Aplicar OPTIMIZE_FOR_SEQUENTIAL_KEY a inventory_movimientoinventario
SELECT TOP 1 @pk_name = name FROM sys.indexes 
WHERE object_id = OBJECT_ID('inventory_movimientoinventario') AND is_primary_key = 1;

IF @pk_name IS NOT NULL
BEGIN
    EXEC('ALTER INDEX [' + @pk_name + '] ON [dbo].[inventory_movimientoinventario] SET (OPTIMIZE_FOR_SEQUENTIAL_KEY = ON);');
    PRINT 'OPTIMIZE_FOR_SEQUENTIAL_KEY aplicado a inventory_movimientoinventario.';
END
GO

-- -----------------------------------------------------------------------------
-- 5. TUNING DE FILLFACTOR PARA TABLAS ALTA CONCURRENCIA DE UPDATE
-- -----------------------------------------------------------------------------
-- StockBodega no tiene un índice llamado 'idx_stock_bodega_producto' — sus
-- únicos índices con nombre explícito son las dos UniqueConstraint parciales
-- de gestion/models.py (con/sin lote), que son además el índice que golpea
-- cada select_for_update()/get_or_create() de stock (el hot path de
-- concurrencia real de la tabla).
IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'inventory_stockbodega_unique_without_lote' AND object_id = OBJECT_ID('inventory_stockbodega'))
BEGIN
    ALTER INDEX [inventory_stockbodega_unique_without_lote] ON [dbo].[inventory_stockbodega] REBUILD WITH (FILLFACTOR = 85);
    PRINT 'FILLFACTOR=85 aplicado a inventory_stockbodega_unique_without_lote.';
END
GO

IF EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'inventory_stockbodega_unique_with_lote' AND object_id = OBJECT_ID('inventory_stockbodega'))
BEGIN
    ALTER INDEX [inventory_stockbodega_unique_with_lote] ON [dbo].[inventory_stockbodega] REBUILD WITH (FILLFACTOR = 85);
    PRINT 'FILLFACTOR=85 aplicado a inventory_stockbodega_unique_with_lote.';
END
GO

PRINT '=== OPTIMIZACIÓN DE BASE DE DATOS TEXCORE FINALIZADA CON ÉXITO ===';
GO
