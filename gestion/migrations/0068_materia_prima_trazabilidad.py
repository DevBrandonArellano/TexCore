# Sprint 6 (10-Jun-2026): F0-001 — Trazabilidad de Materia Prima
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gestion', '0067_pagocliente_es_anticipo_pedidoventa_monto_pagado'),
    ]

    operations = [
        migrations.CreateModel(
            name='MateriaPrimaLote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lote_proveedor', models.CharField(db_index=True, max_length=100)),
                ('fecha_recepcion', models.DateField(db_index=True)),
                ('cantidad_kg', models.DecimalField(decimal_places=3, max_digits=12)),
                ('costo_unitario', models.DecimalField(decimal_places=3, max_digits=12)),
                ('certificado_calidad', models.FileField(blank=True, null=True, upload_to='certificados/%Y/%m/')),
                ('numero_documento_entrada', models.CharField(blank=True, max_length=100)),
                ('cantidad_consumida', models.DecimalField(decimal_places=3, default=0, max_digits=12)),
                ('completamente_consumida', models.BooleanField(default=False)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('bodega_recepcion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='materias_primas_recibidas', to='gestion.bodega')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='materias_primas', to='gestion.producto')),
                ('proveedor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lotes_suministrados', to='gestion.proveedor')),
                ('sede', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='materias_primas', to='gestion.sede')),
            ],
            options={
                'verbose_name': 'Materia Prima Lote',
                'verbose_name_plural': 'Materias Primas Lotes',
                'unique_together': {('proveedor', 'lote_proveedor', 'fecha_recepcion')},
            },
        ),
        migrations.CreateModel(
            name='ConsumoMateriaPrima',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cantidad_kg', models.DecimalField(decimal_places=3, max_digits=12)),
                ('porcentaje_utilizado', models.DecimalField(decimal_places=2, max_digits=5, null=True)),
                ('fecha_consumo', models.DateTimeField(auto_now_add=True)),
                ('lote_produccion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='consumos_materia_prima', to='gestion.loteproduccion')),
                ('materia_prima_lote', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumos', to='gestion.materiaprimalote')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Consumo Materia Prima',
                'unique_together': {('lote_produccion', 'materia_prima_lote')},
            },
        ),
        migrations.AddField(
            model_name='loteproduccion',
            name='materias_primas',
            field=models.ManyToManyField(blank=True, related_name='lotes_produccion', through='gestion.ConsumoMateriaPrima', to='gestion.materiaprimalote'),
        ),
        migrations.AddIndex(
            model_name='materiaprimalote',
            index=models.Index(fields=['producto', 'proveedor', '-fecha_recepcion'], name='idx_mp_prod_prov_fecha'),
        ),
        migrations.AddIndex(
            model_name='materiaprimalote',
            index=models.Index(fields=['sede', 'completamente_consumida'], name='idx_mp_sede_consumida'),
        ),
        migrations.AddConstraint(
            model_name='consumomateriaprima',
            constraint=models.CheckConstraint(
                condition=models.Q(cantidad_kg__gt=0),
                name='gestion_consumomp_cantidad_positiva',
            ),
        ),
    ]
