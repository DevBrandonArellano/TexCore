-- =============================================================================
-- TEXCORE STORED PROCEDURES OPTIMIZATION SCRIPT (ESQUEMA 2026) - SQL SERVER 2022
-- Ecosistema: Django 5 (`gestion`, `inventory`, `internal_api`) + SQLAlchemy / FastAPI
-- Autor: Principal Database Architect & SQL Server 2022 Expert
-- =============================================================================

USE [texcore_db];
GO

-- -----------------------------------------------------------------------------
-- 1. sp_GetKardexBodega
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetKardexBodega
    @BodegaID    INT,
    @ProductoID  INT = NULL,
    @FechaInicio DATETIME = NULL,
    @FechaFin    DATETIME = NULL,
    @ProveedorID INT = NULL,
    @LoteCodigo  NVARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        m.id,
        CONVERT(VARCHAR(19), m.fecha, 120) AS fecha,
        m.tipo_movimiento,
        m.documento_ref,
        CASE WHEN m.bodega_destino_id = @BodegaID THEN m.cantidad ELSE 0 END AS entrada,
        CASE WHEN m.bodega_origen_id = @BodegaID THEN m.cantidad ELSE 0 END AS salida,
        m.saldo_resultante,
        p.codigo AS codigo_producto,
        p.descripcion AS descripcion_producto,
        u.username AS usuario,
        l.codigo_lote AS lote,
        m.editado,
        CAST(CASE WHEN aud.movimiento_id IS NOT NULL THEN 1 ELSE 0 END AS BIT) AS has_audit
    FROM dbo.inventory_movimientoinventario m
    INNER JOIN dbo.gestion_producto p ON p.id = m.producto_id
    LEFT JOIN dbo.gestion_customuser u ON u.id = m.usuario_id
    LEFT JOIN dbo.gestion_loteproduccion l ON l.id = m.lote_id
    LEFT JOIN (
        SELECT DISTINCT movimiento_id 
        FROM dbo.inventory_auditoriamovimiento
    ) aud ON aud.movimiento_id = m.id
    WHERE (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
      AND (@ProductoID IS NULL OR m.producto_id = @ProductoID)
      AND (@FechaInicio IS NULL OR m.fecha >= @FechaInicio)
      AND (@FechaFin IS NULL OR m.fecha <= @FechaFin)
      AND (@ProveedorID IS NULL OR m.proveedor_id = @ProveedorID)
      AND (@LoteCodigo IS NULL OR l.codigo_lote = @LoteCodigo OR l.codigo_lote LIKE @LoteCodigo + '%')
    ORDER BY m.fecha ASC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 2. sp_GetProductosCatalogo
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetProductosCatalogo
    @SedeID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        p.id,
        p.codigo,
        p.descripcion,
        p.tipo,
        p.unidad_medida,
        p.precio_base,
        p.stock_minimo,
        p.sede_id
    FROM dbo.gestion_producto p
    WHERE (@SedeID IS NULL OR p.sede_id = @SedeID)
    ORDER BY p.codigo
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 3. sp_GetUsuariosSistema
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetUsuariosSistema
    @SedeID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        u.id,
        u.username,
        u.first_name,
        u.last_name,
        u.email,
        u.sede_id,
        ISNULL(s.nombre, 'Sin Sede') AS sede_nombre
    FROM dbo.gestion_customuser u
    LEFT JOIN dbo.gestion_sede s ON u.sede_id = s.id
    WHERE u.is_active = 1
      AND (@SedeID IS NULL OR u.sede_id = @SedeID)
    ORDER BY u.username
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 4. sp_GetStockActualBodega
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetStockActualBodega
    @BodegaID   INT,
    @ProductoID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        s.id,
        s.cantidad,
        p.id AS producto_id,
        p.codigo AS producto_codigo,
        p.descripcion AS producto_descripcion,
        b.id AS bodega_id,
        b.nombre AS bodega_nombre,
        l.id AS lote_id,
        l.codigo_lote AS lote_codigo
    FROM dbo.inventory_stockbodega s
    INNER JOIN dbo.gestion_producto p ON p.id = s.producto_id
    INNER JOIN dbo.gestion_bodega b ON b.id = s.bodega_id
    LEFT JOIN dbo.gestion_loteproduccion l ON l.id = s.lote_id
    WHERE s.bodega_id = @BodegaID
      AND s.cantidad > 0
      AND (@ProductoID IS NULL OR s.producto_id = @ProductoID)
    ORDER BY p.descripcion, l.codigo_lote
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 5. sp_GetValorizacionInventario
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetValorizacionInventario
    @BodegaID INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        s.id,
        s.cantidad,
        p.precio_base,
        (s.cantidad * p.precio_base) AS valor_total,
        p.descripcion AS producto_descripcion,
        p.codigo AS producto_codigo
    FROM dbo.inventory_stockbodega s
    INNER JOIN dbo.gestion_producto p ON p.id = s.producto_id
    WHERE s.bodega_id = @BodegaID
      AND s.cantidad > 0
    ORDER BY valor_total DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 6. sp_GetInventarioAging
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetInventarioAging
    @BodegaID    INT,
    @DiasMinimos INT = 30
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaCorte DATETIME = DATEADD(day, -@DiasMinimos, GETDATE());

    WITH ProductosRecientes AS (
        SELECT DISTINCT m.producto_id
        FROM dbo.inventory_movimientoinventario m
        WHERE m.bodega_origen_id = @BodegaID
          AND m.fecha >= @FechaCorte
    )
    SELECT 
        s.id,
        s.cantidad,
        p.codigo AS producto_codigo,
        p.descripcion AS producto_descripcion,
        p.precio_base
    FROM dbo.inventory_stockbodega s
    INNER JOIN dbo.gestion_producto p ON p.id = s.producto_id
    LEFT JOIN ProductosRecientes pr ON pr.producto_id = s.producto_id
    WHERE s.bodega_id = @BodegaID
      AND s.cantidad > 0
      AND pr.producto_id IS NULL
    ORDER BY s.cantidad DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 7. sp_GetRotacionInventario
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetRotacionInventario
    @BodegaID    INT,
    @FechaInicio DATETIME = NULL,
    @FechaFin    DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        p.codigo AS producto_codigo,
        p.descripcion AS producto_descripcion,
        SUM(m.cantidad) AS total_salidas
    FROM dbo.inventory_movimientoinventario m
    INNER JOIN dbo.gestion_producto p ON p.id = m.producto_id
    WHERE m.bodega_origen_id = @BodegaID
      AND (@FechaInicio IS NULL OR m.fecha >= @FechaInicio)
      AND (@FechaFin IS NULL OR m.fecha <= @FechaFin)
    GROUP BY p.codigo, p.descripcion
    ORDER BY total_salidas DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 8. sp_GetStockCeroBodega
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetStockCeroBodega
    @BodegaID INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        s.id,
        s.cantidad,
        p.codigo AS producto_codigo,
        p.descripcion AS producto_descripcion
    FROM dbo.inventory_stockbodega s
    INNER JOIN dbo.gestion_producto p ON p.id = s.producto_id
    WHERE s.bodega_id = @BodegaID
      AND s.cantidad = 0
    ORDER BY p.descripcion
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 9. sp_GetResumenMovimientos
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetResumenMovimientos
    @BodegaID    INT,
    @FechaInicio DATETIME = NULL,
    @FechaFin    DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        m.tipo_movimiento,
        SUM(m.cantidad) AS total_cantidad,
        COUNT(m.id) AS total_operaciones
    FROM dbo.inventory_movimientoinventario m
    WHERE (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
      AND (@FechaInicio IS NULL OR m.fecha >= @FechaInicio)
      AND (@FechaFin IS NULL OR m.fecha <= @FechaFin)
    GROUP BY m.tipo_movimiento
    ORDER BY total_cantidad DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 10. sp_GetVentasPorVendedor
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetVentasPorVendedor
    @VendedorID  INT,
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT 
        pv.id AS PedidoID,
        pv.guia_remision AS GuiaRemision,
        CONVERT(VARCHAR(10), pv.fecha_pedido, 105) AS Fecha,
        pv.estado AS Estado,
        pv.esta_pagado AS EstaPagado,
        pv.monto_pagado AS MontoPagado,
        c.nombre_razon_social AS ClienteNombre
    FROM dbo.gestion_pedidoventa pv
    INNER JOIN dbo.gestion_cliente c ON c.id = pv.cliente_id
    WHERE pv.vendedor_asignado_id = @VendedorID
      AND pv.anulado = 0
      AND (@FechaInicioDateTime IS NULL OR pv.fecha_pedido >= @FechaInicioDateTime)
      AND (@FechaFinExclusive IS NULL OR pv.fecha_pedido < @FechaFinExclusive)
    ORDER BY pv.fecha_pedido DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 11. sp_GetTopClientesPorVendedor
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetTopClientesPorVendedor
    @VendedorID  INT,
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT TOP 10
        pv.cliente_id AS ClienteID,
        c.nombre_razon_social AS ClienteNombre,
        COUNT(pv.id) AS TotalPedidos,
        SUM(ISNULL(d.total_con_iva, 0)) AS TotalMonto
    FROM dbo.gestion_pedidoventa pv
    INNER JOIN dbo.gestion_cliente c ON c.id = pv.cliente_id
    LEFT JOIN dbo.gestion_detallepedido d ON d.pedido_venta_id = pv.id
    WHERE pv.vendedor_asignado_id = @VendedorID
      AND pv.anulado = 0
      AND (@FechaInicioDateTime IS NULL OR pv.fecha_pedido >= @FechaInicioDateTime)
      AND (@FechaFinExclusive IS NULL OR pv.fecha_pedido < @FechaFinExclusive)
    GROUP BY pv.cliente_id, c.nombre_razon_social
    ORDER BY TotalPedidos DESC, TotalMonto DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 12. sp_GetDeudoresPorVendedor
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetDeudoresPorVendedor
    @VendedorID INT
AS
BEGIN
    SET NOCOUNT ON;

    WITH VentasCliente AS (
        SELECT 
            pv.cliente_id,
            SUM(ISNULL(d.total_con_iva, 0) - ISNULL(pv.valor_retencion, 0)) AS TotalFacturado
        FROM dbo.gestion_pedidoventa pv
        LEFT JOIN dbo.gestion_detallepedido d ON d.pedido_venta_id = pv.id
        WHERE pv.anulado = 0
        GROUP BY pv.cliente_id
    ),
    PagosCliente AS (
        SELECT 
            p.cliente_id,
            SUM(p.monto) AS TotalPagado
        FROM dbo.gestion_pagocliente p
        GROUP BY p.cliente_id
    )
    SELECT 
        c.id AS ClienteID,
        c.ruc_cedula AS RUC,
        c.nombre_razon_social AS ClienteNombre,
        c.limite_credito AS LimiteCredito,
        c.plazo_credito_dias AS PlazoCreditoDias,
        ISNULL(p.TotalPagado, 0) AS TotalPagado,
        (ISNULL(v.TotalFacturado, 0) - ISNULL(p.TotalPagado, 0)) AS SaldoPendiente
    FROM dbo.gestion_cliente c
    LEFT JOIN VentasCliente v ON v.cliente_id = c.id
    LEFT JOIN PagosCliente p ON p.cliente_id = c.id
    WHERE c.vendedor_asignado_id = @VendedorID
      AND c.is_active = 1
      AND (ISNULL(v.TotalFacturado, 0) - ISNULL(p.TotalPagado, 0)) > 0
    ORDER BY SaldoPendiente DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 13. sp_GetVentasGerencial
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetVentasGerencial
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL,
    @SedeID      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT 
        pv.id AS PedidoID, 
        pv.guia_remision AS GuiaRemision,
        CONVERT(VARCHAR(10), pv.fecha_pedido, 105) AS Fecha,
        pv.estado AS Estado,
        pv.esta_pagado AS EstaPagado,
        c.nombre_razon_social AS ClienteNombre,
        u.username AS VendedorNombre,
        ISNULL(s.nombre, 'Sin Sede') AS SedeNombre,
        ISNULL(pv.valor_retencion, 0) AS RetencionAplicada,
        (SUM(ISNULL(d.total_con_iva, 0)) - ISNULL(pv.valor_retencion, 0)) AS TotalFinalVenta
    FROM dbo.gestion_pedidoventa pv
    LEFT JOIN dbo.gestion_cliente c ON pv.cliente_id = c.id
    LEFT JOIN dbo.gestion_customuser u ON pv.vendedor_asignado_id = u.id
    LEFT JOIN dbo.gestion_sede s ON pv.sede_id = s.id
    LEFT JOIN dbo.gestion_detallepedido d ON d.pedido_venta_id = pv.id
    WHERE pv.anulado = 0
      AND (@FechaInicioDateTime IS NULL OR pv.fecha_pedido >= @FechaInicioDateTime)
      AND (@FechaFinExclusive IS NULL OR pv.fecha_pedido < @FechaFinExclusive)
      AND (@SedeID IS NULL OR pv.sede_id = @SedeID)
    GROUP BY pv.id, pv.guia_remision, pv.fecha_pedido, pv.estado, pv.esta_pagado, c.nombre_razon_social, u.username, s.nombre, pv.valor_retencion
    ORDER BY pv.id DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 14. sp_GetTopClientesGerencial
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetTopClientesGerencial
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL,
    @SedeID      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT TOP 20
        pv.cliente_id AS ClienteID,
        c.nombre_razon_social AS ClienteNombre,
        COUNT(DISTINCT pv.id) AS TotalPedidos,
        SUM(ISNULL(d.total_con_iva, 0)) AS TotalMonto
    FROM dbo.gestion_pedidoventa pv
    INNER JOIN dbo.gestion_cliente c ON c.id = pv.cliente_id
    LEFT JOIN dbo.gestion_detallepedido d ON d.pedido_venta_id = pv.id
    WHERE pv.anulado = 0
      AND (@FechaInicioDateTime IS NULL OR pv.fecha_pedido >= @FechaInicioDateTime)
      AND (@FechaFinExclusive IS NULL OR pv.fecha_pedido < @FechaFinExclusive)
      AND (@SedeID IS NULL OR pv.sede_id = @SedeID)
    GROUP BY pv.cliente_id, c.nombre_razon_social
    ORDER BY TotalPedidos DESC, TotalMonto DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 15. sp_GetDeudoresGerencial
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetDeudoresGerencial
    @SedeID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    WITH VentasCliente AS (
        SELECT 
            pv.cliente_id,
            SUM(ISNULL(d.total_con_iva, 0) - ISNULL(pv.valor_retencion, 0)) AS TotalFacturado
        FROM dbo.gestion_pedidoventa pv
        LEFT JOIN dbo.gestion_detallepedido d ON d.pedido_venta_id = pv.id
        WHERE pv.anulado = 0
        GROUP BY pv.cliente_id
    ),
    PagosCliente AS (
        SELECT 
            p.cliente_id,
            SUM(p.monto) AS TotalPagado
        FROM dbo.gestion_pagocliente p
        GROUP BY p.cliente_id
    )
    SELECT 
        c.id AS ClienteID,
        c.ruc_cedula AS RUC,
        c.nombre_razon_social AS ClienteNombre,
        u.username AS VendedorNombre,
        ISNULL(s.nombre, 'Sin Sede') AS SedeNombre,
        c.limite_credito AS LimiteCredito,
        ISNULL(p.TotalPagado, 0) AS TotalPagado,
        (ISNULL(v.TotalFacturado, 0) - ISNULL(p.TotalPagado, 0)) AS SaldoPendiente
    FROM dbo.gestion_cliente c
    LEFT JOIN dbo.gestion_customuser u ON c.vendedor_asignado_id = u.id
    LEFT JOIN dbo.gestion_sede s ON c.sede_id = s.id
    LEFT JOIN VentasCliente v ON v.cliente_id = c.id
    LEFT JOIN PagosCliente p ON p.cliente_id = c.id
    WHERE c.is_active = 1
      AND (ISNULL(v.TotalFacturado, 0) - ISNULL(p.TotalPagado, 0)) > 0
      AND (@SedeID IS NULL OR c.sede_id = @SedeID)
    ORDER BY SaldoPendiente DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 16. sp_GetOrdenesProduccionGerencial
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetOrdenesProduccionGerencial
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL,
    @SedeID      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT
        op.id                           AS id_orden,
        op.codigo                       AS codigo_orden,
        p_salida.codigo                 AS codigo_producto,
        p_salida.descripcion            AS producto,
        fc.nombre_color                 AS formula_color,
        fc.tipo_sustrato                AS tipo_sustrato,
        op.peso_neto_requerido          AS peso_requerido_kg,
        prod.total_peso                 AS peso_producido_kg,
        CASE
            WHEN op.peso_neto_requerido > 0
            THEN CAST(ROUND(prod.total_peso * 100.0 / op.peso_neto_requerido, 2) AS DECIMAL(8,2))
            ELSE 0
        END                             AS avance_pct,
        op.estado                       AS estado,
        op.prioridad                    AS prioridad,
        sd.nombre                       AS sede,
        a.nombre                        AS area,
        m.nombre                        AS maquina,
        CONCAT(u.first_name, ' ', u.last_name) AS operario,
        prod.fecha_inicio               AS fecha_inicio,
        prod.fecha_fin                  AS fecha_fin
    FROM dbo.gestion_ordenproduccion op
    LEFT JOIN dbo.gestion_producto     p_salida ON p_salida.id = op.producto_salida_id
    LEFT JOIN dbo.gestion_sede         sd       ON sd.id = op.sede_id
    LEFT JOIN dbo.gestion_formulacolor fc       ON fc.id = op.formula_color_id
    LEFT JOIN dbo.gestion_area         a        ON a.id  = op.area_id
    LEFT JOIN dbo.gestion_maquina      m        ON m.id  = op.maquina_asignada_id
    LEFT JOIN dbo.gestion_customuser   u        ON u.id  = op.operario_asignado_id
    OUTER APPLY (
        SELECT 
            ISNULL(SUM(lp.peso_neto_producido), 0) AS total_peso,
            MIN(lp.hora_inicio) AS fecha_inicio,
            MAX(lp.hora_final)  AS fecha_fin,
            COUNT(lp.id)        AS total_lotes,
            SUM(CASE WHEN (@FechaInicioDateTime IS NULL OR lp.hora_inicio >= @FechaInicioDateTime) 
                      AND (@FechaFinExclusive IS NULL OR lp.hora_inicio < @FechaFinExclusive) THEN 1 ELSE 0 END) AS lotes_en_rango
        FROM dbo.gestion_loteproduccion lp
        WHERE lp.orden_produccion_id = op.id
    ) AS prod
    WHERE (@SedeID IS NULL OR op.sede_id = @SedeID)
      AND (prod.lotes_en_rango > 0 OR (prod.total_lotes = 0 AND (@FechaInicioDateTime IS NULL OR op.fecha_creacion >= @FechaInicioDateTime)))
    ORDER BY sd.nombre, op.estado, op.codigo
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 17. sp_GetLotesProduccionGerencial
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetLotesProduccionGerencial
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL,
    @SedeID      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT
        lp.id                                   AS id_lote,
        lp.codigo_lote                          AS codigo_lote,
        op.codigo                               AS orden_produccion,
        p.codigo                                AS codigo_producto,
        p.descripcion                           AS producto,
        sd.nombre                               AS sede,
        a.nombre                                AS area,
        m.nombre                                AS maquina,
        CONCAT(u.first_name, ' ', u.last_name)  AS operario,
        lp.turno                                AS turno,
        lp.peso_bruto                           AS peso_bruto_kg,
        lp.tara                                 AS tara_kg,
        lp.peso_neto_producido                  AS peso_neto_kg,
        lp.peso_merma                           AS peso_merma_kg,
        lp.cantidad_metros                      AS cantidad_metros,
        lp.unidades_empaque                     AS unidades_empaque,
        lp.presentacion                         AS presentacion,
        lp.clasificacion_calidad                AS clasificacion_calidad,
        lp.tipo_merma                           AS tipo_merma,
        lp.hora_inicio                          AS hora_inicio,
        lp.hora_final                           AS hora_final
    FROM dbo.gestion_loteproduccion lp
    INNER JOIN dbo.gestion_ordenproduccion op ON op.id = lp.orden_produccion_id
    LEFT  JOIN dbo.gestion_producto        p  ON p.id  = op.producto_salida_id
    LEFT  JOIN dbo.gestion_sede            sd ON sd.id = op.sede_id
    LEFT  JOIN dbo.gestion_area            a  ON a.id  = op.area_id
    LEFT  JOIN dbo.gestion_maquina         m  ON m.id  = lp.maquina_id
    LEFT  JOIN dbo.gestion_customuser      u  ON u.id  = lp.operario_id
    WHERE (@SedeID IS NULL OR op.sede_id = @SedeID)
      AND (@FechaInicioDateTime IS NULL OR lp.hora_inicio >= @FechaInicioDateTime)
      AND (@FechaFinExclusive IS NULL OR lp.hora_inicio < @FechaFinExclusive)
    ORDER BY lp.hora_inicio DESC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 18. sp_GetTendenciaProduccionGerencial
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetTendenciaProduccionGerencial
    @FechaInicio DATE = NULL,
    @FechaFin    DATE = NULL,
    @SedeID      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @FechaFinExclusive DATETIME = CASE WHEN @FechaFin IS NOT NULL THEN DATEADD(day, 1, CAST(@FechaFin AS DATETIME)) ELSE NULL END;
    DECLARE @FechaInicioDateTime DATETIME = CASE WHEN @FechaInicio IS NOT NULL THEN CAST(@FechaInicio AS DATETIME) ELSE NULL END;

    SELECT 
        CAST(lp.hora_inicio AS DATE) AS fecha,
        SUM(lp.peso_neto_producido) AS total_peso,
        COUNT(lp.id) AS total_lotes
    FROM dbo.gestion_loteproduccion lp
    INNER JOIN dbo.gestion_ordenproduccion op ON op.id = lp.orden_produccion_id
    WHERE (@SedeID IS NULL OR op.sede_id = @SedeID)
      AND (@FechaInicioDateTime IS NULL OR lp.hora_inicio >= @FechaInicioDateTime)
      AND (@FechaFinExclusive IS NULL OR lp.hora_inicio < @FechaFinExclusive)
    GROUP BY CAST(lp.hora_inicio AS DATE)
    ORDER BY fecha ASC
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 19. sp_GetStockAgrupadoPorSede
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetStockAgrupadoPorSede
    @SedeID INT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT 
        p.id AS producto_id,
        p.codigo AS codigo_producto,
        p.descripcion AS descripcion_producto,
        sd.id AS sede_id,
        sd.nombre AS sede_nombre,
        SUM(s.cantidad) AS stock_total
    FROM dbo.inventory_stockbodega s
    INNER JOIN dbo.gestion_producto p ON p.id = s.producto_id
    INNER JOIN dbo.gestion_bodega b ON b.id = s.bodega_id
    INNER JOIN dbo.gestion_sede sd ON sd.id = b.sede_id
    WHERE (@SedeID IS NULL OR sd.id = @SedeID)
    GROUP BY p.id, p.codigo, p.descripcion, sd.id, sd.nombre
    ORDER BY sd.nombre, p.descripcion
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 20. sp_GetRetroKardex
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetRetroKardex
    @BodegaID   INT,
    @FechaCorte DATETIME
AS
BEGIN
    SET NOCOUNT ON;

    WITH MovimientosPosteriores AS (
        SELECT 
            m.producto_id,
            SUM(CASE WHEN m.bodega_destino_id = @BodegaID THEN m.cantidad ELSE 0 END) AS entradas_post,
            SUM(CASE WHEN m.bodega_origen_id = @BodegaID THEN m.cantidad ELSE 0 END) AS salidas_post
        FROM dbo.inventory_movimientoinventario m
        WHERE (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
          AND m.fecha > @FechaCorte
        GROUP BY m.producto_id
    )
    SELECT 
        p.id AS producto_id,
        p.codigo AS codigo_producto,
        p.descripcion AS descripcion_producto,
        ISNULL(s.cantidad_actual, 0) AS stock_actual,
        (ISNULL(s.cantidad_actual, 0) - ISNULL(mp.entradas_post, 0) + ISNULL(mp.salidas_post, 0)) AS stock_en_corte
    FROM dbo.gestion_producto p
    LEFT JOIN (
        SELECT producto_id, SUM(cantidad) AS cantidad_actual
        FROM dbo.inventory_stockbodega
        WHERE bodega_id = @BodegaID
        GROUP BY producto_id
    ) s ON s.producto_id = p.id
    LEFT JOIN MovimientosPosteriores mp ON mp.producto_id = p.id
    WHERE (ISNULL(s.cantidad_actual, 0) - ISNULL(mp.entradas_post, 0) + ISNULL(mp.salidas_post, 0)) > 0
    ORDER BY p.descripcion
    OPTION (RECOMPILE);
END
GO

-- -----------------------------------------------------------------------------
-- 21. sp_GetReporteOrdenProduccionPorId
-- -----------------------------------------------------------------------------
CREATE OR ALTER PROCEDURE dbo.sp_GetReporteOrdenProduccionPorId
    @OrdenID INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Conjunto 1: Encabezado de la Orden
    SELECT 
        op.id,
        op.codigo,
        op.estado,
        op.prioridad,
        op.peso_neto_requerido,
        p_in.codigo AS producto_entrada_codigo,
        p_in.descripcion AS producto_entrada_descripcion,
        p_out.codigo AS producto_salida_codigo,
        p_out.descripcion AS producto_salida_descripcion,
        fc.nombre_color AS formula_color,
        b_in.nombre AS bodega_entrada,
        b_out.nombre AS bodega_salida,
        sd.nombre AS sede,
        a.nombre AS area,
        m.nombre AS maquina_asignada,
        CONCAT(u.first_name, ' ', u.last_name) AS operario_asignado,
        op.fecha_inicio_planificada,
        op.fecha_fin_planificada,
        op.fecha_creacion
    FROM dbo.gestion_ordenproduccion op
    LEFT JOIN dbo.gestion_producto p_in ON p_in.id = op.producto_entrada_id
    LEFT JOIN dbo.gestion_producto p_out ON p_out.id = op.producto_salida_id
    LEFT JOIN dbo.gestion_formulacolor fc ON fc.id = op.formula_color_id
    LEFT JOIN dbo.gestion_bodega b_in ON b_in.id = op.bodega_entrada_id
    LEFT JOIN dbo.gestion_bodega b_out ON b_out.id = op.bodega_salida_id
    LEFT JOIN dbo.gestion_sede sd ON sd.id = op.sede_id
    LEFT JOIN dbo.gestion_area a ON a.id = op.area_id
    LEFT JOIN dbo.gestion_maquina m ON m.id = op.maquina_asignada_id
    LEFT JOIN dbo.gestion_customuser u ON u.id = op.operario_asignado_id
    WHERE op.id = @OrdenID;

    -- Conjunto 2: Lotes Producidos
    SELECT 
        lp.id,
        lp.codigo_lote,
        lp.peso_neto_producido,
        lp.peso_bruto,
        lp.tara,
        lp.peso_merma,
        lp.cantidad_metros,
        lp.unidades_empaque,
        lp.presentacion,
        lp.clasificacion_calidad,
        lp.hora_inicio,
        lp.hora_final
    FROM dbo.gestion_loteproduccion lp
    WHERE lp.orden_produccion_id = @OrdenID
    ORDER BY lp.hora_inicio ASC;

    -- Conjunto 3: Transformaciones Máquina a Máquina
    SELECT 
        t.id,
        t.numero_secuencia,
        p_in.descripcion AS producto_entrada,
        p_out.descripcion AS producto_salida,
        m.nombre AS maquina,
        t.peso_entrada,
        t.peso_salida,
        t.merma,
        t.estado,
        t.fecha_inicio,
        t.fecha_fin
    FROM dbo.gestion_transformacionproducto t
    INNER JOIN dbo.gestion_producto p_in ON p_in.id = t.producto_entrada_id
    INNER JOIN dbo.gestion_producto p_out ON p_out.id = t.producto_salida_id
    INNER JOIN dbo.gestion_maquina m ON m.id = t.maquina_id
    WHERE t.orden_produccion_id = @OrdenID
    ORDER BY t.numero_secuencia ASC;
END
GO

PRINT '=== ACTUALIZACIÓN TOTAL DE STORED PROCEDURES TEXCORE (2026) FINALIZADA CON ÉXITO ===';
GO
