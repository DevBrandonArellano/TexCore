"""
Recepción de materia prima F0-001 como única vía de compra (decisión del
1-oct-2026) y su vínculo con el movimiento COMPRA.

- `materia-prima/` solo lista y recibe (`registrar-entrada`): el alta, la
  edición y el borrado genéricos esquivaban MateriaPrimaService (stock +
  movimiento COMPRA). Lectura acotada por sede y por bodegas operables.
- La recepción valida bodega (operable), producto y proveedor (globales o de
  la sede de la bodega).
- El movimiento COMPRA queda enlazado a su lote de MP: editarlo ajusta el lote
  sin bajar de lo consumido; borrarlo exige que el lote no tenga consumos.
  (El enlace de compras previas lo hacía una migración de datos, retirada al
  unificar las migraciones el 1-oct-2026.)

Técnicas ISTQB: partición de equivalencia por rol y por sede, valores límite
(cantidad nueva igual / menor a lo consumido) y transición de estados del lote.
"""
from datetime import date
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import MateriaPrimaLote
from gestion.services.materia_prima_service import MateriaPrimaService
from gestion.tests.factories import (
    BodegaFactory,
    CustomUserFactory,
    ProductoFactory,
    ProveedorFactory,
    SedeFactory,
)
from inventory.models import MovimientoInventario, StockBodega

URL_LISTA = '/api/materia-prima/'
URL_RECEPCION = '/api/materia-prima/registrar-entrada/'


def _campos_con_error(resp):
    return resp.data.get('error', {}).get('fields', resp.data)


def _filas(resp):
    return resp.data['results'] if isinstance(resp.data, dict) else resp.data


class _RecepcionMixin:

    def setUp(self):
        self.client = APIClient()
        self.sede_a = SedeFactory()
        self.sede_b = SedeFactory()
        self.bodega_a = BodegaFactory(sede=self.sede_a)
        self.bodega_a2 = BodegaFactory(sede=self.sede_a)
        self.bodega_b = BodegaFactory(sede=self.sede_b)
        self.proveedor_a = ProveedorFactory(sede=self.sede_a)
        self.proveedor_b = ProveedorFactory(sede=self.sede_b)
        self.proveedor_global = ProveedorFactory(sede=None)
        self.producto_a = ProductoFactory(sede=self.sede_a, tipo='materia_prima')
        self.producto_b = ProductoFactory(sede=self.sede_b, tipo='materia_prima')
        self.bodeguero = CustomUserFactory(sede=self.sede_a, groups=['bodeguero'])
        self.bodeguero.bodegas_asignadas.add(self.bodega_a)

    def _payload(self, **extra):
        return {'proveedor': self.proveedor_a.id, 'producto': self.producto_a.id,
                'lote_proveedor': 'LP-001', 'cantidad_kg': '100.000', 'costo_unitario': '2.500',
                'bodega_recepcion': self.bodega_a.id, 'fecha_recepcion': '2026-09-30', **extra}

    def _recibir(self, bodega, lote='LP-SVC', proveedor=None, cantidad='100.000'):
        return MateriaPrimaService.registrar_entrada(
            proveedor=proveedor or self.proveedor_a, producto=self.producto_a, lote_proveedor=lote,
            cantidad_kg=Decimal(cantidad), costo_unitario=Decimal('2.000'), bodega_recepcion=bodega,
            fecha_recepcion=date(2026, 9, 30), usuario=self.bodeguero,
        )


