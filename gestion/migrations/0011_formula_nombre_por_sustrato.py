from django.db import migrations


class Migration(migrations.Migration):
    """Un color tiene una fórmula por tipo de material: la unicidad pasa de
    (nombre_color, sede) a (nombre_color, tipo_sustrato, sede).

    Relajar una restricción única no puede fallar con datos existentes: ninguna fila
    que cumplía la restricción anterior puede incumplir la nueva."""

    dependencies = [
        ("gestion", "0010_cifrar_datos_personales"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="formulacolor",
            unique_together={("codigo", "sede"), ("nombre_color", "tipo_sustrato", "sede")},
        ),
    ]
