from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework.test import APIClient
from inventory.models import HistorialDespacho, DetalleHistorialDespacho, DetalleHistorialDespachoPedido
from gestion.models import Producto, Bodega, Sede, Cliente, PedidoVenta, OrdenProduccion, LoteProduccion
from inventory.serializers import HistorialDespachoSerializer

User = get_user_model()

class HistorialDespachoUnitTests(TestCase):
    def setUp(self):
        # Configurar ambiente básico
        self.user = User.objects.create_user(username='test_user', password='test_password')
        self.sede = Sede.objects.create(nombre="Sede Central", location="123 Calle")
        self.bodega = Bodega.objects.create(nombre="Bodega 1", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="PROD-01",
            descripcion="Producto Test",
            tipo="tela",
            unidad_medida="kg",
            precio_base=Decimal('15.00')
        )
        self.cliente = Cliente.objects.create(
            ruc_cedula="1234567890",
            nombre_razon_social="Cliente Uno", 
            direccion_envio="Av 1",
            nivel_precio="normal"
        )

        self.pedido = PedidoVenta.objects.create(
            cliente=self.cliente,
            fecha_vencimiento="2023-12-01",
            estado="pendiente",
            guia_remision="G-TEST-123",
            sede=self.sede
        )

        self.orden = OrdenProduccion.objects.create(
            codigo="OP-TEST",
            producto=self.producto,
            peso_neto_requerido=Decimal('20.00'),
            estado="en_proceso",
            bodega=self.bodega,
            sede=self.sede
        )

        self.lote = LoteProduccion.objects.create(
            codigo_lote="LOTE-TEST-001",
            peso_neto_producido=Decimal('20.00'),
            orden_produccion=self.orden,
            operario=self.user,
            turno="Mañana",
            hora_inicio="2023-01-01T08:00:00Z",
            hora_final="2023-01-01T10:00:00Z"
        )

        self.client = APIClient()

    def test_serializer_contains_expected_fields(self):
        """Prueba que el serializador contenga todos los campos requeridos con datos correctos"""
        historial = HistorialDespacho.objects.create(
            usuario=self.user,
            total_bultos=1,
            total_peso=Decimal('20.00'),
            observaciones="Observaciones unitarias"
        )

        DetalleHistorialDespacho.objects.create(
            historial=historial,
            lote=self.lote,
            producto=self.producto,
            peso=Decimal('20.00')
        )

        DetalleHistorialDespachoPedido.objects.create(
            historial=historial,
            pedido=self.pedido,
            cantidad_despachada=20
        )

        serializer = HistorialDespachoSerializer(instance=historial)
        data = serializer.data

        self.assertEqual(data['id'], historial.id)
        self.assertEqual(data['total_bultos'], 1)
        self.assertEqual(data['total_peso'], '20.00')
        self.assertEqual(data['usuario_nombre'], self.user.username)
        self.assertEqual(data['observaciones'], "Observaciones unitarias")

        # Serializadores anidados
        self.assertEqual(len(data['detalles']), 1)
        self.assertEqual(data['detalles'][0]['codigo_lote'], "LOTE-TEST-001")
        self.assertEqual(data['detalles'][0]['producto_nombre'], "Producto Test")

        self.assertEqual(len(data['pedidos_detalle']), 1)
        self.assertEqual(data['pedidos_detalle'][0]['guia_remision'], "G-TEST-123")
        self.assertEqual(data['pedidos_detalle'][0]['cliente_nombre'], "Cliente Uno")

    def test_api_view_filters_and_returns_data(self):
        """Prueba el endpoint del ViewSet"""
        self.client.force_authenticate(user=self.user)
        historial_h1 = HistorialDespacho.objects.create(
            usuario=self.user, total_bultos=1, total_peso=Decimal('10.00')
        )
        historial_h2 = HistorialDespacho.objects.create(
            usuario=self.user, total_bultos=2, total_peso=Decimal('30.00')
        )

        response = self.client.get('/api/inventory/historial-despachos/')
        self.assertEqual(response.status_code, 200)

        # Handle paginated or non-paginated response
        if isinstance(response.data, dict):
            results = response.data.get('results', [])
        else:
            results = response.data
            
        self.assertEqual(len(results), 2)
        
        # Debe venir ordenado por -fecha_despacho (h2 y h1)
        self.assertEqual(results[0]['id'], historial_h2.id)
        self.assertEqual(results[1]['id'], historial_h1.id)

    def test_api_view_unauthenticated(self):
        """Un usuario no autenticado no debe poder acceder al historial"""
        response = self.client.get('/api/inventory/historial-despachos/')
        self.assertEqual(response.status_code, 401)
