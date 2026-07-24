"""
Pruebas de OeeService — OEE = Disponibilidad × Rendimiento × Calidad
(OEE for Operators — Productivity Press).

Supuestos documentados:
- run_time = Σ(hora_final − hora_inicio) de lotes de la máquina/área en el rango.
- downtime = Σ duración de ParoMaquina con planificado=False en el rango.
- Disponibilidad = run_time / (run_time + downtime).
- Rendimiento = min(1, producción_real / producción_teórica), con
  producción_teórica = capacidad_maxima × (run_time_horas / DURACION_TURNO_HORAS=8).
- Calidad = FPY = neto_primera / neto_total.

Técnicas ISTQB: EP (con/sin paros, con/sin producción), BVA (denominador cero).
"""
from datetime import datetime
from decimal import Decimal

from django.test import TestCase

from gestion.services.oee_service import OeeService
from gestion.tests.factories import (
    SedeFactory, AreaFactory, MaquinaFactory, LoteProduccionFactory, ParoMaquinaFactory,
)

DESDE = datetime(2026, 1, 1, 0, 0)
HASTA = datetime(2026, 1, 2, 0, 0)


class OeeServiceMaquinaTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        # capacidad_maxima en kg/turno de 8h
        self.maquina = MaquinaFactory(area=self.area, capacidad_maxima=Decimal('100.00'))

    def test_oee_dado_sin_lotes_ni_paros_cuando_calcula_entonces_todo_cero(self):
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertEqual(resultado['disponibilidad'], 0.0)
        self.assertEqual(resultado['rendimiento'], 0.0)
        self.assertEqual(resultado['calidad'], 0.0)
        self.assertEqual(resultado['oee'], 0.0)

    def test_oee_dado_lote_sin_paros_cuando_calcula_entonces_disponibilidad_100(self):
        # 8h de producción, sin downtime → disponibilidad = 8/(8+0) = 1.0
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('100.000'),
            clasificacion_calidad='primera',
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertAlmostEqual(resultado['disponibilidad'], 1.0, places=4)

    def test_oee_dado_lote_con_paro_no_planificado_cuando_calcula_entonces_disponibilidad_real(self):
        # 8h run_time + 2h downtime no planificado → disp = 8/(8+2) = 0.8
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('100.000'),
            clasificacion_calidad='primera',
        )
        ParoMaquinaFactory(
            maquina=self.maquina,
            inicio=datetime(2026, 1, 1, 16, 0),
            fin=datetime(2026, 1, 1, 18, 0),
            categoria='AVERIA',
            planificado=False,
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertAlmostEqual(resultado['disponibilidad'], 0.8, places=4)

    def test_oee_dado_paro_planificado_cuando_calcula_entonces_no_penaliza_disponibilidad(self):
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('100.000'),
            clasificacion_calidad='primera',
        )
        ParoMaquinaFactory(
            maquina=self.maquina,
            inicio=datetime(2026, 1, 1, 16, 0),
            fin=datetime(2026, 1, 1, 18, 0),
            categoria='MANTENIMIENTO_PLANIFICADO',
            planificado=True,
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertAlmostEqual(resultado['disponibilidad'], 1.0, places=4)

    def test_oee_dado_produccion_real_cuando_calcula_entonces_rendimiento_relativo_a_teorico(self):
        # run_time = 8h, capacidad_maxima=100kg/turno(8h) → teórico = 100 * (8/8) = 100kg
        # producido = 50kg → rendimiento = 0.5
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('50.000'),
            clasificacion_calidad='primera',
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertAlmostEqual(resultado['rendimiento'], 0.5, places=4)

    def test_oee_dado_produccion_supera_teorico_cuando_calcula_entonces_rendimiento_topea_en_1(self):
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('150.000'),
            clasificacion_calidad='primera',
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertEqual(resultado['rendimiento'], 1.0)

    def test_oee_dado_mezcla_de_calidad_cuando_calcula_entonces_fpy_correcto(self):
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 12, 0),
            peso_neto_producido=Decimal('75.000'),
            clasificacion_calidad='primera',
        )
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 12, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('25.000'),
            clasificacion_calidad='segunda',
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertAlmostEqual(resultado['calidad'], 0.75, places=4)

    def test_oee_dado_a_p_q_conocidos_cuando_calcula_entonces_oee_es_el_producto(self):
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 16, 0),
            peso_neto_producido=Decimal('50.000'),
            clasificacion_calidad='primera',
        )
        ParoMaquinaFactory(
            maquina=self.maquina,
            inicio=datetime(2026, 1, 1, 16, 0),
            fin=datetime(2026, 1, 1, 18, 0),
            categoria='AVERIA',
            planificado=False,
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        esperado = resultado['disponibilidad'] * resultado['rendimiento'] * resultado['calidad']
        self.assertAlmostEqual(resultado['oee'], esperado, places=6)

    def test_oee_dado_lote_fuera_del_rango_cuando_calcula_entonces_no_se_incluye(self):
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio=datetime(2025, 12, 1, 8, 0),
            hora_final=datetime(2025, 12, 1, 16, 0),
            peso_neto_producido=Decimal('100.000'),
            clasificacion_calidad='primera',
        )
        resultado = OeeService.calcular_oee_maquina(self.maquina, DESDE, HASTA)
        self.assertEqual(resultado['disponibilidad'], 0.0)


class OeeServiceAreaTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina1 = MaquinaFactory(area=self.area, capacidad_maxima=Decimal('100.00'))
        self.maquina2 = MaquinaFactory(area=self.area, capacidad_maxima=Decimal('100.00'))

    def test_oee_area_dado_dos_maquinas_cuando_calcula_entonces_agrega_ambas(self):
        for maquina in (self.maquina1, self.maquina2):
            LoteProduccionFactory(
                maquina=maquina,
                hora_inicio=datetime(2026, 1, 1, 8, 0),
                hora_final=datetime(2026, 1, 1, 16, 0),
                peso_neto_producido=Decimal('100.000'),
                clasificacion_calidad='primera',
            )
        resultado = OeeService.calcular_oee_area(self.area, DESDE, HASTA)
        self.assertAlmostEqual(resultado['disponibilidad'], 1.0, places=4)
        self.assertAlmostEqual(resultado['downtime_min'], 0.0, places=4)

    def test_oee_area_dado_sin_produccion_cuando_calcula_entonces_cero_sin_dividir_por_cero(self):
        resultado = OeeService.calcular_oee_area(self.area, DESDE, HASTA)
        self.assertEqual(resultado['oee'], 0.0)
