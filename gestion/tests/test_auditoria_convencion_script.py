"""
Pruebas del gate ISTQB (`scripts/auditar_convencion_pruebas.py`).

La tesis afirma que los casos de prueba se diseñan con técnicas de caja negra del ISTQB
(CTFL v4.0). El gate lo hace verificable en el pipeline: cada prueba sigue la convención
`test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]` (en el frontend,
«dado … cuando … entonces») y cada archivo de prueba declara las técnicas que aplica.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): nombre conforme / sin objeto / sin alguna de las tres
  partes; archivo con técnica declarada / sin la palabra ISTQB / con ISTQB sin técnica.
- Caja blanca (CB): extracción de nombres de funciones anidadas en clases, `async`,
  `it.each` y comillas de los tres tipos.
"""

import importlib.util
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ruta = Path(settings.BASE_DIR) / "scripts" / "auditar_convencion_pruebas.py"
_spec = importlib.util.spec_from_file_location("auditar_convencion_pruebas", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
auditoria = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(auditoria)


class NombrePythonTest(SimpleTestCase):
    def test_nombre_dado_las_cuatro_partes_cuando_se_valida_entonces_es_conforme(self):
        self.assertTrue(auditoria.nombre_python_valido("test_lote_dado_stock_cero_cuando_valida_entonces_400"))

    def test_nombre_dado_sin_objeto_cuando_se_valida_entonces_no_es_conforme(self):
        self.assertFalse(auditoria.nombre_python_valido("test_dado_texto_cuando_sanea_entonces_lo_elimina"))

    def test_nombre_dado_sin_dado_cuando_se_valida_entonces_no_es_conforme(self):
        self.assertFalse(auditoria.nombre_python_valido("test_health_ok_cuando_existen_entonces_200"))

    def test_nombre_dado_sin_ninguna_parte_cuando_se_valida_entonces_no_es_conforme(self):
        self.assertFalse(auditoria.nombre_python_valido("test_get_pdf_strategy_retorna_instancia"))

    def test_nombres_dado_codigo_con_clases_y_async_cuando_se_extraen_entonces_salen_todas_las_pruebas(self):
        codigo = (
            "def test_a_dado_b_cuando_c_entonces_d(): pass\n"
            "def ayudante(): pass\n"
            "class Prueba:\n"
            "    def test_mala(self): pass\n"
            "    async def test_x_dado_y_cuando_z_entonces_w(self): pass\n"
        )
        self.assertEqual(
            auditoria.pruebas_python(codigo),
            ["test_a_dado_b_cuando_c_entonces_d", "test_mala", "test_x_dado_y_cuando_z_entonces_w"],
        )


class NombreFrontendTest(SimpleTestCase):
    def test_nombre_dado_dado_cuando_entonces_cuando_se_valida_entonces_es_conforme(self):
        self.assertTrue(auditoria.nombre_front_valido("dado un 401 cuando falla entonces reintenta"))

    def test_nombre_dado_orden_alterado_cuando_se_valida_entonces_no_es_conforme(self):
        self.assertFalse(auditoria.nombre_front_valido("cuando falla dado un 401 entonces reintenta"))

    def test_nombres_dado_it_test_e_each_cuando_se_extraen_entonces_salen_todos(self):
        codigo = (
            "it('dado a cuando b entonces c', () => {});\n"
            'test("muestra el total", () => {});\n'
            "it.each([[1, 2], [3, 4]])(`dado %i cuando suma entonces %i`, () => {});\n"
            "describe('bloque', () => {});\n"
        )
        self.assertEqual(
            auditoria.pruebas_front(codigo),
            ["dado a cuando b entonces c", "muestra el total", "dado %i cuando suma entonces %i"],
        )


class TecnicasDeclaradasTest(SimpleTestCase):
    def test_tecnicas_dado_istqb_con_tecnica_cuando_se_valida_entonces_declara(self):
        self.assertTrue(auditoria.declara_tecnicas('"""\nTécnicas ISTQB aplicadas:\n- EP: válido / inválido.\n"""'))

    def test_tecnicas_dado_nombre_largo_de_la_tecnica_cuando_se_valida_entonces_declara(self):
        self.assertTrue(auditoria.declara_tecnicas("/** Técnicas ISTQB: análisis de valores límite. */"))

    def test_tecnicas_dado_sin_la_palabra_istqb_cuando_se_valida_entonces_no_declara(self):
        self.assertFalse(auditoria.declara_tecnicas('"""Pruebas de EP del lote."""'))

    def test_tecnicas_dado_istqb_sin_ninguna_tecnica_cuando_se_valida_entonces_no_declara(self):
        self.assertFalse(auditoria.declara_tecnicas('"""Pruebas según ISTQB."""'))


class GateDelRepositorioTest(SimpleTestCase):
    def test_gate_dado_el_repositorio_cuando_se_audita_entonces_no_hay_hallazgos(self):
        hallazgos = auditoria.auditar()
        self.assertEqual(hallazgos, [], "\n".join(map(str, hallazgos[:30])))
