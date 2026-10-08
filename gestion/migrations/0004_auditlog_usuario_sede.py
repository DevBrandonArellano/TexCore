"""AuditLog.usuario_sede_id y dos índices compuestos para el listado por sede.

El listado filtra `usuario_sede_id OR object_sede_id` en los últimos 30 días; cada rama
tiene su índice (sede, -fecha_hora). El índice simple de object_sede_id se retira porque
el compuesto empieza por esa columna. El relleno de las filas existentes va en 0005.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('gestion', '0003_cadenas_vacias_sin_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditlog',
            name='usuario_sede_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='object_sede_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['object_sede_id', '-fecha_hora'], name='idx_audit_objsede_fecha'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['usuario_sede_id', '-fecha_hora'], name='idx_audit_usrsede_fecha'),
        ),
    ]
