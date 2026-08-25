"""
Pruebas de ProcessDespachoAPIView (inventory/views/despacho_views.py).

Cubre el bug reportado en producción: despachar solo una parte de un pedido lo
marcaba como 'despachado' completo en vez de 'despachado_parcial', y un
segundo intento de despacho volvía a pedir el 100% original en vez de solo lo
restante. También cubre la asignación de cada lote escaneado al pedido
correcto cuando un despacho cubre varios pedidos a la vez (antes,
DetalleHistorialDespachoPedido.cantidad_despachada quedaba siempre en 0).

Técnicas ISTQB aplicadas:
- Partición de equivalencia: despacho completo / parcial / excedente.
- Prueba de transición de estados (STT): pendiente -> despachado_parcial ->
  despachado a través de dos despachos sucesivos del mismo pedido.
"""
from decimal import Decimal
from datetime import datetime

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    CustomUser, Bodega, Producto, LoteProduccion,
    PedidoVenta, DetallePedido, Sede, Cliente
)
from inventory.models import StockBodega, DetalleHistorialDespachoPedido, HistorialDespacho


class ProcessDespachoAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.usuario = CustomUser.objects.create_user(username='despacho_user', password='test123')
        despacho_group, _ = Group.objects.get_or_create(name='despacho')
        self.usuario.groups.add(despacho_group)
        self.client.force_authenticate(user=self.usuario)

        self.sede = Sede.objects.create(nombre='Sede Test', location='Lima')
        self.bodega = Bodega.objects.create(nombre='Bodega Despacho', sede=self.sede)

        self.producto_a = Producto.objects.create(
            codigo='TELA-A', descripcion='Tela A', tipo='tela',
            stock_minimo=Decimal('0.00'), unidad_medida='kg',
        )
        self.producto_b = Producto.objects.create(
            codigo='TELA-B', descripcion='Tela B', tipo='tela',
            stock_minimo=Decimal('0.00'), unidad_medida='kg',
        )

        self.cliente = Cliente.objects.create(
            ruc_cedula='1234567890', nombre_razon_social='Cliente Test',
            direccion_envio='Direccion Test', nivel_precio='normal',
        )

    def _crear_lote_con_stock(self, codigo_lote, producto, cantidad):
        lote = LoteProduccion.objects.create(
            codigo_lote=codigo_lote,
            peso_neto_producido=cantidad,
            turno='DIURNO',
            hora_inicio=datetime(2026, 1, 1, 8, 0),
            hora_final=datetime(2026, 1, 1, 9, 0),
        )
        # ProcessDespachoAPIView resuelve el producto vía lote.orden_produccion
        # (no vía este StockBodega) — cada test asigna `lote.orden_produccion`
        # después de llamar a este helper.
        StockBodega.objects.create(bodega=self.bodega, producto=producto, lote=lote, cantidad=cantidad)
        return lote

    def _crear_pedido(self, peso_requerido, producto=None):
        pedido = PedidoVenta.objects.create(cliente=self.cliente, guia_remision='GR-TEST', estado='pendiente')
        DetallePedido.objects.create(
            pedido_venta=pedido,
            producto=producto or self.producto_a,
            cantidad=1,
            piezas=1,
            peso=peso_requerido,
            precio_unitario=Decimal('10.000'),
        )
        return pedido

    def test_despacho_completo_dado_stock_cubre_todo_cuando_procesa_entonces_estado_despachado(self):
        from gestion.models import OrdenProduccion
        orden = OrdenProduccion.objects.create(
            codigo='OP-D1', peso_neto_requerido=Decimal('50.00'), producto_salida=self.producto_a,
        )
        lote = self._crear_lote_con_stock('LOTE-D1', self.producto_a, Decimal('50.000'))
        lote.orden_produccion = orden
        lote.save()

        pedido = self._crear_pedido(Decimal('50.000'))

        resp = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido.id],
            'lotes': ['LOTE-D1'],
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'despachado')

        detalle_pedido = DetalleHistorialDespachoPedido.objects.get(pedido=pedido)
        self.assertEqual(detalle_pedido.cantidad_despachada, Decimal('50.000'))

    def test_despacho_parcial_dado_parte_del_stock_cuando_confirma_incompleto_entonces_estado_parcial(self):
        from gestion.models import OrdenProduccion
        orden = OrdenProduccion.objects.create(
            codigo='OP-D2', peso_neto_requerido=Decimal('30.00'), producto_salida=self.producto_a,
        )
        lote = self._crear_lote_con_stock('LOTE-D2', self.producto_a, Decimal('30.000'))
        lote.orden_produccion = orden
        lote.save()

        # Pedido requiere 100 kg, solo se escanean 30 kg -> queda parcial.
        pedido = self._crear_pedido(Decimal('100.000'))

        resp = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido.id],
            'lotes': ['LOTE-D2'],
            'confirmar_incompleto': True,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'despachado_parcial')
        self.assertIsNotNone(pedido.fecha_despacho)

    def test_despacho_parcial_dado_pedido_incompleto_cuando_no_confirma_entonces_409_sin_efectos(self):
        from gestion.models import OrdenProduccion
        orden = OrdenProduccion.objects.create(
            codigo='OP-D3', peso_neto_requerido=Decimal('30.00'), producto_salida=self.producto_a,
        )
        lote = self._crear_lote_con_stock('LOTE-D3', self.producto_a, Decimal('30.000'))
        lote.orden_produccion = orden
        lote.save()

        pedido = self._crear_pedido(Decimal('100.000'))

        resp = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido.id],
            'lotes': ['LOTE-D3'],
        }, format='json')

        self.assertEqual(resp.status_code, 409)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente')  # sin efectos secundarios
        self.assertIn('items_incompletos', resp.data)

    def test_completar_despacho_parcial_dado_segundo_despacho_cuando_cubre_el_resto_entonces_estado_despachado(self):
        """
        Regresión directa del bug reportado: tras un primer despacho parcial,
        un segundo despacho con el resto del stock debe completar el pedido
        SIN volver a exigir el 100% original (solo lo pendiente).
        """
        from gestion.models import OrdenProduccion
        orden = OrdenProduccion.objects.create(
            codigo='OP-D4', peso_neto_requerido=Decimal('100.00'), producto_salida=self.producto_a,
        )
        lote1 = self._crear_lote_con_stock('LOTE-D4-1', self.producto_a, Decimal('30.000'))
        lote1.orden_produccion = orden
        lote1.save()

        pedido = self._crear_pedido(Decimal('100.000'))

        # Primer despacho: 30/100 kg -> parcial
        resp1 = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido.id],
            'lotes': ['LOTE-D4-1'],
            'confirmar_incompleto': True,
        }, format='json')
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'despachado_parcial')

        # Segundo despacho: los 70 kg restantes -> ya NO debe pedir confirmar_incompleto
        # porque _calcular_incompletos debe restar lo ya despachado (30kg) del requerido (100kg).
        lote2 = self._crear_lote_con_stock('LOTE-D4-2', self.producto_a, Decimal('70.000'))
        lote2.orden_produccion = orden
        lote2.save()

        resp2 = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido.id],
            'lotes': ['LOTE-D4-2'],
        }, format='json')

        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'despachado')

    def test_despacho_multipedido_dado_dos_pedidos_cuando_procesa_entonces_asigna_cada_lote_a_su_pedido(self):
        """
        Un despacho puede cubrir varios pedidos a la vez: cada lote escaneado
        debe atribuirse al pedido correcto (no simplemente al primero),
        reflejado en DetalleHistorialDespachoPedido.cantidad_despachada.
        """
        from gestion.models import OrdenProduccion
        orden_a = OrdenProduccion.objects.create(
            codigo='OP-D5A', peso_neto_requerido=Decimal('20.00'), producto_salida=self.producto_a,
        )
        orden_b = OrdenProduccion.objects.create(
            codigo='OP-D5B', peso_neto_requerido=Decimal('15.00'), producto_salida=self.producto_b,
        )
        lote_a = self._crear_lote_con_stock('LOTE-D5A', self.producto_a, Decimal('20.000'))
        lote_a.orden_produccion = orden_a
        lote_a.save()
        lote_b = self._crear_lote_con_stock('LOTE-D5B', self.producto_b, Decimal('15.000'))
        lote_b.orden_produccion = orden_b
        lote_b.save()

        pedido_a = self._crear_pedido(Decimal('20.000'), producto=self.producto_a)
        pedido_b = self._crear_pedido(Decimal('15.000'), producto=self.producto_b)

        resp = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido_a.id, pedido_b.id],
            'lotes': ['LOTE-D5A', 'LOTE-D5B'],
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        pedido_a.refresh_from_db()
        pedido_b.refresh_from_db()
        self.assertEqual(pedido_a.estado, 'despachado')
        self.assertEqual(pedido_b.estado, 'despachado')

        cantidad_a = DetalleHistorialDespachoPedido.objects.get(pedido=pedido_a).cantidad_despachada
        cantidad_b = DetalleHistorialDespachoPedido.objects.get(pedido=pedido_b).cantidad_despachada
        self.assertEqual(cantidad_a, Decimal('20.000'))
        self.assertEqual(cantidad_b, Decimal('15.000'))

    def test_despacho_dado_procesado_por_endpoint_cuando_se_revierte_por_endpoint_entonces_200(self):
        """
        Regresión de bug real: revertir un despacho vía el endpoint HTTP
        siempre fallaba con 500 (ProtectedError al borrar HistorialDespacho
        con DetalleHistorialDespachoPedido aún apuntándole — PROTECT). Los
        tests de test_despacho_reversion.py no lo detectaban porque llaman a
        DespachoReversionService directo (sin pasar por historial.delete()) o
        usan un historial sin pedido vinculado. Este test pasa por el flujo
        HTTP completo real: despachar y luego revertir, ambos vía API.
        """
        from gestion.models import OrdenProduccion
        orden = OrdenProduccion.objects.create(
            codigo='OP-D6', peso_neto_requerido=Decimal('10.00'), producto_salida=self.producto_a,
        )
        lote = self._crear_lote_con_stock('LOTE-D6', self.producto_a, Decimal('10.000'))
        lote.orden_produccion = orden
        lote.save()
        pedido = self._crear_pedido(Decimal('10.000'))

        resp_despacho = self.client.post('/api/inventory/process-despacho/', {
            'pedidos': [pedido.id],
            'lotes': ['LOTE-D6'],
        }, format='json')
        self.assertEqual(resp_despacho.status_code, status.HTTP_200_OK)
        despacho_id = resp_despacho.data['despacho_id']

        resp_revertir = self.client.post(
            f'/api/inventory/historial-despachos/{despacho_id}/revertir/',
            {'justificacion': 'Prueba de reversión end-to-end'}, format='json',
        )

        self.assertEqual(resp_revertir.status_code, status.HTTP_200_OK, f"Error: {resp_revertir.data}")
        self.assertFalse(HistorialDespacho.objects.filter(id=despacho_id).exists())
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'pendiente')
