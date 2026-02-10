from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from decimal import Decimal
from gestion.models import Sede, Cliente, PedidoVenta, DetallePedido, Producto, CustomUser, Bodega
from inventory.models import StockBodega, MovimientoInventario

class UnifiedBusinessLogicTestCase(APITestCase):
    """
    Suite única de pruebas para validar el funcionamiento del sistema TexCore.
    Cubre: Ventas, Crédito, Auditoría de Precios e Inventario.
    """
    def setUp(self):
        # 1. Configuración de Entorno (Sede y Grupos)
        self.sede = Sede.objects.create(nombre="Sede Central", location="Quito")
        self.vendedor_group, _ = Group.objects.get_or_create(name='vendedor')
        self.admin_group, _ = Group.objects.get_or_create(name='admin_sistemas')
        
        # Otorgar permisos a los grupos
        for model in [Cliente, PedidoVenta, DetallePedido, MovimientoInventario]:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            self.vendedor_group.permissions.add(*permissions)
            self.admin_group.permissions.add(*permissions)

        # 2. Configuración de Usuarios
        self.vendedor = CustomUser.objects.create_user(
            username='vendedor1', password='password@123', sede=self.sede
        )
        self.vendedor.groups.add(self.vendedor_group)
        
        self.vendedor2 = CustomUser.objects.create_user(
            username='vendedor2', password='password@123', sede=self.sede
        )
        self.vendedor2.groups.add(self.vendedor_group)

        self.admin = CustomUser.objects.create_user(
            username='adminuser', password='password@123', sede=self.sede
        )
        self.admin.groups.add(self.admin_group)
        
        # 3. Configuración de Catálogo e Inventario
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="P001", descripcion="Tela Premium", tipo="tela", 
            unidad_medida="metros", precio_base=Decimal('10.00')
        )
        # Stock inicial para pruebas de inventario
        StockBodega.objects.create(bodega=self.bodega, producto=self.producto, cantidad=Decimal('100.00'))
        
        # 4. Configuración de Clientes
        self.cliente = Cliente.objects.create(
            ruc_cedula="1234567890", nombre_razon_social="Cliente Test",
            direccion_envio="Direccion 1", nivel_precio="normal",
            limite_credito=Decimal('500.00'), vendedor_asignado=self.vendedor
        )

    # --- PRUEBAS DE VENTAS Y CRÉDITO ---

    def test_dynamic_balance_calculation(self):
        """Verifica que el saldo_pendiente se calcule correctamente según pedidos no pagados."""
        pedido = PedidoVenta.objects.create(cliente=self.cliente, guia_remision="G001", esta_pagado=False, sede=self.sede)
        DetallePedido.objects.create(pedido_venta=pedido, producto=self.producto, cantidad=10, piezas=1, peso=Decimal('10.00'), precio_unitario=Decimal('15.00'))
        
        # 10 * 15 = 150.00
        self.assertEqual(self.cliente.saldo_pendiente, Decimal('150.00'))
        
        # Al marcar como pagado, el saldo debe ser 0
        pedido.esta_pagado = True
        pedido.save()
        self.assertEqual(self.cliente.saldo_pendiente, Decimal('0.00'))

    def test_credit_limit_validation(self):
        """Asegura que un pedido nuevo no pueda exceder el límite de crédito."""
        self.client.force_authenticate(user=self.vendedor)
        url = reverse('pedidoventa-list')
        
        # El saldo actual es 0. Nuevo pedido: 40 * 15 = 600. Límite es 500.
        data = {
            'cliente': self.cliente.id,
            'guia_remision': 'G002',
            'sede': self.sede.id,
            'detalles': [
                {'producto': self.producto.id, 'cantidad': 40, 'piezas': 1, 'peso': 40.0, 'precio_unitario': 15.0}
            ]
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cliente', response.data)

    def test_price_base_validation(self):
        """Asegura que el precio unitario no sea menor al precio_base (costo)."""
        self.client.force_authenticate(user=self.vendedor)
        url = reverse('detallepedido-list')
        pedido = PedidoVenta.objects.create(cliente=self.cliente, guia_remision="GTEST", sede=self.sede)
        
        # precio_base es 10.00. Intentar vender a 9.00 debe fallar.
        data = {
            'pedido_venta': pedido.id,
            'producto': self.producto.id,
            'cantidad': 1,
            'piezas': 1,
            'peso': 1.0,
            'precio_unitario': 9.00
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('precio_unitario', response.data)

    def test_benefit_permission_security(self):
        """Verifica que solo vendedores/admins puedan cambiar el beneficio del cliente."""
        basic_user = CustomUser.objects.create_user(username='basic', password='password')
        url = reverse('cliente-detail', args=[self.cliente.id])
        
        # 1. Usuario básico falla
        self.client.force_authenticate(user=basic_user)
        response = self.client.patch(url, {'tiene_beneficio': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 2. Vendedor tiene éxito
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.patch(url, {'tiene_beneficio': True}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_salesman_filtering(self):
        """Verifica que los vendedores solo vean a sus clientes asignados."""
        cliente2 = Cliente.objects.create(
            ruc_cedula="0987654321", nombre_razon_social="Cliente 2",
            direccion_envio="Direccion 2", nivel_precio="normal",
            vendedor_asignado=self.vendedor2
        )
        
        url = reverse('cliente-list')
        
        # Vendedor 1 solo ve 1 cliente
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.cliente.id)

    # --- PRUEBAS DE INVENTARIO ---

    def test_precision_stock_update(self):
        """Valida que las actualizaciones de stock mantengan precisión decimal via API."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('movimiento-list')
        data = {
            'tipo_movimiento': 'VENTA',
            'producto': self.producto.id,
            'bodega_origen': self.bodega.id,
            'cantidad': '0.33',
            'documento_ref': 'REF1'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto)
        self.assertEqual(stock.cantidad, Decimal('99.67'))

    def test_saldo_resultante_kardex(self):
        """Valida que el saldo_resultante se calcule correctamente en el Kardex."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('movimiento-list')
        data = {
            'tipo_movimiento': 'VENTA',
            'producto': self.producto.id,
            'bodega_origen': self.bodega.id,
            'cantidad': '10.00',
            'documento_ref': 'REF2'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        mov = MovimientoInventario.objects.get(id=response.data['id'])
        self.assertEqual(mov.saldo_resultante, Decimal('90.00'))
