# Generated manually for reporting_excel SPs

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0014_maquina_operarios'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetKardexBodega
                @BodegaID INT,
                @ProductoID INT
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    m.id,
                    m.fecha,
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
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetKardexBodega;"
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetProductosCatalogo
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    p.id,
                    p.codigo,
                    p.descripcion,
                    p.tipo,
                    p.unidad_medida,
                    p.stock_minimo,
                    p.precio_base
                FROM gestion_producto p
                ORDER BY p.descripcion ASC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetProductosCatalogo;"
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetUsuariosSistema
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    u.id,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.email,
                    CAST(u.is_active AS INT) AS is_active,
                    a.nombre AS area_nombre,
                    s.nombre AS sede_nombre
                FROM gestion_customuser u
                LEFT JOIN gestion_area a ON u.area_id = a.id
                LEFT JOIN gestion_sede s ON u.sede_id = s.id
                ORDER BY u.username ASC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetUsuariosSistema;"
        )
    ]
