"""
Pruebas de gestion/profile_views.py — UserProfileView y get_user_role.

get_user_role resuelve el rol principal de un usuario por prioridad de grupo
(superuser siempre es admin_sistemas; luego el primer grupo que coincida en
la lista de prioridad). UserProfileView expone el perfil + rol vía GET.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): superuser, cada grupo de rol, sin grupos.
- Caja blanca: orden de prioridad cuando el usuario pertenece a más de un grupo.
"""
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.profile_views import get_user_role
from gestion.tests.factories import CustomUserFactory


class GetUserRoleTestCase(TestCase):
    def test_get_user_role_dado_superuser_cuando_resuelve_entonces_admin_sistemas(self):
        user = CustomUserFactory(is_superuser=True)
        self.assertEqual(get_user_role(user), 'admin_sistemas')

    def test_get_user_role_dado_grupo_jefe_area_cuando_resuelve_entonces_jefe_area(self):
        user = CustomUserFactory(groups=['jefe_area'])
        self.assertEqual(get_user_role(user), 'jefe_area')

    def test_get_user_role_dado_grupo_vendedor_cuando_resuelve_entonces_vendedor(self):
        user = CustomUserFactory(groups=['vendedor'])
        self.assertEqual(get_user_role(user), 'vendedor')

    def test_get_user_role_dado_grupo_admin_sistemas_sin_superuser_cuando_resuelve_entonces_admin_sistemas(self):
        user = CustomUserFactory(groups=['admin_sistemas'])
        self.assertEqual(get_user_role(user), 'admin_sistemas')

    def test_get_user_role_dado_grupo_jefe_planta_cuando_resuelve_entonces_jefe_planta(self):
        user = CustomUserFactory(groups=['jefe_planta'])
        self.assertEqual(get_user_role(user), 'jefe_planta')

    def test_get_user_role_dado_grupo_tintorero_cuando_resuelve_entonces_tintorero(self):
        user = CustomUserFactory(groups=['tintorero'])
        self.assertEqual(get_user_role(user), 'tintorero')

    def test_get_user_role_dado_grupo_ejecutivo_cuando_resuelve_entonces_ejecutivo(self):
        user = CustomUserFactory(groups=['ejecutivo'])
        self.assertEqual(get_user_role(user), 'ejecutivo')

    def test_get_user_role_dado_grupo_bodeguero_cuando_resuelve_entonces_bodeguero(self):
        user = CustomUserFactory(groups=['bodeguero'])
        self.assertEqual(get_user_role(user), 'bodeguero')

    def test_get_user_role_dado_grupo_operario_cuando_resuelve_entonces_operario(self):
        user = CustomUserFactory(groups=['operario'])
        self.assertEqual(get_user_role(user), 'operario')

    def test_get_user_role_dado_grupo_empaquetado_cuando_resuelve_entonces_empaquetado(self):
        user = CustomUserFactory(groups=['empaquetado'])
        self.assertEqual(get_user_role(user), 'empaquetado')

    def test_get_user_role_dado_grupo_despacho_cuando_resuelve_entonces_despacho(self):
        user = CustomUserFactory(groups=['despacho'])
        self.assertEqual(get_user_role(user), 'despacho')

    def test_get_user_role_dado_sin_grupos_cuando_resuelve_entonces_none(self):
        # EP: usuario sin grupos ni superuser -> None
        user = CustomUserFactory()
        self.assertIsNone(get_user_role(user))

    def test_get_user_role_dado_multiples_grupos_cuando_resuelve_entonces_prioriza_admin_sede(self):
        # Caja blanca: admin_sede tiene prioridad sobre jefe_planta en el orden de checks
        user = CustomUserFactory(groups=['jefe_planta', 'admin_sede'])
        self.assertEqual(get_user_role(user), 'admin_sede')


class UserProfileViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('user-profile')

    def test_profile_dado_usuario_no_autenticado_cuando_get_entonces_401(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_dado_usuario_autenticado_cuando_get_entonces_200_con_rol(self):
        Group.objects.get_or_create(name='bodeguero')
        user = CustomUserFactory(groups=['bodeguero'])
        self.client.force_authenticate(user=user)

        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['role'], 'bodeguero')
        self.assertEqual(resp.data['user']['username'], user.username)
