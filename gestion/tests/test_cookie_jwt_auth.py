"""
Pruebas del backend de autenticación JWT por cookie — gestion/auth_backends.py.

CookieJWTAuthentication lee el JWT desde una cookie httponly en vez del header
Authorization. Es la puerta de entrada de autenticación de toda la API.

Técnicas ISTQB aplicadas:
- Caja blanca (cobertura de decisiones): rama sin cookie (None), token válido,
  token inválido/expirado (except InvalidToken/TokenError).
- Particiones de equivalencia (EP): cookie ausente / válida / corrupta / expirada.
"""
from datetime import timedelta

from django.test import TestCase, RequestFactory, override_settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from gestion.auth_backends import CookieJWTAuthentication

User = get_user_model()
COOKIE_NAME = 'access_token'


class CookieJWTAuthenticationTestCase(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.backend = CookieJWTAuthentication()
        self.user = User.objects.create_user(username='jwt_user', password='x')

    def _request_with_cookie(self, **cookies):
        req = self.rf.get('/api/protegido/')
        req.COOKIES.update(cookies)
        return req

    def test_auth_dado_sin_cookie_cuando_autentica_entonces_none(self):
        # Caja blanca: rama raw_token is None -> return None
        req = self.rf.get('/api/protegido/')
        self.assertIsNone(self.backend.authenticate(req))

    def test_auth_dado_token_valido_cuando_autentica_entonces_retorna_usuario(self):
        # Caso feliz: cookie con access token válido
        token = str(AccessToken.for_user(self.user))
        req = self._request_with_cookie(**{COOKIE_NAME: token})
        user, validated = self.backend.authenticate(req)
        self.assertEqual(user, self.user)
        self.assertIsNotNone(validated)

    def test_auth_dado_token_corrupto_cuando_autentica_entonces_none(self):
        # EP: token sintácticamente inválido -> except -> None
        req = self._request_with_cookie(**{COOKIE_NAME: 'esto.no.es-un-jwt'})
        self.assertIsNone(self.backend.authenticate(req))

    def test_auth_dado_token_expirado_cuando_autentica_entonces_none(self):
        # EP/BVA: token cuya expiración ya pasó -> TokenError -> None
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        req = self._request_with_cookie(**{COOKIE_NAME: str(token)})
        self.assertIsNone(self.backend.authenticate(req))

    def test_auth_dado_cookie_con_otro_nombre_cuando_autentica_entonces_none(self):
        # El token está en una cookie con nombre distinto al configurado
        token = str(AccessToken.for_user(self.user))
        req = self._request_with_cookie(otra_cookie=token)
        self.assertIsNone(self.backend.authenticate(req))

    @override_settings(SIMPLE_JWT={'AUTH_COOKIE': 'token_custom'})
    def test_auth_dado_nombre_cookie_configurable_cuando_autentica_entonces_usa_settings(self):
        # Caja blanca: el nombre de cookie se lee de settings.SIMPLE_JWT['AUTH_COOKIE']
        token = str(AccessToken.for_user(self.user))
        req = self._request_with_cookie(token_custom=token)
        user, _ = self.backend.authenticate(req)
        self.assertEqual(user, self.user)
