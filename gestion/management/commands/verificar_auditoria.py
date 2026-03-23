"""
Comando para verificar que la auditoría está funcionando.
Uso: python manage.py verificar_auditoria
"""
from django.core.management.base import BaseCommand
from gestion.models import AuditLog


class Command(BaseCommand):
    help = 'Verifica que la auditoría está activa y muestra estadísticas'

    def handle(self, *args, **options):
        total = AuditLog.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Total registros en auditoría: {total}'))

        if total == 0:
            self.stdout.write(self.style.WARNING(
                'No hay logs. Crea/edita/elimina una sede, producto o usuario desde la app y vuelve a ejecutar.'
            ))
            return

        # Últimos 5
        ultimos = AuditLog.objects.select_related('usuario', 'content_type')[:5]
        self.stdout.write('\nÚltimos 5 registros:')
        for log in ultimos:
            tabla = log.content_type.model if log.content_type else 'N/A'
            user = log.usuario.username if log.usuario else 'Sistema'
            self.stdout.write(f'  {log.fecha_hora} | {log.accion} | {tabla} #{log.object_id} | por {user}')
