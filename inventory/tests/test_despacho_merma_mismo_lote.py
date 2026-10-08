"""
Un lote con merma vendible tiene DOS filas de stock con el mismo lote: el producto
terminado (bodega de salida de la máquina) y la merma (producto_merma en bodega_merma),
que MermaStockService registra antes que la entrada a PT.

Defecto encontrado con la simulación de operación (2026-10-06): las búsquedas de stock
por lote no fijaban el producto y tomaban la fila de la merma. Al escanear el lote se
despachaba la merma (y el Kardex registraba una VENTA del producto terminado desde la
bodega de merma), el producto terminado quedaba en stock y el pedido, en
'despachado_parcial'. La reserva MTO también comprometía la merma.

Técnica ISTQB: partición de equivalencia sobre el orden en que se crearon las filas de
stock del lote (merma antes / después del producto terminado).
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
from inventory.models import MovimientoInventario, StockBodega
from inventory.services.reserva_service import ReservaService
from inventory.views import ValidateLoteAPIView

PT_KG = Decimal('480.000')
MERMA_KG = Decimal('12.500')


class _LoteConMermaMixin:
    """Lote cuyo stock vive en dos filas: producto terminado y merma vendible."""

    merma_primero = True

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Merma', location='Quito')
        self.bodega_pt = Bodega.objects.create(nombre='PT', sede=self.sede)
        self.bodega_merma = Bodega.objects.create(nombre='Merma', sede=self.sede)
        self.usuario = CustomUser.objects.create_user(username='despacho_merma', password='x', sede=self.sede)
        self.usuario.groups.add(Group.objects.get_or_create(name='despacho')[0])
        self.usuario.bodegas_asignadas.add(self.bodega_pt, self.bodega_merma)

        self.hilo = Producto.objects.create(codigo='HT-1', descripcion='Hilo teñido', tipo='hilo',
                                            unidad_medida='kg', stock_minimo=Decimal('0'), sede=self.sede)
        self.merma = Producto.objects.create(codigo='SUB-1', descripcion='Merma', tipo='subproducto',
                                             unidad_medida='kg', stock_minimo=Decimal('0'), sede=self.sede)
        orden = OrdenProduccion.objects.create(codigo='OP-M1', sede=self.sede, producto_salida=self.hilo,
                                               peso_neto_requerido=Decimal('492.50'))
        self.lote = LoteProduccion.objects.create(
            orden_produccion=orden, codigo_lote='OP-M1-L1', peso_neto_producido=PT_KG, peso_merma=MERMA_KG,
            turno='Matutino', hora_inicio=datetime(2026, 1, 1, 6, tzinfo=UTC),
            hora_final=datetime(2026, 1, 1, 11, tzinfo=UTC))
        filas = [(self.bodega_merma, self.merma, MERMA_KG), (self.bodega_pt, self.hilo, PT_KG)]
        if not self.merma_primero:
            filas.reverse()
        for bodega, producto, cantidad in filas:
            StockBodega.objects.create(bodega=bodega, producto=producto, lote=self.lote, cantidad=cantidad)
        # Como MermaStockService: la merma deja su movimiento MERMA-<lote>, que es lo que
        # el despacho usa para no venderla.
        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION', producto=self.merma, lote=self.lote, bodega_destino=self.bodega_merma,
            cantidad=MERMA_KG, documento_ref=f'MERMA-{self.lote.codigo_lote}', usuario=self.usuario,
            saldo_resultante=MERMA_KG)

        cliente = Cliente.objects.create(ruc_cedula='1790000000001', nombre_razon_social='Cliente Merma',
                                         direccion_envio='Quito', nivel_precio='normal', sede=self.sede)
        self.pedido = PedidoVenta.objects.create(cliente=cliente, guia_remision='GR-M1', estado='pendiente',
                                                 sede=self.sede)
        DetallePedido.objects.create(pedido_venta=self.pedido, producto=self.hilo, cantidad=1, piezas=24,
                                     peso=PT_KG, precio_unitario=Decimal('12.000'))

    def _stock(self, producto):
        return StockBodega.objects.get(lote=self.lote, producto=producto)

    def _despachar(self):
        client = APIClient()
        client.force_authenticate(user=self.usuario)
        return client.post('/api/inventory/process-despacho/', {
            'pedidos': [self.pedido.id], 'lotes': [self.lote.codigo_lote],
        }, format='json')


class DespachoMermaCreadaPrimeroTestCase(_LoteConMermaMixin, TestCase):
    merma_primero = True

    def test_despacho_dado_lote_con_merma_cuando_escanea_el_lote_entonces_despacha_el_producto_terminado(self):
        resp = self._despachar()

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self._stock(self.hilo).cantidad, Decimal('0'))
        self.assertEqual(self._stock(self.merma).cantidad, MERMA_KG)
        venta = MovimientoInventario.objects.get(tipo_movimiento='VENTA', lote=self.lote)
        self.assertEqual((venta.producto, venta.bodega_origen, venta.cantidad), (self.hilo, self.bodega_pt, PT_KG))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, 'despachado')

    def test_validar_lote_dado_lote_con_merma_cuando_escanea_entonces_informa_el_stock_del_producto(self):
        request = APIRequestFactory().post('/api/scanning/validate', {'code': self.lote.codigo_lote}, format='json')
        force_authenticate(request, user=self.usuario)

        resp = ValidateLoteAPIView.as_view()(request)

        self.assertTrue(resp.data['valid'])
        self.assertEqual(Decimal(resp.data['lote']['peso']), PT_KG)
        self.assertEqual(resp.data['lote']['bodega_id'], self.bodega_pt.id)

    def test_reserva_mto_dado_lote_con_merma_cuando_reserva_entonces_solo_compromete_el_producto(self):
        ReservaService.reservar_lote_para_pedido(self.lote, self.pedido)

        self.assertEqual(self._stock(self.hilo).stock_comprometido, PT_KG)
        self.assertEqual(self._stock(self.merma).stock_comprometido, Decimal('0'))

    def test_liberar_reserva_dado_lote_con_merma_reservado_cuando_libera_entonces_merma_intacta(self):
        ReservaService.reservar_lote_para_pedido(self.lote, self.pedido)
        merma = self._stock(self.merma)
        merma.stock_comprometido = Decimal('3.000')    # comprometida por otro motivo
        merma._justificacion_auditoria = 'Reserva de la merma para otro cliente'
        merma.save()
        self.lote.refresh_from_db()

        ReservaService.liberar_reserva_lote(self.lote, justificacion='Pedido anulado')

        self.assertEqual(self._stock(self.hilo).stock_comprometido, Decimal('0'))
        self.assertEqual(self._stock(self.merma).stock_comprometido, Decimal('3.000'))


class DespachoMermaCreadaDespuesTestCase(_LoteConMermaMixin, TestCase):
    merma_primero = False

    def test_despacho_dado_pedido_que_tambien_pide_la_merma_cuando_escanea_el_lote_entonces_no_la_vende(self):
        DetallePedido.objects.create(pedido_venta=self.pedido, producto=self.merma, cantidad=1, piezas=1,
                                     peso=MERMA_KG, precio_unitario=Decimal('2.000'))
        client = APIClient()
        client.force_authenticate(user=self.usuario)

        resp = client.post('/api/inventory/process-despacho/', {
            'pedidos': [self.pedido.id], 'lotes': [self.lote.codigo_lote], 'confirmar_incompleto': True,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self._stock(self.merma).cantidad, MERMA_KG)
        self.assertEqual(resp.data['items_no_despachados'], {'Merma': {
            'requerido': float(MERMA_KG), 'escaneado': 0.0, 'faltante': float(MERMA_KG)}})

    def test_despacho_dado_merma_creada_despues_cuando_escanea_entonces_no_lo_reporta_incompleto(self):
        resp = self._despachar()

        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(self._stock(self.hilo).cantidad, Decimal('0'))
        self.assertEqual(self._stock(self.merma).cantidad, MERMA_KG)
