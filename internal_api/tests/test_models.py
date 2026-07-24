"""Tests TDD para ServiceCredential. EP + STT."""
from django.test import TestCase
from django.contrib.auth.hashers import check_password
from internal_api.models import ServiceCredential


class TestServiceCredentialCreacion(TestCase):
    """EP: creación normal de una credencial de servicio."""

    def test_service_credential_dado_datos_validos_cuando_crea_entonces_almacena_hash(self):
        cred = ServiceCredential.objects.create(
            name="scanning_service",
            secret_hash=ServiceCredential.hash_secret("mi-secreto"),
            allowed_scopes=["lotes:read"],
        )
        self.assertEqual(cred.name, "scanning_service")
        self.assertTrue(check_password("mi-secreto", cred.secret_hash))

    def test_service_credential_dado_secreto_incorrecto_cuando_verifica_entonces_retorna_false(self):
        cred = ServiceCredential.objects.create(
            name="reporting_excel",
            secret_hash=ServiceCredential.hash_secret("correcto"),
            allowed_scopes=["reports:read"],
        )
        self.assertFalse(check_password("incorrecto", cred.secret_hash))


class TestServiceCredentialEstado(TestCase):
    """STT: transición activo → inactivo revoca acceso."""

    def test_service_credential_dado_activo_cuando_desactiva_entonces_is_active_false(self):
        cred = ServiceCredential.objects.create(
            name="svc_test",
            secret_hash=ServiceCredential.hash_secret("secret"),
            allowed_scopes=[],
            is_active=True,
        )
        cred.is_active = False
        cred.save()
        cred.refresh_from_db()
        self.assertFalse(cred.is_active)
