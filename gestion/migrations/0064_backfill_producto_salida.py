from django.db import migrations


def backfill_producto_salida(apps, schema_editor):
    OrdenProduccion = apps.get_model('gestion', 'OrdenProduccion')
    for op in OrdenProduccion.objects.filter(producto_salida__isnull=True):
        op.producto_salida = op.producto_entrada
        op.bodega_salida = op.bodega_entrada
        op.save(update_fields=['producto_salida', 'bodega_salida'])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0063_consumolotedetalle'),
    ]

    operations = [
        migrations.RunPython(backfill_producto_salida, migrations.RunPython.noop),
    ]
