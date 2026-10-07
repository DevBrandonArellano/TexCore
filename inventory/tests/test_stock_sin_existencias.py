"""
GET /api/inventory/stock/ no lista filas sin existencias.

Hallazgo de la prueba de carga con 3 años de operación simulada (2026-10-06): cada lote
vendido deja su fila de stock en cero. El endpoint no pagina (alimenta dashboards que
agregan por bodega) y devolvía las ~49 700 filas de las 4 sedes, casi todas en cero; con
20 workers el backend se quedaba sin memoria (SIGKILL de gunicorn y 502 en nginx). Una
fila con cantidad 0 y nada comprometido no aporta a ninguna suma ni a ninguna pantalla.

Técnica ISTQB: partición de equivalencia y valores límite sobre cantidad/comprometido.
"""
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import CustomUser
from gestion.tests.factories import BodegaFactory, LoteProduccionFactory, ProductoFactory, SedeFactory
from inventory.models import StockBodega


class StockSinExistenciasTestCase(TestCase):
    def setUp(self):
        sede = SedeFactory()
        bodega = BodegaFactory(sede=sede)
        usuario = CustomUser.objects.create_user(username='ejecutivo_stock', password='x', sede=sede)
        usuario.groups.add(Group.objects.get_or_create(name='ejecutivo')[0])
        self.client = APIClient()
        self.client.force_authenticate(usuario)

        def fila(cantidad, comprometido='0'):
            lote = LoteProduccionFactory()
            return StockBodega.objects.create(bodega=bodega, producto=ProductoFactory(sede=sede), lote=lote,
                                              cantidad=Decimal(cantidad), stock_comprometido=Decimal(comprometido))

        self.vendida = fila('0')
        self.minima = fila('0.001')
        self.con_stock = fila('480')
        self.reservada = fila('120', '120')

    def _ids(self):
        resp = self.client.get('/api/inventory/stock/')
        self.assertEqual(resp.status_code, 200)
        return {f['id'] for f in resp.data}

    def test_stock_dado_lote_vendido_en_cero_cuando_lista_entonces_no_aparece(self):
        self.assertNotIn(self.vendida.id, self._ids())

    def test_stock_dado_filas_con_existencias_cuando_lista_entonces_aparecen_todas(self):
        self.assertEqual(self._ids(), {self.minima.id, self.con_stock.id, self.reservada.id})
