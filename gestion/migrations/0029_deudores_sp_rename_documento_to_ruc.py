# Migration para renombrar columna Documento a RUC en reporte de deudores

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0023_detallepedido_subtotal_detallepedido_total_con_iva_and_more'),
    ]

    operations = [
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
                ORDER BY SaldoPendiente DESC;
            END
            ');
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetDeudoresPorVendedor;"
        ),
    ]
