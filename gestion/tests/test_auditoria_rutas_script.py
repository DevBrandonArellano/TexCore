"""
Pruebas de la auditoría de rutas sin consumidor (`scripts/auditar_rutas_frontend.py`).

El frontend arma muchas URL sobre una constante de módulo (`const BASE = '/paros-maquina/'`
y después `${BASE}historial/`), así que el script expande esas constantes antes de buscar:
sin eso, una ruta consumida se reportaba como huérfana y el gate daba un falso positivo.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): constante de cadena / constante que no es cadena / sin constante.
- Análisis de valor límite (BVA): la constante que es el prefijo completo de la ruta y la ruta ausente.
"""

import importlib.util
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ruta = Path(settings.BASE_DIR) / "scripts" / "auditar_rutas_frontend.py"
_spec = importlib.util.spec_from_file_location("auditar_rutas_frontend", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
auditoria = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditoria)


class ExpansionDeConstantesTest(SimpleTestCase):
    def test_expandir_dado_constante_de_cadena_cuando_se_interpola_entonces_queda_la_ruta_literal(self):
        texto = "const BASE = '/paros-maquina/';\napiClient.get(`${BASE}historial/`);"
        self.assertIn("/paros-maquina/historial/", auditoria.expandir_constantes(texto))

    def test_expandir_dado_comillas_dobles_y_backtick_cuando_se_interpola_entonces_tambien_expande(self):
        for cita in ('"', "`"):
            with self.subTest(cita=cita):
                texto = f"const BASE = {cita}/inventory/sugerencias-compra/{cita};\nget(`${{BASE}}ultima-ejecucion/`);"
                self.assertIn("/inventory/sugerencias-compra/ultima-ejecucion/", auditoria.expandir_constantes(texto))

    def test_expandir_dado_constante_que_no_es_cadena_cuando_se_interpola_entonces_no_la_toca(self):
        texto = "const PAGINA = 1;\nconst url = `/lotes/${PAGINA}/`;"
        self.assertIn("${PAGINA}", auditoria.expandir_constantes(texto))

    def test_expandir_dado_texto_sin_constantes_cuando_se_expande_entonces_no_cambia(self):
        texto = "apiClient.get('/maquinas/');"
        self.assertEqual(auditoria.expandir_constantes(texto), texto)


class DeteccionDeConsumidorTest(SimpleTestCase):
    """La ruta se busca sobre el texto ya expandido, como lo hace `main()`."""

    def _consumida(self, ruta, texto):
        segs = auditoria.segmentos(ruta)
        expandido = auditoria.expandir_constantes(texto)
        return bool(auditoria.regex_para(segs, expandido).search(expandido))

    def test_ruta_dado_consumo_por_constante_cuando_se_audita_entonces_cuenta_como_consumida(self):
        texto = "const BASE = '/paros-maquina/';\nawait apiClient.get(`${BASE}historial/`, { params });"
        self.assertTrue(self._consumida("api/^paros-maquina/historial/$", texto))

    def test_ruta_dado_consumo_directo_cuando_se_audita_entonces_cuenta_como_consumida(self):
        self.assertTrue(self._consumida("api/^maquinas/$", "apiClient.get('/maquinas/');"))

    def test_ruta_dado_que_nadie_la_llama_cuando_se_audita_entonces_no_cuenta_como_consumida(self):
        texto = "const BASE = '/paros-maquina/';\napiClient.get(`${BASE}historial/`);"
        self.assertFalse(self._consumida("api/^paros-maquina/exportar/$", texto))
