from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import Group
from gestion.models import Sede, Cliente, CustomUser
from decimal import Decimal

class ClienteImprovementsTestCase(APITestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Test", location="UIO")
        self.vendedor_group, _ = Group.objects.get_or_create(name='vendedor')
        self.vendedor = CustomUser.objects.create_user(
            username='vendedor_test', password='password123', sede=self.sede
        )
        self.vendedor.groups.add(self.vendedor_group)
        self.cliente = Cliente.objects.create(
            ruc_cedula="1799999999001", 
            nombre_razon_social="Cliente Test S.A.",
            direccion_envio="Av. Siempre Viva", 
            nivel_precio="normal",
            limite_credito=Decimal('1000.00'), 
            vendedor_asignado=self.vendedor,
            sede=self.sede
        )
        self.client.force_authenticate(user=self.vendedor)

    def test_soft_delete_inactivar_cliente(self):
        """Valida que un cliente puede ser inactivado vía PATCH."""
        url = reverse('cliente-detail', args=[self.cliente.id])
        payload = {
            "is_active": False,
            "_justificacion_auditoria": "Inactivación por falta de pago"
        }
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.is_active)

    def test_post_ignores_justification(self):
        """Valida que el endpoint de creación (POST) no requiere justificación."""
        url = reverse('cliente-list')
        payload = {
            "ruc_cedula": "1788888888001",
            "nombre_razon_social": "Nuevo Cliente",
            "direccion_envio": "Quito",
            "nivel_precio": "normal",
            "limite_credito": 500,
            "_justificacion_auditoria": "Esta no debería ser necesaria"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_patch_requires_justification(self):
        """Valida que el endpoint de actualización (PATCH) requiere justificación para campos críticos."""
        url = reverse('cliente-detail', args=[self.cliente.id])
        payload = {
            "limite_credito": 2000.00
            # Falta _justificacion_auditoria
        }
        response = self.client.patch(url, payload, format='json')
        # El modelo AuditableModelMixin lanza ValidationError si falta justificación en UPDATE
        # DRF convierte ValidationError de Django en 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Ahora con justificación
        payload["_justificacion_auditoria"] = "Aumento de cupo aprobado por gerencia"
        response = self.client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
