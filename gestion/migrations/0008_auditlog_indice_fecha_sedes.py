"""RD-06: un índice por fecha que incluye las dos sedes reemplaza a los de la 0004.

Con un índice por cada rama de `usuario_sede_id OR object_sede_id`, SQL Server 2022 no
buscaba por sede: recorría los dos índices completos y los cruzaba. Sobre ~1 M de
auditorías, el COUNT de la paginación hacía ~10 000 lecturas y era el 40 % de la CPU de
la base con 250 usuarios (Query Store, 8-oct-2026). El listado siempre acota por fecha,
así que basta un índice por -fecha_hora que incluya las dos sedes: lee solo el rango
(~300 lecturas) y además sirve el orden. También cubre al índice simple de fecha_hora.

Se crea el índice nuevo antes de borrar los anteriores para no dejar la tabla sin uno.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('gestion', '0007_metros_tela_cuatro_decimales'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['-fecha_hora'], include=('usuario_sede_id', 'object_sede_id'),
                name='idx_audit_fecha_sedes',
            ),
        ),
        migrations.RemoveIndex(
            model_name='auditlog',
            name='idx_audit_objsede_fecha',
        ),
        migrations.RemoveIndex(
            model_name='auditlog',
            name='idx_audit_usrsede_fecha',
        ),
        migrations.AlterField(
            model_name='auditlog',
            name='fecha_hora',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
