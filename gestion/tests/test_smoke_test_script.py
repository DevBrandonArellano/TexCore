"""
Pruebas de humo del release (`scripts/smoke_test.py`): el script recibe las URL de nginx
por línea de comandos y las abre con `urllib`. Solo acepta `http://` y `https://`: un
esquema como `file://` leería un archivo del runner en lugar de consultar el servicio.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): esquema permitido / no permitido.
- Análisis de valor límite (BVA): la URL sin esquema y la que lo trae en mayúsculas.
"""

import importlib.util
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ruta = Path(settings.BASE_DIR) / "scripts" / "smoke_test.py"
_spec = importlib.util.spec_from_file_location("smoke_test", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
smoke = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(smoke)


class EsquemaDeLasUrlTest(SimpleTestCase):
    def test_base_dado_esquema_no_http_cuando_arranca_entonces_sale_con_2_sin_abrir_nada(self):
        for base in ("file:///etc/passwd", "ftp://servidor/api", "localhost:8443"):
            with self.subTest(base=base):
                self.assertEqual(smoke.main([base]), 2)

    def test_http_dado_esquema_no_http_cuando_arranca_entonces_sale_con_2(self):
        self.assertEqual(smoke.main(["https://localhost:8443", "--http", "file:///etc/hosts"]), 2)

    def test_base_dado_esquema_en_mayusculas_cuando_se_valida_entonces_se_acepta(self):
        self.assertTrue(smoke._url_valida("HTTPS://localhost:8443"))
        self.assertTrue(smoke._url_valida("http://localhost:8080"))
        self.assertFalse(smoke._url_valida("file:///etc/passwd"))
