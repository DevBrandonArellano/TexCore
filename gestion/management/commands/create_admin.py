import os
import secrets

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
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'sistemas')
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists.'))
            return

        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'sistemas@example.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
        password_generada = password is None
        if password_generada:
            password = secrets.token_urlsafe(18)

        User.objects.create_superuser(username, email, password)
        self.stdout.write(self.style.SUCCESS(f'Successfully created new superuser "{username}"'))
        if password_generada:
            self.stdout.write(self.style.WARNING(
                f'No se definió DJANGO_SUPERUSER_PASSWORD — se generó una contraseña aleatoria. '
                f'Anótala ahora, no se volverá a mostrar: {password}'
            ))

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
