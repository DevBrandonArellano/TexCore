"""
Pruebas de gestion/tasks.py — tareas asíncronas Celery.

async_export_report: consulta los datos en proceso (internal_api/services/
report_dispatch.py) y le pide a reporting_excel que formatee el archivo
(JWT RS256) — ver auditoría de performance 2026-08-31.
run_mrp_calculation: recálculo de KPIs de producción/MRP para una sede.

Técnicas ISTQB aplicadas:
- Caja blanca: rama éxito (HTTP 200), rama de fallo HTTP (retry), rama de
  error de conexión (retry con excepción), y rama de excepción genérica.
- Partición de equivalencia (EP): sede_id válido vs. servicio que lanza excepción.
"""
from unittest.mock import MagicMock, patch

import httpx
from django.test import TestCase

from gestion.tasks import async_export_report, run_mrp_calculation


class AsyncExportReportTestCase(TestCase):
    @patch('internal_api.services.report_dispatch.resolve_report')
    @patch('gestion.tasks.httpx.Client')
    @patch('gestion.tasks.JWTServiceAuthentication.generate_token', return_value='fake-token')
    def test_export_dado_respuesta_200_cuando_ejecuta_entonces_success(
        self, mock_token, mock_client_cls, mock_resolve,
    ):
        mock_resolve.return_value = ([{"col": 1}], "kardex_test")
        mock_response = MagicMock(status_code=200)
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client

        task = async_export_report
        resultado = task.run(report_path='export/kardex', params={'bodega_id': 1}, user_id=7)

        self.assertEqual(resultado['status'], 'SUCCESS')
        self.assertEqual(resultado['report_path'], 'export/kardex')
        self.assertEqual(resultado['user_id'], 7)

    @patch('internal_api.services.report_dispatch.resolve_report')
    @patch('gestion.tasks.httpx.Client')
    @patch('gestion.tasks.JWTServiceAuthentication.generate_token', return_value='fake-token')
    def test_export_dado_respuesta_error_http_cuando_ejecuta_entonces_reintenta(
        self, mock_token, mock_client_cls, mock_resolve,
    ):
        # Caja blanca: rama status_code != 200 -> self.retry(countdown=60)
        mock_resolve.return_value = ([], "kardex_test")
        mock_response = MagicMock(status_code=500)
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client

        task = async_export_report
        with patch.object(task, 'retry', side_effect=Exception('retry-called')) as mock_retry:
            with self.assertRaises(Exception):
                task.run(report_path='export/kardex', params={'bodega_id': 1}, user_id=1)
            mock_retry.assert_called_once_with(countdown=60)

    @patch('internal_api.services.report_dispatch.resolve_report')
    @patch('gestion.tasks.httpx.Client')
    @patch('gestion.tasks.JWTServiceAuthentication.generate_token', return_value='fake-token')
    def test_export_dado_error_de_conexion_cuando_ejecuta_entonces_reintenta_con_excepcion(
        self, mock_token, mock_client_cls, mock_resolve,
    ):
        # Caja blanca: rama httpx.RequestError -> self.retry(exc=exc, countdown=60)
        mock_resolve.return_value = ([], "kardex_test")
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError('no se pudo conectar')
        mock_client_cls.return_value.__enter__.return_value = mock_client

        task = async_export_report
        with patch.object(task, 'retry', side_effect=Exception('retry-called')) as mock_retry:
            with self.assertRaises(Exception):
                task.run(report_path='export/kardex', params={'bodega_id': 1}, user_id=1)
            self.assertEqual(mock_retry.call_args.kwargs['countdown'], 60)
            self.assertIsInstance(mock_retry.call_args.kwargs['exc'], httpx.ConnectError)


class RunMrpCalculationTestCase(TestCase):
    @patch('gestion.services.produccion_kpi_service.ProduccionKPIService.obtener_kpis')
    def test_mrp_dado_calculo_exitoso_cuando_ejecuta_entonces_success(self, mock_obtener_kpis):
        mock_obtener_kpis.return_value = MagicMock()

        resultado = run_mrp_calculation.run(sede_id=3)

        self.assertEqual(resultado['status'], 'SUCCESS')
        self.assertEqual(resultado['sede_id'], 3)
        self.assertTrue(resultado['kpis_generados'])

    @patch('gestion.services.produccion_kpi_service.ProduccionKPIService.obtener_kpis')
    def test_mrp_dado_servicio_lanza_excepcion_cuando_ejecuta_entonces_error(self, mock_obtener_kpis):
        # Caja blanca: rama except Exception -> status ERROR, no propaga
        mock_obtener_kpis.side_effect = RuntimeError('fallo interno de KPI')

        resultado = run_mrp_calculation.run(sede_id=9)

        self.assertEqual(resultado['status'], 'ERROR')
        self.assertIn('fallo interno de KPI', resultado['error'])
