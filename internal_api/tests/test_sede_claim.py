"""
Tests de la propagación de identidad de sede en el canal servicio-a-servicio.

Cubre:
- El round-trip del claim firmado `sede_id`/`is_admin` en generate_token /
  _validate_token (y su retrocompatibilidad con tokens sin el claim).
- La lógica de `resolve_sede_scope` (defensa en profundidad de reporting_views):
  fuerza la sede del claim para no-admin, rechaza sede ajena, respeta la query
  para admin o cuando no hay claim.

Técnicas ISTQB: EP (con/sin claim; admin/no-admin; sede propia/ajena) + BVA.
"""
from types import SimpleNamespace

from django.test import TestCase

from internal_api.authentication import JWTServiceAuthentication, ServicePrincipal
from internal_api.views.reporting_views import resolve_sede_scope


def _fake_request(user, sede_id=None):
    """Request mínimo: resolve_sede_scope solo usa .user y .query_params.get."""
    params = {}
    if sede_id is not None:
        params['sede_id'] = str(sede_id)
    return SimpleNamespace(user=user, query_params=params)


class ServiceTokenSedeClaimTestCase(TestCase):
    """Round-trip del claim de sede firmado en el JWT de servicio."""

    def setUp(self):
        self.auth = JWTServiceAuthentication()

    def test_token_dado_sede_y_admin_cuando_valida_entonces_poblados_en_principal(self):
        token = JWTServiceAuthentication.generate_token(
            service_name="backend-proxy", scopes=["reports:read"],
            sede_id=7, is_admin=False,
        )
        principal, _ = self.auth._validate_token(token)
        self.assertEqual(principal.sede_id, 7)
        self.assertFalse(principal.is_admin)

    def test_token_dado_admin_cuando_valida_entonces_is_admin_true(self):
        token = JWTServiceAuthentication.generate_token(
            service_name="backend-proxy", scopes=["reports:read"],
            sede_id=None, is_admin=True,
        )
        principal, _ = self.auth._validate_token(token)
        self.assertTrue(principal.is_admin)
        self.assertIsNone(principal.sede_id)

    def test_token_dado_sin_claim_de_sede_cuando_valida_entonces_retrocompatible(self):
        # Retrocompatibilidad: tokens servicio-a-servicio clásicos (reporting_excel)
        # sin claim de sede → sede_id None, is_admin False. No deben romperse.
        token = JWTServiceAuthentication.generate_token(
            service_name="reporting_excel", scopes=["reports:read"],
        )
        principal, _ = self.auth._validate_token(token)
        self.assertIsNone(principal.sede_id)
        self.assertFalse(principal.is_admin)


class ResolveSedeScopeTestCase(TestCase):
    """Caja blanca de la resolución de sede en las vistas internas."""

    def test_scope_dado_claim_no_admin_cuando_sin_query_entonces_fuerza_su_sede(self):
        user = ServicePrincipal("backend-proxy", ["reports:read"], sede_id=3, is_admin=False)
        sede_id, error = resolve_sede_scope(_fake_request(user))
        self.assertIsNone(error)
        self.assertEqual(sede_id, 3)

    def test_scope_dado_claim_no_admin_cuando_query_ajena_entonces_403(self):
        user = ServicePrincipal("backend-proxy", ["reports:read"], sede_id=3, is_admin=False)
        sede_id, error = resolve_sede_scope(_fake_request(user, sede_id=9))
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 403)

    def test_scope_dado_claim_no_admin_cuando_query_propia_entonces_ok(self):
        user = ServicePrincipal("backend-proxy", ["reports:read"], sede_id=3, is_admin=False)
        sede_id, error = resolve_sede_scope(_fake_request(user, sede_id=3))
        self.assertIsNone(error)
        self.assertEqual(sede_id, 3)

    def test_scope_dado_admin_cuando_query_cualquier_sede_entonces_la_respeta(self):
        user = ServicePrincipal("backend-proxy", ["reports:read"], sede_id=3, is_admin=True)
        sede_id, error = resolve_sede_scope(_fake_request(user, sede_id=9))
        self.assertIsNone(error)
        self.assertEqual(sede_id, "9")

    def test_scope_dado_sin_claim_cuando_query_presente_entonces_la_respeta(self):
        # Token clásico (reporting_excel) sin claim: comportamiento retrocompatible.
        user = ServicePrincipal("reporting_excel", ["reports:read"])
        sede_id, error = resolve_sede_scope(_fake_request(user, sede_id=5))
        self.assertIsNone(error)
        self.assertEqual(sede_id, "5")
