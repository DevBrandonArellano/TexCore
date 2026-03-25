from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Creates a superuser if one does not exist, or verifies audit with --verificar'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verificar',
            action='store_true',
            help='Verifica la auditoría en lugar de crear superuser',
        )

    def handle(self, *args, **options):
        if options.get('verificar'):
            self._verificar_auditoria()
            return
        User = get_user_model()
        if not User.objects.filter(username='sistemas').exists():
            User.objects.create_superuser('sistemas', 'sistemas@example.com', 'Sistemas2026*')
            self.stdout.write(self.style.SUCCESS('Successfully created new superuser "sistemas"'))
        else:
            self.stdout.write(self.style.WARNING('Superuser "sistemas" already exists.'))

    def _verificar_auditoria(self):
        from gestion.models import AuditLog
        total = AuditLog.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Total registros en auditoría: {total}'))
        if total == 0:
            self.stdout.write(self.style.WARNING(
                'No hay logs. Crea/edita/elimina una sede, producto o usuario desde la app y vuelve a ejecutar.'
            ))
            return
        ultimos = AuditLog.objects.select_related('usuario', 'content_type')[:5]
        self.stdout.write('\nÚltimos 5 registros:')
        for log in ultimos:
            tabla = log.content_type.model if log.content_type else 'N/A'
            user = log.usuario.username if log.usuario else 'Sistema'
            self.stdout.write(f'  {log.fecha_hora} | {log.accion} | {tabla} #{log.object_id} | por {user}')
