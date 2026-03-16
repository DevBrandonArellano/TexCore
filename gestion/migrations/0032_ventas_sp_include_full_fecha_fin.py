# Incluir todo el día de fecha_fin (fecha_pedido <= @FechaFin excluía ventas del mismo día)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0031_ventas_sp_fecha_como_texto'),
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
                  AND CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                  AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
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
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetTopClientesPorVendedor
                @VendedorID INT,
                @FechaInicio DATE,
                @FechaFin DATE
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.nombre_razon_social AS Cliente,
                    SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) AS TotalComprado,
                    COUNT(DISTINCT pv.id) AS CantidadPedidos
                FROM gestion_pedidoventa pv
                JOIN gestion_cliente c ON pv.cliente_id = c.id
                JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE pv.vendedor_asignado_id = @VendedorID
                  AND CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                  AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
                GROUP BY c.id, c.nombre_razon_social
                ORDER BY TotalComprado DESC;
            END
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
