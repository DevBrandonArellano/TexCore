from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0041_add_sede_to_proveedor_and_formula"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            IF NOT EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'idx_pedido_vendedor_fecha_incl'
                  AND object_id = OBJECT_ID('gestion_pedidoventa')
            )
            BEGIN
                CREATE INDEX idx_pedido_vendedor_fecha_incl
                ON gestion_pedidoventa (vendedor_asignado_id, fecha_pedido)
                INCLUDE (cliente_id, sede_id, esta_pagado);
            END
            """,
            reverse_sql="""
            IF EXISTS (
                SELECT 1
                FROM sys.indexes
                WHERE name = 'idx_pedido_vendedor_fecha_incl'
                  AND object_id = OBJECT_ID('gestion_pedidoventa')
            )
            BEGIN
                DROP INDEX idx_pedido_vendedor_fecha_incl ON gestion_pedidoventa;
            END
            """,
        )
    ]

