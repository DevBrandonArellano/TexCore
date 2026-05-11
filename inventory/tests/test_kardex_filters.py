from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from gestion.models import Bodega, Producto, Sede
from inventory.models import MovimientoInventario

User = get_user_model()

class KardexFilterTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='password')
        # Assign required groups or superuser if needed
        self.user.is_superuser = True
        self.user.save()

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.sede = Sede.objects.create(nombre="Sede 1")
        self.bodega1 = Bodega.objects.create(nombre="Bodega 1", sede=self.sede)
        self.bodega2 = Bodega.objects.create(nombre="Bodega 2", sede=self.sede)

        self.producto1 = Producto.objects.create(codigo="P1", descripcion="Prod 1", tipo="insumo", unidad_medida="kg")
        self.producto2 = Producto.objects.create(codigo="P2", descripcion="Prod 2", tipo="insumo", unidad_medida="kg")

        now = timezone.now()

        # m1: Entrada B1 P1
        self.m1 = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto1,
            cantidad=Decimal('100.00'),
            bodega_destino=self.bodega1,
            saldo_resultante=Decimal('100.00'),
            usuario=self.user,
            fecha=now - timedelta(days=5)
        )

        # m2: Entrada B2 P1
        self.m2 = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto1,
            cantidad=Decimal('50.00'),
            bodega_destino=self.bodega2,
            saldo_resultante=Decimal('50.00'),
            usuario=self.user,
            fecha=now - timedelta(days=4)
        )

        # m3: Entrada B1 P2
        self.m3 = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto2,
            cantidad=Decimal('200.00'),
            bodega_destino=self.bodega1,
            saldo_resultante=Decimal('200.00'),
            usuario=self.user,
            fecha=now - timedelta(days=3)
        )

        # m4: Salida B1 P1
        self.m4 = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA',
            producto=self.producto1,
            cantidad=Decimal('20.00'),
            bodega_origen=self.bodega1,
            saldo_resultante=Decimal('80.00'),
            usuario=self.user,
            fecha=now - timedelta(days=2)
        )

    def test_filter_by_bodega(self):
        response = self.client.get(f'/api/inventory/movimientos/?bodega_id={self.bodega1.id}', format='json')
        self.assertEqual(response.status_code, 200)
        
        data = response.data
        if 'results' in data:
            data = data['results']
        
        # Deben estar m1, m3, m4
        ids = [m['id'] for m in data]
        self.assertIn(self.m1.id, ids)
        self.assertIn(self.m3.id, ids)
        self.assertIn(self.m4.id, ids)
        self.assertNotIn(self.m2.id, ids)

    def test_filter_by_producto(self):
        response = self.client.get(f'/api/inventory/movimientos/?producto_id={self.producto1.id}', format='json')
        
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        ids = [m['id'] for m in data]
        
        # Deben estar m1, m2, m4
        self.assertIn(self.m1.id, ids)
        self.assertIn(self.m2.id, ids)
        self.assertIn(self.m4.id, ids)
        self.assertNotIn(self.m3.id, ids)

    def test_filter_by_tipo_entrada(self):
        response = self.client.get('/api/inventory/movimientos/?tipo=entrada', format='json')
        
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        ids = [m['id'] for m in data]
        
        # Todas las compras (m1, m2, m3)
        self.assertIn(self.m1.id, ids)
        self.assertIn(self.m2.id, ids)
        self.assertIn(self.m3.id, ids)
        self.assertNotIn(self.m4.id, ids)

    def test_filter_by_tipo_salida(self):
        response = self.client.get('/api/inventory/movimientos/?tipo=salida', format='json')
        
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        ids = [m['id'] for m in data]
        
        # Solo m4
        self.assertEqual(len(ids), 1)
        self.assertIn(self.m4.id, ids)

    def test_filter_by_tipo_entrada_and_bodega(self):
        response = self.client.get(f'/api/inventory/movimientos/?tipo=entrada&bodega_id={self.bodega1.id}', format='json')
        
        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        ids = [m['id'] for m in data]
        
        # Entradas en bodega 1 (m1, m3)
        self.assertIn(self.m1.id, ids)
        self.assertIn(self.m3.id, ids)
        self.assertNotIn(self.m2.id, ids)
        self.assertNotIn(self.m4.id, ids)
