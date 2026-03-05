"""
Migration 0019: Extiende FormulaColor y DetalleFormula
con campos para version, estado, tipo_sustrato, tipo_calculo y dosificacion.
Migracion aditiva: todos los campos nuevos tienen default o null=True.
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0018_update_deudores_sp'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # --- FormulaColor: nuevos campos ---
        migrations.AddField(
            model_name='formulacolor',
            name='tipo_sustrato',
            field=models.CharField(
                choices=[
                    ('algodon', 'Algodon'),
                    ('poliester', 'Poliester'),
                    ('nylon', 'Nylon'),
                    ('mixto', 'Mixto'),
                    ('otro', 'Otro'),
                ],
                default='algodon',
                help_text='Tipo de fibra o sustrato al que aplica esta formula',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='formulacolor',
            name='version',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Numero de version. Se incrementa al duplicar la formula',
            ),
        ),
        migrations.AddField(
            model_name='formulacolor',
            name='estado',
            field=models.CharField(
                choices=[('en_pruebas', 'En Pruebas'), ('aprobada', 'Aprobada')],
                db_index=True,
                default='en_pruebas',
                help_text='Estado de aprobacion de la formula',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='formulacolor',
            name='creado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='formulas_creadas',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='formulacolor',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='formulacolor',
            name='fecha_modificacion',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='formulacolor',
            name='observaciones',
            field=models.TextField(
                blank=True,
                help_text='Observaciones generales sobre la formula',
                null=True,
            ),
        ),
        migrations.AlterModelOptions(
            name='formulacolor',
            options={
                'ordering': ['codigo', '-version'],
                'verbose_name': 'Formula de Color',
                'verbose_name_plural': 'Formulas de Color',
            },
        ),

        # --- DetalleFormula: campo legacy con default y nuevos campos ---
        migrations.AlterField(
            model_name='detalleformula',
            name='gramos_por_kilo',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='detalleformula',
            name='tipo_calculo',
            field=models.CharField(
                choices=[('gr_l', 'Concentracion (gr/L)'), ('pct', 'Agotamiento (%)')],
                default='gr_l',
                help_text='Metodo de calculo de dosificacion para este insumo',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='detalleformula',
            name='concentracion_gr_l',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Concentracion en gr/L del insumo en el bano de tintura',
                max_digits=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='detalleformula',
            name='porcentaje',
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                help_text='Porcentaje del insumo sobre el peso de la tela (agotamiento)',
                max_digits=6,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='detalleformula',
            name='orden_adicion',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Orden de adicion del insumo al bano (1 = primero)',
            ),
        ),
        migrations.AddField(
            model_name='detalleformula',
            name='notas',
            field=models.TextField(
                blank=True,
                help_text='Observaciones tecnicas del insumo en esta formula',
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='detalleformula',
            name='formula_color',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='detalles',
                to='gestion.formulacolor',
            ),
        ),
        migrations.AlterModelOptions(
            name='detalleformula',
            options={
                'ordering': ['orden_adicion'],
                'verbose_name': 'Detalle de Formula',
                'verbose_name_plural': 'Detalles de Formula',
            },
        ),
    ]
