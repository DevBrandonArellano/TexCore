"""
Migration 0049 — Índice compuesto en AuditLog para consultas por objeto + fecha.

Mejora el rendimiento de:
- Historial de auditoría de una entidad específica (content_type + object_id + fecha)
- Filtrado en el panel de administración
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0048_auditlog_object_sede_id'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['content_type', 'object_id', 'fecha_hora'],
                name='idx_audit_object_fecha'
            ),
        ),
    ]
