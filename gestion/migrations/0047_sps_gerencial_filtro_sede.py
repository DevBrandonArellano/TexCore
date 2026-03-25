from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0046_sps_gerencial_y_sedes'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetVentasGerencial
                @FechaInicio DATE,
                @FechaFin DATE,
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    pv.id AS PedidoID, 
                    CONVERT(VARCHAR(10), pv.fecha_pedido, 105) AS Fecha,
                    c.nombre_razon_social AS Cliente,
                    u.username AS Vendedor,
                    ISNULL(s.nombre, 'Sin Sede') AS Sede,
                    pv.estado AS Estado,
                    pv.guia_remision AS GuiaRemision,
                    ISNULL(pv.valor_retencion, 0) AS RetencionAplicada,
                    (SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) - ISNULL(pv.valor_retencion, 0)) AS TotalFinalVenta
                FROM gestion_pedidoventa pv
                LEFT JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_customuser u ON pv.vendedor_asignado_id = u.id
                LEFT JOIN gestion_sede s ON u.sede_id = s.id
                LEFT JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                    AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
                    AND (@SedeID IS NULL OR u.sede_id = @SedeID)
                GROUP BY pv.id, pv.fecha_pedido, c.nombre_razon_social, u.username, s.nombre, pv.estado, pv.guia_remision, pv.valor_retencion
                ORDER BY pv.id DESC;
            END
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetTopClientesGerencial
                @FechaInicio DATE,
                @FechaFin DATE,
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.nombre_razon_social AS Cliente,
                    u.username AS Vendedor,
                    ISNULL(s.nombre, 'Sin Sede') AS Sede,
                    SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00)) AS TotalComprado,
                    COUNT(DISTINCT pv.id) AS CantidadPedidos
                FROM gestion_pedidoventa pv
                JOIN gestion_cliente c ON pv.cliente_id = c.id
                LEFT JOIN gestion_customuser u ON pv.vendedor_asignado_id = u.id
                LEFT JOIN gestion_sede s ON u.sede_id = s.id
                JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                WHERE CAST(pv.fecha_pedido AS DATE) >= @FechaInicio 
                    AND CAST(pv.fecha_pedido AS DATE) <= @FechaFin
                    AND (@SedeID IS NULL OR u.sede_id = @SedeID)
                GROUP BY c.id, c.nombre_razon_social, u.username, s.nombre
                ORDER BY TotalComprado DESC;
            END
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetDeudoresGerencial
                @SedeID INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT 
                    c.id AS ClienteID,
                    c.ruc_cedula AS RUC,
                    c.nombre_razon_social AS Cliente,
                    u.username AS Vendedor,
                    ISNULL(s.nombre, 'Sin Sede') AS Sede,
                    c.limite_credito AS LimiteCredito,
                    (ISNULL((
                        SELECT SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00))
                        FROM gestion_pedidoventa pv
                        JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                        WHERE pv.cliente_id = c.id
                    ), 0) - ISNULL((
                        SELECT SUM(pv.valor_retencion)
                        FROM gestion_pedidoventa pv
                        WHERE pv.cliente_id = c.id
                    ), 0) - ISNULL((
                        SELECT SUM(p.monto)
                        FROM gestion_pagocliente p
                        WHERE p.cliente_id = c.id
                    ), 0)) AS SaldoPendiente
                FROM gestion_cliente c
                LEFT JOIN gestion_customuser u ON c.vendedor_asignado_id = u.id
                LEFT JOIN gestion_sede s ON u.sede_id = s.id
                WHERE (ISNULL((
                    SELECT SUM(d.peso * d.precio_unitario * IIF(d.incluye_iva = 1, 1.15, 1.00))
                    FROM gestion_pedidoventa pv
                    JOIN gestion_detallepedido d ON d.pedido_venta_id = pv.id
                    WHERE pv.cliente_id = c.id
                ), 0) - ISNULL((
                    SELECT SUM(pv.valor_retencion)
                    FROM gestion_pedidoventa pv
                    WHERE pv.cliente_id = c.id
                ), 0) - ISNULL((
                    SELECT SUM(p.monto)
                    FROM gestion_pagocliente p
                    WHERE p.cliente_id = c.id
                ), 0)) > 0
                AND (@SedeID IS NULL OR u.sede_id = @SedeID)
                ORDER BY SaldoPendiente DESC;
            END
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
