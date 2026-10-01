"""
Pruebas de endpoints de inventory/views.py no cubiertos por la suite previa:
StockBodegaViewSet, TransferenciaStockAPIView, AlertasStockAPIView, KardexBodegaAPIView.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: ramas RBAC de get_queryset (admin vs bodeguero)
  y ramas de validación de la transferencia (stock insuficiente, sin stock).
- Particiones de equivalencia (EP): stock suficiente / insuficiente / inexistente.
- Análisis de valores límite (BVA): stock = cantidad solicitada (transferencia exacta).
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import MovimientoInventario
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory,
    StockBodegaFactory, AreaFactory, OrdenProduccionFactory, LoteProduccionFactory,
)


class StockBodegaViewSetTestCase(TestCase):
    """Caja blanca de get_queryset: admin ve todo, bodeguero solo asignadas."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega1 = BodegaFactory(sede=self.sede)
        self.bodega2 = BodegaFactory(sede=self.sede)
        self.s1 = StockBodegaFactory(bodega=self.bodega1, producto=ProductoFactory(sede=self.sede))
        self.s2 = StockBodegaFactory(bodega=self.bodega2, producto=ProductoFactory(sede=self.sede))
        self.url = '/api/inventory/stock/'

    def test_stock_dado_admin_cuando_lista_entonces_ve_todo(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_stock_dado_bodeguero_cuando_lista_entonces_solo_asignadas(self):
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        bodeguero.bodegas_asignadas.add(self.bodega1)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_stock_dado_filtro_sede_cuando_lista_entonces_filtra(self):
        otra_sede = SedeFactory()
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url, {'sede_id': otra_sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


class TransferenciaStockAPIViewTestCase(TestCase):
    """Caja blanca de la transferencia atómica entre bodegas."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.origen = BodegaFactory(sede=self.sede)
        self.destino = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.user)
        self.url = '/api/inventory/transferencias/'

    def _stock_origen(self, cantidad):
        return StockBodegaFactory(bodega=self.origen, producto=self.producto, cantidad=Decimal(cantidad))

    def test_transferencia_dado_stock_suficiente_cuando_post_entonces_200(self):
        self._stock_origen('100.00')
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '30.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")

    def test_transferencia_dado_origen_igual_destino_cuando_post_entonces_400(self):
        # Caja negra: validate() rechaza origen == destino
        self._stock_origen('100.00')
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.origen.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transferencia_dado_stock_insuficiente_cuando_post_entonces_400(self):
        # EP: cantidad solicitada > disponible
        self._stock_origen('10.00')
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '50.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transferencia_dado_sin_stock_en_origen_cuando_post_entonces_404(self):
        # Caja blanca: rama StockBodega.DoesNotExist -> 404
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '5.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_transferencia_dado_sin_autenticar_cuando_post_entonces_401(self):
        # La vista declara permission_classes = [IsInventoryWriterOrAdmin]
        # (inventory/views/transferencia_views.py), que rechaza por sí mismo al
        # usuario no autenticado (inventory/permissions.py): anónimo → 401.
        self.client.force_authenticate(user=None)
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_transferencia_dado_vendedor_cuando_post_entonces_403(self):
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.client.force_authenticate(user=vendedor)
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_transferencia_dado_error_inesperado_cuando_post_entonces_queda_logueado(self):
        self._stock_origen('100.00')
        with patch('inventory.views.transferencia_views.logger') as mock_logger:
            with patch(
                'inventory.views.transferencia_views.safe_get_or_create_stock',
                side_effect=RuntimeError('fallo simulado'),
            ):
                resp = self.client.post(self.url, {
                    'producto_id': self.producto.id, 'cantidad': '10.00',
                    'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
                }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        mock_logger.error.assert_called_once()


class AlertasStockAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        # Producto con stock_minimo=10 (default factory) y stock por debajo
        self.producto = ProductoFactory(sede=self.sede, stock_minimo=Decimal('10.000'))
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, cantidad=Decimal('5.000'))
        self.url = '/api/inventory/alertas-stock/'

    def test_alertas_dado_stock_bajo_minimo_cuando_get_entonces_lo_lista(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['faltante'], Decimal('5.000'))

    def test_alertas_dado_bodeguero_sin_asignacion_cuando_get_entonces_vacio(self):
        # Caja blanca: bodeguero sin bodegas asignadas no ve alertas ajenas
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


class KardexBodegaAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.user)

    def test_kardex_dado_sin_producto_id_cuando_get_entonces_400(self):
        # Caja blanca: producto_id obligatorio
        resp = self.client.get(f'/api/inventory/bodegas/{self.bodega.id}/kardex/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kardex_dado_sin_autenticar_cuando_get_entonces_401(self):
        # La vista declara permission_classes = [IsInventoryStaffOrAdmin]
        # (inventory/views/kardex_views.py), que rechaza por sí mismo al usuario
        # no autenticado (inventory/permissions.py): anónimo → 401.
        self.client.force_authenticate(user=None)
        producto = ProductoFactory(sede=self.sede)
        resp = self.client.get(f'/api/inventory/bodegas/{self.bodega.id}/kardex/', {'producto_id': producto.id})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Contrato paginado (RNF-03 · TEX-22): el saldo viaja con cada página ---
    def _entradas(self, producto, n, cantidad='10.000'):
        MovimientoInventario.objects.bulk_create([
            MovimientoInventario(
                tipo_movimiento='COMPRA', producto=producto,
                bodega_destino=self.bodega, cantidad=Decimal(cantidad),
            ) for _ in range(n)
        ])

    def _get(self, producto, **params):
        return self.client.get(
            f'/api/inventory/bodegas/{self.bodega.id}/kardex/', {'producto_id': producto.id, **params})

    def test_kardex_dado_producto_cuando_get_entonces_pagina_con_saldo_inicial_y_resultados(self):
        producto = ProductoFactory(sede=self.sede)
        self._entradas(producto, 3)
        resp = self._get(producto)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['count'], 3)
        self.assertEqual(resp.data['saldo_inicial'], Decimal('0'))
        fila = resp.data['results'][0]
        self.assertEqual(fila['tipo_movimiento'], 'COMPRA')
        self.assertEqual(fila['tipo_movimiento_display'], 'Compra de Material')
        self.assertEqual(fila['entrada'], Decimal('10.000'))
        self.assertEqual(fila['saldo'], Decimal('10.000'))
        self.assertEqual(fila['bodega_destino_nombre'], self.bodega.nombre)
        self.assertEqual(fila['usuario'], 'Sistema')

    def test_kardex_dado_pagina_2_cuando_get_entonces_el_saldo_continua_desde_la_pagina_1(self):
        producto = ProductoFactory(sede=self.sede)
        self._entradas(producto, 5)
        resp = self._get(producto, page=2, page_size=2)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual([f['saldo'] for f in resp.data['results']], [Decimal('30.000'), Decimal('40.000')])

    def test_kardex_dado_page_size_en_el_maximo_cuando_get_entonces_lo_respeta(self):
        # BVA: 500 es el máximo permitido.
        producto = ProductoFactory(sede=self.sede)
        self._entradas(producto, 501, cantidad='1.000')
        resp = self._get(producto, page_size=500)
        self.assertEqual(len(resp.data['results']), 500)

    def test_kardex_dado_page_size_sobre_el_maximo_cuando_get_entonces_lo_limita(self):
        # BVA: 501 se recorta a 500 — un cliente no puede pedir el historial entero de una vez.
        producto = ProductoFactory(sede=self.sede)
        self._entradas(producto, 502, cantidad='1.000')
        resp = self._get(producto, page_size=501)
        self.assertEqual(len(resp.data['results']), 500)
        self.assertEqual(resp.data['results'][-1]['saldo'], Decimal('500.000'))

    def test_kardex_dado_fecha_invalida_cuando_get_entonces_400(self):
        producto = ProductoFactory(sede=self.sede)
        resp = self._get(producto, fecha_inicio='2026-13-45')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kardex_dado_tipo_invalido_cuando_get_entonces_400(self):
        producto = ProductoFactory(sede=self.sede)
        resp = self._get(producto, tipo='transferencia')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kardex_dado_usuario_con_nombre_cuando_get_entonces_muestra_nombre_completo(self):
        producto = ProductoFactory(sede=self.sede)
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=producto, bodega_destino=self.bodega,
            cantidad=Decimal('1.000'), usuario=self.user,
        )
        resp = self._get(producto)
        self.assertEqual(resp.data['results'][0]['usuario'], self.user.get_full_name())


class KardexBodegaRendimientoTestCase(TestCase):
    """
    RNF-03 · TEX-22 CA-3 — el kárdex responde en menos de 3000 ms.

    IMPORTANTE — qué mide y qué NO mide este test: usa APIClient (llamada
    in-process, sin red real) contra SQLite en memoria (settings_test_local),
    así que mide el costo propio de Django + DRF + KardexBodegaAPIView sobre
    un volumen sembrado: permisos, las consultas ORM (saldo inicial con SUM,
    saldo corrido con SUM() OVER, COUNT y la página) y la serialización JSON de
    la página. Se pide la ÚLTIMA página: es el peor caso del OFFSET. NO
    incluye el salto de red real a través de Nginx, ni Gunicorn, ni la
    latencia ni el plan de ejecución de SQL Server 2022 en producción.

    Es un PISO de referencia (si esto ya no está bajo 3 s in-process, el
    sistema real tampoco lo estará) — no el número que importa en planta. Su
    valor está en detectar regresiones. De las dos aserciones, la que de
    verdad protege el umbral es el techo de consultas: es determinista entre
    máquinas y detecta el N+1 que, con volumen real en SQL Server, convierte
    miles de filas en miles de viajes a la base. La medición end-to-end bajo
    carga vive en scripts/loadtest/locustfile.py (fila "/api/inventory/
    bodegas/[id]/kardex/ (RNF-03)").
    """

    UMBRAL_SEGUNDOS = 3.0
    MOVIMIENTOS_POR_SENTIDO = 2500  # 5000 movimientos del producto en la bodega

    # Techo de consultas del GET completo. Son exactamente estas:
    #   1. IsInventoryStaffOrAdmin: user.groups.filter(...).exists()
    #   2. bodegas_visibles: grupos del usuario (autorización por bodega, OWASP A01)
    #   3. get_object_or_404(Bodega) sobre las bodegas visibles
    #   4. get_object_or_404(Producto)
    #   5. saldo inicial: un SUM(CASE ...) sobre los movimientos previos al rango
    #   6. COUNT(*) del paginador
    #   7. la página: values() con sus JOIN y el saldo corrido en ventana
    # Ninguna depende del número de filas: leer una FK fuera del values() o
    # volver a iterar el historial en Python dispara miles de consultas o de
    # filas, y esta aserción falla sin depender del reloj de la máquina.
    MAX_CONSULTAS = 7
    TAMANO_PAGINA = 50

    @classmethod
    def setUpTestData(cls):
        from datetime import timedelta
        from django.utils import timezone
        from gestion.models import Proveedor

        cls.sede = SedeFactory()
        cls.bodega = BodegaFactory(sede=cls.sede)
        otra_bodega = BodegaFactory(sede=cls.sede)
        cls.producto = ProductoFactory(sede=cls.sede)
        otro_producto = ProductoFactory(sede=cls.sede)
        cls.admin = CustomUserFactory(sede=cls.sede, groups=['admin_sistemas'])

        # Variedad real en las FK que se leen en el bucle: si hubiera N+1,
        # cada fila dispararía consultas distintas (no cacheables).
        usuarios = [CustomUserFactory(sede=cls.sede) for _ in range(20)]
        proveedores = [
            Proveedor.objects.create(nombre=f'Proveedor RNF03 {i}', sede=cls.sede)
            for i in range(20)
        ]
        area = AreaFactory(sede=cls.sede)
        op = OrdenProduccionFactory(sede=cls.sede, area=area)
        lotes = [LoteProduccionFactory(orden_produccion=op) for _ in range(20)]

        movimientos = []
        for i in range(cls.MOVIMIENTOS_POR_SENTIDO):
            movimientos.append(MovimientoInventario(
                tipo_movimiento='COMPRA', producto=cls.producto,
                bodega_destino=cls.bodega, cantidad=Decimal('10.000'),
                proveedor=proveedores[i % 20], usuario=usuarios[i % 20],
                documento_ref=f'FAC-{i:05d}',
            ))
            movimientos.append(MovimientoInventario(
                tipo_movimiento='CONSUMO', producto=cls.producto,
                bodega_origen=cls.bodega, cantidad=Decimal('4.000'),
                lote=lotes[i % 20], usuario=usuarios[(i + 7) % 20],
            ))
        # Ruido que el filtro debe descartar: otro producto y otra bodega.
        movimientos += [
            MovimientoInventario(
                tipo_movimiento='COMPRA', producto=otro_producto,
                bodega_destino=cls.bodega, cantidad=Decimal('1.000'),
            ) for _ in range(1000)
        ]
        movimientos += [
            MovimientoInventario(
                tipo_movimiento='COMPRA', producto=cls.producto,
                bodega_destino=otra_bodega, cantidad=Decimal('1.000'),
            ) for _ in range(1000)
        ]
        MovimientoInventario.objects.bulk_create(movimientos, batch_size=500)

        # auto_now_add fija la misma fecha a todo el bulk: se reparte en 100
        # días para que el rango de fechas y el saldo inicial tengan trabajo.
        ids = list(MovimientoInventario.objects.order_by('id').values_list('id', flat=True))
        base = timezone.now() - timedelta(days=100)
        tramo = len(ids) // 100 + 1
        for dia in range(100):
            MovimientoInventario.objects.filter(
                id__in=ids[dia * tramo:(dia + 1) * tramo]
            ).update(fecha=base + timedelta(days=dia))
        cls.fecha_inicio = (base + timedelta(days=20)).date().isoformat()
        cls.fecha_fin = (base + timedelta(days=99)).date().isoformat()

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_kardex_dado_5000_movimientos_cuando_pide_ultima_pagina_entonces_bajo_3s_y_consultas_acotadas(self):
        import math
        from time import perf_counter
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        url = f'/api/inventory/bodegas/{self.bodega.id}/kardex/'
        params = {'producto_id': self.producto.id, 'page_size': self.TAMANO_PAGINA,
                  'fecha_inicio': self.fecha_inicio, 'fecha_fin': self.fecha_fin}
        total = self.client.get(url, params).data['count']
        # Sanidad del volumen: la medición solo vale si el rango tiene miles de filas.
        self.assertGreater(total, 3000)
        ultima = math.ceil(total / self.TAMANO_PAGINA)

        with CaptureQueriesContext(connection) as consultas:
            inicio = perf_counter()
            resp = self.client.get(url, {**params, 'page': ultima})
            duracion = perf_counter() - inicio

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(resp.data['results']), self.TAMANO_PAGINA)
        self.assertLessEqual(len(consultas), self.MAX_CONSULTAS, (
            f"TEX-22 CA-3 (RNF-03): el kárdex ejecutó {len(consultas)} consultas "
            f"(techo {self.MAX_CONSULTAS}) — probable N+1 que degrada el umbral "
            f"de {self.UMBRAL_SEGUNDOS}s con volumen real en SQL Server."
        ))
        self.assertLess(duracion, self.UMBRAL_SEGUNDOS, (
            f"TEX-22 CA-3 (RNF-03): el kárdex tardó {duracion:.3f}s en servir la "
            f"página {ultima} de {total} filas (in-process, sin red) — supera el umbral "
            f"de {self.UMBRAL_SEGUNDOS}s."
        ))


class RetroKardexAPIViewScopingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.producto = ProductoFactory(sede=self.sede)
        self.bodega_a = BodegaFactory(sede=self.sede)
        self.bodega_b = BodegaFactory(sede=self.sede)
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto,
            bodega_destino=self.bodega_a, cantidad=Decimal('10.000'),
        )
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto,
            bodega_destino=self.bodega_b, cantidad=Decimal('20.000'),
        )

    def test_retro_kardex_dado_bodeguero_sin_bodega_b_asignada_cuando_get_entonces_no_ve_bodega_b(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        bodeguero.bodegas_asignadas.add(self.bodega_a)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(reverse('retro-kardex'), {
            'producto_id': self.producto.id, 'fecha_corte': '2026-12-31',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        bodegas_vistas = {r['bodega'] for r in resp.data}
        self.assertIn(self.bodega_a.nombre, bodegas_vistas)
        self.assertNotIn(self.bodega_b.nombre, bodegas_vistas)

    def test_retro_kardex_dado_admin_cuando_get_entonces_ve_todas_las_bodegas(self):
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('retro-kardex'), {
            'producto_id': self.producto.id, 'fecha_corte': '2026-12-31',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        bodegas_vistas = {r['bodega'] for r in resp.data}
        self.assertIn(self.bodega_a.nombre, bodegas_vistas)
        self.assertIn(self.bodega_b.nombre, bodegas_vistas)

    def test_retro_kardex_dado_operario_raso_cuando_get_entonces_403(self):
        operario = CustomUserFactory(groups=['operario'], sede=self.sede)
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('retro-kardex'), {
            'producto_id': self.producto.id, 'fecha_corte': '2026-12-31',
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class MovimientosPorLoteAPIViewScopingTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.bodega_a = BodegaFactory(sede=self.sede)
        self.bodega_b = BodegaFactory(sede=self.sede)
        self.op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.lote = LoteProduccionFactory(orden_produccion=self.op)
        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION', producto=self.op.producto_salida,
            bodega_destino=self.bodega_a, cantidad=Decimal('5.000'), lote=self.lote,
        )

    def test_movimientos_por_lote_dado_bodeguero_sin_bodega_a_asignada_cuando_get_entonces_historial_vacio(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        bodeguero.bodegas_asignadas.add(self.bodega_b)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(reverse('movimientos-lote', args=[self.lote.codigo_lote]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['historial'], [])

    def test_movimientos_por_lote_dado_bodeguero_con_bodega_a_asignada_cuando_get_entonces_ve_movimiento(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        bodeguero.bodegas_asignadas.add(self.bodega_a)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(reverse('movimientos-lote', args=[self.lote.codigo_lote]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['historial']), 1)
