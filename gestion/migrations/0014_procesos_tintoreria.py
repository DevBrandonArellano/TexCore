"""
Fase 1 de recetas versionadas de tintorería
(docs/superpowers/specs/2026-09-24-recetas-versionadas-tintoreria-design.md §5.1–5.4, §5.6).

- Catálogo ProcesoTintoreria por sede y tabla MaquinaProceso.
- Maquina.volumen_bano_litros (distinto de capacidad_maxima, que es kg/turno).
- FaseReceta.nombre (enum de 5 valores) -> FaseReceta.proceso (FK) + ciclo.
- OrdenProduccion.formula_color: CASCADE -> PROTECT.

La migración de datos es reversible: crea los 5 procesos legacy en cada sede (y un
juego sin sede si hay fórmulas sin sede con fases) y reapunta cada fase; al revertir
restaura `nombre` desde el proceso y borra los procesos legacy.
"""
import django.db.models.deletion
from django.db import migrations, models

# Copia congelada de gestion.models.formula.FASES_LEGACY: una migración no debe
# importar código vivo que pueda cambiar después.
FASES_LEGACY = {
    'pre_tratamiento': ('PRE_TRATAMIENTO', 'Pre-Tratamiento / Blanqueo', 'pre_tratamiento'),
    'tintura': ('TINTURA', 'Tintura Principal', 'colorante'),
    'lavado': ('LAVADO', 'Lavado / Jabonado', 'lavado'),
    'suavizado': ('SUAVIZADO', 'Suavizado / Acabado Final', 'acabado'),
    'auxiliares': ('AUXILIARES', 'Baño de Auxiliares Extras', 'auxiliar'),
}
CODIGO_A_ENUM = {codigo: valor for valor, (codigo, _, _) in FASES_LEGACY.items()}
# Procesos creados después de la migración (no legacy): se revierten al enum de su tipo.
TIPO_A_ENUM = {
    'pre_tratamiento': 'pre_tratamiento',
    'colorante': 'tintura',
    'lavado': 'lavado',
    'acabado': 'suavizado',
    'auxiliar': 'auxiliares',
}


def crear_procesos_y_reapuntar_fases(apps, schema_editor):
    Sede = apps.get_model('gestion', 'Sede')
    FaseReceta = apps.get_model('gestion', 'FaseReceta')
    ProcesoTintoreria = apps.get_model('gestion', 'ProcesoTintoreria')

    sede_ids = list(Sede.objects.values_list('id', flat=True))
    if FaseReceta.objects.filter(formula__sede__isnull=True).exists():
        sede_ids.append(None)

    procesos = {}
    for sede_id in sede_ids:
        for valor, (codigo, nombre, tipo) in FASES_LEGACY.items():
            proceso, _ = ProcesoTintoreria.objects.get_or_create(
                codigo=codigo, sede_id=sede_id, defaults={'nombre': nombre, 'tipo': tipo})
            procesos[(valor, sede_id)] = proceso

    for fase in FaseReceta.objects.select_related('formula').iterator():
        fase.proceso = procesos[(fase.nombre, fase.formula.sede_id)]
        fase.save(update_fields=['proceso'])


def restaurar_nombre_desde_proceso(apps, schema_editor):
    FaseReceta = apps.get_model('gestion', 'FaseReceta')
    ProcesoTintoreria = apps.get_model('gestion', 'ProcesoTintoreria')

    for fase in FaseReceta.objects.select_related('proceso').iterator():
        fase.nombre = CODIGO_A_ENUM.get(fase.proceso.codigo) or TIPO_A_ENUM[fase.proceso.tipo]
        fase.save(update_fields=['nombre'])

    FaseReceta.objects.update(proceso=None)
    ProcesoTintoreria.objects.filter(codigo__in=CODIGO_A_ENUM).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0013_replace_producto_intermedio_with_colorante'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProcesoTintoreria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=50)),
                ('nombre', models.CharField(max_length=100)),
                ('tipo', models.CharField(choices=[
                    ('pre_tratamiento', 'Pre-Tratamiento'),
                    ('colorante', 'Colorante'),
                    ('auxiliar', 'Auxiliar'),
                    ('lavado', 'Lavado'),
                    ('acabado', 'Acabado'),
                ], max_length=20)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('activo', models.BooleanField(default=True)),
                ('sede', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='procesos_tintoreria', to='gestion.sede')),
            ],
            options={
                'verbose_name': 'Proceso de Tintoreria',
                'verbose_name_plural': 'Procesos de Tintoreria',
                'ordering': ['codigo'],
                'unique_together': {('codigo', 'sede')},
            },
        ),
        migrations.CreateModel(
            name='MaquinaProceso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('maquina', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='procesos_asignados', to='gestion.maquina')),
                ('proceso', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='maquinas_asignadas', to='gestion.procesotintoreria')),
            ],
            options={
                'verbose_name': 'Proceso por Maquina',
                'verbose_name_plural': 'Procesos por Maquina',
                'unique_together': {('maquina', 'proceso')},
            },
        ),
        migrations.AddField(
            model_name='maquina',
            name='volumen_bano_litros',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True,
                help_text='Volumen del recipiente de tintura en litros. No confundir con '
                          'capacidad_maxima, que es throughput por turno en kg'),
        ),
        migrations.AddField(
            model_name='fasereceta',
            name='ciclo',
            field=models.PositiveIntegerField(
                blank=True, null=True, help_text='Número de ciclo del proceso en la hoja de tintura'),
        ),
        # Nullable mientras se reapuntan las fases existentes; se endurece al final.
        migrations.AddField(
            model_name='fasereceta',
            name='proceso',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='fases', to='gestion.procesotintoreria'),
        ),
        # `nombre` nullable antes de quitarlo: al revertir, RemoveField lo re-añade en
        # este estado (sin NOT NULL), el RunPython inverso lo rellena y solo entonces la
        # inversa de este AlterField restaura el NOT NULL original.
        migrations.AlterField(
            model_name='fasereceta',
            name='nombre',
            field=models.CharField(max_length=50, null=True, choices=[
                ('pre_tratamiento', 'Pre-Tratamiento / Blanqueo'),
                ('tintura', 'Tintura Principal'),
                ('lavado', 'Lavado / Jabonado'),
                ('suavizado', 'Suavizado / Acabado Final'),
                ('auxiliares', 'Baño de Auxiliares Extras'),
            ]),
        ),
        migrations.RunPython(crear_procesos_y_reapuntar_fases, restaurar_nombre_desde_proceso),
        migrations.RemoveField(
            model_name='fasereceta',
            name='nombre',
        ),
        migrations.AlterField(
            model_name='fasereceta',
            name='proceso',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='fases', to='gestion.procesotintoreria'),
        ),
        migrations.AlterField(
            model_name='ordenproduccion',
            name='formula_color',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                to='gestion.formulacolor'),
        ),
    ]
