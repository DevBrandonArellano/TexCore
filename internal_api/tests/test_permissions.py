"""
Pruebas de internal_api/permissions.py — IsInternalService y HasScope.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): request.user es ServicePrincipal / es un
  CustomUser normal / no autenticado; scope presente / ausente / lista vacía.
"""
from unittest.mock import MagicMock

from django.test import TestCase

from gestion.tests.factories import CustomUserFactory
from internal_api.authentication import ServicePrincipal
from internal_api.permissions import HasScope, IsInternalService


class IsInternalServiceTestCase(TestCase):
    def setUp(self):
        self.permission = IsInternalService()

    def test_has_permission_dado_service_principal_cuando_verifica_entonces_true(self):
        request = MagicMock(user=ServicePrincipal(service_name='qa-service'))
        self.assertTrue(self.permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_usuario_normal_cuando_verifica_entonces_false(self):
        request = MagicMock(user=CustomUserFactory())
        self.assertFalse(self.permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_sin_usuario_cuando_verifica_entonces_false(self):
        request = MagicMock(user=None)
        self.assertFalse(self.permission.has_permission(request, MagicMock()))


class HasScopeTestCase(TestCase):
    def test_has_permission_dado_scope_presente_cuando_verifica_entonces_true(self):
        permission = HasScope('reports:read')
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['reports:read', 'lotes:read']))
        self.assertTrue(permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_scope_ausente_cuando_verifica_entonces_false(self):
        permission = HasScope('reports:read')
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['lotes:read']))
        self.assertFalse(permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_sin_scopes_cuando_verifica_entonces_false(self):
        # Caja blanca: rama `getattr(principal, 'scopes', [])` con lista vacía
        permission = HasScope('reports:read')
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=[]))
        self.assertFalse(permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_usuario_sin_atributo_scopes_cuando_verifica_entonces_false(self):
        # Caja blanca: rama `getattr(principal, 'scopes', [])` con default (usuario no ServicePrincipal)
        permission = HasScope('reports:read')
        request = MagicMock(user=object())
        self.assertFalse(permission.has_permission(request, MagicMock()))

    def test_call_dado_instancia_cuando_llama_entonces_retorna_self(self):
        # Caja blanca: __call__ soporta el patrón permission_classes=[HasScope('x')]
        permission = HasScope('reports:read')
        self.assertIs(permission(), permission)
