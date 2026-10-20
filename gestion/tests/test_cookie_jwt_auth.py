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

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from gestion.auth_backends import CookieJWTAuthentication

User = get_user_model()
COOKIE_NAME = "access_token"


class CookieJWTAuthenticationTestCase(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.backend = CookieJWTAuthentication()
        self.user = User.objects.create_user(username="jwt_user", password="x")

    def _request_with_cookie(self, **cookies):
        req = self.rf.get("/api/protegido/")
        req.COOKIES.update(cookies)
        return req

    def test_auth_dado_sin_cookie_cuando_autentica_entonces_none(self):
        # Caja blanca: rama raw_token is None -> return None
        req = self.rf.get("/api/protegido/")
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
        req = self._request_with_cookie(**{COOKIE_NAME: "esto.no.es-un-jwt"})
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

    @override_settings(SIMPLE_JWT={"AUTH_COOKIE": "token_custom"})
    def test_auth_dado_nombre_cookie_configurable_cuando_autentica_entonces_usa_settings(self):
        # Caja blanca: el nombre de cookie se lee de settings.SIMPLE_JWT['AUTH_COOKIE']
        token = str(AccessToken.for_user(self.user))
        req = self._request_with_cookie(token_custom=token)
        user, _ = self.backend.authenticate(req)
        self.assertEqual(user, self.user)


class CookieJWTCsrfTestCase(TestCase):
    """
    Zero Trust de la cookie (OWASP A01, NIST SP 800-207): el navegador envía la cookie
    JWT sola en cualquier petición a la API, también desde otra página. Una escritura con
    la cookie exige además el token CSRF en la cabecera `X-CSRFToken`; las lecturas no.
    Técnicas ISTQB: EP (método seguro / inseguro, con token / sin token / token errado).
    """

    URL = "/api/token/logout/"

    def setUp(self):
        from rest_framework.test import APIClient

        self.user = User.objects.create_user(username="csrf_user", password="x")
        self.client = APIClient(enforce_csrf_checks=True)
        self.client.cookies[COOKIE_NAME] = str(AccessToken.for_user(self.user))

    def _token_csrf(self):
        """El token que el front lee de la cookie `csrftoken` que fija la API."""
        resp = self.client.get("/api/profile/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("csrftoken", resp.cookies)
        return resp.cookies["csrftoken"].value

    def test_escritura_dado_cookie_sin_token_csrf_cuando_post_entonces_403_con_motivo_legible(self):
        resp = self.client.post(self.URL)
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("HttpResponse", str(resp.data))

    def test_escritura_dado_token_csrf_errado_cuando_post_entonces_403(self):
        self._token_csrf()
        self.assertEqual(self.client.post(self.URL, HTTP_X_CSRFTOKEN="token-falso").status_code, 403)

    def test_escritura_dado_cookie_y_token_csrf_cuando_post_entonces_no_es_403(self):
        token = self._token_csrf()
        self.assertNotEqual(self.client.post(self.URL, HTTP_X_CSRFTOKEN=token).status_code, 403)

    def test_lectura_dado_cookie_sin_token_csrf_cuando_get_entonces_200(self):
        self.assertEqual(self.client.get("/api/profile/").status_code, 200)

    def test_login_dado_credenciales_validas_cuando_post_entonces_fija_la_cookie_csrf(self):
        from rest_framework.test import APIClient

        resp = APIClient(enforce_csrf_checks=True).post(
            "/api/token/", {"username": "csrf_user", "password": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("csrftoken", resp.cookies)
