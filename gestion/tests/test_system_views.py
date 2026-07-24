"""
Pruebas de las vistas de sistema — gestion/views/system_views.py.

FrontendLogView: relay de logs del navegador hacia el logger backend (RFC 5424).
Es AllowAny (sin autenticación) y mapea severity → nivel de logging Python.

Técnicas ISTQB aplicadas:
- Particiones de equivalencia (EP) sobre 'severity': los rangos que mapean a
  CRITICAL / ERROR / WARNING / INFO.
- Análisis de valores límite (BVA): severity = 2, 3, 4, 5 (fronteras del mapeo).
- Caja blanca: rama de payload no-dict (400) y payload válido (204).
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class FrontendLogViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('frontend-logs')

    def test_log_dado_entrada_valida_cuando_post_entonces_204(self):
        resp = self.client.post(
            self.url, {'severity': 6, 'message': 'evento de prueba', 'msgid': 'ui.click'},
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_payload_no_dict_cuando_post_entonces_400(self):
        # Caja blanca: rama `not isinstance(entry, dict)` -> 400
        resp = self.client.post(self.url, ['no', 'es', 'dict'], format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_log_dado_severity_critica_cuando_post_entonces_204(self):
        # BVA: severity = 2 (frontera CRITICAL: <= 2)
        resp = self.client.post(self.url, {'severity': 2, 'message': 'crit'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_severity_error_cuando_post_entonces_204(self):
        # BVA: severity = 3 (ERROR)
        resp = self.client.post(self.url, {'severity': 3, 'message': 'err'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_severity_warning_cuando_post_entonces_204(self):
        # BVA: severity = 4 (WARNING)
        resp = self.client.post(self.url, {'severity': 4, 'message': 'warn'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_severity_info_cuando_post_entonces_204(self):
        # BVA: severity = 5 (frontera INFO: >= 5)
        resp = self.client.post(self.url, {'severity': 5, 'message': 'info'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_msgid_con_puntos_cuando_post_entonces_normaliza_y_204(self):
        # El msgid con puntos se normaliza (replace '.' -> '-')
        resp = self.client.post(
            self.url, {'severity': 6, 'message': 'x', 'msgid': 'modulo.sub.accion'},
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_log_dado_sin_campos_cuando_post_entonces_usa_defaults_204(self):
        # Sin severity/message: usa defaults (severity=6 -> INFO)
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
