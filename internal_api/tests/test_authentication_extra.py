"""
Pruebas complementarias de internal_api/authentication.py — ramas que
test_authentication.py no ejercita: token malformado, claim requerido
ausente, generate_token, y authenticate_header.
"""
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed

from internal_api.authentication import JWTServiceAuthentication


class JWTServiceAuthenticationExtraTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = JWTServiceAuthentication()

    def test_auth_dado_token_malformado_cuando_autentica_entonces_lanza_error(self):
        # Caja blanca: rama `except jwt.InvalidTokenError`
        request = self.factory.get("/", HTTP_AUTHORIZATION="Bearer no-es-un-jwt")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    def test_authenticate_header_cuando_llama_entonces_retorna_bearer_realm(self):
        request = self.factory.get("/")
        self.assertEqual(
            self.auth.authenticate_header(request), 'Bearer realm="texcore-internal"',
        )

    def test_generate_token_dado_service_name_y_scopes_cuando_genera_entonces_decodificable(self):
        import jwt
        from django.conf import settings

        token = JWTServiceAuthentication.generate_token(
            service_name="backend-proxy", scopes=["reports:read"], expires_in=60,
        )
        payload = jwt.decode(token, settings.INTERNAL_JWT_PUBLIC_KEY, algorithms=["RS256"])
        self.assertEqual(payload["sub"], "backend-proxy")
        self.assertEqual(payload["type"], "service_access")
        self.assertEqual(payload["scope"], ["reports:read"])

    def test_auth_dado_token_valido_cuando_autentica_entonces_se_puede_usar_generate_token(self):
        # Integración: el token producido por generate_token es válido para el propio backend
        token = JWTServiceAuthentication.generate_token(service_name="backend-proxy", scopes=["reports:read"])
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        principal, _ = self.auth.authenticate(request)
        self.assertEqual(principal.service_name, "backend-proxy")
