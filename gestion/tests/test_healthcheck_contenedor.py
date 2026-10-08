"""HEALTHCHECK del contenedor backend (infrastructure/docker/healthcheck.py).

El script vive fuera de un paquete: se carga por ruta para probar cómo elige
el encabezado Host a partir de ALLOWED_HOSTS.
"""
import importlib.util
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

RUTA = Path(settings.BASE_DIR) / "infrastructure" / "docker" / "healthcheck.py"


def _cargar_healthcheck():
    spec = importlib.util.spec_from_file_location("healthcheck_contenedor", RUTA)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


class HostDeAllowedHostsTest(SimpleTestCase):
    def setUp(self):
        self.healthcheck = _cargar_healthcheck()

    def test_host_dado_allowed_hosts_con_dominio_cuando_se_elige_entonces_usa_el_primero(self):
        with mock.patch.dict("os.environ", {"ALLOWED_HOSTS": "erp.planta.local,backend"}):
            self.assertEqual(self.healthcheck.host_de_allowed_hosts(), "erp.planta.local")

    def test_host_dado_comodin_de_subdominio_cuando_se_elige_entonces_quita_el_punto(self):
        with mock.patch.dict("os.environ", {"ALLOWED_HOSTS": ".planta.local"}):
            self.assertEqual(self.healthcheck.host_de_allowed_hosts(), "planta.local")

    def test_host_dado_asterisco_o_vacio_cuando_se_elige_entonces_usa_localhost(self):
        for valor in ("*", "", " ,backend"):
            with self.subTest(valor=valor), mock.patch.dict("os.environ", {"ALLOWED_HOSTS": valor}):
                self.assertEqual(self.healthcheck.host_de_allowed_hosts(), "localhost")


class MainHealthcheckTest(SimpleTestCase):
    def setUp(self):
        self.healthcheck = _cargar_healthcheck()

    def _respuesta(self, status):
        respuesta = mock.MagicMock(status=status)
        respuesta.__enter__.return_value = respuesta
        return respuesta

    def test_main_dado_backend_responde_200_cuando_se_sondea_entonces_sale_con_0_y_envia_el_host(self):
        with mock.patch.dict("os.environ", {"ALLOWED_HOSTS": "erp.planta.local"}), \
                mock.patch("urllib.request.urlopen", return_value=self._respuesta(200)) as urlopen:
            self.assertEqual(self.healthcheck.main(), 0)
        peticion = urlopen.call_args.args[0]
        self.assertEqual(peticion.full_url, "http://127.0.0.1:8000/api/health/")
        self.assertEqual(peticion.get_header("Host"), "erp.planta.local")

    def test_main_dado_backend_no_responde_cuando_se_sondea_entonces_sale_con_1(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("connection refused")), \
                mock.patch("sys.stderr"):
            self.assertEqual(self.healthcheck.main(), 1)
