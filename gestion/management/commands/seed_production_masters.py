"""
Management command to seed production master roles and permissions for a clean TexCore database launch.
Usage: python manage.py seed_production_masters
"""

import logging
import os
import secrets

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group
from gestion.models import CustomUser

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Seeds system RBAC groups, permissions, and initial admin account for clean deployment.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== INICIANDO SIEMBRA DE ROLES Y PERMISOS DE SISTEMA ==='))

        # 1. Crear Grupos RBAC + asignar permisos vía setup_permissions (gestion).
        # setup_permissions ya crea los 11 grupos reales del sistema, con el
        # nombre exacto (slug en minúsculas: 'admin_sistemas', 'jefe_area', ...)
        # que usa TODO el código de permisos (make_group_permission, IsXxxOrAdmin,
        # etc.). No se crean grupos con nombres "legibles" aparte: un grupo con
        # otro nombre (p.ej. "Jefe de Área") no coincidiría con ningún chequeo de
        # rol y dejaría a cualquier usuario asignado a él sin ningún permiso.
        try:
            from django.core.management import call_command
            call_command('setup_permissions')
            self.stdout.write(self.style.SUCCESS('Grupos RBAC y permisos asignados correctamente (11 roles).'))
        except Exception as e:
            raise CommandError(f'Fallo al crear grupos/permisos RBAC: {e}')

        # 2. Crear Superusuario inicial sin Sede (el Administrador de Sistemas
        # creará las Sedes y Áreas desde el sistema).
        if not CustomUser.objects.filter(is_superuser=True).exists():
            username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
            email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@texcore.local')
            password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')
            password_generada = password is None
            if password_generada:
                password = secrets.token_urlsafe(18)

            admin_user = CustomUser.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Administrador',
                last_name='Sistemas',
                sede=None
            )
            admin_group = Group.objects.filter(name='admin_sistemas').first()
            if admin_group:
                admin_user.groups.add(admin_group)
            self.stdout.write(self.style.SUCCESS(
                f'Superusuario inicial "{username}" (sin sede asignada) creado exitosamente.'))
            if password_generada:
                self.stdout.write(self.style.WARNING(
                    f'No se definió DJANGO_SUPERUSER_PASSWORD — se generó una contraseña aleatoria. '
                    f'Anótala ahora, no se volverá a mostrar: {password}'
                ))
        else:
            self.stdout.write('Superusuario ya existente en la base de datos.')

        self.stdout.write(self.style.SUCCESS('=== SIEMBRA DE INFRAESTRUCTURA DE SISTEMA FINALIZADA EXITOSAMENTE ==='))
