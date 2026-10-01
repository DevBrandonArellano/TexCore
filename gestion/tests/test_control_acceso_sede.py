"""
Control de acceso por rol y por sede (OWASP A01 — Broken Access Control).

Cubre las vistas que obtenían objetos por id sin acotar sede ni rol: registro
de lote, trazabilidad (QR, materias primas con costos y genealogía MES), KPI
de área, corridas/operaciones/planes MES. Técnicas ISTQB: partición de
equivalencia por rol (permitido / no permitido) y por sede (propia / ajena).
"""
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestion.models import OrdenProduccion, PedidoVenta
from gestion.permissions import filtrar_por_sede
from gestion.tests.factories import (
    AreaFactory, BodegaFactory, ClienteFactory, CustomUserFactory, LoteProduccionFactory, MaquinaFactory,
    OrdenProduccionFactory, ProductoFactory, SedeFactory, StockBodegaFactory,
)


class _DosSedesMixin:
    """Sede A (la del usuario) y sede B (ajena), cada una con área, bodegas y OP."""

    @classmethod
    def setUpTestData(cls):
        cls.sede_a = SedeFactory()
        cls.sede_b = SedeFactory()
        cls.area_a = AreaFactory(sede=cls.sede_a)
        cls.area_a2 = AreaFactory(sede=cls.sede_a)
        cls.area_b = AreaFactory(sede=cls.sede_b)
        cls.producto_a = ProductoFactory(sede=cls.sede_a)
        cls.bodega_a = BodegaFactory(sede=cls.sede_a)
        cls.bodega_b = BodegaFactory(sede=cls.sede_b)
        cls.orden_a = OrdenProduccionFactory(
            sede=cls.sede_a, area=cls.area_a, estado='en_proceso',
            producto_entrada=cls.producto_a, producto_salida=cls.producto_a,
            bodega_entrada=cls.bodega_a, bodega_salida=cls.bodega_a,
        )
        cls.orden_b = OrdenProduccionFactory(sede=cls.sede_b, area=cls.area_b)
        cls.lote_a = LoteProduccionFactory(orden_produccion=cls.orden_a, codigo_lote='LOT-ACC-A')
        cls.lote_b = LoteProduccionFactory(orden_produccion=cls.orden_b, codigo_lote='LOT-ACC-B')

    def setUp(self):
        self.client = APIClient()

    def _como(self, grupo, sede=None, area=None):
        user = CustomUserFactory(sede=sede or self.sede_a, groups=[grupo])
        if area is not None:
            user.area = area
            user.save(update_fields=['area'])
        self.client.force_authenticate(user=user)
        return user


class FiltrarPorSedeTestCase(_DosSedesMixin, TestCase):

    def test_filtrar_por_sede_dado_usuario_sin_sede_cuando_filtra_entonces_no_ve_nada(self):
        user = CustomUserFactory(sede=None, groups=['jefe_planta'])
        OrdenProduccionFactory(sede=None)
        self.assertEqual(filtrar_por_sede(OrdenProduccion.objects.all(), user).count(), 0)

    def test_filtrar_por_sede_dado_admin_sistemas_cuando_filtra_entonces_ve_todas(self):
        user = CustomUserFactory(sede=self.sede_a, groups=['admin_sistemas'])
        ids = set(filtrar_por_sede(OrdenProduccion.objects.all(), user).values_list('id', flat=True))
        self.assertTrue({self.orden_a.id, self.orden_b.id} <= ids)


