from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0021_fix_sp_get_inventario_aging'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetInventarioAging
                @BodegaID INT,
                @SedeID INT = NULL,
                @DiasMinimos INT = 30
            AS
            BEGIN
                SET NOCOUNT ON;
                /*
                 * @DiasMinimos selecciona el RANGO de antigüedad (bucket), no un mínimo suelto:
                 *   30  → Reciente (0-30 días sin movimiento)
                 *   60  → Medio (31-90 días)
                 *   90  → Lento (91-180 días)
                 *   180 → Crítico (>180 días o sin ningún movimiento en la bodega)
                 */
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
                    ISNULL(DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()), 9999) AS dias_sin_movimiento,
                    CASE
                        WHEN um.fecha_ultimo_mov IS NULL THEN 'Critico (>180d) - Sin Mov.'
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
                   AND (
                        (@DiasMinimos = 30
                         AND um.fecha_ultimo_mov IS NOT NULL
                         AND DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) BETWEEN 0 AND 30)
                     OR (@DiasMinimos = 60
                         AND um.fecha_ultimo_mov IS NOT NULL
                         AND DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) BETWEEN 31 AND 90)
                     OR (@DiasMinimos = 90
                         AND um.fecha_ultimo_mov IS NOT NULL
                         AND DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) BETWEEN 91 AND 180)
                     OR (@DiasMinimos = 180
                         AND (um.fecha_ultimo_mov IS NULL
                              OR DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) > 180))
                     OR (@DiasMinimos NOT IN (30, 60, 90, 180)
                         AND um.fecha_ultimo_mov IS NOT NULL
                         AND DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()) BETWEEN 0 AND 30)
                   )
                ORDER BY dias_sin_movimiento DESC;
            END
            """,
            reverse_sql="""
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
                    ISNULL(DATEDIFF(DAY, um.fecha_ultimo_mov, GETDATE()), 9999) AS dias_sin_movimiento,
                    CASE
                        WHEN um.fecha_ultimo_mov IS NULL THEN 'Critico (>180d) - Sin Mov.'
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
        ),
    ]
