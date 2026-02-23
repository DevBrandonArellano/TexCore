# Generated manually for reporting_excel SPs adding Sellers Reporting

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0015_create_reporting_sps'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_GetVentasPorVendedor;
            EXEC('
            CREATE PROCEDURE sp_GetVentasPorVendedor
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
                    SUM(d.peso * d.precio_unitario) AS TotalVenta
                FROM gestion_pedidoventa pv
                LEFT JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE pv.vendedor_asignado_id = @VendedorID
                  AND pv.fecha_pedido >= @FechaInicio 
                  AND pv.fecha_pedido <= @FechaFin
                GROUP BY pv.id, pv.fecha_pedido, c.nombre_razon_social, pv.estado, pv.guia_remision
                ORDER BY pv.fecha_pedido DESC;
            END
            ');
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetVentasPorVendedor;"
        ),
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_GetTopClientesPorVendedor;
            EXEC('
            CREATE PROCEDURE sp_GetTopClientesPorVendedor
                @VendedorID INT,
                @FechaInicio DATE,
                @FechaFin DATE
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.nombre_razon_social AS Cliente,
                    SUM(d.peso * d.precio_unitario) AS TotalComprado,
                    COUNT(DISTINCT pv.id) AS CantidadPedidos
                FROM gestion_pedidoventa pv
                JOIN gestion_cliente c ON pv.cliente_id = c.id
                JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE pv.vendedor_asignado_id = @VendedorID
                  AND pv.fecha_pedido >= @FechaInicio 
                  AND pv.fecha_pedido <= @FechaFin
                GROUP BY c.id, c.nombre_razon_social
                ORDER BY TotalComprado DESC;
            END
            ');
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetTopClientesPorVendedor;"
        ),
        migrations.RunSQL(
            sql="""
            DROP PROCEDURE IF EXISTS sp_GetDeudoresPorVendedor;
            EXEC('
            CREATE PROCEDURE sp_GetDeudoresPorVendedor
                @VendedorID INT
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.id AS ClienteID,
                    c.ruc_cedula AS Documento,
                    c.nombre_razon_social AS Cliente,
                    c.limite_credito AS LimiteCredito,
                    (ISNULL((
                        SELECT SUM(d.peso * d.precio_unitario)
                        FROM gestion_pedidoventa pv
                        JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                        WHERE pv.cliente_id = c.id
                    ), 0) - ISNULL((
                        SELECT SUM(p.monto)
                        FROM gestion_pagocliente p
                        WHERE p.cliente_id = c.id
                    ), 0)) AS SaldoPendiente
                FROM gestion_cliente c
                WHERE c.vendedor_asignado_id = @VendedorID
                  AND (ISNULL((
                        SELECT SUM(d.peso * d.precio_unitario)
                        FROM gestion_pedidoventa pv
                        JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                        WHERE pv.cliente_id = c.id
                    ), 0) - ISNULL((
                        SELECT SUM(p.monto)
                        FROM gestion_pagocliente p
                        WHERE p.cliente_id = c.id
                    ), 0)) > 0
                ORDER BY SaldoPendiente DESC;
            END
            ');
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetDeudoresPorVendedor;"
        )
    ]
