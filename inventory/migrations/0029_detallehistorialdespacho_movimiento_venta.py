# Sprint 3 (10-Jun-2026): P1-007 — FK directa despacho → movimiento VENTA
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0028_historialdespacho_items_no_despachados'),
    ]

    operations = [
        migrations.AddField(
            model_name='detallehistorialdespacho',
            name='movimiento_venta',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='detalles_despacho',
                to='inventory.movimientoinventario',
            ),
        ),
    ]
