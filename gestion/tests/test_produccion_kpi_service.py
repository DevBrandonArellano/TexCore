from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date
from django.test import SimpleTestCase, TestCase

from gestion.services.produccion_kpi_service import (
    ProduccionKPIService
)


class ProduccionKPIServiceTest(SimpleTestCase):

    @patch('gestion.services.produccion_kpi_service.OrdenProduccion.objects.all')
    def test_ops_por_estado(self, mock_ops_all):
        mock_qs = MagicMock()
        mock_qs.values.return_value.annotate.return_value = [
            {'estado': 'pendiente', 'total': 10},
            {'estado': 'en_proceso', 'total': 5},
            {'estado': 'finalizada', 'total': 20},
        ]
        mock_ops_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._ops_por_estado()

        self.assertEqual(resultado.pendiente, 10)
        self.assertEqual(resultado.en_proceso, 5)
        self.assertEqual(resultado.finalizada, 20)

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_kg_lotes(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.aggregate.return_value = {'total': Decimal("150.5")}
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._kg_lotes(date(2026, 1, 1), date(2026, 1, 31))

        self.assertEqual(resultado, Decimal("150.5"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_kg_lotes_empty(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.aggregate.return_value = {'total': None}
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._kg_lotes(date(2026, 1, 1), date(2026, 1, 31))

        self.assertEqual(resultado, Decimal("0"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    @patch('gestion.services.produccion_kpi_service.OrdenProduccion.objects.all')
    def test_filtro_sede_id(self, mock_ops_all, mock_lotes_all):
        mock_ops_qs = MagicMock()
        mock_ops_all.return_value = mock_ops_qs

        mock_lotes_qs = MagicMock()
        mock_lotes_all.return_value = mock_lotes_qs

        service = ProduccionKPIService(sede_id=5)

        service._base_ops_qs()
        mock_ops_qs.filter.assert_called_once_with(sede_id=5)

        service._base_lotes_qs()
        mock_lotes_qs.filter.assert_called_once_with(orden_produccion__sede_id=5)


class ProduccionKPIServiceTendenciaTest(TestCase):

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_tendencia_diaria_rango_con_huecos(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {'fecha': date(2026, 4, 11), 'kg': Decimal("50.5")}
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._tendencia_diaria(date(2026, 4, 10), date(2026, 4, 12))

        self.assertEqual(len(resultado), 3)
        self.assertEqual(resultado[0].fecha, "2026-04-10")
        self.assertEqual(resultado[0].kg, Decimal("0"))

        self.assertEqual(resultado[1].fecha, "2026-04-11")
        self.assertEqual(resultado[1].kg, Decimal("50.5"))

        self.assertEqual(resultado[2].fecha, "2026-04-12")
        self.assertEqual(resultado[2].kg, Decimal("0"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_tendencia_diaria_rango_vacio(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = []
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._tendencia_diaria(date(2026, 4, 10), date(2026, 4, 11))

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0].kg, Decimal("0"))
        self.assertEqual(resultado[1].kg, Decimal("0"))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_tendencia_diaria_mismo_dia(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {'fecha': date(2026, 4, 10), 'kg': Decimal("100.0")}
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._tendencia_diaria(date(2026, 4, 10), date(2026, 4, 10))

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].fecha, "2026-04-10")
        self.assertEqual(resultado[0].kg, Decimal("100.0"))


class ProduccionKPIServicePorProductoTest(SimpleTestCase):
    """CU-EJ-08: producción agrupada por producto — drill-down ejecutivo."""

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_produccion_por_producto_dado_lotes_de_varios_productos_cuando_agrupa_entonces_un_item_por_producto(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {
                'orden_produccion__producto_salida_id': 1,
                'orden_produccion__producto_salida__codigo': 'HIL-001',
                'orden_produccion__producto_salida__descripcion': 'Hilo Nylon 40/1',
                'kg_total': Decimal('320.500'),
                'num_lotes': 6,
            },
            {
                'orden_produccion__producto_salida_id': 2,
                'orden_produccion__producto_salida__codigo': 'TEL-007',
                'orden_produccion__producto_salida__descripcion': 'Tela Jersey',
                'kg_total': Decimal('150.000'),
                'num_lotes': 2,
            },
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._produccion_por_producto(date(2026, 8, 1), date(2026, 8, 25))

        self.assertEqual(len(resultado), 2)
        self.assertEqual(resultado[0].producto_id, 1)
        self.assertEqual(resultado[0].producto_codigo, 'HIL-001')
        self.assertEqual(resultado[0].producto_nombre, 'Hilo Nylon 40/1')
        self.assertEqual(resultado[0].kg_total, Decimal('320.500'))
        self.assertEqual(resultado[0].num_lotes, 6)
        self.assertEqual(resultado[1].producto_id, 2)

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_produccion_por_producto_dado_sin_lotes_en_rango_cuando_agrupa_entonces_lista_vacia(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = []
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._produccion_por_producto(date(2026, 8, 1), date(2026, 8, 25))

        self.assertEqual(resultado, [])

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_produccion_por_producto_dado_kg_total_nulo_cuando_agrupa_entonces_decimal_cero(
        self, mock_lotes_all
    ):
        # Borde defensivo: Sum() nunca debería ser None con num_lotes > 0, pero
        # el contrato del dataclass no debe romper si el driver lo devuelve así.
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {
                'orden_produccion__producto_salida_id': 3,
                'orden_produccion__producto_salida__codigo': 'X',
                'orden_produccion__producto_salida__descripcion': None,
                'kg_total': None,
                'num_lotes': 1,
            },
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._produccion_por_producto(date(2026, 8, 1), date(2026, 8, 25))

        self.assertEqual(resultado[0].kg_total, Decimal('0'))
        self.assertEqual(resultado[0].producto_nombre, '')


class ProduccionKPIServiceHistorialProductoTest(SimpleTestCase):
    """CU-EJ-09: historial diario de UN producto — gráfica de drill-down."""

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_historial_producto_dado_rango_con_huecos_cuando_consulta_entonces_rellena_dias_vacios(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = [
            {'fecha': date(2026, 8, 11), 'kg': Decimal('50.5')}
        ]
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        resultado = service._historial_producto(1, date(2026, 8, 10), date(2026, 8, 12))

        self.assertEqual(len(resultado), 3)
        self.assertEqual(resultado[0].fecha, '2026-08-10')
        self.assertEqual(resultado[0].kg, Decimal('0'))
        self.assertEqual(resultado[1].fecha, '2026-08-11')
        self.assertEqual(resultado[1].kg, Decimal('50.5'))
        self.assertEqual(resultado[2].kg, Decimal('0'))

    @patch('gestion.services.produccion_kpi_service.LoteProduccion.objects.all')
    def test_historial_producto_dado_producto_id_cuando_filtra_entonces_usa_ese_producto(
        self, mock_lotes_all
    ):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.values.return_value.annotate.return_value.order_by.return_value = []
        mock_lotes_all.return_value = mock_qs

        service = ProduccionKPIService()
        service._historial_producto(42, date(2026, 8, 10), date(2026, 8, 10))

        _, filtro_kwargs = mock_qs.filter.call_args
        self.assertEqual(filtro_kwargs['orden_produccion__producto_salida_id'], 42)
