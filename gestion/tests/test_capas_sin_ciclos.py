"""
Las capas no se importan en círculo (defecto 58, 14-oct-2026).

`gestion/services/historial_paros.py` importaba el parseo de parámetros desde
`gestion/views/_common.py`. Eso arrastra `gestion/views/__init__.py`, y como un serializer
importa ese servicio, el círculo quedaba cerrado: serializers → services → views → serializers.
Con SQLite el orden de importación lo ocultaba; sobre SQL Server la suite falló al cargar
`gestion.serializers`.

La regla que se protege: **un servicio o un serializer nunca importa de `gestion.views`.**
El parseo de parámetros vive en `gestion/params.py`, que no depende de ninguna capa.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): módulo de servicios / de serializers / de parseo.
- Prueba estática sobre el código fuente (no ejecuta las vistas).
"""

import ast
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
PROHIBIDO = "gestion.views"


def _modulos_importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    modulos: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos.update(alias.name for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module and nodo.level == 0:
            modulos.add(nodo.module)
    return modulos


class CapasSinCiclosTest(SimpleTestCase):
    def test_servicios_dado_el_codigo_cuando_se_revisan_sus_imports_entonces_no_importan_vistas(self):
        for ruta in sorted((BASE / "gestion" / "services").glob("*.py")):
            with self.subTest(modulo=ruta.name):
                culpables = [m for m in _modulos_importados(ruta) if m == PROHIBIDO or m.startswith(PROHIBIDO + ".")]
                self.assertEqual(
                    culpables,
                    [],
                    f"{ruta.name} importa {culpables}: usa gestion/params.py o mueve el helper fuera de views.",
                )

    def test_serializers_dado_el_codigo_cuando_se_revisan_sus_imports_entonces_no_importan_vistas(self):
        for ruta in sorted((BASE / "gestion" / "serializers").glob("*.py")):
            with self.subTest(modulo=ruta.name):
                culpables = [m for m in _modulos_importados(ruta) if m == PROHIBIDO or m.startswith(PROHIBIDO + ".")]
                self.assertEqual(culpables, [], f"{ruta.name} importa {culpables}")

    def test_params_dado_el_modulo_de_parseo_cuando_se_revisa_entonces_no_depende_de_capas(self):
        importados = _modulos_importados(BASE / "gestion" / "params.py")
        propios = [m for m in importados if m.startswith("gestion")]
        self.assertEqual(propios, [], f"gestion/params.py debe ser neutral; importa {propios}")

    def test_common_dado_el_reexport_cuando_se_importa_entonces_sigue_ofreciendo_los_helpers(self):
        from gestion.views._common import parse_date_param, parse_int_param, parse_rango_fechas

        self.assertEqual(parse_int_param("7", "maquina"), 7)
        self.assertIsNone(parse_date_param({}, "fecha_desde"))
        self.assertEqual(parse_rango_fechas({}), (None, None))
