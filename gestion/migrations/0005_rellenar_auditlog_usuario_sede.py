"""Rellena AuditLog.usuario_sede_id de los registros anteriores a la 0004.

Se usa la sede actual del usuario: es la única disponible para las filas viejas (las
nuevas guardan la del momento del cambio). Va por bloques de ids y fuera de una única
transacción (atomic = False) para que, con ~1 M de filas en SQL Server, cada bloque
confirme por separado y no se escale el bloqueo a toda la tabla. Se puede repetir: solo
toca filas con usuario y sin sede.
"""
from django.db import migrations
from django.db.models import OuterRef, Subquery

TAMANO_LOTE = 10_000


def rellenar_usuario_sede(apps, schema_editor, tamano_lote=TAMANO_LOTE):
    AuditLog = apps.get_model('gestion', 'AuditLog')
    CustomUser = apps.get_model('gestion', 'CustomUser')
    # _base_manager: el manager del modelo bloquea update() (TEX-09); el relleno es la
    # única escritura permitida sobre filas existentes y ocurre una sola vez.
    pendientes = AuditLog._base_manager.filter(usuario_id__isnull=False, usuario_sede_id__isnull=True)
    sede_del_usuario = Subquery(CustomUser.objects.filter(pk=OuterRef('usuario_id')).values('sede_id')[:1])

    desde = 0
    while True:
        ids = list(pendientes.filter(pk__gt=desde).order_by('pk').values_list('pk', flat=True)[:tamano_lote])
        if not ids:
            return
        AuditLog._base_manager.filter(pk__in=ids).update(usuario_sede_id=sede_del_usuario)
        desde = ids[-1]


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('gestion', '0004_auditlog_usuario_sede'),
    ]

    operations = [
        migrations.RunPython(rellenar_usuario_sede, migrations.RunPython.noop),
    ]
