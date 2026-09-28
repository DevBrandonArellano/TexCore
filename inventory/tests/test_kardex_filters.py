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

    def test_listado_movimientos_dado_30_filas_con_sus_fk_cuando_get_entonces_consultas_no_crecen(self):
        # RNF-03: el serializador lee producto, lote, ambas bodegas (y su sede,
        # por Bodega.__str__), proveedor y usuario en cada fila. Techo fijo:
        # permiso + rol en get_queryset + COUNT + página con sus JOIN.
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from gestion.models import Proveedor
        from gestion.tests.factories import OrdenProduccionFactory, LoteProduccionFactory

        proveedor = Proveedor.objects.create(nombre='Prov N+1', sede=self.sede)
        lote = LoteProduccionFactory(orden_produccion=OrdenProduccionFactory(sede=self.sede))
        for _ in range(30):
            MovimientoInventario.objects.create(
                tipo_movimiento='TRANSFERENCIA', producto=self.producto1, cantidad=Decimal('1.00'),
                bodega_origen=self.bodega2, bodega_destino=self.bodega1,
                proveedor=proveedor, lote=lote, usuario=self.user,
            )

        with CaptureQueriesContext(connection) as consultas:
            response = self.client.get('/api/inventory/movimientos/', format='json')

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(consultas), 4, f'{len(consultas)} consultas: N+1 en el listado')

    def test_listado_movimientos_dado_page_size_cuando_get_entonces_lo_respeta_con_tope_de_500(self):
        # BVA: la pantalla del kárdex pagina en servidor con su propio tamaño; 501 se recorta.
        MovimientoInventario.objects.bulk_create([
            MovimientoInventario(tipo_movimiento='COMPRA', producto=self.producto1,
                                 bodega_destino=self.bodega1, cantidad=Decimal('1.00'))
            for _ in range(500)
        ])
        for pedido, esperado in ((2, 2), (500, 500), (501, 500)):
            with self.subTest(page_size=pedido):
                resp = self.client.get('/api/inventory/movimientos/', {'page_size': pedido})
                self.assertEqual(len(resp.data['results']), esperado)

    def test_filter_by_tipo_entrada_and_bodega(self):
        response = self.client.get(
            f'/api/inventory/movimientos/?tipo=entrada&bodega_id={self.bodega1.id}',
            format='json')

        data = response.data.get('results', response.data) if isinstance(response.data, dict) else response.data
        ids = [m['id'] for m in data]

        # Entradas en bodega 1 (m1, m3)
        self.assertIn(self.m1.id, ids)
        self.assertIn(self.m3.id, ids)
        self.assertNotIn(self.m2.id, ids)
        self.assertNotIn(self.m4.id, ids)
