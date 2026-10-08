"""
Pruebas de ConfiguracionEmpaqueSede (gestion/models/core.py) y sus dos puntos
de consumo: LoteProduccion.clean() (gestion/models/produccion.py) y
MRPEngine (inventory/services/mrp_engine.py).

TEX-43 (equivalencias de empaque configurables por sede):
- CA-1: la equivalencia de la sede se aplica solo a sus conversiones.
- CA-2: dos sedes con equivalencias distintas no interfieren.
- CA-3: una sede sin configuración propia recibe un aviso; el sistema NO aplica una
  constante (hasta el 7-oct-2026 se usaba 225/15 en silencio).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): sede con configuración / sin configuración / sin sede.
- Valores límite (BVA): 0 y 1 en las equivalencias.
- Caja blanca: rama 'baño' / 'funda' / 'cono' de LoteProduccion.clean(); no
  sobreescribe unidades_empaque si ya viene explícito (> 0).
"""
import importlib
from decimal import Decimal

from django.apps import apps
from django.core.exceptions import ValidationError
from django.test import TestCase

from gestion.models import ConfiguracionEmpaqueSede
from gestion.tests.factories import (
    LoteProduccionFactory,
    OrdenProduccionFactory,
    SedeFactory,
)


class ConfiguracionEmpaqueSedeModelTestCase(TestCase):
    def test_configuracion_empaque_dado_fundas_y_conos_cuando_conos_por_bano_entonces_multiplica(self):
        sede = SedeFactory()
        config = ConfiguracionEmpaqueSede.objects.create(
            sede=sede, fundas_por_bano=10, conos_por_funda=20)
        self.assertEqual(config.conos_por_bano, 200)

    def test_configuracion_empaque_dado_equivalencia_cero_cuando_guarda_entonces_rechaza(self):
        with self.assertRaises(ValidationError):
            ConfiguracionEmpaqueSede.objects.create(sede=SedeFactory(), fundas_por_bano=0, conos_por_funda=15)

    def test_configuracion_empaque_dado_equivalencia_uno_cuando_guarda_entonces_acepta(self):
        config = ConfiguracionEmpaqueSede.objects.create(sede=SedeFactory(), fundas_por_bano=1, conos_por_funda=1)
        self.assertEqual(config.conos_por_bano, 1)

    def test_configuracion_empaque_dado_cambio_sin_justificacion_cuando_guarda_entonces_rechaza(self):
        config = ConfiguracionEmpaqueSede.objects.create(sede=SedeFactory(), fundas_por_bano=15, conos_por_funda=15)
        config.fundas_por_bano = 12
        with self.assertRaises(ValidationError):
            config.save()

    def test_configuracion_empaque_dado_sede_sin_fila_cuando_para_sede_entonces_none(self):
        self.assertIsNone(ConfiguracionEmpaqueSede.para_sede(SedeFactory()))


class LoteProduccionPresentacionEmpaqueTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.orden = OrdenProduccionFactory(sede=self.sede)

    def test_lote_dado_presentacion_bano_sin_configuracion_cuando_guarda_entonces_avisa_sin_usar_constante(self):
        with self.assertRaises(ValidationError) as ctx:
            LoteProduccionFactory(orden_produccion=self.orden, presentacion='baño', unidades_empaque=0)
        self.assertIn('presentacion', ctx.exception.message_dict)
        self.assertIn('no tiene configuradas las equivalencias de empaque',
                      ctx.exception.message_dict['presentacion'][0])

    def test_lote_dado_presentacion_funda_sin_configuracion_cuando_guarda_entonces_avisa(self):
        with self.assertRaises(ValidationError):
            LoteProduccionFactory(orden_produccion=self.orden, presentacion='funda', unidades_empaque=0)

    def test_lote_dado_presentacion_cono_sin_configuracion_cuando_guarda_entonces_siempre_usa_1(self):
        # Caja blanca: la rama 'cono' no consulta ConfiguracionEmpaqueSede.
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='cono', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 1)

    def test_lote_dado_presentacion_bano_con_configuracion_cuando_guarda_entonces_usa_valor_configurado(self):
        ConfiguracionEmpaqueSede.objects.create(
            sede=self.sede, fundas_por_bano=10, conos_por_funda=20)  # 200 conos/baño
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='baño', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 200)

    def test_lote_dado_presentacion_funda_con_configuracion_cuando_guarda_entonces_usa_valor_configurado(self):
        ConfiguracionEmpaqueSede.objects.create(
            sede=self.sede, fundas_por_bano=10, conos_por_funda=20)
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='funda', unidades_empaque=0)
        self.assertEqual(lote.unidades_empaque, 20)

    def test_lote_dado_dos_sedes_con_equivalencias_distintas_cuando_guardan_entonces_cada_una_usa_la_suya(self):
        otra_sede = SedeFactory()
        ConfiguracionEmpaqueSede.objects.create(sede=self.sede, fundas_por_bano=10, conos_por_funda=20)
        ConfiguracionEmpaqueSede.objects.create(sede=otra_sede, fundas_por_bano=12, conos_por_funda=12)
        lote_a = LoteProduccionFactory(orden_produccion=self.orden, presentacion='baño', unidades_empaque=0)
        lote_b = LoteProduccionFactory(orden_produccion=OrdenProduccionFactory(sede=otra_sede),
                                       presentacion='baño', unidades_empaque=0)
        self.assertEqual((lote_a.unidades_empaque, lote_b.unidades_empaque), (200, 144))

    def test_lote_dado_unidades_empaque_explicito_cuando_guarda_entonces_no_consulta_ni_sobreescribe(self):
        # Regla de negocio preexistente: solo se autocompleta si viene vacío/<=0.
        lote = LoteProduccionFactory(
            orden_produccion=self.orden, presentacion='baño', unidades_empaque=999)
        self.assertEqual(lote.unidades_empaque, 999)

    def test_lote_dado_sin_orden_ni_sede_cuando_guarda_bano_entonces_avisa(self):
        # Caja blanca: sin orden ni sede del producto no hay equivalencia que aplicar.
        with self.assertRaises(ValidationError):
            LoteProduccionFactory(orden_produccion=None, producto=None, presentacion='baño', unidades_empaque=0)


class MRPEngineConfiguracionEmpaqueTestCase(TestCase):
    def test_mrp_dado_sede_sin_configuracion_cuando_get_conos_por_bano_entonces_none(self):
        from inventory.services.mrp_engine import MRPEngine
        self.assertIsNone(MRPEngine()._get_conos_por_bano(SedeFactory()))

    def test_mrp_dado_sede_con_configuracion_cuando_get_conos_por_bano_entonces_usa_valor_configurado(self):
        from inventory.services.mrp_engine import MRPEngine
        sede = SedeFactory()
        ConfiguracionEmpaqueSede.objects.create(sede=sede, fundas_por_bano=10, conos_por_funda=10)  # 100
        self.assertEqual(MRPEngine()._get_conos_por_bano(sede), Decimal('100'))

    def test_mrp_dado_sede_sin_configuracion_cuando_procesa_pedidos_entonces_omite_y_la_reporta(self):
        from inventory.services.mrp_engine import MRPEngine
        sede = SedeFactory()
        engine = MRPEngine()
        engine._formula_default = object()  # hay fórmula: el único motivo para omitir es la sede
        reqs = []
        engine._procesar_pedidos_venta(sede, reqs)
        self.assertEqual(reqs, [])
        self.assertEqual(engine.sedes_sin_configuracion_empaque, [sede.nombre])


class RellenoConfiguracionEmpaqueTestCase(TestCase):
    """Caja blanca del RunPython de la migración 0006 (localmente se corre --nomigrations)."""

    def test_relleno_dado_sedes_existentes_cuando_corre_entonces_crea_15_15_sin_pisar_las_configuradas(self):
        migracion = importlib.import_module('gestion.migrations.0006_configuracion_empaque_explicita')
        sin_config = SedeFactory()
        configurada = SedeFactory()
        ConfiguracionEmpaqueSede.objects.create(sede=configurada, fundas_por_bano=10, conos_por_funda=10)

        migracion.crear_configuracion_existente(apps, None)

        nueva = ConfiguracionEmpaqueSede.objects.get(sede=sin_config)
        self.assertEqual((nueva.fundas_por_bano, nueva.conos_por_funda), (15, 15))
        self.assertEqual(ConfiguracionEmpaqueSede.objects.get(sede=configurada).fundas_por_bano, 10)
