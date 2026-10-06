"""Humo de stress_test_data: invariantes de los datos sembrados que usan el loadtest y las demos.

Técnicas ISTQB: prueba de humo + verificación de invariantes sobre una corrida corta.
"""
import io
import random
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from gestion.models import Bodega, CustomUser, OrdenProduccion, PedidoVenta, Sede
from inventory.models import MovimientoInventario, StockBodega


class StressTestDataTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        random.seed(20261005)
        call_command('stress_test_data', dias=3, movimientos_por_dia=5, stdout=io.StringIO())

    def test_stress_dado_bd_vacia_cuando_siembra_entonces_crea_4_sedes_con_3_bodegas_cada_una(self):
        self.assertEqual(Sede.objects.count(), 4)
        for sede in Sede.objects.all():
            self.assertEqual(Bodega.objects.filter(sede=sede).count(), 3)

    def test_stress_dado_siembra_cuando_termina_entonces_existen_los_usuarios_demo_del_login(self):
        for username in ('user_operario', 'user_bodeguero', 'user_vendedor', 'user_despacho', 'admin'):
            self.assertTrue(CustomUser.objects.filter(username=username).exists(), username)

    def test_stress_dado_simulacion_cuando_mueve_stock_entonces_ningun_saldo_queda_negativo(self):
        self.assertFalse(StockBodega.objects.filter(cantidad__lt=0).exists())
        self.assertFalse(MovimientoInventario.objects.filter(saldo_resultante__lt=0).exists())
        self.assertTrue(MovimientoInventario.objects.exists())

    def test_stress_dado_ops_del_operario_demo_cuando_termina_entonces_tienen_materia_prima_para_el_loadtest(self):
        ops = OrdenProduccion.objects.filter(operario_asignado__username='user_operario', estado='en_proceso')
        self.assertTrue(ops.filter(codigo__startswith='OP-STR-CONT-').exists())
        for op in ops:
            stock = StockBodega.objects.get(bodega=op.bodega_entrada, producto=op.producto_entrada, lote=None)
            self.assertGreaterEqual(stock.cantidad, Decimal('50000.00'), op.codigo)

    def test_stress_dado_ventas_cuando_siembra_entonces_el_vendedor_demo_tiene_pedidos_recientes(self):
        self.assertEqual(PedidoVenta.objects.filter(guia_remision__startswith='GR-STR-').count(), 120)
        self.assertEqual(
            PedidoVenta.objects.filter(guia_remision__startswith='GR-DEMO-',
                                       vendedor_asignado__username='user_vendedor').count(),
            80,
        )
