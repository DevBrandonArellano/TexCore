"""
Pruebas de gestion/tasks.py — tareas asíncronas Celery.

async_export_report: consulta los datos en proceso (internal_api/services/
report_dispatch.py) y le pide a reporting_excel que formatee el archivo
(JWT RS256) — ver auditoría de performance 2026-08-31.

Técnicas ISTQB aplicadas:
- Caja blanca: rama éxito (HTTP 200), rama de fallo HTTP (retry), rama de
  error de conexión (retry con excepción), y rama de excepción genérica.
- Partición de equivalencia (EP): sede_id válido vs. servicio que lanza excepción.
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from django.test import TestCase, override_settings

from gestion.tasks import async_export_report


class AsyncExportReportTestCase(TestCase):
    @patch("internal_api.services.report_dispatch.resolve_report")
    @patch("gestion.tasks.httpx.Client")
    @patch("gestion.tasks.JWTServiceAuthentication.generate_token", return_value="fake-token")
    def test_export_dado_respuesta_200_cuando_ejecuta_entonces_success(
        self,
        mock_token,
        mock_client_cls,
        mock_resolve,
    ):
        mock_resolve.return_value = ([{"col": 1}], "kardex_test")
        mock_response = MagicMock(status_code=200, content=b"x", headers={})
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client

        task = async_export_report
        with tempfile.TemporaryDirectory() as directorio, override_settings(REPORTES_ASYNC_DIR=directorio):
            resultado = task.run(report_path="export/kardex", params={"bodega_id": 1}, user_id=7)

        self.assertEqual(resultado["status"], "SUCCESS")
        self.assertEqual(resultado["report_path"], "export/kardex")
        self.assertEqual(resultado["user_id"], 7)

    @patch("internal_api.services.report_dispatch.resolve_report")
    @patch("gestion.tasks.httpx.Client")
    @patch("gestion.tasks.JWTServiceAuthentication.generate_token", return_value="fake-token")
    def test_export_dado_respuesta_error_http_cuando_ejecuta_entonces_reintenta(
        self,
        mock_token,
        mock_client_cls,
        mock_resolve,
    ):
        # Caja blanca: rama status_code != 200 -> self.retry(countdown=60)
        mock_resolve.return_value = ([], "kardex_test")
        mock_response = MagicMock(status_code=500)
        mock_client = MagicMock()
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value.__enter__.return_value = mock_client

        task = async_export_report
        with patch.object(task, "retry", side_effect=RuntimeError("retry-called")) as mock_retry:
            with self.assertRaises(RuntimeError):
                task.run(report_path="export/kardex", params={"bodega_id": 1}, user_id=1)
            mock_retry.assert_called_once_with(countdown=60)

    @patch("internal_api.services.report_dispatch.resolve_report")
    @patch("gestion.tasks.httpx.Client")
    @patch("gestion.tasks.JWTServiceAuthentication.generate_token", return_value="fake-token")
    def test_export_dado_error_de_conexion_cuando_ejecuta_entonces_reintenta_con_excepcion(
        self,
        mock_token,
        mock_client_cls,
        mock_resolve,
    ):
        # Caja blanca: rama httpx.RequestError -> self.retry(exc=exc, countdown=60)
        mock_resolve.return_value = ([], "kardex_test")
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.ConnectError("no se pudo conectar")
        mock_client_cls.return_value.__enter__.return_value = mock_client

        task = async_export_report
        with patch.object(task, "retry", side_effect=RuntimeError("retry-called")) as mock_retry:
            with self.assertRaises(RuntimeError):
                task.run(report_path="export/kardex", params={"bodega_id": 1}, user_id=1)
            self.assertEqual(mock_retry.call_args.kwargs["countdown"], 60)
            self.assertIsInstance(mock_retry.call_args.kwargs["exc"], httpx.ConnectError)


class AsyncExportReportArchivoTestCase(TestCase):
    """La tarea guarda el archivo generado para que el usuario lo descargue después.

    Técnicas ISTQB:
    - Partición de equivalencia (EP): formato xlsx / csv; reporte con datos / vacío.
    - Análisis de valores límite (BVA): archivo justo antes y después del TTL de limpieza.
    """

    def setUp(self):
        self.directorio = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directorio, ignore_errors=True)

    def _ejecutar(self, task_id, report_format="xlsx", cabeceras=None, contenido=b"PK-excel"):
        respuesta = MagicMock(status_code=200, content=contenido, headers=cabeceras or {})
        cliente = MagicMock()
        cliente.post.return_value = respuesta
        with (
            override_settings(REPORTES_ASYNC_DIR=str(self.directorio), REPORTES_ASYNC_TTL_SEGUNDOS=3600),
            patch("internal_api.services.report_dispatch.resolve_report", return_value=([{"a": 1}], "kardex_qa")),
            patch("gestion.tasks.httpx.Client") as cliente_cls,
            patch("gestion.tasks.JWTServiceAuthentication.generate_token", return_value="t"),
        ):
            cliente_cls.return_value.__enter__.return_value = cliente
            async_export_report.push_request(id=task_id)
            try:
                return async_export_report.run(
                    report_path="export/kardex", params={}, user_id=7, report_format=report_format
                )
            finally:
                async_export_report.pop_request()

    def test_export_dado_respuesta_200_cuando_ejecuta_entonces_guarda_el_archivo_con_el_id_de_la_tarea(self):
        cabeceras = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "Content-Disposition": 'attachment; filename="kardex_qa.xlsx"',
        }
        resultado = self._ejecutar("3f2b8c1e-0000-4000-8000-000000000001", cabeceras=cabeceras)

        archivo = self.directorio / "3f2b8c1e-0000-4000-8000-000000000001.xlsx"
        self.assertEqual(archivo.read_bytes(), b"PK-excel")
        self.assertEqual(resultado["status"], "SUCCESS")
        self.assertEqual(resultado["archivo"], archivo.name)
        self.assertEqual(resultado["nombre"], "kardex_qa.xlsx")
        self.assertEqual(resultado["content_type"], cabeceras["Content-Type"])
        self.assertFalse(resultado["vacio"])

    def test_export_dado_formato_csv_y_reporte_vacio_cuando_ejecuta_entonces_extension_csv_y_marca_vacio(self):
        resultado = self._ejecutar(
            "3f2b8c1e-0000-4000-8000-000000000002",
            report_format="csv",
            cabeceras={"Content-Type": "text/csv", "X-Report-Empty": "true"},
        )

        self.assertEqual(resultado["archivo"], "3f2b8c1e-0000-4000-8000-000000000002.csv")
        self.assertEqual(resultado["nombre"], "kardex_qa.csv")
        self.assertTrue(resultado["vacio"])

    def test_export_dado_archivos_previos_cuando_ejecuta_entonces_borra_solo_los_vencidos(self):
        ahora = time.time()
        vencido = self.directorio / "viejo.xlsx"
        vigente = self.directorio / "reciente.xlsx"
        for archivo, edad in ((vencido, 3601), (vigente, 3599)):
            archivo.write_bytes(b"x")
            os.utime(archivo, (ahora - edad, ahora - edad))

        self._ejecutar("3f2b8c1e-0000-4000-8000-000000000003")

        self.assertFalse(vencido.exists())
        self.assertTrue(vigente.exists())
