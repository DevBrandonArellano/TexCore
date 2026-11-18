import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

# Copia congelada de MaterialSustrato.MATERIALES_BASE: una migración no debe depender
# del código vivo del modelo.
MATERIALES_BASE = [
    ("algodon", "Algodón"),
    ("poliester", "Poliéster"),
    ("nylon", "Nylon"),
    ("mixto", "Mixto"),
    ("otro", "Otro"),
]


def sembrar_catalogo(apps, schema_editor):
    """Cada sede recibe los materiales base y cualquier otra clave que ya usen sus
    fórmulas, para que ninguna fórmula existente quede sin material en el catálogo."""
    Sede = apps.get_model("gestion", "Sede")
    FormulaColor = apps.get_model("gestion", "FormulaColor")
    MaterialSustrato = apps.get_model("gestion", "MaterialSustrato")
    nombres_base = dict(MATERIALES_BASE)

    for sede in Sede.objects.all():
        claves = set(nombres_base)
        claves |= set(FormulaColor.objects.filter(sede=sede).values_list("tipo_sustrato", flat=True).distinct())
        MaterialSustrato.objects.bulk_create(
            [
                MaterialSustrato(clave=clave, nombre=nombres_base.get(clave, clave.capitalize()), sede=sede)
                for clave in sorted(c for c in claves if c)
            ]
        )


class Migration(migrations.Migration):
    """Catálogo de materiales (tipo de sustrato) por sede, creable por el tintorero.

    FormulaColor.tipo_sustrato sigue guardando la clave como texto (sin cambio de datos):
    solo pierde la lista fija de opciones."""

    dependencies = [
        ("gestion", "0011_formula_nombre_por_sustrato"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialSustrato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clave", models.CharField(editable=False, max_length=20)),
                (
                    "nombre",
                    models.CharField(max_length=60, validators=[django.core.validators.MinLengthValidator(2)]),
                ),
                ("activo", models.BooleanField(default=True)),
                (
                    "sede",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="materiales_sustrato",
                        to="gestion.sede",
                    ),
                ),
            ],
            options={
                "verbose_name": "Material (tipo de sustrato)",
                "verbose_name_plural": "Materiales (tipos de sustrato)",
                "ordering": ["nombre"],
                "unique_together": {("clave", "sede")},
            },
        ),
        migrations.AlterField(
            model_name="formulacolor",
            name="tipo_sustrato",
            field=models.CharField(
                default="algodon",
                help_text="Clave del material (MaterialSustrato de la sede) al que aplica esta formula",
                max_length=20,
            ),
        ),
        migrations.RunPython(sembrar_catalogo, migrations.RunPython.noop),
    ]
