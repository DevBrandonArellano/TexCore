"""TEX-18 CA-4: LoteProduccion.cantidad_metros pasa de DECIMAL(10, 2) a DECIMAL(12, 4).

Ampliación sin pérdida (más enteros y más decimales): los valores existentes se conservan.
Igual que DetalleOperacionProduccion.cantidad_metros, que ya era DECIMAL(12, 4).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0006_configuracion_empaque_explicita'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loteproduccion',
            name='cantidad_metros',
            field=models.DecimalField(blank=True, decimal_places=4, help_text='Metros reenrollados para telas', max_digits=12, null=True),
        ),
    ]
