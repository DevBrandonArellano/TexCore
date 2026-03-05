# Generated manually - Creates sp_GetRetroKardex and updates sp_GetKardexBodega

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0011_movimientoinventario_calidad_and_more'),
    ]

    operations = [
        # 1. Actualizar sp_GetKardexBodega para hacer @ProductoID opcional
        #    y agregar columnas de producto
        migrations.RunSQL(
            sql="""
            ALTER PROCEDURE sp_GetKardexBodega
                @BodegaID INT,
                @ProductoID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    m.id,
                    CONVERT(VARCHAR(19), m.fecha, 120) AS fecha,
                    m.tipo_movimiento,
                    m.documento_ref,
                    m.cantidad,
                    m.saldo_resultante,
                    m.bodega_origen_id,
                    m.bodega_destino_id,
                    p.codigo AS codigo_producto,
                    p.descripcion AS descripcion_producto
                FROM inventory_movimientoinventario m
                INNER JOIN gestion_producto p ON p.id = m.producto_id
                WHERE (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
                  AND (@ProductoID IS NULL OR m.producto_id = @ProductoID)
                ORDER BY m.fecha ASC;
            END
            """,
            reverse_sql="""
            ALTER PROCEDURE sp_GetKardexBodega
                @BodegaID INT,
                @ProductoID INT
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    m.id,
                    CONVERT(VARCHAR(19), m.fecha, 120) AS fecha,
                    m.tipo_movimiento,
                    m.documento_ref,
                    m.cantidad,
                    m.saldo_resultante,
                    m.bodega_origen_id,
                    m.bodega_destino_id
                FROM inventory_movimientoinventario m
                WHERE m.producto_id = @ProductoID
                  AND (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
                ORDER BY m.fecha ASC;
            END
            """
        ),

        # 2. Crear sp_GetRetroKardex - Calcula stock a una fecha pasada
        #    usando la base de datos para todo el procesamiento
        migrations.RunSQL(
            sql="""
            CREATE PROCEDURE sp_GetRetroKardex
                @FechaCorte DATETIME,
                @ProductoID INT = NULL,
                @BodegaID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                -- CTE que calcula entradas (bodega_destino) y salidas (bodega_origen)
                -- agrupadas por producto y bodega, filtrando hasta la fecha de corte
                ;WITH Entradas AS (
                    SELECT 
                        m.producto_id,
                        m.bodega_destino_id AS bodega_id,
                        SUM(m.cantidad) AS total_entrada
                    FROM inventory_movimientoinventario m
                    WHERE m.fecha <= @FechaCorte
                      AND m.bodega_destino_id IS NOT NULL
                      AND (@ProductoID IS NULL OR m.producto_id = @ProductoID)
                      AND (@BodegaID IS NULL OR m.bodega_destino_id = @BodegaID)
                    GROUP BY m.producto_id, m.bodega_destino_id
                ),
                Salidas AS (
                    SELECT 
                        m.producto_id,
                        m.bodega_origen_id AS bodega_id,
                        SUM(m.cantidad) AS total_salida
                    FROM inventory_movimientoinventario m
                    WHERE m.fecha <= @FechaCorte
                      AND m.bodega_origen_id IS NOT NULL
                      AND (@ProductoID IS NULL OR m.producto_id = @ProductoID)
                      AND (@BodegaID IS NULL OR m.bodega_origen_id = @BodegaID)
                    GROUP BY m.producto_id, m.bodega_origen_id
                ),
                StockCalculado AS (
                    SELECT 
                        COALESCE(e.producto_id, s.producto_id) AS producto_id,
                        COALESCE(e.bodega_id, s.bodega_id) AS bodega_id,
                        ISNULL(e.total_entrada, 0) - ISNULL(s.total_salida, 0) AS stock_calculado
                    FROM Entradas e
                    FULL OUTER JOIN Salidas s 
                        ON e.producto_id = s.producto_id AND e.bodega_id = s.bodega_id
                )
                SELECT 
                    p.descripcion AS producto,
                    p.codigo AS codigo_producto,
                    b.nombre AS bodega,
                    sc.stock_calculado
                FROM StockCalculado sc
                INNER JOIN gestion_producto p ON p.id = sc.producto_id
                INNER JOIN gestion_bodega b ON b.id = sc.bodega_id
                WHERE sc.stock_calculado <> 0
                ORDER BY p.descripcion, b.nombre;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetRetroKardex"
        ),
    ]
