from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from gestion.models import Sede, Bodega, Producto, OrdenProduccion
from gestion.services.registro_lote import RegistroLoteService
from inventory.models import StockBodega, MovimientoInventario

User = get_user_model()

class RegistroLoteMermaTestCase(TestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="H-001",
            descripcion="Hilo Crudo",
            tipo="hilo",
            unidad_medida="kg",
            stock_minimo=10
        )
        self.user = User.objects.create_user(username="operario", password="123", sede=self.sede)

        # Crear stock inicial
        self.stock = StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto,
            cantidad=Decimal('100.00'),
            lote=None
        )

        self.orden = OrdenProduccion.objects.create(
            codigo="OP-MERMA-01",
            producto_entrada=self.producto,
            bodega_entrada=self.bodega,
            peso_neto_requerido=Decimal('50.00'),
            sede=self.sede
        )

    def test_registro_lote_con_merma(self):
        """Verifica que el registro de lote descuente merma y genere movimiento de KARDEX."""
        lote_data = {
            'peso_neto_producido': '40.00',
            'peso_merma': '5.00',
            'tipo_merma': 'maquina',
            'turno': 'Dia',
            'hora_inicio': '2026-05-20T10:00:00Z',
            'hora_final': '2026-05-20T12:00:00Z'
        }

        # Ejecutar servicio
        lote = RegistroLoteService.registrar_lote(self.orden, lote_data, self.user)

        # Validaciones de Lote
        self.assertEqual(lote.peso_neto_producido, Decimal('40.00'))
        self.assertEqual(lote.peso_merma, Decimal('5.00'))
        self.assertEqual(lote.tipo_merma, 'maquina')

        # Validaciones de StockBodega Base
        self.stock.refresh_from_db()
        # 100 inicial - 40 producido - 5 merma = 55
        self.assertEqual(self.stock.cantidad, Decimal('55.00'))

        # Validaciones de Kardex (Movimientos)
        movimientos = MovimientoInventario.objects.filter(documento_ref__contains=self.orden.codigo)
        
        # Deben existir al menos 3 movimientos: 
        # 1. CONSUMO (40kg)
        # 2. MERMA (5kg)
        # 3. PRODUCCION (40kg entrada de producto terminado)
        consumo = movimientos.filter(tipo_movimiento='CONSUMO', cantidad=Decimal('40.00')).exists()
        merma = movimientos.filter(tipo_movimiento='MERMA', cantidad=Decimal('5.00')).exists()
        produccion = movimientos.filter(tipo_movimiento='PRODUCCION', cantidad=Decimal('40.00')).exists()

        self.assertTrue(consumo, "Debe existir un movimiento de CONSUMO por 40kg")
        self.assertTrue(merma, "Debe existir un movimiento de MERMA por 5kg")
        self.assertTrue(produccion, "Debe existir un movimiento de PRODUCCION por 40kg")