"""
Pruebas del gate TDD (`scripts/auditar_tdd.py`).

La tesis afirma que el desarrollo se rige por TDD (Beck, 2003). El gate lo hace verificable en
cada merge request: si cambia el código de producción de un componente (backend, frontend o un
microservicio), en el mismo MR cambian también sus pruebas. Un refactor puro o un cambio de
configuración se declara con la línea `Sin-pruebas: <motivo>` en un commit, y el motivo queda
en el log del pipeline.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): archivo de producción / de prueba / fuera del alcance
  (migración, comando de management, tipos); por componente.
- Tabla de decisión (TD): producción cambiada × pruebas del mismo componente × excepción
  declarada → aprueba / rechaza.
- Análisis de valores límite (BVA): `Sin-pruebas:` sin motivo no cuenta como excepción.
"""

import importlib.util
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ruta = Path(settings.BASE_DIR) / "scripts" / "auditar_tdd.py"
_spec = importlib.util.spec_from_file_location("auditar_tdd", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
tdd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tdd)


class ClasificacionDeArchivosTest(SimpleTestCase):
    def test_clasificar_dado_codigo_de_cada_componente_cuando_clasifica_entonces_produccion_de_ese_componente(self):
        casos = {
            "inventory/views/despacho_views.py": "backend",
            "TexCore/settings.py": "backend",
            "frontend/src/lib/reporteAsync.ts": "frontend",
            "frontend/src/components/ui/button.tsx": "frontend",
            "scanning_service/src/routers/validate.py": "scanning_service",
            "printing_service/src/config.py": "printing_service",
            "reporting_excel/src/main.py": "reporting_excel",
        }
        for ruta, componente in casos.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(tdd.clasificar(ruta), ("produccion", componente))

    def test_clasificar_dado_pruebas_de_cada_componente_cuando_clasifica_entonces_prueba_de_ese_componente(self):
        casos = {
            "gestion/tests/test_dia_de_la_planta.py": "backend",
            "gestion/tests_integrados.py": "backend",
            "frontend/src/lib/reporteAsync.test.ts": "frontend",
            "frontend/src/components/X.test.tsx": "frontend",
            "scanning_service/tests/test_django_client.py": "scanning_service",
            "printing_service/tests/unit/test_config_zona_horaria.py": "printing_service",
        }
        for ruta, componente in casos.items():
            with self.subTest(ruta=ruta):
                self.assertEqual(tdd.clasificar(ruta), ("prueba", componente))

    def test_clasificar_dado_archivo_fuera_del_alcance_cuando_clasifica_entonces_none(self):
        for ruta in (
            "gestion/migrations/0011_algo.py",
            "gestion/management/commands/seed_data.py",
            "frontend/src/vite-env.d.ts",
            "docs/arquitectura/ESTANDARES_DESARROLLO.md",
            ".gitlab-ci.yml",
            "nginx/nginx.conf",
            "scripts/auditar_tdd.py",
        ):
            with self.subTest(ruta=ruta):
                self.assertIsNone(tdd.clasificar(ruta))


class EvaluacionTest(SimpleTestCase):
    def test_evaluar_dado_produccion_con_sus_pruebas_cuando_evalua_entonces_aprueba(self):
        faltan, _ = tdd.evaluar(["inventory/views/despacho_views.py", "inventory/tests/test_process_despacho.py"], [])
        self.assertEqual(faltan, [])

    def test_evaluar_dado_produccion_sin_pruebas_cuando_evalua_entonces_rechaza_ese_componente(self):
        faltan, _ = tdd.evaluar(["frontend/src/lib/reporteAsync.ts", "docs/README.md"], [])
        self.assertEqual(faltan, ["frontend"])

    def test_evaluar_dado_pruebas_de_otro_componente_cuando_evalua_entonces_no_alcanzan(self):
        faltan, _ = tdd.evaluar(["scanning_service/src/routers/validate.py", "gestion/tests/test_tasks.py"], [])
        self.assertEqual(faltan, ["scanning_service"])

    def test_evaluar_dado_solo_documentacion_o_migraciones_cuando_evalua_entonces_aprueba(self):
        faltan, _ = tdd.evaluar(["docs/README.md", "gestion/migrations/0011_algo.py"], [])
        self.assertEqual(faltan, [])

    def test_evaluar_dado_excepcion_declarada_cuando_evalua_entonces_aprueba_y_devuelve_el_motivo(self):
        mensajes = ["refactor(despacho): extraer helper\n\nSin-pruebas: refactor sin cambio de comportamiento\n"]
        faltan, motivos = tdd.evaluar(["inventory/views/despacho_views.py"], mensajes)
        self.assertEqual((faltan, motivos), ([], ["refactor sin cambio de comportamiento"]))

    def test_evaluar_dado_excepcion_sin_motivo_cuando_evalua_entonces_no_cuenta(self):
        faltan, motivos = tdd.evaluar(["inventory/views/despacho_views.py"], ["fix: algo\n\nSin-pruebas:   \n"])
        self.assertEqual((faltan, motivos), (["backend"], []))


class PipelineEjecutaElGateTest(SimpleTestCase):
    """El gate corre en el CI con el historial que necesita y bloquea la construcción de imágenes (EP)."""

    def setUp(self):
        import yaml

        self.ci = yaml.safe_load((Path(settings.BASE_DIR) / ".gitlab-ci.yml").read_text(encoding="utf-8"))

    def test_pipeline_dado_job_lint_tdd_cuando_se_lee_entonces_corre_el_gate_con_historial_completo(self):
        job = self.ci["lint:tdd"]
        self.assertEqual(job["stage"], "lint")
        self.assertIn("python scripts/auditar_tdd.py", job["script"])
        self.assertEqual(str(job["variables"]["GIT_DEPTH"]), "0")

    def test_pipeline_dado_build_de_imagenes_cuando_se_lee_entonces_necesita_el_gate_tdd(self):
        self.assertIn("lint:tdd", self.ci["build:imagenes"]["needs"])


class CommitBaseTest(SimpleTestCase):
    """La base viene del argumento o de las variables del CI; solo se acepta un SHA (EP, BVA)."""

    def test_base_dado_sha_valido_o_ninguno_cuando_resuelve_entonces_lo_usa_o_none(self):
        from unittest.mock import patch

        with patch.dict("os.environ", {"CI_MERGE_REQUEST_DIFF_BASE_SHA": "", "CI_COMMIT_BEFORE_SHA": "0" * 40}):
            self.assertEqual(tdd._base("b8a66b2"), "b8a66b2")
            self.assertIsNone(tdd._base(None))
        with patch.dict("os.environ", {"CI_MERGE_REQUEST_DIFF_BASE_SHA": "a" * 40}):
            self.assertEqual(tdd._base(None), "a" * 40)

    def test_base_dado_texto_que_no_es_sha_cuando_resuelve_entonces_se_detiene(self):
        for invalida in ("HEAD;rm -rf /", "abc", "--output=x"):
            with self.subTest(base=invalida), self.assertRaises(SystemExit):
                tdd._base(invalida)
