"""
Pruebas de ConfiguracionEmpaqueSede (gestion/models/core.py) y sus dos puntos
de consumo: LoteProduccion.clean() (gestion/models/produccion.py) y
MRPEngine (inventory/services/mrp_engine.py).

Barrido de higiene Fase 5.1 (2026-09-02): las equivalencias de empaque
(1 baño = 15 fundas = 225 conos) eran constantes hardcodeadas sin excepción;
CLAUDE.md exige que sean "configurable reference examples per sede, not
system-wide hardcoded constants".

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): sede con ConfiguracionEmpaqueSede propia
  vs. sede sin ella (usa el valor de referencia 225/15 como default).
- Caja blanca: rama 'baño' / 'funda' / 'cono' de LoteProduccion.clean(); no
  sobreescribe unidades_empaque si ya viene explícito (> 0).
"""
from decimal import Decimal

from django.test import TestCase

from gestion.models import ConfiguracionEmpaqueSede
from gestion.tests.factories import (
    LoteProduccionFactory, OrdenProduccionFactory, SedeFactory,
)


class ConfiguracionEmpaqueSedeModelTestCase(TestCase):
    def test_configuracion_empaque_dado_fundas_y_conos_cuando_conos_por_bano_entonces_multiplica(self):
        sede = SedeFactory()
        config = ConfiguracionEmpaqueSede.objects.create(
            sede=sede, fundas_por_bano=10, conos_por_funda=20)
        self.assertEqual(config.conos_por_bano, 200)


class LoteProduccionPresentacionEmpaqueTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.orden = OrdenProduccionFactory(sede=self.sede)

    def test_lote_dado_presentacion_bano_sin_configuracion_cuando_guarda_entonces_usa_225_default(self):
        # LoteProduccion.save() llama a self.clean() internamente.
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='baño', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 225)

    def test_lote_dado_presentacion_funda_sin_configuracion_cuando_guarda_entonces_usa_15_default(self):
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='funda', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 15)

    def test_lote_dado_presentacion_cono_cuando_guarda_entonces_siempre_usa_1(self):
        # Caja blanca: la rama 'cono' no consulta ConfiguracionEmpaqueSede.
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='cono', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 1)

    def test_lote_dado_presentacion_bano_con_configuracion_personalizada_cuando_guarda_entonces_usa_valor_configurado(self):
        ConfiguracionEmpaqueSede.objects.create(
            sede=self.sede, fundas_por_bano=10, conos_por_funda=20)  # 200 conos/baño
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='baño', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 200)

    def test_lote_dado_presentacion_funda_con_configuracion_personalizada_cuando_guarda_entonces_usa_valor_configurado(self):
        ConfiguracionEmpaqueSede.objects.create(
            sede=self.sede, fundas_por_bano=10, conos_por_funda=20)
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='funda', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 20)

    def test_lote_dado_unidades_empaque_explicito_cuando_guarda_entonces_no_sobreescribe(self):
        # Regla de negocio preexistente: solo se autocompleta si viene vacío/<=0.
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='baño', unidades_empaque=999)
        self.assertEqual(lote.unidades_empaque, 999)

    def test_lote_dado_sin_orden_produccion_cuando_guarda_entonces_usa_default_sin_error(self):
        # Caja blanca: self.orden_produccion es nullable — no debe fallar al
        # intentar resolver la sede si no hay orden asociada.
        lote = LoteProduccionFactory(
            orden_produccion=None, presentacion='baño', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 225)


class MRPEngineConfiguracionEmpaqueTestCase(TestCase):
    def test_mrp_dado_sede_sin_configuracion_cuando_get_conos_por_bano_entonces_usa_225_default(self):
        from inventory.services.mrp_engine import MRPEngine
        sede = SedeFactory()
        engine = MRPEngine()
        self.assertEqual(engine._get_conos_por_bano(sede), Decimal('225'))

    def test_mrp_dado_sede_con_configuracion_personalizada_cuando_get_conos_por_bano_entonces_usa_valor_configurado(self):
        from inventory.services.mrp_engine import MRPEngine
        sede = SedeFactory()
        ConfiguracionEmpaqueSede.objects.create(sede=sede, fundas_por_bano=10, conos_por_funda=10)  # 100
        engine = MRPEngine()
        self.assertEqual(engine._get_conos_por_bano(sede), Decimal('100'))
