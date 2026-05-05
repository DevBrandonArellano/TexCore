from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0016_create_mrp_sp'),
    ]

    operations = [
        # 1. Stock Actual por Bodega
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetStockActualBodega
                @BodegaID INT,
                @SedeID INT = NULL,
                @ProductoID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;
                SELECT 
                    p.id AS producto_id,
                    p.codigo AS codigo_producto,
                    p.descripcion AS producto,
                    p.unidad_medida,
                    l.codigo_lote AS lote,
                    s.cantidad AS stock,
                    b.nombre AS bodega,
                    sd.nombre AS sede
                FROM inventory_stockbodega s
                INNER JOIN gestion_producto p ON p.id = s.producto_id
                INNER JOIN gestion_bodega b ON b.id = s.bodega_id
                INNER JOIN gestion_sede sd ON sd.id = b.sede_id
                LEFT JOIN gestion_loteproduccion l ON l.id = s.lote_id
                WHERE s.bodega_id = @BodegaID
                  AND (@SedeID IS NULL OR b.sede_id = @SedeID)
                  AND (@ProductoID IS NULL OR s.producto_id = @ProductoID)
                ORDER BY p.descripcion, l.codigo_lote;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetStockActualBodega"
        ),
        
        # 2. Valorización de Inventario
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetValorizacionInventario
                @BodegaID INT,
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;
                SELECT 
                    p.codigo AS codigo_producto,
                    p.descripcion AS producto,
                    SUM(s.cantidad) AS stock_total,
                    p.precio_base AS precio_unitario,
                    SUM(s.cantidad * p.precio_base) AS valor_total
                FROM inventory_stockbodega s
                INNER JOIN gestion_producto p ON p.id = s.producto_id
                INNER JOIN gestion_bodega b ON b.id = s.bodega_id
                WHERE s.bodega_id = @BodegaID
                  AND (@SedeID IS NULL OR b.sede_id = @SedeID)
                GROUP BY p.codigo, p.descripcion, p.precio_base
                HAVING SUM(s.cantidad) <> 0
                ORDER BY valor_total DESC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetValorizacionInventario"
        ),

        # 3. Inventario Aging (Antigüedad)
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetInventarioAging
                @BodegaID INT,
                @SedeID INT = NULL,
                @DiasMinimos INT = 30
            AS
            BEGIN
                SET NOCOUNT ON;
                WITH UltimoMovimiento AS (
                    SELECT 
                        m.producto_id,
                        MAX(m.fecha) AS fecha_ultimo_mov
                    FROM inventory_movimientoinventario m
                    WHERE (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
                    GROUP BY m.producto_id
                )
                SELECT 
                    p.codigo AS codigo_producto,
                    p.descripcion AS producto,
                    ISNULL(SUM(s.cantidad), 0) AS stock_actual,
                    um.fecha_ultimo_mov AS ultimo_movimiento,
                    DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) AS dias_sin_movimiento,
                    CASE 
                        WHEN DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) > 180 THEN 'Critico (>180d)'
                        WHEN DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) > 90 THEN 'Lento (91-180d)'
                        WHEN DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) > 30 THEN 'Medio (31-90d)'
                        ELSE 'Reciente (0-30d)'
                    END AS estado_aging
                FROM gestion_producto p
                INNER JOIN inventory_stockbodega s ON s.producto_id = p.id
                LEFT JOIN UltimoMovimiento um ON um.producto_id = p.id
                INNER JOIN gestion_bodega b ON b.id = s.bodega_id
                WHERE s.bodega_id = @BodegaID
                  AND (@SedeID IS NULL OR b.sede_id = @SedeID)
                GROUP BY p.codigo, p.descripcion, um.fecha_ultimo_mov
                HAVING (ISNULL(SUM(s.cantidad), 0) > 0) 
                   AND (um.fecha_ultimo_mov IS NULL OR DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) >= @DiasMinimos)
                ORDER BY dias_sin_movimiento DESC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetInventarioAging"
        ),

        # 4. Rotación de Inventario
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetRotacionInventario
                @BodegaID INT,
                @FechaInicio DATETIME,
                @FechaFin DATETIME,
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;
                SELECT 
                    p.codigo AS codigo_producto,
                    p.descripcion AS producto,
                    ISNULL((SELECT SUM(cantidad) FROM inventory_movimientoinventario WHERE producto_id = p.id AND bodega_destino_id = @BodegaID AND fecha BETWEEN @FechaInicio AND @FechaFin), 0) AS entradas,
                    ISNULL((SELECT SUM(cantidad) FROM inventory_movimientoinventario WHERE producto_id = p.id AND bodega_origen_id = @BodegaID AND fecha BETWEEN @FechaInicio AND @FechaFin), 0) AS salidas,
                    ISNULL((SELECT SUM(cantidad) FROM inventory_stockbodega WHERE producto_id = p.id AND bodega_id = @BodegaID), 0) AS stock_actual,
                    CAST(ISNULL((SELECT SUM(cantidad) FROM inventory_movimientoinventario WHERE producto_id = p.id AND bodega_origen_id = @BodegaID AND fecha BETWEEN @FechaInicio AND @FechaFin), 0) / 
                         NULLIF(ISNULL((SELECT SUM(cantidad) FROM inventory_stockbodega WHERE producto_id = p.id AND bodega_id = @BodegaID), 0), 0) AS DECIMAL(10,2)) AS indice_rotacion
                FROM gestion_producto p
                WHERE EXISTS (SELECT 1 FROM inventory_stockbodega WHERE producto_id = p.id AND bodega_id = @BodegaID)
                ORDER BY indice_rotacion DESC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetRotacionInventario"
        ),

        # 5. Resumen de Movimientos (Totales por Tipo)
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetResumenMovimientos
                @BodegaID INT,
                @FechaInicio DATETIME,
                @FechaFin DATETIME,
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;
                SELECT 
                    tipo_movimiento,
                    CASE 
                        WHEN bodega_destino_id = @BodegaID THEN 'ENTRADA'
                        WHEN bodega_origen_id = @BodegaID THEN 'SALIDA'
                        ELSE 'OTRO'
                    END AS direccion,
                    COUNT(*) AS total_operaciones,
                    SUM(cantidad) AS cantidad_total
                FROM inventory_movimientoinventario
                WHERE (bodega_origen_id = @BodegaID OR bodega_destino_id = @BodegaID)
                  AND fecha BETWEEN @FechaInicio AND @FechaFin
                GROUP BY tipo_movimiento, 
                         CASE WHEN bodega_destino_id = @BodegaID THEN 'ENTRADA' WHEN bodega_origen_id = @BodegaID THEN 'SALIDA' ELSE 'OTRO' END
                ORDER BY direccion, cantidad_total DESC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetResumenMovimientos"
        ),
    ]
