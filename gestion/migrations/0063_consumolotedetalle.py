import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0062_componentemezclaop'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsumoLoteDetalle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad_consumida', models.DecimalField(decimal_places=3, max_digits=12, verbose_name='Cantidad Consumida (kg)')),
                ('genera_nuevo_lote', models.BooleanField(default=True, verbose_name='¿Genera nuevo código de lote?')),
                ('lote_origen', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='usos_como_input', to='gestion.loteproduccion', verbose_name='Lote de Origen (input)')),
                ('lote_produccion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumos_detalle', to='gestion.loteproduccion', verbose_name='Lote Producido (output)')),
            ],
            options={
                'verbose_name': 'Detalle de Consumo de Lote',
            },
        ),
        migrations.AddConstraint(
            model_name='consumolotedetalle',
            constraint=models.CheckConstraint(
                check=models.Q(cantidad_consumida__gt=0),
                name='consumo_cantidad_positiva'
            ),
        ),
    ]
