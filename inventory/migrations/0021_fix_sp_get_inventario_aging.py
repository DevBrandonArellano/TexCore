from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0020_remove_movimientoinventario_idx_mov_tipo_fecha_and_more'),
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
            reverse_sql="-- No es necesario revertir esto explícitamente ya que reemplaza el anterior SP"
        ),
    ]
