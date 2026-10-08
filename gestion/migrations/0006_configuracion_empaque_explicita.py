"""TEX-43 CA-3: las equivalencias de empaque dejan de tener un valor del sistema.

Hasta ahora una sede sin ConfiguracionEmpaqueSede usaba en silencio 1 baño = 15 fundas
= 225 conos. Desde esta versión, sin configuración se avisa en lugar de convertir. Para
que el despliegue no cambie el comportamiento de las sedes que ya operan, se les crea
su configuración explícita con esos mismos valores (15/15); las sedes nuevas la
registra su Administrador de Sede. Después se quitan los `default` del modelo.
"""
import django.core.validators
from django.db import migrations, models

FUNDAS_POR_BANO = 15
CONOS_POR_FUNDA = 15


def crear_configuracion_existente(apps, schema_editor):
    Sede = apps.get_model('gestion', 'Sede')
    ConfiguracionEmpaqueSede = apps.get_model('gestion', 'ConfiguracionEmpaqueSede')
    ConfiguracionEmpaqueSede.objects.bulk_create([
        ConfiguracionEmpaqueSede(sede=sede, fundas_por_bano=FUNDAS_POR_BANO, conos_por_funda=CONOS_POR_FUNDA)
        for sede in Sede.objects.filter(configuracion_empaque__isnull=True)
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0005_rellenar_auditlog_usuario_sede'),
    ]

    operations = [
        migrations.RunPython(crear_configuracion_existente, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='configuracionempaquesede',
            name='conos_por_funda',
            field=models.PositiveIntegerField(
                help_text='1 funda = N conos', validators=[django.core.validators.MinValueValidator(1)]),
        ),
        migrations.AlterField(
            model_name='configuracionempaquesede',
            name='fundas_por_bano',
            field=models.PositiveIntegerField(
                help_text='1 baño = N fundas', validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]
