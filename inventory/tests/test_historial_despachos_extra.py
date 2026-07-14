"""
Pruebas complementarias de HistorialDespachoViewSet.get_queryset — filtros
por fecha_desde/fecha_hasta que test_historial_despachos.py no ejercita.
"""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestion.tests.factories import CustomUserFactory
from inventory.models import HistorialDespacho


class HistorialDespachoFiltrosFechaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.user)

        self.reciente = HistorialDespacho.objects.create(
            usuario=self.user, total_bultos=1, total_peso=Decimal('10.00'),
        )
        self.viejo = HistorialDespacho.objects.create(
            usuario=self.user, total_bultos=2, total_peso=Decimal('20.00'),
        )
        hace_30_dias = timezone.now() - timedelta(days=30)
        HistorialDespacho.objects.filter(id=self.viejo.id).update(fecha_despacho=hace_30_dias)

    def _ids(self, resp):
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        return {r['id'] for r in results}

    def test_list_dado_fecha_desde_cuando_get_entonces_excluye_anteriores(self):
        hoy = timezone.now().date().isoformat()
        resp = self.client.get('/api/inventory/historial-despachos/', {'fecha_desde': hoy})
        self.assertEqual(resp.status_code, 200)
        ids = self._ids(resp)
        self.assertIn(self.reciente.id, ids)
        self.assertNotIn(self.viejo.id, ids)

    def test_list_dado_fecha_hasta_cuando_get_entonces_excluye_posteriores(self):
        hace_20_dias = (timezone.now() - timedelta(days=20)).date().isoformat()
        resp = self.client.get('/api/inventory/historial-despachos/', {'fecha_hasta': hace_20_dias})
        self.assertEqual(resp.status_code, 200)
        ids = self._ids(resp)
        self.assertIn(self.viejo.id, ids)
        self.assertNotIn(self.reciente.id, ids)
