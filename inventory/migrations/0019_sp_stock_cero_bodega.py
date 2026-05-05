from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0018_additional_indexes'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetStockCeroBodega
                @BodegaID INT,
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                -- Productos que tienen registro en la bodega con stock <= 0
                -- y productos del catálogo que nunca han tenido stock en esta bodega
                SELECT
                    p.id AS producto_id,
                    p.codigo AS codigo_producto,
                    p.descripcion AS producto,
                    p.unidad_medida,
                    ISNULL(SUM(s.cantidad), 0) AS stock_actual,
                    b.nombre AS bodega,
                    sd.nombre AS sede,
                    CASE
                        WHEN SUM(s.cantidad) IS NULL THEN 'Sin registro en bodega'
                        WHEN SUM(s.cantidad) <= 0    THEN 'Stock agotado'
                        ELSE 'OK'
                    END AS motivo
                FROM gestion_producto p
                CROSS JOIN gestion_bodega b
                INNER JOIN gestion_sede sd ON sd.id = b.sede_id
                LEFT JOIN inventory_stockbodega s
                    ON s.producto_id = p.id AND s.bodega_id = b.id
                WHERE b.id = @BodegaID
                  AND (@SedeID IS NULL OR b.sede_id = @SedeID)
                GROUP BY
                    p.id, p.codigo, p.descripcion, p.unidad_medida,
                    b.nombre, sd.nombre
                HAVING ISNULL(SUM(s.cantidad), 0) <= 0
                ORDER BY p.descripcion ASC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetStockCeroBodega"
        ),
    ]
