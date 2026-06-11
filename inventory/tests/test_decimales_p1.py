"""
Tests Sprint 4 (P1-008): Estandarización de precisión decimal en inventory.
Artefacto RUP: Suite de Pruebas

Diagnóstico CONTEXTO.md: StockBodega/MovimientoInventario usaban 2 decimales
mientras gestion (DetallePedido, LoteProduccion, etc.) usa 3 — el redondeo
cruzado acumula error en el Kardex. Se estandariza TODO el almacenamiento
a DECIMAL(12,3).

Técnicas ISTQB: BVA (el tercer decimal es el límite que antes se perdía).
"""

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import Group

from gestion.models import CustomUser, Sede, Producto, Bodega
from inventory.models import StockBodega, MovimientoInventario


class PrecisionDecimalInventoryTestCase(TestCase):
    """El almacenamiento de inventory debe conservar 3 decimales."""

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Decimales', location='Quito')
        self.user = CustomUser.objects.create_user(username='dec_user', password='test123')
        self.producto = Producto.objects.create(
            codigo='QUIM-DEC', descripcion='Químico Decimales', tipo='quimico',
            unidad_medida='kg', precio_base=Decimal('5.00'), sede=self.sede,
        )
        self.bodega = Bodega.objects.create(nombre='Bodega Decimales', sede=self.sede)

    def test_stock_bodega_conserva_tres_decimales(self):
        """BVA: 10.125 kg debe almacenarse exacto, no redondear a 10.13."""
        stock = StockBodega(
            bodega=self.bodega, producto=self.producto,
            cantidad=Decimal('10.125'),
        )
        stock._justificacion_auditoria = 'Test precisión P1-008'
        stock.save()
        stock.refresh_from_db()
        self.assertEqual(stock.cantidad, Decimal('10.125'),
                         'StockBodega debe almacenar 3 decimales como el resto del sistema')

    def test_movimiento_inventario_conserva_tres_decimales(self):
        """BVA: cantidad y saldo_resultante con 3 decimales exactos."""
        mov = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega,
            cantidad=Decimal('7.375'),
            usuario=self.user,
            documento_ref='TEST-DEC',
            saldo_resultante=Decimal('17.500'),
        )
        mov.refresh_from_db()
        self.assertEqual(mov.cantidad, Decimal('7.375'))
        self.assertEqual(mov.saldo_resultante, Decimal('17.500'))

    def test_kardex_sin_error_acumulado_por_redondeo(self):
        """
        STT acumulación: 10 movimientos de 1.111 kg deben sumar 11.110 exacto.
        Con 2 decimales cada uno redondeaba a 1.11 y el Kardex desfasaba.
        """
        stock = StockBodega(
            bodega=self.bodega, producto=self.producto, cantidad=Decimal('0.000'),
        )
        stock._justificacion_auditoria = 'Init test acumulación'
        stock.save()

        for _ in range(10):
            stock.cantidad += Decimal('1.111')
            stock._justificacion_auditoria = 'Compra parcial'
            stock.save()

        stock.refresh_from_db()
        self.assertEqual(stock.cantidad, Decimal('11.110'),
                         'La suma debe ser exacta sin error de redondeo acumulado')
