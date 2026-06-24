"""
Tests de TrazabilidadService — reconstrucción del flujo completo de producción.

Verifica: orden de los pasos, merma por paso y acumulada, porcentaje de merma,
y encadenamiento a la siguiente área vía TransferenciaInterarea.

Técnicas ISTQB: EP (con/sin transformaciones), BVA (merma 0%), integración de cadena.
"""
from decimal import Decimal
from datetime import datetime

from django.test import TestCase

from gestion.models import TransformacionProducto, TransferenciaInterarea
from gestion.tests.factories import (
    OrdenProduccionFactory, MaquinaFactory, ProductoFactory,
    CustomUserFactory, BodegaFactory,
)


def _crear_transf(orden, secuencia, entrada, salida, peso_e, peso_s, maquina):
    return TransformacionProducto.objects.create(
        orden_produccion=orden,
        numero_secuencia=secuencia,
        producto_entrada=entrada,
        producto_salida=salida,
        maquina=maquina,
        peso_entrada=Decimal(peso_e),
        peso_salida=Decimal(peso_s),
        fecha_inicio=datetime(2026, 1, 1, 8, 0),
        fecha_fin=datetime(2026, 1, 1, 12, 0),
    )


class TrazabilidadServiceTest(TestCase):
    def setUp(self):
        self.orden = OrdenProduccionFactory()
        self.maquina = MaquinaFactory(area=self.orden.area)
        self.p0 = self.orden.producto_entrada
        self.p1 = ProductoFactory(codigo='LANA-REC')
        self.p2 = ProductoFactory(codigo='LANA-TOPS')

    def test_trazabilidad_dado_transformaciones_cuando_construir_entonces_pasos_en_orden(self):
        from gestion.services.trazabilidad import TrazabilidadService
        _crear_transf(self.orden, 1, self.p0, self.p1, '100.000', '95.000', self.maquina)
        _crear_transf(self.orden, 2, self.p1, self.p2, '95.000', '90.000', self.maquina)

        traza = TrazabilidadService.construir(self.orden)

        self.assertEqual(len(traza['pasos']), 2)
        self.assertEqual(traza['pasos'][0]['numero_secuencia'], 1)
        self.assertEqual(traza['pasos'][1]['numero_secuencia'], 2)
        self.assertEqual(traza['pasos'][0]['producto_salida']['codigo'], 'LANA-REC')

    def test_trazabilidad_dado_varias_transf_cuando_construir_entonces_merma_total_es_suma(self):
        from gestion.services.trazabilidad import TrazabilidadService
        _crear_transf(self.orden, 1, self.p0, self.p1, '100.000', '95.000', self.maquina)
        _crear_transf(self.orden, 2, self.p1, self.p2, '95.000', '90.000', self.maquina)

        traza = TrazabilidadService.construir(self.orden)

        # 5 + 5 = 10 kg de merma total
        self.assertEqual(traza['merma_total'], Decimal('10.000'))
        self.assertEqual(traza['peso_inicial'], Decimal('100.000'))
        self.assertEqual(traza['peso_final'], Decimal('90.000'))
        # 10 / 100 * 100 = 10%
        self.assertEqual(traza['merma_porcentaje'], Decimal('10.00'))

    def test_trazabilidad_dado_op_sin_transformaciones_cuando_construir_entonces_pasos_vacio(self):
        from gestion.services.trazabilidad import TrazabilidadService
        traza = TrazabilidadService.construir(self.orden)
        self.assertEqual(traza['pasos'], [])
        self.assertEqual(traza['merma_total'], Decimal('0.000'))
        self.assertEqual(traza['merma_porcentaje'], Decimal('0.00'))

    def test_trazabilidad_dado_transformacion_rechazada_cuando_construir_entonces_no_cuenta_merma(self):
        # Una transformación rechazada es un intento fallido: no debe sumar a la
        # merma ni alterar el peso final del flujo válido.
        from gestion.services.trazabilidad import TrazabilidadService
        _crear_transf(self.orden, 1, self.p0, self.p1, '100.000', '95.000', self.maquina)
        rechazada = _crear_transf(self.orden, 2, self.p1, self.p2, '95.000', '0.000', self.maquina)
        rechazada.estado = 'rechazada'
        rechazada.save()

        traza = TrazabilidadService.construir(self.orden)

        # Solo la transformación completada cuenta
        self.assertEqual(len(traza['pasos']), 1)
        self.assertEqual(traza['merma_total'], Decimal('5.000'))
        self.assertEqual(traza['peso_final'], Decimal('95.000'))

    def test_trazabilidad_dado_ciclo_de_transferencias_cuando_construir_entonces_termina(self):
        # Aun con una referencia circular en TransferenciaInterarea, la
        # construcción debe terminar (detección de ciclos / profundidad acotada).
        from gestion.services.trazabilidad import TrazabilidadService
        _crear_transf(self.orden, 1, self.p0, self.p1, '100.000', '95.000', self.maquina)
        orden_b = OrdenProduccionFactory()
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden, orden_area_destino=orden_b,
            bodega_origen=BodegaFactory(), bodega_destino=BodegaFactory(),
            cantidad_transferida=Decimal('95.000'), usuario_responsable=CustomUserFactory(),
        )
        TransferenciaInterarea.objects.create(
            orden_area_origen=orden_b, orden_area_destino=self.orden,
            bodega_origen=BodegaFactory(), bodega_destino=BodegaFactory(),
            cantidad_transferida=Decimal('95.000'), usuario_responsable=CustomUserFactory(),
        )
        # No debe colgarse ni desbordar la pila
        traza = TrazabilidadService.construir(self.orden)
        self.assertIsNotNone(traza['siguiente'])
        # El ciclo se corta: el nieto no vuelve a la orden raíz
        self.assertIsNone(traza['siguiente']['siguiente'])

    def test_trazabilidad_dado_transferencia_a_otra_area_cuando_construir_entonces_incluye_siguiente(self):
        from gestion.services.trazabilidad import TrazabilidadService
        _crear_transf(self.orden, 1, self.p0, self.p1, '100.000', '90.000', self.maquina)
        orden_destino = OrdenProduccionFactory()
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden,
            orden_area_destino=orden_destino,
            bodega_origen=BodegaFactory(),
            bodega_destino=BodegaFactory(),
            cantidad_transferida=Decimal('90.000'),
            usuario_responsable=CustomUserFactory(),
        )

        traza = TrazabilidadService.construir(self.orden)

        self.assertIsNotNone(traza['siguiente'])
        self.assertEqual(traza['siguiente']['orden_codigo'], orden_destino.codigo)
