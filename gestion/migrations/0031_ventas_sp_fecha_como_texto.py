# Formatea Fecha como texto dd-mm-yyyy en el SP para evitar problemas en Excel

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0030_pedidoventa_fecha_pedido_datetime'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetVentasPorVendedor
                @VendedorID INT,
                @FechaInicio DATE,
                @FechaFin DATE
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    pv.id AS PedidoID, 
                    CONVERT(VARCHAR(10), pv.fecha_pedido, 105) AS Fecha,
                    c.nombre_razon_social AS Cliente,
                    pv.estado AS Estado,
                    pv.guia_remision AS GuiaRemision,
                    SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) AS TotalVenta
                FROM gestion_pedidoventa pv
                LEFT JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE pv.vendedor_asignado_id = @VendedorID
                  AND pv.fecha_pedido >= @FechaInicio 
                  AND pv.fecha_pedido <= @FechaFin
                GROUP BY pv.id, pv.fecha_pedido, c.nombre_razon_social, pv.estado, pv.guia_remision
                ORDER BY pv.fecha_pedido DESC;
            END
            """,
            reverse_sql="""
            CREATE OR ALTER PROCEDURE sp_GetVentasPorVendedor
                @VendedorID INT,
                @FechaInicio DATE,
                @FechaFin DATE
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    pv.id AS PedidoID, 
                    pv.fecha_pedido AS Fecha,
                    c.nombre_razon_social AS Cliente,
                    pv.estado AS Estado,
                    pv.guia_remision AS GuiaRemision,
                    SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) AS TotalVenta
                FROM gestion_pedidoventa pv
                LEFT JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE pv.vendedor_asignado_id = @VendedorID
                  AND pv.fecha_pedido >= @FechaInicio 
                  AND pv.fecha_pedido <= @FechaFin
                GROUP BY pv.id, pv.fecha_pedido, c.nombre_razon_social, pv.estado, pv.guia_remision
                ORDER BY pv.fecha_pedido DESC;
            END
            """,
        ),
    ]
