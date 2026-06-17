from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0027_alter_movimientoinventario_tipo_movimiento'),
    ]

    operations = [
        migrations.AddField(
            model_name='historialdespacho',
            name='items_no_despachados',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Productos del pedido no cubiertos completamente. Ej: {"Hilo Nylon": {"requerido": 100.0, "escaneado": 60.0, "faltante": 40.0}}',
            ),
        ),
    ]
