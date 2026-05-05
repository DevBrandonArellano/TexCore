from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0040_add_cliente_producto_sede_db"),
    ]

    operations = [
        migrations.AddField(
            model_name="proveedor",
            name="sede",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="proveedores",
                to="gestion.sede",
            ),
        ),
        migrations.AddField(
            model_name="formulacolor",
            name="sede",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="formulas_color",
                to="gestion.sede",
            ),
        ),
    ]

