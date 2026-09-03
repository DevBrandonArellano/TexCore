"""
Pruebas de internal_api/views/auth_views.py — ServiceTokenRefreshView y la
rama de validación (400) de ServiceTokenView que test_auth_views.py no cubre.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): refresh token válido / expirado / de tipo
  incorrecto (access en vez de refresh) / servicio inactivo o inexistente.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from internal_api.models import ServiceCredential


def _make_refresh_token(service_name='qa-service', token_type='service_refresh', expired=False):
    now = datetime.now(timezone.utc)
    exp = now - timedelta(seconds=10) if expired else now + timedelta(seconds=900)
    payload = {
        "iss": "texcore", "sub": service_name, "jti": str(uuid.uuid4()),
        "iat": now, "exp": exp, "type": token_type,
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class ServiceTokenViewValidationTestCase(TestCase):
    def test_token_dado_payload_invalido_cuando_post_entonces_400(self):
        client = APIClient()
        resp = client.post('/api/internal/v1/auth/token/', {}, format='json')
        self.assertEqual(resp.status_code, 400)


class ServiceTokenRefreshViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.credential = ServiceCredential.objects.create(
            name='qa-service', secret_hash=make_password('secret123'),
            allowed_scopes=['reports:read'], is_active=True,
        )

    def test_refresh_dado_payload_invalido_cuando_post_entonces_400(self):
        resp = self.client.post('/api/internal/v1/auth/refresh/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_refresh_dado_token_valido_cuando_post_entonces_200_con_nuevo_par(self):
        refresh = _make_refresh_token(service_name='qa-service')
        resp = self.client.post('/api/internal/v1/auth/refresh/', {'refresh_token': refresh}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access_token', resp.data)
        self.assertIn('refresh_token', resp.data)

    def test_refresh_dado_token_expirado_cuando_post_entonces_401(self):
        refresh = _make_refresh_token(service_name='qa-service', expired=True)
        resp = self.client.post('/api/internal/v1/auth/refresh/', {'refresh_token': refresh}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.assertIn('expirado', resp.data['detail'])

    def test_refresh_dado_token_malformado_cuando_post_entonces_401(self):
        resp = self.client.post(
            '/api/internal/v1/auth/refresh/', {'refresh_token': 'no-es-un-jwt-valido'}, format='json',
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn('inválido', resp.data['detail'])

    def test_refresh_dado_tipo_access_en_vez_de_refresh_cuando_post_entonces_401(self):
        # Caja blanca: rama `payload.get('type') != 'service_refresh'`
        access_token = _make_refresh_token(service_name='qa-service', token_type='service_access')
        resp = self.client.post('/api/internal/v1/auth/refresh/', {'refresh_token': access_token}, format='json')
        self.assertEqual(resp.status_code, 401)
        self.assertIn('Tipo de token incorrecto', resp.data['detail'])

    def test_refresh_dado_servicio_inactivo_cuando_post_entonces_403(self):
        self.credential.is_active = False
        self.credential.save(update_fields=['is_active'])
        refresh = _make_refresh_token(service_name='qa-service')
        resp = self.client.post('/api/internal/v1/auth/refresh/', {'refresh_token': refresh}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_refresh_dado_servicio_inexistente_cuando_post_entonces_403(self):
        refresh = _make_refresh_token(service_name='servicio-fantasma')
        resp = self.client.post('/api/internal/v1/auth/refresh/', {'refresh_token': refresh}, format='json')
        self.assertEqual(resp.status_code, 403)

    # EP: request con REMOTE_ADDR público simulado → 403 antes de decodificar el JWT
    def test_refresh_dado_ip_publica_cuando_post_entonces_403(self):
        refresh = _make_refresh_token(service_name='qa-service')
        resp = self.client.post(
            '/api/internal/v1/auth/refresh/', {'refresh_token': refresh}, format='json',
            REMOTE_ADDR='8.8.8.8',
        )
        self.assertEqual(resp.status_code, 403)


class ServiceTokenRefreshViewThrottleTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        cache.clear()

    def tearDown(self):
        cache.clear()

    # STT: 11na petición en el mismo minuto desde la misma IP → 429
    def test_refresh_dado_mas_de_10_intentos_por_minuto_cuando_post_entonces_429(self):
        for _ in range(10):
            resp = self.client.post(
                '/api/internal/v1/auth/refresh/', {'refresh_token': 'no-es-un-jwt-valido'}, format='json',
            )
            self.assertNotEqual(resp.status_code, 429)
        resp = self.client.post(
            '/api/internal/v1/auth/refresh/', {'refresh_token': 'no-es-un-jwt-valido'}, format='json',
        )
        self.assertEqual(resp.status_code, 429)
