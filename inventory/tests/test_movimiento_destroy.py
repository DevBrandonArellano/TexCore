"""
Pruebas de MovimientoInventarioViewSet.destroy() — antes de este cambio no
estaba sobreescrito: usaba el destroy() genérico de DRF, que llama a
instance.delete() sin setear _justificacion_auditoria (exigida por
AuditableModelMixin) -> ValidationError de Django no capturada -> 500, sin
revertir stock. Ahora sigue el mismo patrón que HistorialDespachoViewSet.destroy:
justificación obligatoria, reversión de stock vía MovimientoReversionService,
solo entonces se borra.

Técnicas ISTQB:
- Caja blanca: justificación vacía -> 400 (antes de tocar el servicio).
- Caja blanca: movimiento ligado a un despacho -> 400 (guarda del servicio,
  ValueError capturado).
- Caso feliz: MERMA con justificación -> 204, stock restaurado, movimiento
  original eliminado.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import MovimientoInventario, StockBodega, DetalleHistorialDespacho, HistorialDespacho
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory, StockBodegaFactory,
)


class MovimientoDestroyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=self.bodeguero)

    def _url(self, movimiento_id):
        return reverse('movimiento-detail', args=[movimiento_id])

    def test_destroy_dado_merma_sin_justificacion_cuando_delete_entonces_400(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('70.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='MERMA', producto=self.producto, cantidad=Decimal('30.00'),
            bodega_origen=self.bodega, usuario=self.bodeguero, saldo_resultante=Decimal('70.00'),
        )
        resp = self.client.delete(self._url(movimiento.id), {'justificacion': ''}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(MovimientoInventario.objects.filter(id=movimiento.id).exists())

    def test_destroy_dado_merma_con_justificacion_cuando_delete_entonces_204_y_revierte_stock(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('70.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='MERMA', producto=self.producto, cantidad=Decimal('30.00'),
            bodega_origen=self.bodega, usuario=self.bodeguero, saldo_resultante=Decimal('70.00'),
        )
        resp = self.client.delete(
            self._url(movimiento.id), {'justificacion': 'Merma registrada por error de digitación'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, getattr(resp, 'data', None))

        self.assertFalse(MovimientoInventario.objects.filter(id=movimiento.id).exists())
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('100.00'))
        # Movimiento compensatorio creado para trazabilidad
        self.assertTrue(MovimientoInventario.objects.filter(documento_ref=f"REVERT-Mov-#{movimiento.id}").exists())

    def test_destroy_dado_movimiento_ligado_a_despacho_cuando_delete_entonces_400(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('0.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA', producto=self.producto, cantidad=Decimal('10.00'),
            bodega_origen=self.bodega, usuario=self.bodeguero, saldo_resultante=Decimal('0.00'),
        )
        historial = HistorialDespacho.objects.create(
            usuario=self.bodeguero, total_bultos=1, total_peso=Decimal('10.00'))
        DetalleHistorialDespacho.objects.create(
            historial=historial, producto=self.producto, peso=Decimal('10.00'), movimiento_venta=movimiento)

        resp = self.client.delete(
            self._url(movimiento.id), {'justificacion': 'Intento de borrar un movimiento de despacho'},
            format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(MovimientoInventario.objects.filter(id=movimiento.id).exists())

    def test_destroy_dado_vendedor_cuando_delete_entonces_403(self):
        # Regresión: el permiso de escritura (IsInventoryWriterOrAdmin) ya
        # cubre destroy() desde el Fix de RBAC previo.
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.client.force_authenticate(user=vendedor)
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='MERMA', producto=self.producto, cantidad=Decimal('1.00'),
            bodega_origen=self.bodega, usuario=self.bodeguero, saldo_resultante=Decimal('0.00'),
        )
        resp = self.client.delete(self._url(movimiento.id), {'justificacion': 'no autorizado'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
