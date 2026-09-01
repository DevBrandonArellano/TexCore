"""
Pruebas de gestion/management/commands/create_admin.py — Fase 1.1 del
barrido de higiene (2026-09-01): el comando ya no puede generar una
contraseña estática/predecible.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con DJANGO_SUPERUSER_PASSWORD / sin ella,
  superuser ya existente / no existente.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase


class CreateAdminCommandTestCase(TestCase):
    def test_create_admin_dado_sin_env_vars_cuando_ejecuta_entonces_password_no_es_estatica(self):
        call_command('create_admin')
        User = get_user_model()
        user = User.objects.get(username='sistemas')
        self.assertFalse(user.check_password('Sistemas2026*'))

    def test_create_admin_dado_password_env_var_cuando_ejecuta_entonces_usa_esa_password(self):
        os.environ['DJANGO_SUPERUSER_PASSWORD'] = 'ClaveDePruebaSegura123!'
        try:
            call_command('create_admin')
            User = get_user_model()
            user = User.objects.get(username='sistemas')
            self.assertTrue(user.check_password('ClaveDePruebaSegura123!'))
        finally:
            del os.environ['DJANGO_SUPERUSER_PASSWORD']

    def test_create_admin_dado_superuser_ya_existe_cuando_ejecuta_entonces_no_duplica(self):
        call_command('create_admin')
        User = get_user_model()
        self.assertEqual(User.objects.filter(username='sistemas').count(), 1)
        call_command('create_admin')
        self.assertEqual(User.objects.filter(username='sistemas').count(), 1)
