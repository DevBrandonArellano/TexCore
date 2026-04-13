from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import date
from django.test import SimpleTestCase

from gestion.services.produccion_kpi_service import (
    ProduccionKPIService,
    OpsEstado,
    TendenciaDia,
    ProduccionKPIs
)

class ProduccionKPIServiceTest(SimpleTestCase):
    
    @patch('gestion.models.OrdenProduccion.objects.all')
    def test_ops_por_estado(self, mock_ops_all):
        # Setup mock
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

    @patch('gestion.models.LoteProduccion.objects.all')
    def test_kg_lotes(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.aggregate.return_value = {'total': Decimal("150.5")}
        mock_lotes_all.return_value = mock_qs
        
        service = ProduccionKPIService()
        resultado = service._kg_lotes(date(2026, 1, 1), date(2026, 1, 31))
        
        self.assertEqual(resultado, Decimal("150.5"))
        
    @patch('gestion.models.LoteProduccion.objects.all')
    def test_kg_lotes_empty(self, mock_lotes_all):
        mock_qs = MagicMock()
        mock_qs.filter.return_value.aggregate.return_value = {'total': None}
        mock_lotes_all.return_value = mock_qs
        
        service = ProduccionKPIService()
        resultado = service._kg_lotes(date(2026, 1, 1), date(2026, 1, 31))
        
        self.assertEqual(resultado, Decimal("0"))
