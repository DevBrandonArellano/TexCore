"""
GET /api/inventory/stock/ paginado y GET /api/inventory/stock/resumen/.

Hallazgo de la prueba de carga del 2026-10-06 (3 años de operación simulada): el listado
sin paginar devolvía 28 799 filas (8 MB) por petición del administrador y los workers se
quedaban sin memoria. El listado pasa a `PaginacionAcotada` (como kárdex y materia prima)
con filtros en servidor; los dashboards que sumaban el universo completo usan el resumen
agregado en la base.

Técnica ISTQB: partición de equivalencia (filtros), valores límite (tamaño de página y su
tope) y pruebas de control de acceso (OWASP A01).
"""
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from gestion.tests.factories import (
    BodegaFactory,
    CustomUserFactory,
    LoteProduccionFactory,
    ProductoFactory,
    SedeFactory,
    StockBodegaFactory,
)

URL = '/api/inventory/stock/'
URL_RESUMEN = '/api/inventory/stock/resumen/'


class _StockMixin:
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()
        self.bodega_a = BodegaFactory(sede=self.sede, nombre='A Producto terminado')
        self.bodega_b = BodegaFactory(sede=self.sede, nombre='B Merma')
        self.bodega_otra = BodegaFactory(sede=self.otra_sede, nombre='Otra sede')
        self.hilo = ProductoFactory(sede=self.sede, codigo='HIL-ROJO', descripcion='Hilo rojo 30/1')
        self.tela = ProductoFactory(sede=self.sede, codigo='TEL-AZUL', descripcion='Tela azul')
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])

    def _como(self, usuario):
        self.client.force_authenticate(user=usuario)


class StockPaginadoTestCase(_StockMixin, TestCase):
    def test_stock_dado_mas_de_una_pagina_cuando_lista_entonces_responde_paginado(self):
        for _ in range(55):
            StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo, lote=LoteProduccionFactory())
        self._como(self.admin)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['count'], 55)
        self.assertEqual(len(resp.data['results']), 50)
        self.assertIsNotNone(resp.data['next'])

    def test_stock_dado_page_size_sobre_el_tope_cuando_lista_entonces_aplica_500(self):
        for _ in range(3):
            StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo, lote=LoteProduccionFactory())
        self._como(self.admin)
        resp = self.client.get(URL, {'page_size': 10_000})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data['results']), 3)

    def test_stock_dado_filtro_bodega_y_producto_cuando_lista_entonces_solo_esas_filas(self):
        buscada = StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo)
        StockBodegaFactory(bodega=self.bodega_b, producto=self.hilo)
        StockBodegaFactory(bodega=self.bodega_a, producto=self.tela)
        self._como(self.admin)
        resp = self.client.get(URL, {'bodega_id': self.bodega_a.id, 'producto_id': self.hilo.id})
        self.assertEqual([f['id'] for f in resp.data['results']], [buscada.id])

    def test_stock_dado_id_no_numerico_cuando_lista_entonces_400(self):
        self._como(self.admin)
        resp = self.client.get(URL, {'bodega_id': 'abc'})
        self.assertEqual(resp.status_code, 400)

    def test_stock_dado_busqueda_por_codigo_de_lote_cuando_lista_entonces_lo_encuentra(self):
        lote = LoteProduccionFactory(codigo_lote='LT-BUSCADO-01')
        buscada = StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo, lote=lote)
        StockBodegaFactory(bodega=self.bodega_a, producto=self.tela, lote=LoteProduccionFactory())
        self._como(self.admin)
        resp = self.client.get(URL, {'search': 'buscado'})
        self.assertEqual([f['id'] for f in resp.data['results']], [buscada.id])

    def test_stock_dado_busqueda_por_producto_cuando_lista_entonces_lo_encuentra(self):
        buscada = StockBodegaFactory(bodega=self.bodega_a, producto=self.tela)
        StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo)
        self._como(self.admin)
        resp = self.client.get(URL, {'search': 'azul'})
        self.assertEqual([f['id'] for f in resp.data['results']], [buscada.id])

    def test_stock_dado_filtro_bodega_de_otra_sede_cuando_bodeguero_lista_entonces_vacio(self):
        StockBodegaFactory(bodega=self.bodega_otra, producto=ProductoFactory(sede=self.otra_sede))
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        bodeguero.bodegas_asignadas.add(self.bodega_a)
        self._como(bodeguero)
        resp = self.client.get(URL, {'bodega_id': self.bodega_otra.id})
        self.assertEqual(resp.data['count'], 0)

    def test_stock_dado_varias_bodegas_cuando_lista_entonces_ordena_por_bodega_y_producto(self):
        s3 = StockBodegaFactory(bodega=self.bodega_b, producto=self.hilo)
        s2 = StockBodegaFactory(bodega=self.bodega_a, producto=self.tela)
        s1 = StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo)
        self._como(self.admin)
        resp = self.client.get(URL)
        self.assertEqual([f['id'] for f in resp.data['results']], [s1.id, s2.id, s3.id])


