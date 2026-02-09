from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import Group
from decimal import Decimal
from gestion.models import Sede, Bodega, Producto, CustomUser, LoteProduccion
from inventory.models import StockBodega, MovimientoInventario
from django.utils import timezone


class StockBodegaModelTestCase(TestCase):
    """Test cases for StockBodega model."""
    
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="PROD001",
            descripcion="Hilo de Algodon",
            tipo="hilo",
            unidad_medida="kg",
            stock_minimo=10.00
        )

    def test_stock_creation(self):
        """Verify that stock record can be created."""
        stock = StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto,
            cantidad=100.00
        )
        self.assertEqual(stock.cantidad, Decimal('100.00'))
        self.assertEqual(stock.bodega, self.bodega)
        self.assertEqual(stock.producto, self.producto)

    def test_stock_string_representation(self):
        """Verify stock string representation."""
        stock = StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto,
            cantidad=50.00
        )
        expected = "50.0 x Hilo de Algodon en Bodega Principal (Sede Central)"
        self.assertEqual(str(stock), expected)

    def test_stock_with_lote(self):
        """Verify stock with lote information."""
        lote = LoteProduccion.objects.create(
            codigo_lote="LOTE001",
            peso_neto_producido=100.00,
            maquina="Maquina 1",
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now()
        )
        stock = StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto,
            lote=lote,
            cantidad=25.00
        )
        self.assertIn("(Lote: LOTE001)", str(stock))

    def test_stock_uniqueness_constraint(self):
        """Verify that duplicate stock entries (bodega, producto, lote) are prevented."""
        StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto,
            cantidad=10.00
        )
        # Attempting to create duplicate should raise an error
        with self.assertRaises(Exception):
            StockBodega.objects.create(
                bodega=self.bodega,
                producto=self.producto,
                cantidad=20.00
            )


class MovimientoInventarioModelTestCase(TestCase):
    """Test cases for MovimientoInventario model."""
    
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="PROD001",
            descripcion="Hilo de Algodon",
            tipo="hilo",
            unidad_medida="kg"
        )

    def test_movement_creation_compra(self):
        """Verify that purchase movements can be recorded."""
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega,
            cantidad=50.00,
            saldo_resultante=50.00
        )
        self.assertEqual(movimiento.cantidad, Decimal('50.00'))
        self.assertEqual(movimiento.tipo_movimiento, 'COMPRA')
        self.assertEqual(movimiento.bodega_destino, self.bodega)

    def test_movement_string_representation(self):
        """Verify movement string representation."""
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega,
            cantidad=50.00,
            saldo_resultante=50.00
        )
        self.assertIn("Compra de Material", str(movimiento))
        self.assertIn("Hilo de Algodon", str(movimiento))

    def test_movement_ordering(self):
        """Verify movements are ordered by fecha descending."""
        mov1 = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega,
            cantidad=50.00,
            saldo_resultante=50.00
        )
        mov2 = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA',
            producto=self.producto,
            bodega_origen=self.bodega,
            cantidad=10.00,
            saldo_resultante=40.00
        )
        movements = list(MovimientoInventario.objects.all())
        self.assertEqual(movements[0], mov2)  # Most recent first
        self.assertEqual(movements[1], mov1)


