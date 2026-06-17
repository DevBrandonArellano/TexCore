# Sprint 4 (10-Jun-2026): P1-008 — estandarización de precisión decimal.
# inventory usaba DECIMAL(12,2) mientras gestion usa DECIMAL(12,3); el redondeo
# cruzado acumulaba error en el Kardex. Ampliar precisión es seguro (sin pérdida
# de datos): SQL Server convierte 10.13 → 10.130.
#
# NOTA SQL Server: los CHECK constraints y el índice con INCLUDE sobre
# 'cantidad'/'saldo_resultante' bloquean ALTER COLUMN — se sueltan antes y se
# recrean después (mismo patrón que 0051_fix_token_blacklist_mssql en gestion).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0029_detallehistorialdespacho_movimiento_venta'),
    ]

    operations = [
        # 1. Soltar dependencias que bloquean ALTER COLUMN en SQL Server
        migrations.RemoveConstraint(
            model_name='movimientoinventario',
            name='inventory_movimientoinventario_cantidad_positiva',
        ),
        migrations.RemoveConstraint(
            model_name='movimientoinventario',
            name='inventory_movimientoinventario_saldo_positivo',
        ),
        migrations.RemoveIndex(
            model_name='movimientoinventario',
            name='idx_mov_bodega_fecha_incl',
        ),

        # 2. Ampliar precisión a 3 decimales
        migrations.AlterField(
            model_name='stockbodega',
            name='cantidad',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='cantidad',
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
        migrations.AlterField(
            model_name='movimientoinventario',
            name='saldo_resultante',
            field=models.DecimalField(decimal_places=3, default=0.0, max_digits=12),
        ),
        migrations.AlterField(
            model_name='historialdespacho',
            name='total_peso',
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),
        migrations.AlterField(
            model_name='detallehistorialdespacho',
            name='peso',
            field=models.DecimalField(decimal_places=3, max_digits=12),
        ),

        # 3. Recrear constraints e índice
        migrations.AddConstraint(
            model_name='movimientoinventario',
            constraint=models.CheckConstraint(
                condition=models.Q(cantidad__gte=0),
                name='inventory_movimientoinventario_cantidad_positiva',
            ),
        ),
        migrations.AddConstraint(
            model_name='movimientoinventario',
            constraint=models.CheckConstraint(
                condition=models.Q(saldo_resultante__gte=0),
                name='inventory_movimientoinventario_saldo_positivo',
            ),
        ),
        migrations.AddIndex(
            model_name='movimientoinventario',
            index=models.Index(
                fields=['bodega_origen', 'fecha'],
                include=['producto', 'cantidad', 'saldo_resultante'],
                name='idx_mov_bodega_fecha_incl',
            ),
        ),
    ]
