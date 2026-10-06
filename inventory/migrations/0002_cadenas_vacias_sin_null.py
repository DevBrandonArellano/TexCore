"""DJ001 (Ruff): los CharField/TextField opcionales dejan de admitir NULL y usan '' como vacío.

Primero se normalizan los NULL existentes a '' y después se cambia el esquema; así el
ALTER COLUMN ... NOT NULL no falla en SQL Server con filas antiguas.
"""
from django.db import migrations, models

CAMPOS = {
    'historialdespacho': ('observaciones',),
    'movimientoinventario': ('calidad', 'documento_ref', 'observaciones', 'pais'),
    'ordencomprasugerida': ('observaciones',),
}


def nulos_a_vacio(apps, schema_editor):
    for modelo, campos in CAMPOS.items():
        Modelo = apps.get_model('inventory', modelo)
        for campo in campos:
            Modelo.objects.filter(**{f'{campo}__isnull': True}).update(**{campo: ''})


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(nulos_a_vacio, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='historialdespacho',
            name='observaciones',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='calidad',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='documento_ref',
            field=models.CharField(blank=True, db_index=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='observaciones',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='pais',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AlterField(
            model_name='ordencomprasugerida',
            name='observaciones',
            field=models.TextField(blank=True, default=''),
        ),
    ]
