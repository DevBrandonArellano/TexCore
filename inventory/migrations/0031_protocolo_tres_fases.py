# Sprint 6 (10-Jun-2026): Protocolo 3-fase para transiciones entre bodegas.
# Default 'completado' mantiene compatibilidad con todos los movimientos
# históricos (que eran de 1 sola fase).
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0030_estandarizar_decimales_tres_lugares'),
    ]

    operations = [
        migrations.AddField(
            model_name='movimientoinventario',
            name='estado_movimiento',
            field=models.CharField(
                choices=[
                    ('solicitado', 'Reservado - Solicitud creada'),
                    ('en_transito', 'En Tránsito - Entre bodegas'),
                    ('completado', 'Completado - En bodega destino'),
                    ('revertido', 'Revertido - Cancelado'),
                ],
                db_index=True,
                default='completado',
                help_text='Fase del movimiento en transición',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='movimientoinventario',
            name='bodega_transicion',
            field=models.ForeignKey(
                blank=True,
                help_text='Bodega intermedia si es transferencia entre áreas',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='movimientos_en_transito',
                to='gestion.bodega',
            ),
        ),
    ]
