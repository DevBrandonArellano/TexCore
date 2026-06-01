import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0061_add_transformacion_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComponenteMezclaOP',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('porcentaje', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Porcentaje (%)')),
                ('cantidad_kg', models.DecimalField(decimal_places=3, max_digits=12, verbose_name='Cantidad calculada (kg)')),
                ('bodega', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gestion.bodega', verbose_name='Bodega Origen del Componente')),
                ('orden', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='componentes_mezcla', to='gestion.ordenproduccion', verbose_name='Orden de Producción')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gestion.producto', verbose_name='Producto Componente')),
            ],
            options={
                'verbose_name': 'Componente de Mezcla',
            },
        ),
        migrations.AddConstraint(
            model_name='componentemezclaop',
            constraint=models.CheckConstraint(
                check=models.Q(porcentaje__gt=0) & models.Q(porcentaje__lte=100),
                name='componente_porcentaje_rango'
            ),
        ),
        migrations.AlterUniqueTogether(
            name='componentemezclaop',
            unique_together={('orden', 'producto')},
        ),
    ]
