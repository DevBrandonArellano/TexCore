"""
Pruebas de internal_api/permissions.py — IsInternalService y HasScope.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): request.user es ServicePrincipal / es un
  CustomUser normal / no autenticado; scope presente / ausente / lista vacía.
"""
from unittest.mock import MagicMock

from django.test import TestCase
from rest_framework.permissions import BasePermission

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
        permission = HasScope('reports:read')()
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['reports:read', 'lotes:read']))
        self.assertTrue(permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_scope_ausente_cuando_verifica_entonces_false(self):
        permission = HasScope('reports:read')()
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['lotes:read']))
        self.assertFalse(permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_sin_scopes_cuando_verifica_entonces_false(self):
        # Caja blanca: rama `getattr(principal, 'scopes', [])` con lista vacía
        permission = HasScope('reports:read')()
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=[]))
        self.assertFalse(permission.has_permission(request, MagicMock()))

    def test_has_permission_dado_usuario_sin_atributo_scopes_cuando_verifica_entonces_false(self):
        # Caja blanca: rama `getattr(principal, 'scopes', [])` con default (usuario no ServicePrincipal)
        permission = HasScope('reports:read')()
        request = MagicMock(user=object())
        self.assertFalse(permission.has_permission(request, MagicMock()))

    def test_has_scope_dado_un_scope_cuando_se_crea_entonces_es_una_clase_de_permiso(self):
        # DRF instancia cada entrada de permission_classes: HasScope('x') debe ser una clase.
        clase = HasScope('reports:read')
        self.assertTrue(issubclass(clase, BasePermission))
        self.assertEqual(clase.required_scope, 'reports:read')

    def test_has_scope_dado_dos_scopes_cuando_se_crean_entonces_no_comparten_estado(self):
        lectura, escritura = HasScope('reports:read'), HasScope('reports:write')
        request = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['reports:read']))
        self.assertTrue(lectura().has_permission(request, MagicMock()))
        self.assertFalse(escritura().has_permission(request, MagicMock()))
        self.assertEqual(lectura.required_scope, 'reports:read')

    def test_has_scope_dado_composicion_con_and_cuando_verifica_entonces_exige_servicio_y_scope(self):
        permiso = (IsInternalService & HasScope('reports:read'))()
        con_scope = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['reports:read']))
        sin_scope = MagicMock(user=ServicePrincipal(service_name='qa', scopes=['lotes:read']))
        usuario = MagicMock(user=CustomUserFactory())
        self.assertTrue(permiso.has_permission(con_scope, MagicMock()))
        self.assertFalse(permiso.has_permission(sin_scope, MagicMock()))
        self.assertFalse(permiso.has_permission(usuario, MagicMock()))
