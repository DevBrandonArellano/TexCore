"""Humo de simular_operacion: invariantes de una corrida corta con los servicios reales.

Técnicas ISTQB: prueba de humo + verificación de invariantes (stock = Kardex, sin saldos
negativos, fechas en el período simulado, pedidos despachados completos).
"""
import io
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone

from gestion.models import LoteProduccion, OrdenProduccion, PedidoVenta, Sede
from inventory.models import MovimientoInventario, StockBodega

DESDE, HASTA = date(2026, 3, 5), date(2026, 3, 14)


def _saldo_segun_kardex(movimientos):
    saldo = defaultdict(Decimal)
    for m in movimientos.values('estado_movimiento', 'producto_id', 'lote_id', 'bodega_origen_id',
                                'bodega_destino_id', 'bodega_transicion_id', 'cantidad'):
        destino = m['bodega_transicion_id'] if m['estado_movimiento'] == 'en_transito' else m['bodega_destino_id']
        if m['bodega_origen_id']:
            saldo[(m['bodega_origen_id'], m['producto_id'], m['lote_id'])] -= m['cantidad']
        if destino:
            saldo[(destino, m['producto_id'], m['lote_id'])] += m['cantidad']
    return saldo


class SimularOperacionTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command('simular_operacion', sedes=1, dias=10, hasta=HASTA, toneladas_anuales=150,
                     kg_por_bano=450, semilla=7, stdout=io.StringIO())
        cls.sede = Sede.objects.get(nombre__startswith='Empresa Textil')

    def test_simular_dado_corrida_cuando_termina_entonces_el_stock_de_cada_bodega_es_el_del_kardex(self):
        saldo = _saldo_segun_kardex(MovimientoInventario.objects.filter(producto__sede=self.sede))
        stock = {(s.bodega_id, s.producto_id, s.lote_id): s.cantidad
                 for s in StockBodega.objects.filter(bodega__sede=self.sede)}
        self.assertTrue(stock)
        for clave in set(saldo) | set(stock):
            self.assertEqual(stock.get(clave, Decimal('0')), saldo.get(clave, Decimal('0')), clave)

    def test_simular_dado_corrida_cuando_termina_entonces_ningun_saldo_queda_negativo(self):
        self.assertFalse(StockBodega.objects.filter(cantidad__lt=0).exists())
        self.assertFalse(MovimientoInventario.objects.filter(saldo_resultante__lt=0).exists())

    def test_simular_dado_reloj_simulado_cuando_registra_entonces_las_fechas_caen_en_el_periodo(self):
        fechas = [timezone.localtime(f).date() for f in MovimientoInventario.objects.values_list('fecha', flat=True)]
        self.assertGreaterEqual(min(fechas), DESDE)
        self.assertLessEqual(max(fechas), HASTA + timedelta(days=1))   # el turno nocturno cruza el día
        pedidos = PedidoVenta.objects.filter(sede=self.sede)
        self.assertTrue(pedidos.exists())
        self.assertTrue(all(DESDE <= timezone.localtime(p.fecha_pedido).date() <= HASTA for p in pedidos))

    def test_simular_dado_banos_cuando_produce_entonces_cada_op_tiene_un_lote_y_version_de_formula(self):
        ordenes = OrdenProduccion.objects.filter(sede=self.sede).exclude(codigo__contains='-CONT-')
        self.assertTrue(ordenes.exists())
        self.assertFalse(ordenes.exclude(estado='finalizada').exists())
        self.assertFalse(ordenes.filter(version_formula__isnull=True).exists())
        self.assertEqual(LoteProduccion.objects.filter(orden_produccion__sede=self.sede).count(), ordenes.count())

    def test_simular_dado_cierre_cuando_termina_entonces_cada_maquina_tiene_una_op_continua_con_hilo_en_linea(self):
        continuas = OrdenProduccion.objects.filter(sede=self.sede, codigo__contains='-CONT-')
        self.assertEqual(continuas.count(), 4)
        for orden in continuas:
            self.assertEqual(orden.estado, 'en_proceso')
            self.assertEqual(orden.operario_asignado.username, 'e1_operario')
            stock = StockBodega.objects.get(bodega=orden.bodega_entrada, producto=orden.producto_entrada, lote=None)
            self.assertGreaterEqual(stock.cantidad, Decimal('20000'))

    def test_simular_dado_roles_cuando_crea_la_sede_entonces_hay_un_usuario_por_cada_grupo_rbac(self):
        from gestion.models import CustomUser
        for rol in ('admin_sistemas', 'admin_sede', 'ejecutivo', 'bodeguero', 'jefe_planta', 'jefe_area',
                    'tintorero', 'vendedor', 'despacho', 'empaquetado', 'operario'):
            self.assertTrue(CustomUser.objects.filter(username=f'e1_{rol}', groups__name=rol).exists(), rol)

    def test_simular_dado_despachos_cuando_escanea_lotes_entonces_los_pedidos_quedan_completos(self):
        estados = set(PedidoVenta.objects.filter(sede=self.sede).values_list('estado', flat=True))
        self.assertIn('despachado', estados)
        self.assertNotIn('despachado_parcial', estados)
        ventas = MovimientoInventario.objects.filter(tipo_movimiento='VENTA', producto__sede=self.sede)
        self.assertTrue(ventas.exists())
        self.assertEqual(set(ventas.values_list('bodega_origen__nombre', flat=True)), {'Producto Terminado E1'})

    def test_simular_dado_simulacion_existente_cuando_se_vuelve_a_ejecutar_entonces_command_error(self):
        with self.assertRaises(CommandError):
            call_command('simular_operacion', sedes=1, dias=1, stdout=io.StringIO())
