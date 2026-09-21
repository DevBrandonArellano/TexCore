from django.db import migrations, models


def migrate_producto_intermedio_to_colorante(apps, schema_editor):
    Producto = apps.get_model('gestion', 'Producto')
    Producto.objects.filter(tipo='producto_intermedio').update(tipo='colorante')


def reverse_colorante_to_producto_intermedio(apps, schema_editor):
    Producto = apps.get_model('gestion', 'Producto')
    Producto.objects.filter(tipo='colorante').update(tipo='producto_intermedio')


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0012_detallepedido_cantidad_fabricada_and_more'),
    ]

    operations = [
        migrations.RunPython(
            migrate_producto_intermedio_to_colorante,
            reverse_colorante_to_producto_intermedio,
        ),
        migrations.AlterField(
            model_name='producto',
            name='tipo',
            field=models.CharField(
                choices=[
                    ('hilo', 'Hilo'),
                    ('tela', 'Tela'),
                    ('subproducto', 'Subproducto'),
                    ('quimico', 'Químico'),
                    ('insumo', 'Insumo'),
                    ('materia_prima', 'Materia prima'),
                    ('colorante', 'Colorantes'),
                ],
                max_length=20,
            ),
        ),
    ]
