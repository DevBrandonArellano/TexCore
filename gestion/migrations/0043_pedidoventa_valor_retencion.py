# Migration to add missing valor_retencion column before SP migration 0044
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0042_pedidoventa_idx_pedido_vendedor_fecha_incl'),
    ]

    operations = [
        migrations.AddField(
            model_name='pedidoventa',
            name='valor_retencion',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=12),
        ),
    ]
