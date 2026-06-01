import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0060_rename_producto_and_bodega'),
    ]

    operations = [
        migrations.AddField(
            model_name='ordenproduccion',
            name='producto_salida',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='ordenes_como_salida',
                to='gestion.producto',
                verbose_name='Producto de Salida'
            ),
        ),
        migrations.AddField(
            model_name='ordenproduccion',
            name='bodega_salida',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='ordenes_salida',
                to='gestion.bodega',
                verbose_name='Bodega de Salida (PT)'
            ),
        ),
        migrations.AddField(
            model_name='maquina',
            name='producto_merma',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='maquinas_generadoras',
                to='gestion.producto',
                verbose_name='Producto de Merma'
            ),
        ),
        migrations.AddField(
            model_name='maquina',
            name='bodega_merma',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='maquinas_merma',
                to='gestion.bodega',
                verbose_name='Bodega de Merma'
            ),
        ),
    ]
