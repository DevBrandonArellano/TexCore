from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from gestion.tests.factories import ProductoFactory, SedeFactory
from inventory.models import MRPEjecucion, OrdenCompraSugerida
from inventory.services.executive_kpi_service import ExecutiveKPIService


class ExecutiveKPIServiceTest(SimpleTestCase):

    @patch('inventory.services.executive_kpi_service.StockBodega.objects.filter')
    def test_kpi_ejecutivo_dado_stock_bajo_minimo_cuando_calcula_entonces_cuenta_productos(self, mock_filter):
        mock_qs = MagicMock()
        mock_qs.values.return_value.distinct.return_value.count.return_value = 5
        mock_filter.return_value = mock_qs

        service = ExecutiveKPIService()
        stock = service._stock_kpis()

        self.assertEqual(stock.productos_bajo_minimo, 5)

    @patch('inventory.services.executive_kpi_service.Cliente.objects.filter')
    @patch('inventory.services.executive_kpi_service.PedidoVenta.objects.all')
    def test_kpi_ejecutivo_dado_pedidos_y_clientes_cuando_calcula_cartera_entonces_suma_saldos(
            self, mock_pedidos_all, mock_cliente_filter):
        mock_clientes_qs = MagicMock()
        mock_clientes_qs.aggregate.return_value = {
            'cxc': Decimal("5000.00"),
            'vencida': Decimal("1000.00")
        }
        mock_cliente_filter.return_value = mock_clientes_qs

        mock_pedidos_qs = MagicMock()
        mock_pedidos_qs.values.return_value.annotate.return_value = [
            {'estado': 'pendiente', 'total': 8},
            {'estado': 'despachado', 'total': 12},
        ]
        mock_pedidos_all.return_value = mock_pedidos_qs

        service = ExecutiveKPIService()
        cartera = service._cartera_kpis()

        self.assertEqual(cartera.cuentas_por_cobrar, Decimal("5000.00"))
        self.assertEqual(cartera.cartera_vencida, Decimal("1000.00"))
        self.assertEqual(cartera.pedidos_pendientes, 8)
        self.assertEqual(cartera.pedidos_despachados, 12)

    @patch('inventory.services.executive_kpi_service.Cliente.objects.filter')
    @patch('inventory.services.executive_kpi_service.PedidoVenta.objects.all')
    def test_kpi_ejecutivo_dado_sin_datos_cuando_calcula_cartera_entonces_retorna_ceros(
            self, mock_pedidos_all, mock_cliente_filter):
        mock_clientes_qs = MagicMock()
        mock_clientes_qs.aggregate.return_value = {
            'cxc': None,
            'vencida': None
        }
        mock_cliente_filter.return_value = mock_clientes_qs

        mock_pedidos_qs = MagicMock()
        mock_pedidos_qs.values.return_value.annotate.return_value = []
        mock_pedidos_all.return_value = mock_pedidos_qs

        service = ExecutiveKPIService()
        cartera = service._cartera_kpis()

        self.assertEqual(cartera.cuentas_por_cobrar, Decimal("0"))
        self.assertEqual(cartera.cartera_vencida, Decimal("0"))
        self.assertEqual(cartera.pedidos_pendientes, 0)
        self.assertEqual(cartera.pedidos_despachados, 0)

    @patch('inventory.services.executive_kpi_service.StockBodega.objects.filter')
    @patch('inventory.services.executive_kpi_service.Cliente.objects.filter')
    @patch('inventory.services.executive_kpi_service.PedidoVenta.objects.all')
    def test_kpi_ejecutivo_dado_sede_id_cuando_calcula_entonces_filtra_por_sede(
            self,
            mock_pedidos_all,
            mock_cliente_filter,
            mock_stock_filter):
        (mock_stock_filter.return_value.filter.return_value
         .values.return_value.distinct.return_value.count.return_value) = 0

        mock_cliente_filter.return_value.filter.return_value.aggregate.return_value = {'cxc': None, 'vencida': None}
        mock_pedidos_all.return_value.filter.return_value.values.return_value.annotate.return_value = []

        service = ExecutiveKPIService(sede_id=10)

        service._stock_kpis()
        mock_stock_filter.return_value.filter.assert_called_with(bodega__sede_id=10)

        service._cartera_kpis()
        mock_cliente_filter.return_value.filter.assert_called_with(sede_id=10)
        mock_pedidos_all.return_value.filter.assert_called_with(sede_id=10)


class MRPKPIsTestCase(TestCase):
    """KPI del MRP (ADR-012): sugerencias de compra vigentes, productos a producir de la
    última ejecución completada de cada sede y la fecha de esa ejecución."""

    def setUp(self):
        self.sede_a = SedeFactory()
        self.sede_b = SedeFactory()
        self.producto = ProductoFactory(tipo='quimico')

    @staticmethod
    def _ejecucion(sede, minutos, estado=MRPEjecucion.ESTADO_COMPLETADA, productos=0):
        momento = timezone.now() - timedelta(minutes=minutos)
        return MRPEjecucion.objects.create(sede=sede, inicio=momento, fin=momento, estado=estado,
                                           productos_a_producir=productos)

    def _sugerencia(self, ejecucion):
        OrdenCompraSugerida.objects.create(
            ejecucion=ejecucion, producto=ProductoFactory(tipo='quimico'), sede=ejecucion.sede,
            requerido=Decimal('1'), stock_minimo=Decimal('0'), stock_disponible=Decimal('0'),
            cantidad_sugerida=Decimal('1'),
        )

    def test_kpi_mrp_dado_ejecuciones_en_dos_sedes_cuando_calcula_entonces_usa_la_ultima_completada_de_cada_una(self):
        self._ejecucion(self.sede_a, 60, productos=9)  # anterior: no cuenta
        ultima_a = self._ejecucion(self.sede_a, 10, productos=3)
        self._ejecucion(self.sede_a, 1, estado=MRPEjecucion.ESTADO_FALLIDA, productos=99)
        ultima_b = self._ejecucion(self.sede_b, 5, productos=2)
        self._sugerencia(ultima_a)
        self._sugerencia(ultima_a)
        self._sugerencia(ultima_b)

        mrp = ExecutiveKPIService()._mrp_kpis()

        self.assertEqual(mrp.sugerencias_compra, 3)
        self.assertEqual(mrp.productos_a_producir, 5)  # 3 + 2
        self.assertEqual(mrp.ultima_ejecucion, ultima_b.inicio)

    def test_kpi_mrp_dado_sede_id_cuando_calcula_entonces_solo_esa_sede(self):
        ultima_a = self._ejecucion(self.sede_a, 10, productos=3)
        self._sugerencia(ultima_a)
        self._sugerencia(self._ejecucion(self.sede_b, 5, productos=2))

        mrp = ExecutiveKPIService(sede_id=self.sede_a.id)._mrp_kpis()

        self.assertEqual((mrp.sugerencias_compra, mrp.productos_a_producir), (1, 3))
        self.assertEqual(mrp.ultima_ejecucion, ultima_a.inicio)

    def test_kpi_mrp_dado_sin_ejecuciones_cuando_calcula_entonces_ceros_y_sin_fecha(self):
        mrp = ExecutiveKPIService()._mrp_kpis()
        self.assertEqual((mrp.sugerencias_compra, mrp.productos_a_producir, mrp.ultima_ejecucion), (0, 0, None))
