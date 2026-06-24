"""
Tests de integración del flujo completo de transformaciones (ISTQB: integración).

Reproduce el caso real de la planta textil:
  Área Preparación: Recolectora → Mezcladora → Tops (3 transformaciones, con merma)
  → Transferencia interárea → Área Hilatura (continúa la cadena)

Verifica de extremo a extremo: secuenciación automática, continuidad de códigos,
merma acumulada y trazabilidad que cruza de un área a la siguiente.
"""
from decimal import Decimal

from django.test import TestCase

from gestion.models import TransferenciaInterarea
from gestion.services.transformacion import TransformacionService
from gestion.services.trazabilidad import TrazabilidadService
from gestion.tests.factories import (
    SedeFactory, AreaFactory, ProductoFactory, CustomUserFactory,
    MaquinaFactory, OrdenProduccionFactory, BodegaFactory,
)


class FlujoPreparacionIntegracionTest(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.area_prep = AreaFactory(sede=self.sede, nombre='Preparación')
        self.jefe = CustomUserFactory(sede=self.sede, area=self.area_prep, groups=['jefe_area'])

        # Materia prima inicial de la OP de Preparación
        self.mp_lana = ProductoFactory(codigo='MP-LANA-001', descripcion='Lana cruda')
        self.orden_prep = OrdenProduccionFactory(
            sede=self.sede, area=self.area_prep, producto_entrada=self.mp_lana,
            peso_neto_requerido=Decimal('1000.00'),
        )
        # Máquinas del área de Preparación
        self.recolectora = MaquinaFactory(area=self.area_prep, nombre='Recolectora 1')
        self.mezcladora = MaquinaFactory(area=self.area_prep, nombre='Mezcladora')
        self.tops = MaquinaFactory(area=self.area_prep, nombre='Máquina Tops')

    def _registrar(self, maquina, salida_codigo, peso_e, peso_s):
        salida = ProductoFactory(codigo=salida_codigo, sede=self.sede)
        return TransformacionService.registrar(
            self.orden_prep,
            {
                'maquina': maquina.id,
                'producto_salida': salida.id,
                'peso_entrada': Decimal(peso_e),
                'peso_salida': Decimal(peso_s),
                'fecha_inicio': '2026-01-01T08:00:00Z',
                'fecha_fin': '2026-01-01T12:00:00Z',
            },
            self.jefe,
        )

    def test_flujo_dado_tres_maquinas_cuando_transforma_entonces_cadena_y_merma_correctas(self):
        t1 = self._registrar(self.recolectora, 'LANA-REC', '1000.000', '980.000')
        t2 = self._registrar(self.mezcladora, 'LANA-MEZCLA', '980.000', '960.000')
        t3 = self._registrar(self.tops, 'LANA-TOPS', '960.000', '940.000')

        # Secuenciación automática
        self.assertEqual([t1.numero_secuencia, t2.numero_secuencia, t3.numero_secuencia], [1, 2, 3])
        # Continuidad de códigos: la entrada de cada paso = salida del anterior
        self.assertEqual(t1.producto_entrada, self.mp_lana)
        self.assertEqual(t2.producto_entrada, t1.producto_salida)
        self.assertEqual(t3.producto_entrada, t2.producto_salida)

        traza = TrazabilidadService.construir(self.orden_prep)
        self.assertEqual(len(traza['pasos']), 3)
        # Merma total = 20 + 20 + 20 = 60 kg
        self.assertEqual(traza['merma_total'], Decimal('60.000'))
        self.assertEqual(traza['peso_inicial'], Decimal('1000.000'))
        self.assertEqual(traza['peso_final'], Decimal('940.000'))
        self.assertEqual(traza['merma_porcentaje'], Decimal('6.00'))

    def test_flujo_dado_transferencia_a_hilatura_cuando_trazabilidad_entonces_cruza_areas(self):
        self._registrar(self.recolectora, 'LANA-REC', '1000.000', '980.000')
        self._registrar(self.tops, 'LANA-TOPS', '980.000', '940.000')

        # Transferencia a la siguiente área (Hilatura)
        area_hil = AreaFactory(sede=self.sede, nombre='Hilatura')
        tops_producto = ProductoFactory(codigo='LANA-TOPS-IN')
        orden_hil = OrdenProduccionFactory(
            sede=self.sede, area=area_hil, producto_entrada=tops_producto,
            peso_neto_requerido=Decimal('940.00'),
        )
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_prep,
            orden_area_destino=orden_hil,
            bodega_origen=BodegaFactory(sede=self.sede),
            bodega_destino=BodegaFactory(sede=self.sede),
            cantidad_transferida=Decimal('940.000'),
            usuario_responsable=self.jefe,
        )
        # Hilatura procesa su primera máquina
        maq_hil = MaquinaFactory(area=area_hil, nombre='Continua de Hilar')
        TransformacionService.registrar(
            orden_hil,
            {
                'maquina': maq_hil.id,
                'producto_salida': ProductoFactory(codigo='HILO-001', sede=self.sede).id,
                'peso_entrada': Decimal('940.000'),
                'peso_salida': Decimal('910.000'),
                'fecha_inicio': '2026-01-02T08:00:00Z',
                'fecha_fin': '2026-01-02T12:00:00Z',
            },
            CustomUserFactory(sede=self.sede, area=area_hil, groups=['jefe_area']),
        )

        traza = TrazabilidadService.construir(self.orden_prep)
        # La trazabilidad de Preparación enlaza con Hilatura
        self.assertIsNotNone(traza['siguiente'])
        self.assertEqual(traza['siguiente']['orden_codigo'], orden_hil.codigo)
        self.assertEqual(traza['siguiente']['area'], 'Hilatura')
        self.assertEqual(len(traza['siguiente']['pasos']), 1)
