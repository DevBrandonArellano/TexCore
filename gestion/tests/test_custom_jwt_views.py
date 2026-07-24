"""
Pruebas de gestion/custom_jwt_views.py — login/refresh/logout basados en JWT
por cookie httponly (CustomTokenObtainPairView, CustomTokenRefreshView,
LogoutView).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): credenciales válidas / inválidas, refresh
  cookie presente / ausente, refresh token válido / inválido en logout.
- Caja blanca: ramas de seteo/borrado de cookies httponly y remoción del
  campo 'access' del body en refresh.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from gestion.tests.factories import CustomUserFactory

ACCESS_COOKIE = 'access_token'
REFRESH_COOKIE = 'refresh_token'


class CustomTokenObtainPairViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('token_obtain_pair')
        self.user = CustomUserFactory(username='login_user', groups=['vendedor'])

    def test_login_dado_credenciales_validas_cuando_post_entonces_200_con_cookies(self):
        resp = self.client.post(
            self.url, {'username': 'login_user', 'password': 'TestPass123!'}, format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['role'], 'vendedor')
        self.assertEqual(resp.data['user']['username'], 'login_user')
        self.assertNotIn('access', resp.data)
        self.assertIn(ACCESS_COOKIE, resp.cookies)
        self.assertIn(REFRESH_COOKIE, resp.cookies)
        self.assertTrue(resp.cookies[ACCESS_COOKIE]['httponly'])

    def test_login_dado_credenciales_invalidas_cuando_post_entonces_401(self):
        resp = self.client.post(
            self.url, {'username': 'login_user', 'password': 'contraseña-incorrecta'}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class CustomTokenRefreshViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('token_refresh')
        self.user = CustomUserFactory(username='refresh_user')

    def test_refresh_dado_cookie_valida_cuando_post_entonces_200_con_nueva_cookie_access(self):
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[REFRESH_COOKIE] = str(refresh)

        resp = self.client.post(self.url, {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn('access', resp.data)
        self.assertIn(ACCESS_COOKIE, resp.cookies)

    def test_refresh_dado_sin_cookie_cuando_post_entonces_401(self):
        # Caja blanca: rama `if not refresh_token` -> raise InvalidToken
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_dado_cookie_invalida_cuando_post_entonces_401_y_borra_cookies(self):
        self.client.cookies[REFRESH_COOKIE] = 'token-corrupto-no-valido'

        resp = self.client.post(self.url, {}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp.cookies[ACCESS_COOKIE].value, '')
        self.assertEqual(resp.cookies[REFRESH_COOKIE].value, '')


class LogoutViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('token_logout')
        self.user = CustomUserFactory(username='logout_user')

    def test_logout_dado_usuario_no_autenticado_cuando_post_entonces_401(self):
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_dado_refresh_valido_cuando_post_entonces_200_blacklistea_y_borra_cookies(self):
        self.client.force_authenticate(user=self.user)
        refresh = RefreshToken.for_user(self.user)
        self.client.cookies[REFRESH_COOKIE] = str(refresh)

        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.cookies[ACCESS_COOKIE].value, '')
        self.assertEqual(resp.cookies[REFRESH_COOKIE].value, '')

    def test_logout_dado_sin_cookie_refresh_cuando_post_entonces_200_sin_blacklist(self):
        # EP: no hay refresh token que invalidar; el logout igual responde 200
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_logout_dado_refresh_ya_invalido_cuando_post_entonces_200_no_falla(self):
        # Caja blanca: rama except TokenError -> pass (token corrupto/expirado, no bloquea logout)
        self.client.force_authenticate(user=self.user)
        self.client.cookies[REFRESH_COOKIE] = 'no-es-un-jwt-valido'

        resp = self.client.post(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
