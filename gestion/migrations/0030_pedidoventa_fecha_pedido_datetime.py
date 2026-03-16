# Migration para cambiar fecha_pedido de Date a DateTime (fecha y hora real de la venta)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0029_deudores_sp_rename_documento_to_ruc'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pedidoventa',
            name='fecha_pedido',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
