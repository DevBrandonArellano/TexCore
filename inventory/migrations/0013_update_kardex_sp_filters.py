from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0012_alter_sp_getkardexbodega_optional_product'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER PROCEDURE sp_GetKardexBodega
                @BodegaID INT,
                @ProductoID INT = NULL,
                @FechaInicio DATETIME = NULL,
                @FechaFin DATETIME = NULL,
                @ProveedorID INT = NULL,
                @LoteCodigo NVARCHAR(100) = NULL
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
                    CAST(CASE WHEN EXISTS (SELECT 1 FROM inventory_auditoriamovimiento a WHERE a.movimiento_id = m.id) THEN 1 ELSE 0 END AS BIT) AS has_audit
                FROM inventory_movimientoinventario m
                INNER JOIN gestion_producto p ON p.id = m.producto_id
                LEFT JOIN gestion_customuser u ON u.id = m.usuario_id
                LEFT JOIN gestion_loteproduccion l ON l.id = m.lote_id
                WHERE (m.bodega_origen_id = @BodegaID OR m.bodega_destino_id = @BodegaID)
                  AND (@ProductoID IS NULL OR m.producto_id = @ProductoID)
                  AND (@FechaInicio IS NULL OR m.fecha >= @FechaInicio)
                  AND (@FechaFin IS NULL OR m.fecha <= @FechaFin)
                  AND (@ProveedorID IS NULL OR m.proveedor_id = @ProveedorID)
                  AND (@LoteCodigo IS NULL OR l.codigo_lote LIKE '%' + @LoteCodigo + '%')
                ORDER BY m.fecha ASC;
            END
            """,
            reverse_sql="""
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
            """
        ),
    ]
