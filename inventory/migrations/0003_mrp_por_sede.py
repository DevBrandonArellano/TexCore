"""MRP por sede (ADR-012).

- `MRPEjecucion`: cada corrida del motor por sede, con su resultado y sus advertencias.
- `RequerimientoMaterial` pasa a vincularse a la orden de producción que lo origina y a
  la corrida que lo calculó (deja `origen_tipo`/`origen_id`: los pedidos ya no generan
  requerimientos de compra, sino necesidad de producción).
- `OrdenCompraSugerida` es informativa: pierde `estado` y `observaciones` y guarda su
  desglose (requerido, stock mínimo, disponible).

Los requerimientos y las sugerencias son datos calculados: se borran antes de cambiar
el esquema y se regeneran con la próxima ejecución del MRP. Las columnas obligatorias
se agregan admitiendo NULL y se endurecen después, sobre tablas ya vacías.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def borrar_resultados_calculados(apps, schema_editor):
    apps.get_model('inventory', 'RequerimientoMaterial').objects.all().delete()
    apps.get_model('inventory', 'OrdenCompraSugerida').objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0008_auditlog_indice_fecha_sedes'),
        ('inventory', '0002_cadenas_vacias_sin_null'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(borrar_resultados_calculados, migrations.RunPython.noop),
        migrations.CreateModel(
            name='MRPEjecucion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('inicio', models.DateTimeField()),
                ('fin', models.DateTimeField()),
                ('estado', models.CharField(
                    choices=[('completada', 'Completada'), ('fallida', 'Fallida')], max_length=20)),
                ('requerimientos', models.PositiveIntegerField(default=0)),
                ('sugerencias_compra', models.PositiveIntegerField(default=0)),
                ('productos_a_producir', models.PositiveIntegerField(default=0)),
                ('advertencias', models.JSONField(blank=True, default=list)),
                ('mensaje_error', models.TextField(blank=True, default='')),
                ('iniciada_por', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='ejecuciones_mrp', to=settings.AUTH_USER_MODEL)),
                ('sede', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, related_name='ejecuciones_mrp', to='gestion.sede')),
            ],
            options={
                'verbose_name': 'Ejecución del MRP',
                'verbose_name_plural': 'Ejecuciones del MRP',
                'ordering': ['-inicio', '-id'],
                'indexes': [models.Index(fields=['sede', '-inicio'], name='inventory_m_sede_id_0c8697_idx')],
            },
        ),
        # --- OrdenCompraSugerida: informativa, sin estados ---------------------------
        migrations.AlterUniqueTogether(name='ordencomprasugerida', unique_together=set()),
        migrations.RemoveField(model_name='ordencomprasugerida', name='estado'),
        migrations.RemoveField(model_name='ordencomprasugerida', name='observaciones'),
        migrations.AddField(
            model_name='ordencomprasugerida',
            name='ejecucion',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='sugerencias', to='inventory.mrpejecucion'),
        ),
        migrations.AlterField(
            model_name='ordencomprasugerida',
            name='ejecucion',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sugerencias', to='inventory.mrpejecucion'),
        ),
        migrations.AddField(
            model_name='ordencomprasugerida',
            name='requerido',
            field=models.DecimalField(
                decimal_places=3, default=0, max_digits=12,
                help_text='Suma de lo que piden las órdenes abiertas (kg)'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ordencomprasugerida',
            name='stock_minimo',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='ordencomprasugerida',
            name='stock_disponible',
            field=models.DecimalField(
                decimal_places=3, default=0, max_digits=12,
                help_text='Stock de la sede menos lo comprometido (kg)'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='ordencomprasugerida',
            name='cantidad_sugerida',
            field=models.DecimalField(
                decimal_places=3, max_digits=12, help_text='Requerido + stock mínimo − disponible (kg)'),
        ),
        migrations.AddConstraint(
            model_name='ordencomprasugerida',
            constraint=models.UniqueConstraint(
                fields=('ejecucion', 'producto'), name='inventory_sugerencia_unica_por_ejecucion'),
        ),
        # --- RequerimientoMaterial: por orden de producción ---------------------------
        migrations.RemoveField(model_name='requerimientomaterial', name='origen_tipo'),
        migrations.RemoveField(model_name='requerimientomaterial', name='origen_id'),
        migrations.RemoveField(model_name='requerimientomaterial', name='fecha_calculo'),
        migrations.AddField(
            model_name='requerimientomaterial',
            name='ejecucion',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='requerimientos_material', to='inventory.mrpejecucion'),
        ),
        migrations.AlterField(
            model_name='requerimientomaterial',
            name='ejecucion',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='requerimientos_material', to='inventory.mrpejecucion'),
        ),
        migrations.AddField(
            model_name='requerimientomaterial',
            name='orden_produccion',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='requerimientos_mrp', to='gestion.ordenproduccion'),
        ),
        migrations.AlterField(
            model_name='requerimientomaterial',
            name='orden_produccion',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='requerimientos_mrp', to='gestion.ordenproduccion'),
        ),
        migrations.AlterField(
            model_name='requerimientomaterial',
            name='cantidad_necesaria',
            field=models.DecimalField(decimal_places=3, help_text='Cantidad en kg', max_digits=12),
        ),
    ]
