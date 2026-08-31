-- =============================================================================
-- TEXCORE — ÍNDICES PARA REPORTES BAJO CARGA CONCURRENTE (SQL SERVER 2022)
-- =============================================================================
-- Contexto: auditoría de performance (2026-08-31) encontró que
-- internal_api/views/reporting_views.py — el path de datos real de todos los
-- reportes ejecutivos/gerenciales/producción (los 21 SP de
-- V3__optimize_stored_procedures_texcore.sql NO se ejecutan, ver comentario en
-- ese archivo) — filtra/agrega sobre columnas sin índice de soporte en varios
-- de los 18 endpoints de reporte. Este script agrega los índices priorizados
-- por número de rutas de reporte afectadas, antes de la prueba de carga de
-- 100 usuarios concurrentes (scripts/loadtest/).
--
-- Sigue el mismo patrón idempotente (IF NOT EXISTS) de V2.
-- =============================================================================

USE [texcore_db];
GO

-- -----------------------------------------------------------------------------
-- A. Índice Covering para Movimientos de Inventario Salientes / Origen
-- -----------------------------------------------------------------------------
-- Kardex, Aging, Rotación y Resumen de Movimientos filtran
-- (bodega_origen_id = @X OR bodega_destino_id = @X). Solo 'destino' tenía
-- índice dedicado (idx_mov_destino_fecha_incl, V2); 'origen' forzaba scan.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_mov_origen_fecha_incl' AND object_id = OBJECT_ID('inventory_movimientoinventario'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_mov_origen_fecha_incl]
    ON [dbo].[inventory_movimientoinventario] ([bodega_origen_id], [fecha])
    INCLUDE ([producto_id], [cantidad], [tipo_movimiento], [saldo_resultante]);
    PRINT 'Índice covering idx_mov_origen_fecha_incl creado.';
END
GO

-- -----------------------------------------------------------------------------
-- B. Índice para Pedidos de Venta filtrados por Vendedor (reportes de vendedor)
-- -----------------------------------------------------------------------------
-- idx_pv_activos_gerencial (V2) solo tiene 'vendedor_asignado_id' como INCLUDE,
-- no como clave líder — las 3 vistas de reporte por vendedor
-- (VentasVendedorView, TopClientesVendedorView, DeudoresVendedorView) no
-- pueden hacer seek con ese índice. Se agrega uno nuevo en vez de modificar
-- el existente, que sigue sirviendo a las vistas gerenciales por sede.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_pv_vendedor_fecha' AND object_id = OBJECT_ID('gestion_pedidoventa'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_pv_vendedor_fecha]
    ON [dbo].[gestion_pedidoventa] ([vendedor_asignado_id], [fecha_pedido])
    INCLUDE ([cliente_id], [sede_id], [monto_pagado], [valor_retencion], [estado])
    WHERE ([anulado] = 0);
    PRINT 'Índice idx_pv_vendedor_fecha creado.';
END
GO

-- -----------------------------------------------------------------------------
-- C. Índice Covering para Detalle de Pedido (agregación de ventas)
-- -----------------------------------------------------------------------------
-- Sin ningún índice hasta ahora. Se une/suma en 5 rutas de reporte
-- (top-clientes vendedor/gerencial, deudores vendedor/gerencial, ventas
-- gerencial) vía pedido_venta_id, agregando total_con_iva.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_detpedido_pedido_incl' AND object_id = OBJECT_ID('gestion_detallepedido'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_detpedido_pedido_incl]
    ON [dbo].[gestion_detallepedido] ([pedido_venta_id])
    INCLUDE ([total_con_iva], [subtotal], [producto_id]);
    PRINT 'Índice covering idx_detpedido_pedido_incl creado.';
END
GO

-- -----------------------------------------------------------------------------
-- D. Índice Covering para Stock por Bodega/Producto (reportes de inventario)
-- -----------------------------------------------------------------------------
-- 6 rutas de reporte (stock actual, valorización, aging, stock cero,
-- agrupado por sede, retro-kardex) filtran por bodega_id/producto_id; solo
-- había cobertura incidental vía las UniqueConstraint (bodega+producto+lote).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_stock_bodega_producto_incl' AND object_id = OBJECT_ID('inventory_stockbodega'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_stock_bodega_producto_incl]
    ON [dbo].[inventory_stockbodega] ([bodega_id], [producto_id])
    INCLUDE ([cantidad], [lote_id]);
    PRINT 'Índice covering idx_stock_bodega_producto_incl creado.';
END
GO

PRINT '=== V4: ÍNDICES DE REPORTES PARA CARGA CONCURRENTE APLICADOS ===';
GO
