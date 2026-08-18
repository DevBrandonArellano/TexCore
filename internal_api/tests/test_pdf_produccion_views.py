"""
Pruebas unitarias para vistas de generación de PDFs de producción en internal_api:
  - ReporteAvancePdfView
  - BalanceMasasPdfView
  - Permiso IsInternalServiceOrUser (ServicePrincipal y Usuario Jefe de Planta/Área)
"""
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import httpx

from gestion.models import Sede, OrdenProduccion, LoteProduccion, Bodega
from internal_api.authentication import JWTServiceAuthentication

User = get_user_model()


class TestPdfProduccionViews(APITestCase):

    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)

        self.group_jefe_planta, _ = Group.objects.get_or_create(name="jefe_planta")
        self.group_operario, _ = Group.objects.get_or_create(name="operario")


        self.user_jefe = User.objects.create_user(
            username="jefe_planta_user",
            email="jefe@texcore.com",
            password="Password123!",
            sede=self.sede,
        )
        self.user_jefe.groups.add(self.group_jefe_planta)

        self.user_sin_permiso = User.objects.create_user(
            username="operario_user",
            email="operario@texcore.com",
            password="Password123!",
            sede=self.sede,
        )
        self.user_sin_permiso.groups.add(self.group_operario)

        self.service_token = JWTServiceAuthentication.generate_token(
            service_name="scanning-service",
            scopes=["reports:read"],
        )

        self.url_avance = reverse("internal_api:reports_produccion_reporte_avance")
        self.url_balance = reverse("internal_api:reports_produccion_reporte_balance")

    def test_reporte_avance_usuario_sin_permiso_retorna_403(self):
        self.client.force_authenticate(user=self.user_sin_permiso)
        response = self.client.post(self.url_avance, {"empresa_nombre": "TexCore"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reporte_balance_servicio_sin_sede_id_retorna_400(self):
        # Un llamador de SERVICIO (ServicePrincipal, sin sede) que no envía
        # sede_id no tiene sede derivable → 400. (Un usuario humano con sede la
        # deriva automáticamente; ver test_reporte_balance_usuario_jefe_deriva_su_sede.)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.service_token}")
        response = self.client.post(self.url_balance, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("httpx.Client.post")
    def test_reporte_balance_usuario_jefe_deriva_su_sede(self, mock_httpx_post):
        # El jefe de planta con sede NO necesita enviar sede_id: se deriva de su
        # identidad autenticada (el frontend ya no la envía, evitando fugas de
        # sede ajena). Con la sede derivada, la vista procede al printing_service.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 balance derivado"
        mock_httpx_post.return_value = mock_response

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(self.url_balance, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("httpx.Client.post")
    def test_reporte_avance_usuario_jefe_exito(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 test avance content"
        mock_httpx_post.return_value = mock_response

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(
            self.url_avance,
            {"empresa_nombre": "TexCore Industrial", "sede_id": self.sede.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=\"reporte_avance_", response["Content-Disposition"])

    @patch("httpx.Client.post")
    def test_reporte_balance_service_token_exito(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 test balance content"
        mock_httpx_post.return_value = mock_response

        response = self.client.post(
            self.url_balance,
            {"sede_id": self.sede.id, "mes_label": "Agosto 2026", "empresa_nombre": "TexCore"},
            HTTP_AUTHORIZATION=f"Bearer {self.service_token}",
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    @patch("httpx.Client.post")
    def test_reporte_avance_printing_service_error_http_502(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error in printing service"
        mock_httpx_post.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(self.url_avance, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch("httpx.Client.post")
    def test_reporte_balance_printing_service_conexion_fallida_503(self, mock_httpx_post):
        mock_httpx_post.side_effect = httpx.RequestError("Connection timeout", request=MagicMock())

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(self.url_balance, {"sede_id": self.sede.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
