# Generated migration for DescargaQuimicoOP and bodega_quimicos field
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0021_proveedor'),
    ]

    operations = [
        # Agregar campo bodega_quimicos a OrdenProduccion
        migrations.AddField(
            model_name='ordenproduccion',
            name='bodega_quimicos',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordenes_quimicos', to='gestion.bodega'),
        ),
        # Agregar campo fecha_modificacion a OrdenProduccion
        migrations.AddField(
            model_name='ordenproduccion',
            name='fecha_modificacion',
            field=models.DateTimeField(auto_now=True),
        ),
        # Crear modelo DescargaQuimicoOP
        migrations.CreateModel(
            name='DescargaQuimicoOP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_calculo', models.CharField(choices=[('gr_l', 'Concentración (gr/L)'), ('pct', 'Agotamiento (%)')], default='gr_l', max_length=10)),
                ('cantidad_calculada_kg', models.DecimalField(decimal_places=6, max_digits=12)),
                ('cantidad_real_kg', models.DecimalField(blank=True, decimal_places=6, max_digits=12, null=True)),
                ('estado', models.CharField(choices=[('aplicada', 'Aplicada'), ('revertida', 'Revertida')], default='aplicada', max_length=20)),
                ('fecha_descarga', models.DateTimeField(auto_now_add=True)),
                ('justificacion', models.TextField(blank=True, null=True)),
                ('bodega', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gestion.bodega')),
                ('descargado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('fase', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion.fasereceta')),
                ('orden_produccion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='descargas_quimicos', to='gestion.ordenproduccion')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='gestion.producto')),
            ],
            options={
                'verbose_name': 'Descarga Química OP',
                'verbose_name_plural': 'Descargas Químicas OP',
                'ordering': ['-fecha_descarga'],
            },
        ),
        # Índices agregados en migración separada debido a problema de orden
    ]