class StockResumenTestCase(_StockMixin, TestCase):
    def setUp(self):
        super().setUp()
        StockBodegaFactory(bodega=self.bodega_a, producto=self.hilo, cantidad=Decimal('100.500'))
        StockBodegaFactory(bodega=self.bodega_a, producto=self.tela, cantidad=Decimal('50.000'))
        StockBodegaFactory(bodega=self.bodega_b, producto=self.hilo, cantidad=Decimal('10.000'))
        # Sin existencias: no cuenta (igual que el listado).
        StockBodegaFactory(bodega=self.bodega_b, producto=self.tela, cantidad=Decimal('0'))
        StockBodegaFactory(bodega=self.bodega_otra, producto=ProductoFactory(sede=self.otra_sede),
                           cantidad=Decimal('999'))

    def test_resumen_dado_admin_cuando_filtra_sede_entonces_totaliza_por_bodega(self):
        self._como(self.admin)
        resp = self.client.get(URL_RESUMEN, {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Decimal(str(resp.data['total_cantidad'])), Decimal('160.500'))
        self.assertEqual(resp.data['productos'], 2)
        self.assertEqual(resp.data['bodegas'], 2)
        por_bodega = {b['bodega_id']: b for b in resp.data['por_bodega']}
        self.assertEqual(Decimal(str(por_bodega[self.bodega_a.id]['cantidad'])), Decimal('150.500'))
        self.assertEqual(por_bodega[self.bodega_a.id]['filas'], 2)
        self.assertEqual(por_bodega[self.bodega_a.id]['bodega'], self.bodega_a.nombre)
        self.assertEqual(Decimal(str(por_bodega[self.bodega_b.id]['cantidad'])), Decimal('10.000'))

    def test_resumen_dado_bodeguero_cuando_consulta_entonces_solo_sus_bodegas(self):
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        bodeguero.bodegas_asignadas.add(self.bodega_b)
        self._como(bodeguero)
        resp = self.client.get(URL_RESUMEN)
        self.assertEqual([b['bodega_id'] for b in resp.data['por_bodega']], [self.bodega_b.id])
        self.assertEqual(Decimal(str(resp.data['total_cantidad'])), Decimal('10.000'))

    def test_resumen_dado_operario_raso_cuando_consulta_entonces_403(self):
        self._como(CustomUserFactory(sede=self.sede, groups=['operario']))
        self.assertEqual(self.client.get(URL_RESUMEN).status_code, 403)

    def test_resumen_dado_muchas_bodegas_cuando_consulta_entonces_consultas_constantes(self):
        for _ in range(10):
            StockBodegaFactory(bodega=BodegaFactory(sede=self.sede), producto=self.hilo)
        self._como(self.admin)
        self.client.get(URL_RESUMEN)  # calienta la caché de grupos/permisos
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(URL_RESUMEN)
        self.assertEqual(resp.status_code, 200)
        self.assertLessEqual(len(ctx.captured_queries), 8)
