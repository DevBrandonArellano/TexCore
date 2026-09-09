"""
Pruebas de ClienteViewSet — requisito de justificación de auditoría en updates.

Migrado desde gestion/tests_cliente_improvements.py (Fase 6.3 del barrido de
higiene, 2026-09-02): mismo archivo suelto en la raíz de gestion/, renombrado
a convención ISTQB y con factories en vez de creación manual de fixtures.

Técnicas ISTQB aplicadas:
- Caja blanca: AuditableModelMixin.clean() exige _justificacion_auditoria en
  UPDATE de un registro con requiere_justificacion_auditoria=True, pero no en
  CREATE (is_new=True salta la validación).
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.tests.factories import ClienteFactory, CustomUserFactory, SedeFactory


class ClienteAuditoriaJustificacionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.cliente = ClienteFactory(sede=self.sede, vendedor_asignado=self.vendedor)
        self.client.force_authenticate(user=self.vendedor)

    def test_cliente_dado_is_active_false_con_justificacion_cuando_patch_entonces_inactiva(self):
        url = reverse('cliente-detail', args=[self.cliente.id])
        resp = self.client.patch(url, {
            'is_active': False, '_justificacion_auditoria': 'Inactivación por falta de pago',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.is_active)

    def test_cliente_dado_creacion_cuando_post_sin_justificacion_entonces_201(self):
        # Caja blanca: is_new=True no exige justificación (solo aplica a UPDATE)
        resp = self.client.post(reverse('cliente-list'), {
            'ruc_cedula': '1788888888001', 'nombre_razon_social': 'Nuevo Cliente Test',
            'direccion_envio': 'Quito', 'nivel_precio': 'normal', 'limite_credito': '500',
            '_justificacion_auditoria': 'Esta no debería ser necesaria',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_cliente_dado_update_sin_justificacion_cuando_patch_entonces_400(self):
        url = reverse('cliente-detail', args=[self.cliente.id])
        resp = self.client.patch(url, {'limite_credito': '2000.00'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cliente_dado_update_con_justificacion_cuando_patch_entonces_200(self):
        url = reverse('cliente-detail', args=[self.cliente.id])
        resp = self.client.patch(url, {
            'limite_credito': '2000.00',
            '_justificacion_auditoria': 'Aumento de cupo aprobado por gerencia',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
