"""Tests para JWTServiceAuthentication. EP + BVA."""
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed

from internal_api.authentication import JWTServiceAuthentication, ServicePrincipal


def _make_token(sub="scanning_service", scope=None, exp_delta=900, token_type="service_access"):
    """Helper: genera token RS256 válido para tests."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore",
        "sub": sub,
        "scope": scope or ["lotes:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=exp_delta),
        "type": token_type,
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class TestJWTServiceAuthentication(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = JWTServiceAuthentication()

    # EP: token válido → retorna ServicePrincipal
    def test_auth_dado_token_valido_cuando_autentica_entonces_retorna_principal(self):
        token = _make_token()
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        principal, _ = result
        self.assertEqual(principal.service_name, "scanning_service")
        self.assertIn("lotes:read", principal.scopes)

    # EP: sin header Authorization → retorna None (no es error, solo no aplica)
    def test_auth_dado_sin_header_cuando_autentica_entonces_retorna_none(self):
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    # BVA: token expirado → AuthenticationFailed
    def test_auth_dado_token_expirado_cuando_autentica_entonces_lanza_error(self):
        token = _make_token(exp_delta=-1)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    # EP: tipo de token incorrecto → AuthenticationFailed
    def test_auth_dado_tipo_refresh_cuando_autentica_entonces_lanza_error(self):
        token = _make_token(token_type="service_refresh")
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)
