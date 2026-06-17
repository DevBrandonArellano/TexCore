# Sprint 6 (10-Jun-2026): F0-002 — Costeo de Producción por Lote
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gestion', '0068_materia_prima_trazabilidad'),
    ]

    operations = [
        migrations.CreateModel(
            name='TarifaOperario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_contrato', models.CharField(choices=[('tiempo', 'Por Tiempo'), ('pieza', 'Por Pieza')], default='tiempo', max_length=20)),
                ('tarifa_hora', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('tarifa_pieza', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('vigente_desde', models.DateField()),
                ('vigente_hasta', models.DateField(blank=True, null=True)),
                ('operario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tarifas', to=settings.AUTH_USER_MODEL)),
                ('sede', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion.sede')),
            ],
            options={
                'verbose_name': 'Tarifa de Operario',
                'unique_together': {('operario', 'vigente_desde', 'sede')},
            },
        ),
        migrations.CreateModel(
            name='CostoHoraMaquina',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('costo_hora', models.DecimalField(decimal_places=2, max_digits=8)),
                ('vigente_desde', models.DateField()),
                ('vigente_hasta', models.DateField(blank=True, null=True)),
                ('maquina', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='costos_hora', to='gestion.maquina')),
            ],
            options={
                'verbose_name': 'Costo Hora Maquina',
                'unique_together': {('maquina', 'vigente_desde')},
            },
        ),
        migrations.CreateModel(
            name='CostoLoteProduccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('costo_materia_prima', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('costo_quimicos', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('costo_operario', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('costo_maquina', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('otros_costos', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('total_costo', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('precio_venta_esperado', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('margen_bruto', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('margen_bruto_pct', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('calculado_en', models.DateTimeField(auto_now_add=True)),
                ('recalculado_en', models.DateTimeField(blank=True, null=True)),
                ('lote_produccion', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='costo', to='gestion.loteproduccion')),
            ],
            options={
                'verbose_name': 'Costo Lote Produccion',
                'ordering': ['-calculado_en'],
            },
        ),
    ]
