# Reportes gerenciales consolidados (sin filtro por vendedor) para ejecutivos

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0036_merge_20260312_1702'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetVentasGerencial
                @FechaInicio DATE,
                @FechaFin DATE
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    pv.id AS PedidoID, 
                    CONVERT(VARCHAR(10), pv.fecha_pedido, 105) AS Fecha,
                    c.nombre_razon_social AS Cliente,
                    u.username AS Vendedor,
                    pv.estado AS Estado,
                    pv.guia_remision AS GuiaRemision,
                    SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) AS TotalVenta
                FROM gestion_pedidoventa pv
                LEFT JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_customuser u ON pv.vendedor_asignado_id = u.id
                LEFT JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                  AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
                GROUP BY pv.id, pv.fecha_pedido, c.nombre_razon_social, u.username, pv.estado, pv.guia_remision
                ORDER BY pv.id ASC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetVentasGerencial;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetTopClientesGerencial
                @FechaInicio DATE,
                @FechaFin DATE
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.nombre_razon_social AS Cliente,
                    u.username AS Vendedor,
                    SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) AS TotalComprado,
                    COUNT(DISTINCT pv.id) AS CantidadPedidos
                FROM gestion_pedidoventa pv
                JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_customuser u ON pv.vendedor_asignado_id = u.id
                JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                  AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
                GROUP BY c.id, c.nombre_razon_social, u.username
                ORDER BY TotalComprado DESC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetTopClientesGerencial;",
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetDeudoresGerencial
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.id AS ClienteID,
                    c.ruc_cedula AS RUC,
                    c.nombre_razon_social AS Cliente,
                    u.username AS Vendedor,
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
                LEFT JOIN gestion_customuser u ON c.vendedor_asignado_id = u.id
                WHERE (ISNULL((
                    SELECT SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00))
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
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetDeudoresGerencial;",
        ),
    ]
