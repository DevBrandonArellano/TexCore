"""Tests para endpoints de autenticación de servicios. EP + STT."""
import jwt
from django.conf import settings
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from internal_api.models import ServiceCredential


def _create_credential(name="scanning_service", secret="test-secret", scopes=None, active=True):
    return ServiceCredential.objects.create(
        name=name,
        secret_hash=ServiceCredential.hash_secret(secret),
        allowed_scopes=scopes or ["lotes:read"],
        is_active=active,
    )


class TestServiceTokenView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/internal/v1/auth/token/"

    # EP: credenciales válidas → 200 + tokens
    def test_token_dado_credenciales_validas_cuando_solicita_entonces_retorna_200(self):
        _create_credential()
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "test-secret"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.data)
        self.assertIn("refresh_token", resp.data)
        self.assertEqual(resp.data["expires_in"], 900)

    # EP: payload del access_token contiene sub y scope correctos
    def test_token_dado_credenciales_validas_cuando_decodifica_entonces_payload_correcto(self):
        _create_credential()
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "test-secret"},
            format="json",
        )
        payload = jwt.decode(
            resp.data["access_token"],
            settings.INTERNAL_JWT_PUBLIC_KEY,
            algorithms=["RS256"],
        )
        self.assertEqual(payload["sub"], "scanning_service")
        self.assertEqual(payload["type"], "service_access")
        self.assertIn("lotes:read", payload["scope"])

    # EP: secreto incorrecto → 401
    def test_token_dado_secreto_incorrecto_cuando_solicita_entonces_retorna_401(self):
        _create_credential()
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    # STT: servicio inactivo → 403
    def test_token_dado_servicio_inactivo_cuando_solicita_entonces_retorna_403(self):
        _create_credential(active=False)
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "test-secret"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)

    # EP: servicio inexistente → 401
    def test_token_dado_servicio_inexistente_cuando_solicita_entonces_retorna_401(self):
        resp = self.client.post(
            self.url,
            {"service_name": "no_existe", "service_secret": "x"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    # EP: request con REMOTE_ADDR público simulado → 403 antes de validar credenciales
    def test_token_dado_ip_publica_cuando_solicita_entonces_retorna_403(self):
        _create_credential()
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "test-secret"},
            format="json",
            REMOTE_ADDR="8.8.8.8",
        )
        self.assertEqual(resp.status_code, 403)


class TestServiceTokenViewThrottle(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/internal/v1/auth/token/"
        cache.clear()

    def tearDown(self):
        cache.clear()

    # STT: 11na petición en el mismo minuto desde la misma IP → 429
    def test_token_dado_mas_de_10_intentos_por_minuto_cuando_solicita_entonces_retorna_429(self):
        _create_credential()
        for _ in range(10):
            resp = self.client.post(
                self.url,
                {"service_name": "scanning_service", "service_secret": "wrong"},
                format="json",
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            self.url,
            {"service_name": "scanning_service", "service_secret": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, 429)