class RecepcionMateriaPrimaAlcanceTestCase(_RecepcionMixin, TestCase):

    def test_recepcion_dado_bodega_no_asignada_cuando_post_entonces_400_sin_stock(self):
        self.client.force_authenticate(user=self.bodeguero)
        resp = self.client.post(URL_RECEPCION, self._payload(bodega_recepcion=self.bodega_a2.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('bodega_recepcion', _campos_con_error(resp))
        self.assertFalse(StockBodega.objects.filter(bodega=self.bodega_a2).exists())

    def test_recepcion_dado_admin_sede_y_bodega_de_otra_sede_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede_a, groups=['admin_sede']))
        resp = self.client.post(URL_RECEPCION, self._payload(bodega_recepcion=self.bodega_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(MateriaPrimaLote.objects.exists())

    def test_recepcion_dado_producto_de_otra_sede_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.bodeguero)
        resp = self.client.post(URL_RECEPCION, self._payload(producto=self.producto_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('producto', _campos_con_error(resp))

    def test_recepcion_dado_proveedor_de_otra_sede_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.bodeguero)
        resp = self.client.post(URL_RECEPCION, self._payload(proveedor=self.proveedor_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('proveedor', _campos_con_error(resp))

    def test_recepcion_dado_proveedor_global_cuando_post_entonces_201_y_enlaza_movimiento(self):
        self.client.force_authenticate(user=self.bodeguero)
        resp = self.client.post(URL_RECEPCION, self._payload(
            proveedor=self.proveedor_global.id, pais='Perú', calidad='Primera'), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        mp = MateriaPrimaLote.objects.get(pk=resp.data['id'])
        mov = MovimientoInventario.objects.get(materia_prima_lote=mp)
        self.assertEqual((mov.tipo_movimiento, mov.cantidad), ('COMPRA', Decimal('100.000')))
        self.assertEqual((mov.pais, mov.calidad), ('Perú', 'Primera'))

    def test_recepcion_dado_cantidad_cero_cuando_post_entonces_400(self):
        self.client.force_authenticate(user=self.bodeguero)
        resp = self.client.post(URL_RECEPCION, self._payload(cantidad_kg='0.000'), format='json')
        self.assertEqual(resp.status_code, 400)

    def test_recepcion_dado_duplicado_cuando_post_entonces_400_sin_doble_stock(self):
        self.client.force_authenticate(user=self.bodeguero)
        self.assertEqual(self.client.post(URL_RECEPCION, self._payload(), format='json').status_code, 201)
        resp = self.client.post(URL_RECEPCION, self._payload(), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto_a).cantidad,
                         Decimal('100.000'))

    def test_materia_prima_dado_admin_sede_cuando_lista_entonces_solo_su_sede(self):
        propio = self._recibir(self.bodega_a, lote='LP-A')
        ajeno = MateriaPrimaService.registrar_entrada(
            proveedor=self.proveedor_b, producto=self.producto_b, lote_proveedor='LP-B',
            cantidad_kg=Decimal('5'), costo_unitario=Decimal('1'), bodega_recepcion=self.bodega_b,
            fecha_recepcion=date(2026, 9, 30), usuario=self.bodeguero)
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede_a, groups=['admin_sede']))
        ids = {f['id'] for f in _filas(self.client.get(URL_LISTA))}
        self.assertIn(propio.id, ids)
        self.assertNotIn(ajeno.id, ids)

    def test_materia_prima_dado_page_size_cuando_lista_entonces_respeta_el_tamano_de_bloque(self):
        for i in range(3):
            self._recibir(self.bodega_a, lote=f'LP-PAG-{i}')
        self.client.force_authenticate(user=self.bodeguero)
        resp = self.client.get(URL_LISTA, {'page_size': 2, 'page': 1})
        self.assertEqual((resp.data['count'], len(resp.data['results'])), (3, 2))

    def test_materia_prima_dado_admin_cuando_crea_edita_o_borra_por_via_generica_entonces_rechazado(self):
        mp = self._recibir(self.bodega_a)
        self.client.force_authenticate(user=CustomUserFactory(groups=['admin_sistemas']))
        self.assertEqual(self.client.post(URL_LISTA, self._payload(lote_proveedor='LP-GEN'),
                                          format='json').status_code, 405)
        url = f'{URL_LISTA}{mp.id}/'
        self.assertEqual(self.client.patch(url, {'cantidad_kg': '1'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        mp.refresh_from_db()
        self.assertEqual(mp.cantidad_kg, Decimal('100.000'))


class CompraVinculadaALoteMPTestCase(_RecepcionMixin, TestCase):

    def setUp(self):
        super().setUp()
        self.mp = self._recibir(self.bodega_a)
        self.mov = MovimientoInventario.objects.get(materia_prima_lote=self.mp)
        self.client.force_authenticate(user=self.bodeguero)
        self.url = f'/api/inventory/movimientos/{self.mov.id}/'

    def _consumir(self, kg):
        MateriaPrimaLote.objects.filter(pk=self.mp.pk).update(cantidad_consumida=Decimal(kg))

    def test_compra_dado_nueva_cantidad_mayor_a_lo_consumido_cuando_edita_entonces_ajusta_el_lote(self):
        self._consumir('30')
        resp = self.client.patch(self.url, {'cantidad': '80.000', 'razon_cambio': 'Corrección de pesaje'},
                                 format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.cantidad_kg, Decimal('80.000'))
        self.assertFalse(self.mp.completamente_consumida)

    def test_compra_dado_nueva_cantidad_igual_a_lo_consumido_cuando_edita_entonces_lote_agotado(self):
        self._consumir('30')
        resp = self.client.patch(self.url, {'cantidad': '30.000', 'razon_cambio': 'Corrección de pesaje'},
                                 format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.mp.refresh_from_db()
        self.assertTrue(self.mp.completamente_consumida)

    def test_compra_dado_nueva_cantidad_menor_a_lo_consumido_cuando_edita_entonces_400_sin_cambios(self):
        self._consumir('30')
        resp = self.client.patch(self.url, {'cantidad': '29.000', 'razon_cambio': 'Corrección de pesaje'},
                                 format='json')
        self.assertEqual(resp.status_code, 400)
        self.mp.refresh_from_db()
        self.mov.refresh_from_db()
        self.assertEqual((self.mp.cantidad_kg, self.mov.cantidad), (Decimal('100.000'), Decimal('100.000')))

    def test_compra_dado_lote_con_consumos_cuando_borra_entonces_400_y_se_conserva(self):
        self._consumir('1')
        resp = self.client.delete(self.url, {'justificacion': 'Registro duplicado'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(MateriaPrimaLote.objects.filter(pk=self.mp.pk).exists())
        self.assertTrue(MovimientoInventario.objects.filter(pk=self.mov.pk).exists())

    def test_compra_dado_lote_sin_consumos_cuando_borra_entonces_elimina_lote_y_revierte_stock(self):
        resp = self.client.delete(self.url, {'justificacion': 'Registro duplicado'}, format='json')
        self.assertEqual(resp.status_code, 204, resp.data)
        self.assertFalse(MateriaPrimaLote.objects.filter(pk=self.mp.pk).exists())
        self.assertEqual(StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto_a).cantidad,
                         Decimal('0'))

    def test_compra_dado_bodega_no_asignada_cuando_edita_entonces_400(self):
        otro = CustomUserFactory(sede=self.sede_a, groups=['bodeguero'])
        otro.bodegas_asignadas.add(self.bodega_a2)
        self.client.force_authenticate(user=otro)
        resp = self.client.patch(self.url, {'cantidad': '90.000', 'razon_cambio': 'Corrección de pesaje'},
                                 format='json')
        self.assertEqual(resp.status_code, 400)
        self.mov.refresh_from_db()
        self.assertEqual(self.mov.cantidad, Decimal('100.000'))
