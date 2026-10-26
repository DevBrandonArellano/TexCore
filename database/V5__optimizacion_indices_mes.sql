-- =============================================================================
-- TEXCORE — ÍNDICES DE ALTO RENDIMIENTO PARA NÚCLEO MES (SQL SERVER 2022)
-- =============================================================================
-- Contexto: Arquitectura MES Nivel 3 (ISA-95) para soporte transaccional de
-- alta velocidad en las 3 modalidades:
-- 1. Producción Continua (pesajes directos sin OP)
-- 2. Producción Contra Stock / MTS (planes de reposición y control de desvío)
-- 3. Producción Bajo Pedido / MTO (reserva inmutable y despacho comercial)
--
-- Incluye:
-- - Índices filtrados para corridas activas en piso de planta
-- - Índices bidireccionales de alto rendimiento para grafos DAG de GenealogiaLote
-- - Índices de aceleración para reservas MTO y control de stock comprometido
-- - Índices para avance y agregaciones en planes de producción MTS
--
-- Sigue el mismo patrón idempotente (IF NOT EXISTS) de V2, V3 y V4.
-- =============================================================================

USE [texcore_db];
GO

-- -----------------------------------------------------------------------------
-- 1. Corridas de Producción Activas en Piso de Planta (Filtered Index)
-- -----------------------------------------------------------------------------
-- Acelera la pantalla de pesaje de operarios y el dashboard de planta que
-- consultan permanentemente corridas 'en_proceso' o 'pausada' por sede.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_corrida_activa_sede' AND object_id = OBJECT_ID('gestion_corridaproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_corrida_activa_sede]
    ON [dbo].[gestion_corridaproduccion] ([sede_id], [estado], [fecha_jornada])
    INCLUDE ([codigo], [modalidad], [area_id], [linea_id], [maquina_principal_id], [turno], [hora_inicio])
    WHERE ([estado] IN ('en_proceso', 'pausada'));
    PRINT 'Índice filtrado idx_corrida_activa_sede creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 2. Corridas vinculadas a Órdenes de Producción
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_corrida_op' AND object_id = OBJECT_ID('gestion_corridaproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_corrida_op]
    ON [dbo].[gestion_corridaproduccion] ([orden_produccion_id])
    INCLUDE ([codigo], [estado], [modalidad])
    WHERE ([orden_produccion_id] IS NOT NULL);
    PRINT 'Índice idx_corrida_op creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 3. Grafo DAG de Genealogía de Lotes: Trazabilidad Hacia Adelante (Downstream)
-- -----------------------------------------------------------------------------
-- Consulta: ¿Qué lotes hijos se fabricaron a partir de este lote padre?
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_genealogia_padre_hijo' AND object_id = OBJECT_ID('gestion_genealogialote'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_genealogia_padre_hijo]
    ON [dbo].[gestion_genealogialote] ([lote_padre_id], [lote_hijo_id])
    INCLUDE ([operacion_id], [cantidad_padre_usada], [timestamp]);
    PRINT 'Índice idx_genealogia_padre_hijo creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 4. Grafo DAG de Genealogía de Lotes: Trazabilidad Hacia Atrás (Upstream)
-- -----------------------------------------------------------------------------
-- Consulta: ¿De qué lotes padres proviene este lote terminado o intermedio?
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_genealogia_hijo_padre' AND object_id = OBJECT_ID('gestion_genealogialote'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_genealogia_hijo_padre]
    ON [dbo].[gestion_genealogialote] ([lote_hijo_id], [lote_padre_id])
    INCLUDE ([operacion_id], [cantidad_padre_usada], [timestamp]);
    PRINT 'Índice idx_genealogia_hijo_padre creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 5. Secuencia de Operaciones de Producción en Corrida
-- -----------------------------------------------------------------------------
-- Acelera el ordenamiento cronológico de balance de masa y reversiones atómicas.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_operacion_corrida_secuencia' AND object_id = OBJECT_ID('gestion_operacionproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_operacion_corrida_secuencia]
    ON [dbo].[gestion_operacionproduccion] ([corrida_id], [numero_secuencia])
    INCLUDE ([maquina_id], [proceso_id], [operario_id], [estado], [hora_inicio], [hora_fin]);
    PRINT 'Índice idx_operacion_corrida_secuencia creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 6. Reservas MTO en Lotes de Producción (Filtered Index)
-- -----------------------------------------------------------------------------
-- Acelera la verificación de aislamiento en ValidateLoteAPIView y ProcessDespachoAPIView.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_lote_reserva_pedido' AND object_id = OBJECT_ID('gestion_loteproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_lote_reserva_pedido]
    ON [dbo].[gestion_loteproduccion] ([pedido_venta_reserva_id])
    INCLUDE ([codigo_lote], [producto_id], [peso_neto_producido])
    WHERE ([pedido_venta_reserva_id] IS NOT NULL);
    PRINT 'Índice filtrado idx_lote_reserva_pedido creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 7. Stock Comprometido MTO en Bodega (Filtered Index)
-- -----------------------------------------------------------------------------
-- Acelera el cálculo de stock disponible para venta libre en tiempo real.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_stockbodega_comprometido' AND object_id = OBJECT_ID('inventory_stockbodega'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_stockbodega_comprometido]
    ON [dbo].[inventory_stockbodega] ([bodega_id], [producto_id], [stock_comprometido])
    INCLUDE ([cantidad], [lote_id])
    WHERE ([stock_comprometido] > 0);
    PRINT 'Índice filtrado idx_stockbodega_comprometido creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 8. Planes de Producción Contra Stock (MTS) por Sede y Estado
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_plan_sede_estado' AND object_id = OBJECT_ID('gestion_planproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_plan_sede_estado]
    ON [dbo].[gestion_planproduccion] ([sede_id], [estado], [fecha_inicio], [fecha_fin])
    INCLUDE ([codigo], [supervisor_id]);
    PRINT 'Índice idx_plan_sede_estado creado.';
END
GO

-- -----------------------------------------------------------------------------
-- 9. Detalle de Plan de Producción (MTS) por Plan y Producto Objetivo
-- -----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'idx_detalleplan_plan_prod' AND object_id = OBJECT_ID('gestion_detalleplanproduccion'))
BEGIN
    CREATE NONCLUSTERED INDEX [idx_detalleplan_plan_prod]
    ON [dbo].[gestion_detalleplanproduccion] ([plan_id], [producto_objetivo_id])
    INCLUDE ([cantidad_planificada], [cantidad_ejecutada], [cantidad_aceptada], [cantidad_segunda], [estado]);
    PRINT 'Índice idx_detalleplan_plan_prod creado.';
END
GO
