"""
Métricas DORA (Fase 6 del plan de CI/CD) calculadas desde los despliegues del environment
`production` de GitLab y los jobs `rollback:produccion`.

Se prueba el cálculo puro de `scripts/metricas_dora.py` y la traducción de las respuestas de
la API de GitLab; la petición HTTP en sí solo arma esas listas.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): despliegue exitoso / fallido; con y sin rollback.
- Análisis de valor límite (BVA): periodo sin despliegues; un único despliegue.
- Partición de equivalencia (EP) en la API de GitLab: despliegue con `success` / `failed` /
  en curso o cancelado; con el commit en el propio despliegue / sin él; job de rollback
  exitoso / de otro nombre / fuera del periodo.
"""

import importlib.util
from datetime import UTC, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

_ruta = Path(settings.BASE_DIR) / "scripts" / "metricas_dora.py"
_spec = importlib.util.spec_from_file_location("metricas_dora", _ruta)
assert _spec is not None and _spec.loader is not None, f"No se pudo cargar {_ruta}"
dora = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dora)

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _despliegue(dias, exito=True, horas_desde_commit=24.0):
    creado = T0 + timedelta(days=dias)
    return dora.Despliegue(creado=creado, exitoso=exito, fecha_commit=creado - timedelta(hours=horas_desde_commit))


class MetricasDoraTest(SimpleTestCase):
    def test_metricas_dado_periodo_sin_despliegues_cuando_calcula_entonces_todo_en_cero_o_sin_dato(self):
        m = dora.calcular_metricas([], [], periodo_dias=28)
        self.assertEqual(m.despliegues_por_semana, 0)
        self.assertIsNone(m.lead_time_horas)
        self.assertIsNone(m.tasa_fallos)
        self.assertIsNone(m.mttr_horas)

    def test_frecuencia_dado_8_exitosos_en_4_semanas_cuando_calcula_entonces_2_por_semana(self):
        despliegues = [_despliegue(d) for d in range(0, 28, 4)] + [_despliegue(27)]
        m = dora.calcular_metricas(despliegues, [], periodo_dias=28)
        self.assertEqual(m.despliegues_por_semana, 2.0)

    def test_lead_time_dado_varios_despliegues_cuando_calcula_entonces_mediana_desde_el_commit(self):
        despliegues = [_despliegue(1, horas_desde_commit=h) for h in (10, 30, 20)]
        self.assertEqual(dora.calcular_metricas(despliegues, [], periodo_dias=28).lead_time_horas, 20.0)

    def test_tasa_fallos_dado_un_fallo_y_un_rollback_en_4_cuando_calcula_entonces_50_por_ciento(self):
        despliegues = [_despliegue(1), _despliegue(2, exito=False), _despliegue(3), _despliegue(4)]
        rollbacks = [T0 + timedelta(days=3, hours=2)]
        self.assertEqual(dora.calcular_metricas(despliegues, rollbacks, periodo_dias=28).tasa_fallos, 0.5)

    def test_mttr_dado_fallo_recuperado_cuando_calcula_entonces_horas_hasta_el_siguiente_exito(self):
        despliegues = [_despliegue(1), _despliegue(2, exito=False), _despliegue(2.25)]
        self.assertEqual(dora.calcular_metricas(despliegues, [], periodo_dias=28).mttr_horas, 6.0)

    def test_mttr_dado_rollback_cuando_calcula_entonces_el_rollback_cuenta_como_recuperacion(self):
        despliegues = [_despliegue(1), _despliegue(2, exito=False)]
        rollbacks = [T0 + timedelta(days=2, hours=1)]
        self.assertEqual(dora.calcular_metricas(despliegues, rollbacks, periodo_dias=28).mttr_horas, 1.0)

    def test_mttr_dado_fallo_sin_recuperar_cuando_calcula_entonces_no_inventa_dato(self):
        m = dora.calcular_metricas([_despliegue(1, exito=False)], [], periodo_dias=28)
        self.assertEqual(m.tasa_fallos, 1.0)
        self.assertIsNone(m.mttr_horas)


class ApiGitLabTest(SimpleTestCase):
    def _despliegue_api(self, estado, creado="2026-10-02T12:00:00.000Z", commit="2026-10-01T12:00:00.000Z"):
        d = {"id": 7, "status": estado, "created_at": creado, "sha": "abc123"}
        if commit:
            d["deployable"] = {"commit": {"committed_date": commit}}
        return d

    def test_despliegue_dado_success_con_commit_cuando_se_traduce_entonces_exitoso_con_su_fecha(self):
        d = dora.despliegue_de_gitlab(self._despliegue_api("success"), fecha_commit=None)
        self.assertTrue(d.exitoso)
        self.assertEqual(d.creado - d.fecha_commit, timedelta(days=1))

    def test_despliegue_dado_failed_cuando_se_traduce_entonces_no_exitoso(self):
        d = dora.despliegue_de_gitlab(self._despliegue_api("failed"), fecha_commit=None)
        self.assertFalse(d.exitoso)

    def test_despliegue_dado_en_curso_o_cancelado_cuando_se_traduce_entonces_no_cuenta(self):
        for estado in ("running", "created", "blocked", "canceled"):
            with self.subTest(estado=estado):
                self.assertIsNone(dora.despliegue_de_gitlab(self._despliegue_api(estado), fecha_commit=None))

    def test_despliegue_dado_sin_commit_en_la_respuesta_cuando_se_traduce_entonces_usa_el_que_se_le_da(self):
        fecha = datetime(2026, 10, 1, 6, 0, tzinfo=UTC)
        d = dora.despliegue_de_gitlab(self._despliegue_api("success", commit=None), fecha_commit=fecha)
        self.assertEqual(d.fecha_commit, fecha)

    def test_despliegue_dado_sin_ninguna_fecha_de_commit_cuando_se_traduce_entonces_pide_el_commit(self):
        self.assertTrue(dora.necesita_commit(self._despliegue_api("success", commit=None)))
        self.assertFalse(dora.necesita_commit(self._despliegue_api("success")))

    def test_rollbacks_dado_jobs_cuando_se_filtran_entonces_solo_los_exitosos_del_periodo(self):
        desde = datetime(2026, 10, 1, tzinfo=UTC)
        jobs = [
            {"name": "rollback:produccion", "status": "success", "created_at": "2026-10-05T10:00:00.000Z"},
            {"name": "rollback:produccion", "status": "failed", "created_at": "2026-10-06T10:00:00.000Z"},
            {"name": "deploy:produccion", "status": "success", "created_at": "2026-10-07T10:00:00.000Z"},
            {"name": "rollback:produccion", "status": "success", "created_at": "2026-09-01T10:00:00.000Z"},
        ]
        self.assertEqual(dora.rollbacks_de_gitlab(jobs, desde), [datetime(2026, 10, 5, 10, 0, tzinfo=UTC)])
