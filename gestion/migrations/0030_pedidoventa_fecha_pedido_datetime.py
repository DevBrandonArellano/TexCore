# Migration para cambiar fecha_pedido de Date a DateTime (fecha y hora real de la venta)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0029_deudores_sp_rename_documento_to_ruc'),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS idx_pedido_vendedor_fecha_incl ON dbo.gestion_pedidoventa;",
            reverse_sql="""
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'idx_pedido_vendedor_fecha_incl' AND object_id = OBJECT_ID(N'dbo.gestion_pedidoventa'))
            BEGIN
                CREATE NONCLUSTERED INDEX idx_pedido_vendedor_fecha_incl ON dbo.gestion_pedidoventa (vendedor_asignado_id, fecha_pedido) INCLUDE (cliente_id, estado);
            END
            """,
        ),
        migrations.AlterField(
            model_name='pedidoventa',
            name='fecha_pedido',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.RunSQL(
            sql="""
            IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'idx_pedido_vendedor_fecha_incl' AND object_id = OBJECT_ID(N'dbo.gestion_pedidoventa'))
            BEGIN
                CREATE NONCLUSTERED INDEX idx_pedido_vendedor_fecha_incl ON dbo.gestion_pedidoventa (vendedor_asignado_id, fecha_pedido) INCLUDE (cliente_id, estado);
            END
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_pedido_vendedor_fecha_incl ON dbo.gestion_pedidoventa;",
        ),
    ]
