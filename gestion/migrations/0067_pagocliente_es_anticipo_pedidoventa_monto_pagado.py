# Sprint 2 (10-Jun-2026): Anticipos de cliente (P1-002) y pagos parciales (P1-003)
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0066_maquina_bodega_entrada_maquina_bodega_salida_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagocliente',
            name='es_anticipo',
            field=models.BooleanField(
                default=False,
                help_text='Pago por adelantado: el excedente sobre la deuda queda como saldo a favor',
            ),
        ),
        migrations.AddField(
            model_name='pedidoventa',
            name='monto_pagado',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=12),
        ),
    ]