class StockUpdateLogicTestCase(APITestCase):
    """Test cases for stock update logic through API."""
    
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega1 = Bodega.objects.create(nombre="Bodega 1", sede=self.sede)
        self.bodega2 = Bodega.objects.create(nombre="Bodega 2", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="PROD001",
            descripcion="Hilo de Algodon",
            tipo="hilo",
            unidad_medida="kg",
            stock_minimo=10.00
        )
        
        # Create user with permissions
        self.group = Group.objects.create(name='admin_sistemas')
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            sede=self.sede
        )
        self.user.groups.add(self.group)
        self.user.bodegas_asignadas.add(self.bodega1, self.bodega2)
        self.client.force_authenticate(user=self.user)

    def test_compra_increases_stock(self):
        """Test that COMPRA movement increases stock."""
        url = reverse('movimientoinventario-list')
        data = {
            'tipo_movimiento': 'COMPRA',
            'producto': self.producto.id,
            'bodega_destino': self.bodega1.id,
            'cantidad': '100.00',
            'saldo_resultante': '100.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Verify stock was created
        stock = StockBodega.objects.get(bodega=self.bodega1, producto=self.producto)
        self.assertEqual(stock.cantidad, Decimal('100.00'))

    def test_multiple_compras_accumulate_stock(self):
        """Test that multiple purchases accumulate stock correctly."""
        url = reverse('movimientoinventario-list')
        
        # First purchase
        self.client.post(url, {
            'tipo_movimiento': 'COMPRA',
            'producto': self.producto.id,
            'bodega_destino': self.bodega1.id,
            'cantidad': '50.00',
            'saldo_resultante': '50.00'
        }, format='json')
        
        # Second purchase
        self.client.post(url, {
            'tipo_movimiento': 'COMPRA',
            'producto': self.producto.id,
            'bodega_destino': self.bodega1.id,
            'cantidad': '30.00',
            'saldo_resultante': '80.00'
        }, format='json')
        
        stock = StockBodega.objects.get(bodega=self.bodega1, producto=self.producto)
        self.assertEqual(stock.cantidad, Decimal('80.00'))

    def test_venta_decreases_stock(self):
        """Test that VENTA movement decreases stock."""
        # First create stock
        StockBodega.objects.create(
            bodega=self.bodega1,
            producto=self.producto,
            cantidad=100.00
        )
        
        url = reverse('movimientoinventario-list')
        data = {
            'tipo_movimiento': 'VENTA',
            'producto': self.producto.id,
            'bodega_origen': self.bodega1.id,
            'cantidad': '25.00',
            'saldo_resultante': '75.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        stock = StockBodega.objects.get(bodega=self.bodega1, producto=self.producto)
        self.assertEqual(stock.cantidad, Decimal('75.00'))

    def test_venta_insufficient_stock_fails(self):
        """Test that sale with insufficient stock fails."""
        StockBodega.objects.create(
            bodega=self.bodega1,
            producto=self.producto,
            cantidad=10.00
        )
        
        url = reverse('movimientoinventario-list')
        data = {
            'tipo_movimiento': 'VENTA',
            'producto': self.producto.id,
            'bodega_origen': self.bodega1.id,
            'cantidad': '50.00',
            'saldo_resultante': '-40.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class TransferenciaStockTestCase(APITestCase):
    """Test cases for stock transfers between warehouses."""
    
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega1 = Bodega.objects.create(nombre="Bodega 1", sede=self.sede)
        self.bodega2 = Bodega.objects.create(nombre="Bodega 2", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="PROD001",
            descripcion="Hilo de Algodon",
            tipo="hilo",
            unidad_medida="kg"
        )
        
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            sede=self.sede
        )
        self.client.force_authenticate(user=self.user)
        
        # Create initial stock in bodega1
        self.stock_origen = StockBodega.objects.create(
            bodega=self.bodega1,
            producto=self.producto,
            cantidad=100.00
        )

    def test_transferencia_success(self):
        """Test successful stock transfer between warehouses."""
        url = reverse('transferencia-stock')
        data = {
            'producto_id': self.producto.id,
            'bodega_origen_id': self.bodega1.id,
            'bodega_destino_id': self.bodega2.id,
            'cantidad': '30.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify stock decreased in origin
        self.stock_origen.refresh_from_db()
        self.assertEqual(self.stock_origen.cantidad, Decimal('70.00'))
        
        # Verify stock increased in destination
        stock_destino = StockBodega.objects.get(bodega=self.bodega2, producto=self.producto)
        self.assertEqual(stock_destino.cantidad, Decimal('30.00'))
        
        # Verify movement was recorded
        movimiento = MovimientoInventario.objects.filter(tipo_movimiento='TRANSFERENCIA').first()
        self.assertIsNotNone(movimiento)
        self.assertEqual(movimiento.cantidad, Decimal('30.00'))

    def test_transferencia_insufficient_stock(self):
        """Test transfer fails with insufficient stock."""
        url = reverse('transferencia-stock')
        data = {
            'producto_id': self.producto.id,
            'bodega_origen_id': self.bodega1.id,
            'bodega_destino_id': self.bodega2.id,
            'cantidad': '150.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_transferencia_same_bodega_fails(self):
        """Test transfer to same warehouse fails validation."""
        url = reverse('transferencia-stock')
        data = {
            'producto_id': self.producto.id,
            'bodega_origen_id': self.bodega1.id,
            'bodega_destino_id': self.bodega1.id,
            'cantidad': '30.00'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class KardexCalculationTestCase(APITestCase):
    """Test cases for Kardex calculation logic."""
    
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="PROD001",
            descripcion="Hilo de Algodon",
            tipo="hilo",
            unidad_medida="kg"
        )
        
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            sede=self.sede
        )
        self.client.force_authenticate(user=self.user)

    def test_kardex_calculation_multiple_movements(self):
        """Test Kardex correctly calculates running balance."""
        # Create movements
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega,
            cantidad=100.00,
            saldo_resultante=100.00
        )
        MovimientoInventario.objects.create(
            tipo_movimiento='VENTA',
            producto=self.producto,
            bodega_origen=self.bodega,
            cantidad=30.00,
            saldo_resultante=70.00
        )
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega,
            cantidad=50.00,
            saldo_resultante=120.00
        )
        
        url = reverse('kardex-bodega', kwargs={'bodega_id': self.bodega.id})
        response = self.client.get(url, {'producto_id': self.producto.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        kardex = response.data
        
        # Verify running balance
        self.assertEqual(len(kardex), 3)
        self.assertEqual(kardex[0]['saldo_resultante'], 100.00)
        self.assertEqual(kardex[1]['saldo_resultante'], 70.00)
        self.assertEqual(kardex[2]['saldo_resultante'], 120.00)


class StockAlertsTestCase(APITestCase):
    """Test cases for stock alerts functionality."""
    
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        
        self.producto_low = Producto.objects.create(
            codigo="PROD001",
            descripcion="Producto Bajo Stock",
            tipo="hilo",
            unidad_medida="kg",
            stock_minimo=50.00
        )
        self.producto_ok = Producto.objects.create(
            codigo="PROD002",
            descripcion="Producto Stock OK",
            tipo="hilo",
            unidad_medida="kg",
            stock_minimo=10.00
        )
        
        # Create stocks
        StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto_low,
            cantidad=20.00  # Below minimum
        )
        StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto_ok,
            cantidad=50.00  # Above minimum
        )
        
        self.user = CustomUser.objects.create_user(
            username='testuser',
            password='testpass123',
            sede=self.sede
        )
        self.user.bodegas_asignadas.add(self.bodega)
        self.client.force_authenticate(user=self.user)

    def test_stock_alerts_returns_low_stock_items(self):
        """Test that alerts endpoint returns items below minimum stock."""
        url = reverse('alertas-stock')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        alert = response.data[0]
        self.assertEqual(alert['producto_codigo'], 'PROD001')
        self.assertEqual(alert['stock_actual'], 20.00)
        self.assertEqual(alert['stock_minimo'], 50.00)
        self.assertEqual(alert['faltante'], 30.00)

