from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from gestion.models import Sede, Bodega
from unittest.mock import patch
import httpx

User = get_user_model()

class ReportingProxyRBACtest(TestCase):
    def setUp(self):
        # 1. Configuración de Sede y Bodegas
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega_asignada = Bodega.objects.create(nombre="Bodega Asignada", sede=self.sede)
        self.bodega_ajena = Bodega.objects.create(nombre="Bodega Ajena", sede=self.sede)

        # 2. Configuración de Roles
        self.group_bodeguero, _ = Group.objects.get_or_create(name='bodeguero')
        self.group_admin, _ = Group.objects.get_or_create(name='admin_sistemas')

        # 3. Usuarios
        self.bodeguero = User.objects.create_user(username='bodeguero_test', password='password123')
        self.bodeguero.groups.add(self.group_bodeguero)
        self.bodeguero.bodegas_asignadas.add(self.bodega_asignada)
        self.bodeguero.save()

        self.admin = User.objects.create_user(username='admin_test', password='password123', is_superuser=True)
        self.admin.groups.add(self.group_admin)
        self.admin.save()

        self.client = APIClient()

    @patch("httpx.Client.get")
    def test_bodeguero_access_assigned_bodega(self, mock_httpx_get):
        """Un bodeguero DEBE poder acceder a reportes de su bodega asignada"""
        self.client.force_authenticate(user=self.bodeguero)
        
        # Simular respuesta exitosa del microservicio
        mock_httpx_get.return_value = httpx.Response(
            200, content=b"fake_excel_content", 
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        )

        url = f'/api/reporting/export/kardex?bodega_id={self.bodega_asignada.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"fake_excel_content")
        
        # Verificar que se envió el header de seguridad interna
        # mock_httpx_get.call_args[1]['headers'] contiene los headers
        sent_headers = mock_httpx_get.call_args[1]['headers']
        self.assertIn("X-Internal-Key", sent_headers)

    def test_bodeguero_access_denied_other_bodega(self):
        """Un bodeguero NO DEBE poder acceder a reportes de una bodega no asignada"""
        self.client.force_authenticate(user=self.bodeguero)
        
        url = f'/api/reporting/export/kardex?bodega_id={self.bodega_ajena.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertEqual(data["detail"], "No tiene permiso para acceder a esta bodega")

    @patch("httpx.Client.get")
    def test_admin_access_any_bodega(self, mock_httpx_get):
        """Un administrador puede acceder a CUALQUIER bodega"""
        self.client.force_authenticate(user=self.admin)
        
        mock_httpx_get.return_value = httpx.Response(200, content=b"admin_ok")

        url = f'/api/reporting/export/kardex?bodega_id={self.bodega_ajena.id}'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"admin_ok")

    @patch("httpx.Client.get")
    def test_general_report_requires_no_bodega(self, mock_httpx_get):
        """El catálogo de productos no requiere bodega_id para el bodeguero"""
        self.client.force_authenticate(user=self.bodeguero)
        
        mock_httpx_get.return_value = httpx.Response(200, content=b"catalogo_ok")

        url = '/api/reporting/export/productos'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b"catalogo_ok")

    @patch("httpx.Client.get")
    def test_restricted_report_requires_bodega_id(self, mock_httpx_get):
        """Si falta bodega_id en un reporte restringido, debe dar 400"""
        self.client.force_authenticate(user=self.bodeguero)
        
        url = '/api/reporting/export/kardex' # Sin bodega_id
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bodega_id es requerido", response.json()["detail"])

    def test_unauthenticated_denied(self):
        """Sin autenticación no hay acceso"""
        self.client.force_authenticate(user=None)
        
        url = '/api/reporting/export/productos'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
