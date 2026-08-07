from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
User = get_user_model()
from gestion.models import Cliente, PedidoVenta, DetallePedido, Producto, Sede
from decimal import Decimal
import logging

class PedidoVentaOptimizationTest(TestCase):
    """
    Pruebas ISTQB (Caja Negra y Caja Blanca) enfocadas en Rendimiento (ISO 25010).
    Asegura que el listado de Pedidos no genere problemas N+1 queries al cargar detalles,
    maximizando la eficiencia en base de datos.
    """
    def setUp(self):
        self.client = APIClient()
        self.sede = Sede.objects.create(nombre="Sede Principal", location="Quito")
        self.user = User.objects.create_user(username="test_admin", password="password")
        self.user.sede = self.sede
        self.user.save()
        grupo_admin, _ = Group.objects.get_or_create(name='admin_sistemas')
        self.user.groups.add(grupo_admin)

        self.cliente = Cliente.objects.create(
            ruc_cedula="1234567890",
            nombre_razon_social="Cliente Test",
            direccion_envio="Av Siempre Viva",
            nivel_precio="normal",
            sede=self.sede
        )
        self.producto = Producto.objects.create(
            codigo="PROD1",
            descripcion="Hilo de Algodon",
            tipo="hilo",
            unidad_medida="kg",
            precio_base=10.0
        )

        # Crear 10 pedidos con 5 detalles cada uno
        for i in range(10):
            pedido = PedidoVenta.objects.create(
                cliente=self.cliente,
                sede=self.sede,
                vendedor_asignado=self.user,
                guia_remision=f"GR-{i:04d}",
                estado='pendiente'
            )
            for j in range(5):
                DetallePedido.objects.create(
                    pedido_venta=pedido,
                    producto=self.producto,
                    cantidad=1,
                    piezas=1,
                    peso=Decimal('10.00'),
                    precio_unitario=Decimal('10.00')
                )
        
        self.client.force_authenticate(user=self.user)

    def test_pedidos_list_n_plus_one_queries(self):
        """
        Prueba de optimización: Al listar los pedidos, Django REST no debe
        realizar queries adicionales por cada detalle, asegurando una complejidad O(1)
        en el número de consultas independientemente de la cantidad de registros (prefetch_related).
        """
        # La primera query inicializa caches y auth, por lo que primero hacemos una request warmup
        self.client.get('/api/v1/pedidos-venta/?limit=5', HTTP_ACCEPT='application/json')

        # Ahora probamos con assertNumQueries
        # Consultas esperadas (aprox): 
        # 1 para el usuario (auth)
        # 1 para el count de pedidos (paginacion)
        # 1 para PedidoVenta
        # 1 para prefetch de Detalles
        # TOTAL esperado: < 10 queries, NO ~50 queries.
        with self.assertNumQueriesLessThan(15):
            response = self.client.get('/api/v1/pedidos-venta/?limit=10', HTTP_ACCEPT='application/json')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data['results']), 10)

    def assertNumQueriesLessThan(self, num):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        class LessThanQueriesContext(CaptureQueriesContext):
            def __exit__(self, exc_type, exc_value, traceback):
                super().__exit__(exc_type, exc_value, traceback)
                if exc_type is not None:
                    return
                executed = len(self)
                if executed >= num:
                    self.test_case.fail(
                        f"{executed} queries executed, {num} or more expected to not be exceeded."
                    )
        
        context = LessThanQueriesContext(connection)
        context.test_case = self
        return context

    def test_pedidos_list_filtros_vendedor_y_sede(self):
        """
        Prueba ISTQB: Cobertura de filtros por vendedor_id, vendedor_username, sede_id y limit inválido.
        """
        res_vendedor_id = self.client.get(f'/api/v1/pedidos-venta/?vendedor_id={self.user.id}', HTTP_ACCEPT='application/json')
        self.assertEqual(res_vendedor_id.status_code, 200)

        res_vendedor_inv = self.client.get('/api/v1/pedidos-venta/?vendedor_id=invalido', HTTP_ACCEPT='application/json')
        self.assertEqual(res_vendedor_inv.status_code, 200)

        res_vendedor_user = self.client.get(f'/api/v1/pedidos-venta/?vendedor_username={self.user.username}', HTTP_ACCEPT='application/json')
        self.assertEqual(res_vendedor_user.status_code, 200)

        res_sede = self.client.get(f'/api/v1/pedidos-venta/?sede_id={self.sede.id}', HTTP_ACCEPT='application/json')
        self.assertEqual(res_sede.status_code, 200)

        res_limit_inv = self.client.get('/api/v1/pedidos-venta/?limit=invalido', HTTP_ACCEPT='application/json')
        self.assertEqual(res_limit_inv.status_code, 200)

    def test_clientes_list_filtros_vendedor(self):
        """
        Prueba ISTQB: Cobertura de filtros de clientes por vendedor_id, vendedor_username y valores inválidos.
        """
        res_vendedor_id = self.client.get(f'/api/v1/clientes/?vendedor_id={self.user.id}', HTTP_ACCEPT='application/json')
        self.assertEqual(res_vendedor_id.status_code, 200)

        res_vendedor_inv = self.client.get('/api/v1/clientes/?vendedor_id=invalido', HTTP_ACCEPT='application/json')
        self.assertEqual(res_vendedor_inv.status_code, 200)

        res_vendedor_user = self.client.get(f'/api/v1/clientes/?vendedor_username={self.user.username}', HTTP_ACCEPT='application/json')
        self.assertEqual(res_vendedor_user.status_code, 200)

        res_sede = self.client.get(f'/api/v1/clientes/?sede_id={self.sede.id}', HTTP_ACCEPT='application/json')
        self.assertEqual(res_sede.status_code, 200)


