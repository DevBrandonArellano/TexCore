from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.test import SimpleTestCase

from inventory.services.executive_kpi_service import (
    ExecutiveKPIService,
    MRPKPIs,
    StockKPIs,
    CarteraKPIs
)

class ExecutiveKPIServiceTest(SimpleTestCase):

    @patch('inventory.services.executive_kpi_service.OrdenCompraSugerida.objects.all')
    @patch('inventory.services.executive_kpi_service.OrdenCompraSugerida.objects.filter')
    def test_mrp_kpis(self, mock_filter, mock_all):
        mock_qs = MagicMock()
        mock_qs.values.return_value.annotate.return_value = [
            {'estado': 'PENDIENTE', 'total': 3},
            {'estado': 'APROBADA', 'total': 2},
        ]
        mock_all.return_value = mock_qs

        mock_filter_qs = MagicMock()
        mock_filter_qs.values.return_value.distinct.return_value.count.return_value = 1
        mock_filter.return_value = mock_filter_qs

        service = ExecutiveKPIService()
        mrp = service._mrp_kpis()

        self.assertEqual(mrp.ocs_pendientes, 3)
        self.assertEqual(mrp.ocs_aprobadas, 2)
        self.assertEqual(mrp.ocs_rechazadas, 0)
        self.assertEqual(mrp.productos_en_deficit, 1)

    @patch('inventory.services.executive_kpi_service.StockBodega.objects.filter')
    def test_stock_kpis(self, mock_filter):
        mock_qs = MagicMock()
        mock_qs.values.return_value.distinct.return_value.count.return_value = 5
        mock_filter.return_value = mock_qs

        service = ExecutiveKPIService()
        stock = service._stock_kpis()

        self.assertEqual(stock.productos_bajo_minimo, 5)

    @patch('inventory.services.executive_kpi_service.Cliente.objects.filter')
    @patch('inventory.services.executive_kpi_service.PedidoVenta.objects.all')
    def test_cartera_kpis(self, mock_pedidos_all, mock_cliente_filter):
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
    def test_cartera_kpis_nulos(self, mock_pedidos_all, mock_cliente_filter):
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

    @patch('inventory.services.executive_kpi_service.OrdenCompraSugerida.objects.all')
    @patch('inventory.services.executive_kpi_service.OrdenCompraSugerida.objects.filter')
    @patch('inventory.services.executive_kpi_service.StockBodega.objects.filter')
    @patch('inventory.services.executive_kpi_service.Cliente.objects.filter')
    @patch('inventory.services.executive_kpi_service.PedidoVenta.objects.all')
    def test_filtro_sede_id(self, mock_pedidos_all, mock_cliente_filter, mock_stock_filter, mock_ocs_filter, mock_ocs_all):
        mock_ocs_all.return_value.filter.return_value.values.return_value.annotate.return_value = []
        mock_ocs_filter.return_value.filter.return_value.values.return_value.distinct.return_value.count.return_value = 0
        
        mock_stock_filter.return_value.filter.return_value.values.return_value.distinct.return_value.count.return_value = 0
        
        mock_cliente_filter.return_value.filter.return_value.aggregate.return_value = {'cxc': None, 'vencida': None}
        mock_pedidos_all.return_value.filter.return_value.values.return_value.annotate.return_value = []

        service = ExecutiveKPIService(sede_id=10)
        
        service._mrp_kpis()
        mock_ocs_all.return_value.filter.assert_called_with(sede_id=10)
        mock_ocs_filter.return_value.filter.assert_called_with(sede_id=10)

        service._stock_kpis()
        mock_stock_filter.return_value.filter.assert_called_with(bodega__sede_id=10)

        service._cartera_kpis()
        mock_cliente_filter.return_value.filter.assert_called_with(sede_id=10)
        mock_pedidos_all.return_value.filter.assert_called_with(sede_id=10)
