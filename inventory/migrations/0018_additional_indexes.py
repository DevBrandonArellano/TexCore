"""
Migration 0018 — Índices adicionales para consultas frecuentes.

Añade índices que mejoran el rendimiento de:
- Kardex filtrado por tipo_movimiento + fecha
- Kardex filtrado por producto + fecha
- AuditLog filtrado por objeto + fecha (para historial por entidad)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0017_reporting_sps'),
    ]

    operations = [
        # Índice para consultas de Kardex por tipo de movimiento y fecha
        migrations.AddIndex(
            model_name='movimientoinventario',
            index=models.Index(
                fields=['tipo_movimiento', 'fecha'],
                name='idx_mov_tipo_fecha'
            ),
        ),
        # Índice para consultas de historial por producto en un rango de fechas
        migrations.AddIndex(
            model_name='movimientoinventario',
            index=models.Index(
                fields=['producto', 'fecha'],
                name='idx_mov_producto_fecha'
            ),
        ),
    ]
