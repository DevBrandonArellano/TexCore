"""
Pruebas de inventory/reportes_async.py — estado y descarga de las exportaciones
encoladas en Celery (?async=true en /api/reporting/...).

El token que devuelve el encolado está firmado y lleva el id de la tarea y el del
usuario: nadie consulta ni descarga la tarea de otro.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): token válido / alterado / de otro usuario;
  tarea pendiente / terminada con éxito / con fallo / con excepción.
- Tabla de decisión: estado de la tarea × existencia del archivo → código HTTP de la descarga.
- Caja blanca: rama de token vencido (max_age).
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from inventory.reportes_async import firmar_tarea, leer_tarea

User = get_user_model()

TASK_ID = "3f2b8c1e-0000-4000-8000-0000000000aa"
RESULTADO_OK = {
    "status": "SUCCESS",
    "archivo": f"{TASK_ID}.xlsx",
    "nombre": "kardex_qa.xlsx",
    "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "vacio": False,
    "user_id": None,
}


def _tarea(state, result=None):
    return MagicMock(state=state, result=result)


class TokenTareaTestCase(TestCase):
    def test_token_dado_mismo_usuario_cuando_se_lee_entonces_devuelve_el_id_de_la_tarea(self):
        self.assertEqual(leer_tarea(firmar_tarea(TASK_ID, 5), 5), TASK_ID)

    def test_token_dado_otro_usuario_cuando_se_lee_entonces_none(self):
        self.assertIsNone(leer_tarea(firmar_tarea(TASK_ID, 5), 6))

    def test_token_dado_alterado_cuando_se_lee_entonces_none(self):
        self.assertIsNone(leer_tarea(firmar_tarea(TASK_ID, 5) + "x", 5))

    @override_settings(REPORTES_ASYNC_TTL_SEGUNDOS=-1)
    def test_token_dado_vencido_cuando_se_lee_entonces_none(self):
        self.assertIsNone(leer_tarea(firmar_tarea(TASK_ID, 5), 5))


class EstadoReporteAsyncTestCase(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="dueno_async_qa", password="x")
        self.otro = User.objects.create_user(username="otro_async_qa", password="x")
        self.client = APIClient()
        self.client.force_authenticate(user=self.usuario)
        self.token = firmar_tarea(TASK_ID, self.usuario.id)

    def _estado(self, token=None):
        return self.client.get(f"/api/reporting/tareas/{token or self.token}/")

    @patch("inventory.reportes_async.AsyncResult")
    def test_estado_dado_tarea_pendiente_cuando_consulta_entonces_en_proceso(self, mock_async):
        mock_async.return_value = _tarea("PENDING")
        resp = self._estado()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"estado": "en_proceso"})
        mock_async.assert_called_once_with(TASK_ID)

    @patch("inventory.reportes_async.AsyncResult")
    def test_estado_dado_tarea_reintentando_cuando_consulta_entonces_en_proceso(self, mock_async):
        mock_async.return_value = _tarea("RETRY")
        self.assertEqual(self._estado().json()["estado"], "en_proceso")

    @patch("inventory.reportes_async.AsyncResult")
    def test_estado_dado_tarea_exitosa_cuando_consulta_entonces_listo_con_url_de_descarga(self, mock_async):
        mock_async.return_value = _tarea("SUCCESS", RESULTADO_OK)
        cuerpo = self._estado().json()
        self.assertEqual(cuerpo["estado"], "listo")
        self.assertEqual(cuerpo["nombre"], "kardex_qa.xlsx")
        self.assertFalse(cuerpo["vacio"])
        self.assertEqual(cuerpo["descarga_url"], f"/api/reporting/tareas/{self.token}/descarga/")

    @patch("inventory.reportes_async.AsyncResult")
    def test_estado_dado_tarea_que_devolvio_fallo_cuando_consulta_entonces_error(self, mock_async):
        mock_async.return_value = _tarea("SUCCESS", {"status": "FAILURE"})
        self.assertEqual(self._estado().json()["estado"], "error")

    @patch("inventory.reportes_async.AsyncResult")
    def test_estado_dado_tarea_con_excepcion_cuando_consulta_entonces_error(self, mock_async):
        mock_async.return_value = _tarea("FAILURE", RuntimeError("reintentos agotados"))
        self.assertEqual(self._estado().json()["estado"], "error")

    @patch("inventory.reportes_async.AsyncResult")
    def test_estado_dado_token_de_otro_usuario_cuando_consulta_entonces_404_sin_consultar_celery(self, mock_async):
        resp = self._estado(firmar_tarea(TASK_ID, self.otro.id))
        self.assertEqual(resp.status_code, 404)
        mock_async.assert_not_called()

    def test_estado_dado_anonimo_cuando_consulta_entonces_401(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(self._estado().status_code, 401)


class DescargaReporteAsyncTestCase(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username="dueno_descarga_qa", password="x")
        self.client = APIClient()
        self.client.force_authenticate(user=self.usuario)
        self.token = firmar_tarea(TASK_ID, self.usuario.id)
        self.directorio = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directorio, ignore_errors=True)
        ajustes = override_settings(REPORTES_ASYNC_DIR=str(self.directorio))
        ajustes.enable()
        self.addCleanup(ajustes.disable)

    def _descargar(self, token=None):
        return self.client.get(f"/api/reporting/tareas/{token or self.token}/descarga/")

    @patch("inventory.reportes_async.AsyncResult")
    def test_descarga_dado_tarea_lista_cuando_descarga_entonces_200_con_el_archivo_y_cabeceras(self, mock_async):
        (self.directorio / f"{TASK_ID}.xlsx").write_bytes(b"PK-excel")
        mock_async.return_value = _tarea("SUCCESS", {**RESULTADO_OK, "vacio": True})

        resp = self._descargar()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"PK-excel")
        self.assertEqual(resp["Content-Type"], RESULTADO_OK["content_type"])
        self.assertIn('filename="kardex_qa.xlsx"', resp["Content-Disposition"])
        self.assertEqual(resp["X-Report-Empty"], "true")

    @patch("inventory.reportes_async.AsyncResult")
    def test_descarga_dado_tarea_en_proceso_cuando_descarga_entonces_409(self, mock_async):
        mock_async.return_value = _tarea("STARTED")
        self.assertEqual(self._descargar().status_code, 409)

    @patch("inventory.reportes_async.AsyncResult")
    def test_descarga_dado_tarea_con_fallo_cuando_descarga_entonces_409(self, mock_async):
        mock_async.return_value = _tarea("SUCCESS", {"status": "FAILURE"})
        self.assertEqual(self._descargar().status_code, 409)

    @patch("inventory.reportes_async.AsyncResult")
    def test_descarga_dado_archivo_ya_limpiado_cuando_descarga_entonces_410(self, mock_async):
        mock_async.return_value = _tarea("SUCCESS", RESULTADO_OK)
        self.assertEqual(self._descargar().status_code, 410)

    @patch("inventory.reportes_async.AsyncResult")
    def test_descarga_dado_resultado_con_ruta_manipulada_cuando_descarga_entonces_no_sale_del_directorio(
        self, mock_async
    ):
        # Defensa en profundidad: aunque el resultado guardado traiga otra ruta, el archivo
        # se resuelve solo con el id de la tarea (que viene del token firmado).
        (self.directorio / f"{TASK_ID}.xlsx").write_bytes(b"PK-excel")
        mock_async.return_value = _tarea("SUCCESS", {**RESULTADO_OK, "archivo": "../../etc/passwd"})
        resp = self._descargar()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content), b"PK-excel")

    @patch("inventory.reportes_async.AsyncResult")
    def test_descarga_dado_token_invalido_cuando_descarga_entonces_404(self, mock_async):
        self.assertEqual(self._descargar("no-es-un-token").status_code, 404)
        mock_async.assert_not_called()


class BrokerCaidoFallaRapidoTestCase(TestCase):
    """Con Redis caído, encolar debe fallar en pocos segundos: mientras tanto un worker
    síncrono de gunicorn queda bloqueado (medido en el stack: 25,7 s antes de acotar
    también los reintentos del result backend)."""

    def test_encolar_dado_redis_inalcanzable_cuando_publica_entonces_falla_en_menos_de_5_segundos(self):
        import time

        from celery import Celery
        from kombu.exceptions import OperationalError

        app = Celery("texcore_broker_caido_qa")
        app.config_from_object("django.conf:settings", namespace="CELERY")
        # Con el namespace CELERY mandan las claves en mayúsculas. settings_test activa el
        # modo eager; aquí se publica de verdad contra un Redis que no existe.
        inalcanzable = "redis://127.0.0.1:1/0"
        app.conf.update(
            CELERY_TASK_ALWAYS_EAGER=False,
            CELERY_BROKER_URL=inalcanzable,
            CELERY_RESULT_BACKEND=inalcanzable,
            broker_url=inalcanzable,
            result_backend=inalcanzable,
        )

        @app.task
        def tarea_qa():  # pragma: no cover — nunca llega a ejecutarse
            return None

        inicio = time.monotonic()
        with self.assertRaises(OperationalError):
            tarea_qa.delay()
        self.assertLess(time.monotonic() - inicio, 5)
