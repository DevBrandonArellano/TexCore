"""
Fase 1.5b del barrido de higiene (2026-09-01): generate_next_lote_codigo()
(gestion/models/produccion.py) lee lotes.count() sin lock — dos registros
concurrentes del mismo OP podrían calcular el mismo código de lote
(mitigado solo por unique_together, que falla con IntegrityError en vez de
prevenir la condición de carrera). registrar_lote() ahora adquiere
select_for_update() sobre la orden antes de generar el código.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from gestion.models import OrdenProduccion
from gestion.services.registro_lote import RegistroLoteService
from gestion.tests.factories import CustomUserFactory, OrdenProduccionFactory, StockBodegaFactory


class RegistroLoteLockTestCase(TestCase):
    def setUp(self):
        self.orden = OrdenProduccionFactory()
        self.user = CustomUserFactory(sede=self.orden.sede)
        StockBodegaFactory(
            bodega=self.orden.bodega_entrada, producto=self.orden.producto_entrada,
            cantidad=Decimal('1000.00'), lote=None,
        )

    def test_registrar_lote_dado_orden_cuando_registra_entonces_bloquea_orden_con_select_for_update(self):
        lote_data = {
            'peso_neto_producido': '10.00',
            'peso_merma': '0.00',
            'tipo_merma': 'maquina',
            'turno': 'Dia',
            'hora_inicio': '2026-09-01T08:00:00Z',
            'hora_final': '2026-09-01T10:00:00Z',
        }
        with patch.object(
            OrdenProduccion.objects, 'select_for_update',
            wraps=OrdenProduccion.objects.select_for_update,
        ) as mock_lock:
            RegistroLoteService.registrar_lote(self.orden, lote_data, self.user)

        mock_lock.assert_called_once()
