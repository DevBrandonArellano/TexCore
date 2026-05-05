from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0037_gerencial_reporting_sps'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='pedidoventa',
            name='anulado',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AddField(
            model_name='pedidoventa',
            name='motivo_anulacion',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='pedidoventa',
            name='anulado_por',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='pedidos_anulados',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='pedidoventa',
            name='fecha_anulacion',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
