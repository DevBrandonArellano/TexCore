# Agrega columna Nro consecutivo (1, 2, 3...) a reportes Ventas y Deudores

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0033_reportes_orden_por_id'),
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
                    ROW_NUMBER() OVER (ORDER BY pv.id) AS Nro,
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
                ORDER BY pv.id ASC;
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
                  AND CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                  AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
                GROUP BY pv.id, pv.fecha_pedido, c.nombre_razon_social, pv.estado, pv.guia_remision
                ORDER BY pv.id ASC;
            END
            """,
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetDeudoresPorVendedor
                @VendedorID INT
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    ROW_NUMBER() OVER (ORDER BY c.id) AS Nro,
                    c.id AS ClienteID,
                    c.ruc_cedula AS RUC,
                    c.nombre_razon_social AS Cliente,
                    c.limite_credito AS LimiteCredito,
                    (ISNULL((
                        SELECT SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00))
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
                        SELECT SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00))
                        FROM gestion_pedidoventa pv
                        JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                        WHERE pv.cliente_id = c.id
                    ), 0) - ISNULL((
                        SELECT SUM(p.monto)
                        FROM gestion_pagocliente p
                        WHERE p.cliente_id = c.id
                    ), 0)) > 0
                ORDER BY c.id ASC;
            END
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
