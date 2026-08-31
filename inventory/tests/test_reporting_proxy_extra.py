"""
Pruebas complementarias de inventory/reporting_proxy.py — ramas que
test_reporting_proxy.py no ejercita: fallback por sede, bodega inexistente,
path traversal, modo async, y errores del microservicio (4xx/timeout/500).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): bodega inexistente, path fuera de whitelist,
  respuesta 200/4xx/5xx del microservicio, conexión caída.
- Caja blanca: rama de fallback por sede (sin asignación M2M explícita) y
  rama `is_async` que delega a Celery en vez de llamar sincrónicamente.
"""
import os
from unittest.mock import MagicMock, patch

import httpx
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import Bodega, Sede
from inventory.reporting_proxy import _get_required_env, _validate_report_path

User = get_user_model()


class GetRequiredEnvTestCase(TestCase):
    def test_get_required_env_dado_variable_presente_cuando_llama_entonces_retorna_valor(self):
        with patch.dict('os.environ', {'MI_VAR_QA': 'valor123'}):
            self.assertEqual(_get_required_env('MI_VAR_QA'), 'valor123')

    def test_get_required_env_dado_variable_ausente_cuando_llama_entonces_error(self):
        os.environ.pop('VAR_QA_INEXISTENTE', None)
        with self.assertRaises(ImproperlyConfigured):
            _get_required_env('VAR_QA_INEXISTENTE')


class ValidateReportPathTestCase(TestCase):
    def test_validate_dado_path_traversal_cuando_valida_entonces_false(self):
        self.assertFalse(_validate_report_path('export/../secreto'))

    def test_validate_dado_doble_slash_cuando_valida_entonces_false(self):
        self.assertFalse(_validate_report_path('export//kardex'))

    def test_validate_dado_backslash_cuando_valida_entonces_false(self):
        self.assertFalse(_validate_report_path('export\\kardex'))

    def test_validate_dado_prefijo_no_permitido_cuando_valida_entonces_false(self):
        self.assertFalse(_validate_report_path('admin/secreto'))

    def test_validate_dado_path_valido_cuando_valida_entonces_true(self):
        self.assertTrue(_validate_report_path('export/kardex'))


class ReportingProxyViewExtraTestCase(TestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede QA", location="Quito")
        self.otra_sede = Sede.objects.create(nombre="Otra Sede QA", location="Guayaquil")
        self.bodega = Bodega.objects.create(nombre="Bodega QA", sede=self.sede)

        self.group_bodeguero, _ = Group.objects.get_or_create(name='bodeguero')
        self.usuario_misma_sede = User.objects.create_user(
            username='mismasede_qa', password='x', sede=self.sede,
        )
        self.usuario_misma_sede.groups.add(self.group_bodeguero)

        self.client = APIClient()

    @patch("httpx.Client.get")
    def test_get_dado_usuario_sin_asignacion_pero_misma_sede_cuando_get_entonces_200(self, mock_get):
        # Caja blanca: fallback por sede cuando no hay asignación M2M explícita
        self.client.force_authenticate(user=self.usuario_misma_sede)
        mock_get.return_value = httpx.Response(200, content=b"ok-por-sede")

        url = f'/api/reporting/export/kardex?bodega_id={self.bodega.id}'
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content, b"ok-por-sede")

    def test_get_dado_bodega_inexistente_cuando_get_entonces_404(self):
        self.client.force_authenticate(user=self.usuario_misma_sede)
        resp = self.client.get('/api/reporting/export/kardex?bodega_id=999999')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_dado_path_fuera_de_whitelist_cuando_get_entonces_400(self):
        admin = User.objects.create_user(username='admin_qa2', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        resp = self.client.get('/api/reporting/admin/secreto')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('no permitida', resp.json()['detail'])

    @patch('gestion.tasks.async_export_report.delay')
    def test_get_dado_modo_async_cuando_get_entonces_202_y_no_llama_httpx(self, mock_delay):
        admin = User.objects.create_user(username='admin_qa3', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        mock_delay.return_value = MagicMock(id='task-123')

        with patch("httpx.Client.get") as mock_get:
            resp = self.client.get('/api/reporting/export/productos?async=true')
            mock_get.assert_not_called()

        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json()['task_id'], 'task-123')

    @patch("httpx.Client.get")
    def test_get_dado_microservicio_responde_error_cuando_get_entonces_propaga_status(self, mock_get):
        admin = User.objects.create_user(username='admin_qa4', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        mock_get.return_value = httpx.Response(400, json={"detail": "parámetro inválido"})

        resp = self.client.get('/api/reporting/export/productos')

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()['detail'], 'parámetro inválido')

    @patch("httpx.Client.get")
    def test_get_dado_microservicio_responde_error_sin_json_cuando_get_entonces_detalle_generico(self, mock_get):
        # Caja blanca: rama `except BaseException` al parsear el body de error
        admin = User.objects.create_user(username='admin_qa5', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        mock_get.return_value = httpx.Response(500, content=b'not-json')

        resp = self.client.get('/api/reporting/export/productos')

        self.assertEqual(resp.status_code, 500)
        self.assertIn('Error 500', resp.json()['detail'])

    @patch("httpx.Client.get")
    def test_get_dado_content_disposition_cuando_get_entonces_lo_copia(self, mock_get):
        admin = User.objects.create_user(username='admin_qa6', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        mock_get.return_value = httpx.Response(
            200, content=b"excel", headers={"Content-Disposition": 'attachment; filename="r.xlsx"'},
        )

        resp = self.client.get('/api/reporting/export/productos')

        self.assertEqual(resp['Content-Disposition'], 'attachment; filename="r.xlsx"')

    @patch("httpx.Client.get", side_effect=httpx.ConnectError("no se pudo conectar"))
    def test_get_dado_error_de_conexion_cuando_get_entonces_502(self, mock_get):
        admin = User.objects.create_user(username='admin_qa7', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        resp = self.client.get('/api/reporting/export/productos')
        self.assertEqual(resp.status_code, 502)

    @patch("httpx.Client.get", side_effect=RuntimeError("fallo inesperado"))
    def test_get_dado_excepcion_generica_cuando_get_entonces_500(self, mock_get):
        admin = User.objects.create_user(username='admin_qa8', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        resp = self.client.get('/api/reporting/export/productos')
        self.assertEqual(resp.status_code, 500)

    @patch("httpx.Client.get")
    def test_get_dado_query_param_format_xlsx_cuando_get_entonces_200_no_404(self, mock_get):
        """
        Regresión: 'format' es el query param reservado por DRF para negociación
        de contenido (URL_FORMAT_OVERRIDE). Como el proxy reenvía 'format=xlsx'/
        'csv' al microservicio (no es un renderer DRF), sin el override de
        content_negotiation_class la vista nunca llegaba a ejecutar get() —
        DefaultContentNegotiation.filter_renderers lanzaba Http404 antes.
        """
        admin = User.objects.create_user(username='admin_qa9', password='x', is_superuser=True)
        self.client.force_authenticate(user=admin)
        mock_get.return_value = httpx.Response(200, content=b"excel-xlsx")

        resp = self.client.get('/api/reporting/gerencial/ventas', {
            'fecha_inicio': '2026-08-01', 'fecha_fin': '2026-08-31', 'format': 'xlsx',
        })

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content, b"excel-xlsx")