class RegistrarLoteAccesoTestCase(_DosSedesMixin, TestCase):

    def _payload(self, **extra):
        ahora = timezone.now().isoformat()
        return {'peso_neto_producido': '10.00', 'turno': 'Dia',
                'hora_inicio': ahora, 'hora_final': ahora, **extra}

    def _url(self, orden):
        return f'/api/ordenes-produccion/{orden.id}/registrar-lote/'

    def test_registrar_lote_dado_rol_vendedor_cuando_post_entonces_403(self):
        self._como('vendedor')
        resp = self.client.post(self._url(self.orden_a), self._payload(), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_registrar_lote_dado_orden_de_otra_sede_cuando_post_entonces_404(self):
        self._como('jefe_planta')
        resp = self.client.post(self._url(self.orden_b), self._payload(), format='json')
        self.assertEqual(resp.status_code, 404)

    def test_registrar_lote_dado_operario_de_otra_area_cuando_post_entonces_403(self):
        self._como('operario', area=self.area_a2)
        resp = self.client.post(self._url(self.orden_a), self._payload(), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_registrar_lote_dado_maquina_de_otra_sede_cuando_post_entonces_400(self):
        self._como('jefe_planta')
        maquina_b = MaquinaFactory(area=self.area_b)
        resp = self.client.post(self._url(self.orden_a), self._payload(maquina=maquina_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('maquina', resp.data)

    def test_registrar_lote_dado_operario_acreditado_de_otra_sede_cuando_post_entonces_400(self):
        self._como('jefe_planta')
        ajeno = CustomUserFactory(sede=self.sede_b, groups=['operario'])
        resp = self.client.post(self._url(self.orden_a), self._payload(operario=ajeno.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('operario', resp.data)

    def test_registrar_lote_dado_operario_de_su_area_con_stock_cuando_post_entonces_201(self):
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto_a, cantidad=Decimal('500.00'))
        self._como('operario', area=self.area_a)
        resp = self.client.post(self._url(self.orden_a), self._payload(), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)


class TrazabilidadAccesoTestCase(_DosSedesMixin, TestCase):

    def test_trazabilidad_qr_dado_lote_de_otra_sede_cuando_get_entonces_404(self):
        self._como('operario')
        self.assertEqual(self.client.get('/api/trazabilidad-lote/LOT-ACC-B/').status_code, 404)

    def test_trazabilidad_qr_dado_lote_de_su_sede_cuando_get_entonces_200(self):
        self._como('operario')
        self.assertEqual(self.client.get('/api/trazabilidad-lote/LOT-ACC-A/').status_code, 200)

    def test_trazabilidad_costos_dado_rol_operario_cuando_get_entonces_403(self):
        self._como('operario')
        resp = self.client.get('/api/trazabilidad/lote-produccion/', {'lote_id': self.lote_a.id})
        self.assertEqual(resp.status_code, 403)

    def test_trazabilidad_costos_dado_lote_de_otra_sede_cuando_get_entonces_404(self):
        self._como('bodeguero')
        resp = self.client.get('/api/trazabilidad/lote-produccion/', {'lote_id': self.lote_b.id})
        self.assertEqual(resp.status_code, 404)

    def test_trazabilidad_costos_dado_bodeguero_de_la_sede_cuando_get_entonces_200(self):
        self._como('bodeguero')
        resp = self.client.get('/api/trazabilidad/lote-produccion/', {'lote_id': self.lote_a.id})
        self.assertEqual(resp.status_code, 200)

    def test_genealogia_dado_lote_de_otra_sede_cuando_get_entonces_404(self):
        self._como('jefe_planta')
        resp = self.client.get('/api/corridas-produccion/trazabilidad-lote/', {'codigo': 'LOT-ACC-B'})
        self.assertEqual(resp.status_code, 404)


class LotesListadoAccesoTestCase(_DosSedesMixin, TestCase):

    def test_lotes_dado_operario_cuando_lista_entonces_no_ve_lotes_de_otra_sede(self):
        self._como('operario')
        resp = self.client.get('/api/lotes-produccion/')
        data = resp.data.get('results', resp.data) if isinstance(resp.data, dict) else resp.data
        codigos = {fila['codigo_lote'] for fila in data}
        self.assertIn('LOT-ACC-A', codigos)
        self.assertNotIn('LOT-ACC-B', codigos)

    def test_lote_dado_lote_de_otra_sede_cuando_retrieve_entonces_404(self):
        self._como('empaquetado')
        self.assertEqual(self.client.get(f'/api/lotes-produccion/{self.lote_b.id}/').status_code, 404)


class KPIAreaAccesoTestCase(_DosSedesMixin, TestCase):

    def test_kpi_area_dado_jefe_planta_y_area_de_otra_sede_cuando_get_entonces_404(self):
        self._como('jefe_planta')
        self.assertEqual(self.client.get('/api/kpi-area/', {'area': self.area_b.id}).status_code, 404)

    def test_kpi_area_dado_jefe_planta_y_area_de_su_sede_cuando_get_entonces_200(self):
        self._como('jefe_planta')
        self.assertEqual(self.client.get('/api/kpi-area/', {'area': self.area_a.id}).status_code, 200)


class MesAccesoTestCase(_DosSedesMixin, TestCase):

    def test_corridas_dado_rol_vendedor_cuando_lista_entonces_403(self):
        self._como('vendedor')
        self.assertEqual(self.client.get('/api/corridas-produccion/').status_code, 403)

    def test_operaciones_dado_rol_vendedor_cuando_lista_entonces_403(self):
        self._como('vendedor')
        self.assertEqual(self.client.get('/api/operaciones-produccion/').status_code, 403)

    def test_iniciar_corrida_dado_area_de_otra_sede_cuando_post_entonces_404(self):
        self._como('operario', area=self.area_a)
        resp = self.client.post('/api/corridas-produccion/iniciar-corrida/',
                                {'area_id': self.area_b.id, 'modalidad': 'CONTINUA'}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_iniciar_corrida_dado_sede_id_ajeno_cuando_post_entonces_403(self):
        self._como('operario', area=self.area_a)
        resp = self.client.post('/api/corridas-produccion/iniciar-corrida/',
                                {'area_id': self.area_a.id, 'sede_id': self.sede_b.id, 'modalidad': 'CONTINUA'},
                                format='json')
        self.assertEqual(resp.status_code, 403)

    def test_iniciar_corrida_dado_maquina_de_otra_sede_cuando_post_entonces_404(self):
        self._como('operario', area=self.area_a)
        maquina_b = MaquinaFactory(area=self.area_b)
        resp = self.client.post('/api/corridas-produccion/iniciar-corrida/',
                                {'area_id': self.area_a.id, 'maquina_principal_id': maquina_b.id,
                                 'modalidad': 'CONTINUA'}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_planes_dado_rol_operario_cuando_lista_entonces_403(self):
        self._como('operario')
        self.assertEqual(self.client.get('/api/planes-produccion/').status_code, 403)

    def test_crear_plan_desde_alertas_dado_sede_ajena_cuando_post_entonces_403(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/planes-produccion/crear-desde-alertas/',
                                {'sede_id': self.sede_b.id, 'items': []}, format='json')
        self.assertEqual(resp.status_code, 403)

    def test_crear_plan_desde_alertas_dado_supervisor_de_otra_sede_cuando_post_entonces_404(self):
        self._como('jefe_planta')
        ajeno = CustomUserFactory(sede=self.sede_b, groups=['jefe_planta'])
        resp = self.client.post('/api/planes-produccion/crear-desde-alertas/',
                                {'sede_id': self.sede_a.id, 'supervisor_id': ajeno.id, 'items': []},
                                format='json')
        self.assertEqual(resp.status_code, 404)

    @patch('gestion.views.mes_views.ReposicionService.analizar_necesidades_reposicion', return_value=[])
    def test_necesidades_dado_jefe_planta_y_sede_ajena_cuando_get_entonces_usa_su_sede(self, analizar):
        self._como('jefe_planta')
        resp = self.client.get('/api/planes-produccion/necesidades-reposicion/', {'sede': self.sede_b.id})
        self.assertEqual(resp.status_code, 200)
        analizar.assert_called_once_with(sede_id=self.sede_a.id)

    def test_necesidades_dado_jefe_planta_sin_sede_cuando_get_entonces_403(self):
        user = CustomUserFactory(sede=None, groups=['jefe_planta'])
        self.client.force_authenticate(user=user)
        self.assertEqual(self.client.get('/api/planes-produccion/necesidades-reposicion/').status_code, 403)


class VentasAccesoTestCase(_DosSedesMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.cliente_a = ClienteFactory(sede=cls.sede_a)
        cls.cliente_b = ClienteFactory(sede=cls.sede_b)
        cls.pedido_a = PedidoVenta.objects.create(cliente=cls.cliente_a, guia_remision='GR-A', sede=cls.sede_a)
        cls.pedido_b = PedidoVenta.objects.create(cliente=cls.cliente_b, guia_remision='GR-B', sede=cls.sede_b)

    @staticmethod
    def _ids(resp):
        data = resp.data.get('results', resp.data) if isinstance(resp.data, dict) else resp.data
        return {fila['id'] for fila in data}

    def test_pedidos_dado_admin_sede_cuando_lista_entonces_no_ve_otra_sede(self):
        self._como('admin_sede')
        ids = self._ids(self.client.get('/api/pedidos-venta/'))
        self.assertIn(self.pedido_a.id, ids)
        self.assertNotIn(self.pedido_b.id, ids)

    def test_pedido_dado_producto_de_otra_sede_en_detalle_cuando_post_entonces_400(self):
        self._como('admin_sede')
        producto_b = ProductoFactory(sede=self.sede_b, precio_base=Decimal('1.000'))
        resp = self.client.post('/api/pedidos-venta/', {
            'cliente': self.cliente_a.id, 'guia_remision': 'GR-AJENO',
            'detalles': [{'producto': producto_b.id, 'cantidad': 1, 'piezas': 1,
                          'peso': '1.000', 'precio_unitario': '5.000'}],
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PedidoVenta.objects.filter(guia_remision='GR-AJENO').exists())

    def test_pedido_dado_detalle_con_peso_no_positivo_cuando_post_entonces_400(self):
        self._como('admin_sede')
        resp = self.client.post('/api/pedidos-venta/', {
            'cliente': self.cliente_a.id, 'guia_remision': 'GR-NEG',
            'detalles': [{'producto': self.producto_a.id, 'cantidad': 1, 'piezas': 1,
                          'peso': '-5.000', 'precio_unitario': '100.000'}],
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(PedidoVenta.objects.filter(guia_remision='GR-NEG').exists())

    def test_pago_dado_cliente_de_otra_sede_cuando_post_entonces_400(self):
        self._como('admin_sede')
        resp = self.client.post('/api/pagos-cliente/',
                                {'cliente': self.cliente_b.id, 'monto': '10.00', 'es_anticipo': True},
                                format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('cliente', str(resp.data))

    def test_pedido_dado_vendedor_y_cliente_no_asignado_cuando_post_entonces_400(self):
        self._como('vendedor')
        resp = self.client.post('/api/pedidos-venta/',
                                {'cliente': self.cliente_a.id, 'guia_remision': 'GR-X', 'detalles': []},
                                format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('cliente', str(resp.data))

    def test_pedido_dado_admin_sistemas_cuando_crea_entonces_hereda_sede_del_cliente(self):
        self._como('admin_sistemas')
        resp = self.client.post('/api/pedidos-venta/',
                                {'cliente': self.cliente_b.id, 'guia_remision': 'GR-Y',
                                 'sede': self.sede_a.id, 'detalles': []},
                                format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(PedidoVenta.objects.get(pk=resp.data['id']).sede_id, self.sede_b.id)


class ErroresInternosSinDetalleTestCase(_DosSedesMixin, TestCase):
    """CWE-209: un 500 no devuelve el texto de la excepción al cliente."""

    @patch('gestion.views.mes_views.GenealogiaService.obtener_trazabilidad_hacia_atras',
           side_effect=RuntimeError('detalle interno SQL'))
    def test_genealogia_dado_error_inesperado_cuando_get_entonces_500_sin_detalle(self, _):
        self._como('jefe_planta')
        resp = self.client.get('/api/corridas-produccion/trazabilidad-lote/', {'codigo': 'LOT-ACC-A'})
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detalle interno SQL', str(resp.data))

    @patch('gestion.views.production_lote_views.RegistroLoteService.registrar_lote',
           side_effect=RuntimeError('detalle interno SQL'))
    def test_registrar_lote_dado_error_inesperado_cuando_post_entonces_500_sin_detalle(self, _):
        self._como('jefe_planta')
        ahora = datetime(2026, 1, 1, 8, 0).isoformat()
        resp = self.client.post(f'/api/ordenes-produccion/{self.orden_a.id}/registrar-lote/',
                                {'peso_neto_producido': '10.00', 'hora_inicio': ahora, 'hora_final': ahora},
                                format='json')
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detalle interno SQL', str(resp.data))
