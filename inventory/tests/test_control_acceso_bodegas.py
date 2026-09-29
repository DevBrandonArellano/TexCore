"""
Visibilidad de bodegas por rol (OWASP A01): admin_sistemas/ejecutivo ven todas
las sedes; admin_sede, las bodegas de su sede; el resto, sus bodegas asignadas.
Técnica ISTQB: partición de equivalencia por rol y por sede (propia / ajena).
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import PedidoVenta
from gestion.tests.factories import (
    BodegaFactory, ClienteFactory, CustomUserFactory, LoteProduccionFactory, OrdenProduccionFactory,
    ProductoFactory, SedeFactory, StockBodegaFactory,
)
from inventory.permissions import bodegas_visibles


class _DosSedesMixin:

    @classmethod
    def setUpTestData(cls):
        cls.sede_a = SedeFactory()
        cls.sede_b = SedeFactory()
        cls.bodega_a = BodegaFactory(sede=cls.sede_a)
        cls.bodega_a2 = BodegaFactory(sede=cls.sede_a)
        cls.bodega_b = BodegaFactory(sede=cls.sede_b)
        cls.producto = ProductoFactory(sede=cls.sede_a)
        cls.stock_a = StockBodegaFactory(bodega=cls.bodega_a, producto=cls.producto)
        cls.stock_b = StockBodegaFactory(bodega=cls.bodega_b, producto=cls.producto)

    def setUp(self):
        self.client = APIClient()

    def _como(self, grupo, bodegas=()):
        user = CustomUserFactory(sede=self.sede_a, groups=[grupo])
        user.bodegas_asignadas.add(*bodegas)
        self.client.force_authenticate(user=user)
        return user

    @staticmethod
    def _ids(resp, campo='id'):
        data = resp.data.get('results', resp.data) if isinstance(resp.data, dict) else resp.data
        return {fila[campo] for fila in data}


class BodegasVisiblesTestCase(_DosSedesMixin, TestCase):

    def test_bodegas_visibles_dado_admin_sistemas_cuando_consulta_entonces_todas(self):
        self.assertIsNone(bodegas_visibles(CustomUserFactory(groups=['admin_sistemas'])))

    def test_bodegas_visibles_dado_admin_sede_cuando_consulta_entonces_solo_su_sede(self):
        ids = set(bodegas_visibles(self._como('admin_sede')).values_list('id', flat=True))
        self.assertEqual(ids, {self.bodega_a.id, self.bodega_a2.id})

    def test_bodegas_visibles_dado_bodeguero_cuando_consulta_entonces_solo_asignadas(self):
        ids = set(bodegas_visibles(self._como('bodeguero', [self.bodega_a])).values_list('id', flat=True))
        self.assertEqual(ids, {self.bodega_a.id})

    def test_listado_bodegas_dado_admin_sede_cuando_lista_entonces_no_ve_otra_sede(self):
        self._como('admin_sede')
        ids = self._ids(self.client.get('/api/bodegas/'))
        self.assertIn(self.bodega_a.id, ids)
        self.assertNotIn(self.bodega_b.id, ids)

    def test_stock_dado_admin_sede_cuando_lista_entonces_no_ve_otra_sede(self):
        self._como('admin_sede')
        ids = self._ids(self.client.get('/api/inventory/stock/'))
        self.assertIn(self.stock_a.id, ids)
        self.assertNotIn(self.stock_b.id, ids)


class KardexAccesoTestCase(_DosSedesMixin, TestCase):

    def _kardex(self, bodega):
        return self.client.get(f'/api/inventory/bodegas/{bodega.id}/kardex/', {'producto_id': self.producto.id})

    def test_kardex_dado_bodega_no_asignada_cuando_get_entonces_404(self):
        self._como('bodeguero', [self.bodega_a])
        self.assertEqual(self._kardex(self.bodega_a2).status_code, 404)

    def test_kardex_dado_admin_sede_y_bodega_de_otra_sede_cuando_get_entonces_404(self):
        self._como('admin_sede')
        self.assertEqual(self._kardex(self.bodega_b).status_code, 404)

    def test_kardex_dado_bodega_asignada_cuando_get_entonces_200(self):
        self._como('bodeguero', [self.bodega_a])
        self.assertEqual(self._kardex(self.bodega_a).status_code, 200)


class MovimientosPorLoteTestCase(_DosSedesMixin, TestCase):

    def test_movimientos_lote_dado_movimiento_sin_usuario_cuando_get_entonces_200_como_sistema(self):
        from inventory.models import MovimientoInventario
        lote = LoteProduccionFactory(orden_produccion=OrdenProduccionFactory(sede=self.sede_a))
        MovimientoInventario.objects.create(tipo_movimiento='PRODUCCION', producto=self.producto,
                                            bodega_destino=self.bodega_a, lote=lote,
                                            cantidad=Decimal('5.000'), usuario=None)
        self._como('bodeguero', [self.bodega_a])
        resp = self.client.get(f'/api/inventory/lotes/{lote.codigo_lote}/movimientos/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['historial'][0]['usuario'], 'Sistema')


class ReporteAccesoTestCase(_DosSedesMixin, TestCase):

    def test_reporte_dado_admin_sede_y_bodega_de_otra_sede_cuando_get_entonces_403(self):
        self._como('admin_sede')
        resp = self.client.get('/api/reporting/stock-actual', {'bodega_id': self.bodega_b.id})
        self.assertEqual(resp.status_code, 403)


class DespachoAccesoTestCase(_DosSedesMixin, TestCase):

    def test_despacho_dado_pedido_de_otra_sede_cuando_post_entonces_404(self):
        self._como('despacho', [self.bodega_a])
        cliente_b = ClienteFactory(sede=self.sede_b)
        pedido_b = PedidoVenta.objects.create(cliente=cliente_b, guia_remision='GR-B', sede=self.sede_b)
        resp = self.client.post('/api/inventory/process-despacho/',
                                {'pedidos': [pedido_b.id], 'lotes': ['X']}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_despacho_dado_id_de_pedido_no_numerico_cuando_post_entonces_400(self):
        self._como('despacho', [self.bodega_a])
        resp = self.client.post('/api/inventory/process-despacho/',
                                {'pedidos': ['abc'], 'lotes': ['X']}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_escaneo_dado_lote_solo_en_bodega_no_asignada_cuando_valida_entonces_sin_stock(self):
        self._como('despacho', [self.bodega_a])
        lote = LoteProduccionFactory(orden_produccion=OrdenProduccionFactory(sede=self.sede_b))
        StockBodegaFactory(bodega=self.bodega_b, producto=self.producto, lote=lote, cantidad=Decimal('50.00'))
        resp = self.client.post('/api/scanning/validate', {'code': lote.codigo_lote}, format='json')
        self.assertFalse(resp.data['valid'])
