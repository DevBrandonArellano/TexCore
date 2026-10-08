"""
Despacho de un lote con un producto distinto al de su OP, registrado a mano.

El movimiento manual acepta entradas de cualquier producto en un lote (decisión de
producto del 2026-10-07: se permite y el despacho debe verlo). Hasta ahora el despacho
buscaba solo la fila del producto de la OP, así que ese stock no se podía vender, y el
Kardex registraba siempre el producto de la OP.

Reglas que se prueban:
- al escanear el lote se despachan sus filas vendibles: la del producto de la OP y las de
  otros productos que pidan los pedidos seleccionados; cada una con su producto en el
  Kardex y en el detalle del despacho;
- la merma vendible (la que MermaStockService registró como MERMA-<lote>) nunca se
  despacha, aunque esté en otra bodega;
- una fila de un producto que ningún pedido pide se queda en stock;
- la reversión devuelve cada fila a su producto y bodega.

Técnica ISTQB: partición de equivalencia sobre las filas de stock del lote y prueba de
transición (despacho → reversión).
"""
from datetime import UTC, datetime
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from gestion.models import (
    Bodega,
    Cliente,
    CustomUser,
    DetallePedido,
    LoteProduccion,
    OrdenProduccion,
    PedidoVenta,
    Producto,
    Sede,
)
from inventory.models import DetalleHistorialDespacho, HistorialDespacho, MovimientoInventario, StockBodega
from inventory.services.despacho_reversion import DespachoReversionService
from inventory.views import ValidateLoteAPIView

PT_KG = Decimal('480.000')
MANUAL_KG = Decimal('30.000')
MERMA_KG = Decimal('12.500')


class _LoteConProductoManualMixin:
    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Manual', location='Quito')
        self.bodega_pt = Bodega.objects.create(nombre='PT', sede=self.sede)
        self.bodega_merma = Bodega.objects.create(nombre='Merma', sede=self.sede)
        self.bodega_otra = Bodega.objects.create(nombre='Tránsito', sede=self.sede)
        self.usuario = CustomUser.objects.create_user(username='despacho_manual', password='x', sede=self.sede)
        self.usuario.groups.add(Group.objects.get_or_create(name='despacho')[0])
        self.usuario.bodegas_asignadas.add(self.bodega_pt, self.bodega_merma, self.bodega_otra)

        def producto(codigo, tipo):
            return Producto.objects.create(codigo=codigo, descripcion=codigo, tipo=tipo, unidad_medida='kg',
                                           stock_minimo=Decimal('0'), sede=self.sede)

        self.hilo = producto('HILO-OP', 'hilo')
        self.cono = producto('HILO-CONO', 'hilo')
        self.merma = producto('MERMA-1', 'subproducto')
        orden = OrdenProduccion.objects.create(codigo='OP-MAN', sede=self.sede, producto_salida=self.hilo,
                                               peso_neto_requerido=Decimal('500'))
        self.lote = LoteProduccion.objects.create(
            orden_produccion=orden, codigo_lote='OP-MAN-L1', peso_neto_producido=PT_KG, peso_merma=MERMA_KG,
            turno='Matutino', hora_inicio=datetime(2026, 1, 1, 6, tzinfo=UTC),
            hora_final=datetime(2026, 1, 1, 11, tzinfo=UTC))

        self.cliente = Cliente.objects.create(ruc_cedula='1790000000001', nombre_razon_social='Cliente Manual',
                                              direccion_envio='Quito', nivel_precio='normal', sede=self.sede)

    # --- filas de stock del lote -------------------------------------------------
    def _fila(self, bodega, producto, cantidad):
        return StockBodega.objects.create(bodega=bodega, producto=producto, lote=self.lote, cantidad=cantidad)

    def _merma(self, bodega=None):
        """Como MermaStockService: la fila y su movimiento MERMA-<lote>."""
        fila = self._fila(bodega or self.bodega_merma, self.merma, MERMA_KG)
        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION', producto=self.merma, lote=self.lote, bodega_destino=self.bodega_merma,
            cantidad=MERMA_KG, documento_ref=f'MERMA-{self.lote.codigo_lote}', usuario=self.usuario,
            saldo_resultante=MERMA_KG)
        return fila

    def _pedido(self, *detalles):
        pedido = PedidoVenta.objects.create(cliente=self.cliente, guia_remision=f'GR-{PedidoVenta.objects.count()}',
                                            estado='pendiente', sede=self.sede)
        for producto, peso in detalles:
            DetallePedido.objects.create(pedido_venta=pedido, producto=producto, cantidad=1, piezas=1,
                                         peso=peso, precio_unitario=Decimal('12.000'))
        return pedido

    def _despachar(self, *pedidos, **extra):
        client = APIClient()
        client.force_authenticate(user=self.usuario)
        return client.post('/api/inventory/process-despacho/', {
            'pedidos': [p.id for p in pedidos], 'lotes': [self.lote.codigo_lote], **extra,
        }, format='json')

    def _cantidad(self, fila):
        fila.refresh_from_db()
        return fila.cantidad


