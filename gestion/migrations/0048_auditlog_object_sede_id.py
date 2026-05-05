from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gestion", "0047_sps_gerencial_filtro_sede"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="object_sede_id",
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True),
        ),
    ]
