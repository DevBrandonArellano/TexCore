from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0059_loteproduccion_clasificacion_calidad_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ordenproduccion',
            old_name='producto',
            new_name='producto_entrada',
        ),
        migrations.RenameField(
            model_name='ordenproduccion',
            old_name='bodega',
            new_name='bodega_entrada',
        ),
    ]