class DespachoProductoManualTestCase(_LoteConProductoManualMixin, TestCase):
    def test_despacho_dado_lote_con_producto_manual_pedido_cuando_escanea_entonces_vende_ambas_filas(self):
        pt = self._fila(self.bodega_pt, self.hilo, PT_KG)
        manual = self._fila(self.bodega_pt, self.cono, MANUAL_KG)
        pedido = self._pedido((self.hilo, PT_KG), (self.cono, MANUAL_KG))

        resp = self._despachar(pedido)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual((self._cantidad(pt), self._cantidad(manual)), (Decimal('0'), Decimal('0')))
        ventas = {(m.producto_id, m.bodega_origen_id, m.cantidad)
                  for m in MovimientoInventario.objects.filter(tipo_movimiento='VENTA', lote=self.lote)}
        self.assertEqual(ventas, {(self.hilo.id, self.bodega_pt.id, PT_KG),
                                  (self.cono.id, self.bodega_pt.id, MANUAL_KG)})
        detalles = {(d.producto_id, d.peso, d.pedido_id) for d in DetalleHistorialDespacho.objects.all()}
        self.assertEqual(detalles, {(self.hilo.id, PT_KG, pedido.id), (self.cono.id, MANUAL_KG, pedido.id)})
        historial = HistorialDespacho.objects.get()
        self.assertEqual(historial.total_peso, PT_KG + MANUAL_KG)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'despachado')

    def test_despacho_dado_solo_el_producto_manual_en_stock_cuando_escanea_entonces_lo_vende(self):
        manual = self._fila(self.bodega_pt, self.cono, MANUAL_KG)
        pedido = self._pedido((self.cono, MANUAL_KG))

        resp = self._despachar(pedido)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self._cantidad(manual), Decimal('0'))
        venta = MovimientoInventario.objects.get(tipo_movimiento='VENTA', lote=self.lote)
        self.assertEqual(venta.producto, self.cono)

    def test_despacho_dado_producto_manual_que_nadie_pide_cuando_escanea_entonces_queda_en_stock(self):
        pt = self._fila(self.bodega_pt, self.hilo, PT_KG)
        manual = self._fila(self.bodega_pt, self.cono, MANUAL_KG)
        pedido = self._pedido((self.hilo, PT_KG))

        resp = self._despachar(pedido)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self._cantidad(pt), Decimal('0'))
        self.assertEqual(self._cantidad(manual), MANUAL_KG)
        self.assertFalse(MovimientoInventario.objects.filter(tipo_movimiento='VENTA', producto=self.cono).exists())

    def test_despacho_dado_merma_y_producto_manual_cuando_escanea_entonces_la_merma_no_sale(self):
        pt = self._fila(self.bodega_pt, self.hilo, PT_KG)
        manual = self._fila(self.bodega_pt, self.cono, MANUAL_KG)
        merma = self._merma()
        pedido = self._pedido((self.hilo, PT_KG), (self.cono, MANUAL_KG), (self.merma, MERMA_KG))

        resp = self._despachar(pedido, confirmar_incompleto=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual((self._cantidad(pt), self._cantidad(manual)), (Decimal('0'), Decimal('0')))
        self.assertEqual(self._cantidad(merma), MERMA_KG)

    def test_despacho_dado_merma_trasladada_a_otra_bodega_cuando_escanea_entonces_sigue_sin_salir(self):
        self._fila(self.bodega_pt, self.hilo, PT_KG)
        merma = self._merma(bodega=self.bodega_otra)
        pedido = self._pedido((self.hilo, PT_KG), (self.merma, MERMA_KG))

        resp = self._despachar(pedido, confirmar_incompleto=True)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self._cantidad(merma), MERMA_KG)

    def test_despacho_dado_ambas_filas_cubren_el_pedido_cuando_escanea_entonces_no_lo_reporta_incompleto(self):
        self._fila(self.bodega_pt, self.hilo, PT_KG)
        self._fila(self.bodega_otra, self.cono, MANUAL_KG)
        pedido = self._pedido((self.hilo, PT_KG), (self.cono, MANUAL_KG))

        resp = self._despachar(pedido)

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)

    def test_reversion_dado_despacho_con_producto_manual_cuando_revierte_entonces_devuelve_cada_fila(self):
        pt = self._fila(self.bodega_pt, self.hilo, PT_KG)
        manual = self._fila(self.bodega_otra, self.cono, MANUAL_KG)
        pedido = self._pedido((self.hilo, PT_KG), (self.cono, MANUAL_KG))
        self.assertEqual(self._despachar(pedido).status_code, status.HTTP_200_OK)

        DespachoReversionService.revertir_despacho(HistorialDespacho.objects.get(), self.usuario, 'Cliente rechazó')

        self.assertEqual((self._cantidad(pt), self._cantidad(manual)), (PT_KG, MANUAL_KG))


