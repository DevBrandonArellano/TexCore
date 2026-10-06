"""DJ001 (Ruff): los CharField/TextField opcionales dejan de admitir NULL y usan '' como vacío.

Primero se normalizan los NULL existentes a '' y después se cambia el esquema; así el
ALTER COLUMN ... NOT NULL no falla en SQL Server con filas antiguas.
"""
from django.db import migrations, models

CAMPOS = {
    'auditlog': ('justificacion',),
    'corridaproduccion': ('observaciones',),
    'descargaquimicoop': ('justificacion',),
    'detalleformula': ('notas',),
    'eventoetiqueta': ('motivo',),
    'fasereceta': ('observaciones',),
    'formulacolor': ('description', 'observaciones'),
    'lineaproduccion': ('descripcion',),
    'loteproduccion': ('presentacion', 'tipo_merma'),
    'operacionproduccion': ('motivo_reversion', 'observaciones'),
    'ordenproduccion': ('observaciones',),
    'ordenproduccionsubproceso': ('motivo_rechazo', 'observaciones'),
    'pagocliente': ('comprobante', 'notas'),
    'pedidoventa': ('motivo_anulacion',),
    'procesotintoreria': ('descripcion',),
    'processstep': ('description',),
    'producto': ('calidad', 'pais_origen', 'presentacion'),
    'transferenciainterarea': ('observaciones',),
    'transformacionproducto': ('observaciones',),
}


def nulos_a_vacio(apps, schema_editor):
    for modelo, campos in CAMPOS.items():
        Modelo = apps.get_model('gestion', modelo)
        for campo in campos:
            Modelo.objects.filter(**{f'{campo}__isnull': True}).update(**{campo: ''})


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0002_fix_token_blacklist_mssql'),
    ]

    operations = [
        migrations.RunPython(nulos_a_vacio, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='auditlog',
            name='justificacion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='corridaproduccion',
            name='observaciones',
            field=models.TextField(blank=True, default='', verbose_name='Observaciones'),
        ),
        migrations.AlterField(
            model_name='descargaquimicoop',
            name='justificacion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='detalleformula',
            name='notas',
            field=models.TextField(blank=True, default='', help_text='Observaciones tecnicas del insumo en esta formula'),
        ),
        migrations.AlterField(
            model_name='eventoetiqueta',
            name='motivo',
            field=models.CharField(blank=True, choices=[('DANIADA', 'Etiqueta Dañada'), ('PERDIDA', 'Etiqueta Perdida'), ('ATASCO', 'Atasco de Impresora'), ('CORRECCION_PESO', 'Corrección de Peso'), ('RECLASIFICACION', 'Reclasificación de Calidad'), ('REEMPAQUE', 'Reempaque'), ('OTRO', 'Otro')], default='', max_length=30),
        ),
        migrations.AlterField(
            model_name='fasereceta',
            name='observaciones',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='formulacolor',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='formulacolor',
            name='observaciones',
            field=models.CharField(blank=True, default='', help_text='Observaciones generales sobre la formula', max_length=500),
        ),
        migrations.AlterField(
            model_name='lineaproduccion',
            name='descripcion',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AlterField(
            model_name='loteproduccion',
            name='presentacion',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='loteproduccion',
            name='tipo_merma',
            field=models.CharField(blank=True, choices=[('maquina', 'Falla Técnica / Máquina'), ('material', 'Calidad de Hilo / Material'), ('setup', 'Arranque / Setup'), ('corte', 'Corte / Empalme'), ('otro', 'Otro')], default='', max_length=50),
        ),
        migrations.AlterField(
            model_name='operacionproduccion',
            name='motivo_reversion',
            field=models.TextField(blank=True, default='', help_text='Justificación obligatoria en caso de anulación o reversión de inventarios.', verbose_name='Motivo de Reversión'),
        ),
        migrations.AlterField(
            model_name='operacionproduccion',
            name='observaciones',
            field=models.TextField(blank=True, default='', verbose_name='Observaciones'),
        ),
        migrations.AlterField(
            model_name='ordenproduccion',
            name='observaciones',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='ordenproduccionsubproceso',
            name='motivo_rechazo',
            field=models.TextField(blank=True, default='', help_text='Si fue rechazado, incluir el motivo'),
        ),
        migrations.AlterField(
            model_name='ordenproduccionsubproceso',
            name='observaciones',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='pagocliente',
            name='comprobante',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='pagocliente',
            name='notas',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='pedidoventa',
            name='motivo_anulacion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='procesotintoreria',
            name='descripcion',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='processstep',
            name='description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='producto',
            name='calidad',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='producto',
            name='pais_origen',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='producto',
            name='presentacion',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='transferenciainterarea',
            name='observaciones',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='transformacionproducto',
            name='observaciones',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
