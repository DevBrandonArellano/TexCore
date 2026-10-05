"""
Sincronización de RegistroLoteService.registrar_lote con el motor MES y con la reserva MTO
cuando el lote llega sin máquina.

Regresión (detectada al tipar con mypy, 5-oct-2026): OperacionProduccion exige máquina y
operario. Sin máquina, su creación fallaba dentro del mismo try que la reserva MTO y el
avance del plan, y el `except` se los saltaba en silencio: un lote de una OP bajo pedido
quedaba sin reservar para ese pedido.

Técnicas ISTQB:
- Partición de equivalencia (EP): máquina en el payload / solo asignada en la OP / ninguna;
  OP bajo pedido (MTO) / sin pedido.
"""
from decimal import Decimal

from django.test import TestCase

from gestion.models import LoteProduccion, OperacionProduccion, OrdenProduccion
from gestion.services.registro_lote import RegistroLoteService
from gestion.tests.factories import (
    CustomUserFactory,
    DetallePedidoFactory,
    MaquinaFactory,
    OrdenProduccionFactory,
    PedidoVentaFactory,
    StockBodegaFactory,
)

LOTE = {
    'peso_merma': '0.00', 'tipo_merma': 'maquina', 'turno': 'Dia',
    'hora_inicio': '2026-09-01T08:00:00Z', 'hora_final': '2026-09-01T10:00:00Z',
    'peso_neto_producido': '40.00',
}


class RegistroLoteSincronizacionMesTestCase(TestCase):

    def setUp(self):
        self.orden = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        self.user = CustomUserFactory(sede=self.orden.sede)
        StockBodegaFactory(
            bodega=self.orden.bodega_entrada, producto=self.orden.producto_entrada,
            cantidad=Decimal('1000.00'), lote=None,
        )

    def _hacer_mto(self):
        pedido = PedidoVentaFactory(sede=self.orden.sede, estado='pendiente')
        detalle = DetallePedidoFactory(
            pedido_venta=pedido, producto=self.orden.producto_salida, peso=Decimal('100.000'),
            cantidad_fabricada=Decimal('0.000'), estado_fabricacion='pendiente',
        )
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(pedido_venta=pedido, detalle_pedido=detalle)
        self.orden.refresh_from_db()
        return pedido, detalle

    def test_registro_dado_op_mto_sin_maquina_cuando_registra_entonces_reserva_el_lote_para_el_pedido(self):
        pedido, detalle = self._hacer_mto()

        lote = RegistroLoteService.registrar_lote(self.orden, dict(LOTE), self.user)

        lote.refresh_from_db()
        detalle.refresh_from_db()
        self.assertEqual(lote.pedido_venta_reserva, pedido)
        self.assertEqual(detalle.cantidad_fabricada, Decimal('40.000'))

    def test_registro_dado_maquina_solo_asignada_en_la_op_cuando_registra_entonces_la_usa_y_crea_la_operacion_mes(self):
        maquina = MaquinaFactory(area=self.orden.area)
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(maquina_asignada=maquina)
        self.orden.refresh_from_db()

        lote = RegistroLoteService.registrar_lote(self.orden, dict(LOTE), self.user)

        self.assertEqual(lote.maquina, maquina)
        operacion = OperacionProduccion.objects.get(corrida__orden_produccion=self.orden)
        self.assertEqual(operacion.maquina, maquina)
        self.assertEqual(operacion.operario, self.user)

    def test_registro_dado_op_sin_maquina_cuando_registra_entonces_guarda_lote_y_avisa_que_no_hay_operacion_mes(self):
        with self.assertLogs('gestion.services.registro_lote', level='WARNING') as logs:
            lote = RegistroLoteService.registrar_lote(self.orden, dict(LOTE), self.user)

        self.assertTrue(LoteProduccion.objects.filter(pk=lote.pk).exists())
        self.assertFalse(OperacionProduccion.objects.filter(corrida__orden_produccion=self.orden).exists())
        self.assertTrue(any('sin máquina' in m for m in logs.output), logs.output)