class ValidarLoteProductoManualTestCase(_LoteConProductoManualMixin, TestCase):
    def _validar(self):
        request = APIRequestFactory().post('/api/scanning/validate', {'code': self.lote.codigo_lote}, format='json')
        force_authenticate(request, user=self.usuario)
        return ValidateLoteAPIView.as_view()(request)

    def test_validar_lote_dado_producto_manual_cuando_escanea_entonces_informa_todas_las_filas_vendibles(self):
        self._fila(self.bodega_pt, self.hilo, PT_KG)
        self._fila(self.bodega_otra, self.cono, MANUAL_KG)
        self._merma()

        resp = self._validar()

        self.assertTrue(resp.data['valid'])
        lote = resp.data['lote']
        # Compatibilidad: producto, peso y bodega principales siguen siendo los de la OP.
        self.assertEqual((lote['producto_id'], Decimal(lote['peso']), lote['bodega_id']),
                         (self.hilo.id, PT_KG, self.bodega_pt.id))
        self.assertEqual(Decimal(lote['peso_total']), PT_KG + MANUAL_KG)
        self.assertEqual(
            {(p['producto_id'], Decimal(p['peso']), p['bodega_id']) for p in lote['productos']},
            {(self.hilo.id, PT_KG, self.bodega_pt.id), (self.cono.id, MANUAL_KG, self.bodega_otra.id)},
        )

    def test_validar_lote_dado_solo_producto_manual_cuando_escanea_entonces_es_valido_con_ese_producto(self):
        self._fila(self.bodega_otra, self.cono, MANUAL_KG)

        resp = self._validar()

        self.assertTrue(resp.data['valid'])
        self.assertEqual((resp.data['lote']['producto_id'], Decimal(resp.data['lote']['peso'])),
                         (self.cono.id, MANUAL_KG))

    def test_validar_lote_dado_solo_merma_cuando_escanea_entonces_no_tiene_stock_vendible(self):
        self._merma()

        resp = self._validar()

        self.assertFalse(resp.data['valid'])
