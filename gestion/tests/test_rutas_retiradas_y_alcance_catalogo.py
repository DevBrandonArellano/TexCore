"""
Fase B (spec 2026-09-29 §7): rutas del backend retiradas por no tener
consumidor en el frontend, y copias de la regla de sede unificadas.

- Las rutas retiradas responden 404: alias `quimicos/`, `detalle-formulas/`,
  `detalles-pedido/` y el flujo de subprocesos anterior a MES. Sus escrituras
  esquivaban el alcance por sede y, en las fórmulas, el versionado.
- Usuarios y catálogo usan los helpers únicos: un usuario sin sede no ve los
  usuarios sin sede, y no modifica los productos globales (sin sede).

Técnicas ISTQB: partición de equivalencia por ruta (retirada / vigente) y
valores límite (usuario sin sede).
"""
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import Producto
from gestion.tests.factories import CustomUserFactory, ProductoFactory, SedeFactory

RUTAS_RETIRADAS = (
    '/api/quimicos/',
    '/api/detalle-formulas/',
    '/api/detalles-pedido/',
    '/api/area-process-steps/',
    '/api/ordenes-produccion-subprocesos/',
)


class RutasRetiradasTestCase(TestCase):

    def test_rutas_retiradas_dado_admin_sistemas_cuando_get_o_post_entonces_404(self):
        client = APIClient()
        client.force_authenticate(user=CustomUserFactory(groups=['admin_sistemas']))
        for ruta in RUTAS_RETIRADAS:
            with self.subTest(ruta=ruta):
                self.assertEqual(client.get(ruta).status_code, 404)
                self.assertEqual(client.post(ruta, {}, format='json').status_code, 404)

    def test_chemicals_dado_admin_sistemas_cuando_get_entonces_sigue_disponible(self):
        client = APIClient()
        client.force_authenticate(user=CustomUserFactory(groups=['admin_sistemas']))
        self.assertEqual(client.get('/api/chemicals/').status_code, 200)


class DetallesSinConsumidorRetiradosTestCase(TestCase):
    """Fase B, B6: detalle REST que ninguna pantalla, microservicio ni prueba de
    carga usaba; los listados siguen disponibles."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=CustomUserFactory(groups=['admin_sistemas']))

    def test_detalles_dado_admin_sistemas_cuando_get_entonces_404_y_el_listado_sigue(self):
        for base in ('/api/inventory/stock/', '/api/inventory/audit-logs/', '/api/procesos-tintoreria/',
                     '/api/operaciones-produccion/'):
            with self.subTest(base=base):
                self.assertEqual(self.client.get(f'{base}1/').status_code, 404)
                self.assertEqual(self.client.get(base).status_code, 200)


class AlcanceUsuariosYCatalogoTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()

    def test_usuarios_dado_admin_sede_sin_sede_cuando_lista_entonces_no_ve_usuarios_sin_sede(self):
        sin_sede = CustomUserFactory(sede=None, groups=['operario'])
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=['admin_sede']))
        datos = self.client.get('/api/users/').data
        filas = datos['results'] if isinstance(datos, dict) else datos
        self.assertNotIn(sin_sede.id, {u['id'] for u in filas})

    def test_producto_global_dado_bodeguero_sin_sede_cuando_edita_entonces_404_y_no_cambia(self):
        global_ = ProductoFactory(sede=None, descripcion='Global original')
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=['bodeguero']))
        resp = self.client.patch(f'/api/productos/{global_.id}/', {'descripcion': 'Alterado'}, format='json')
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Producto.objects.get(pk=global_.pk).descripcion, 'Global original')

    def test_producto_global_dado_bodeguero_con_sede_cuando_lista_entonces_lo_ve(self):
        global_ = ProductoFactory(sede=None)
        ajeno = ProductoFactory(sede=SedeFactory())
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=['bodeguero']))
        datos = self.client.get('/api/productos/').data
        ids = {p['id'] for p in (datos['results'] if isinstance(datos, dict) else datos)}
        self.assertIn(global_.id, ids)
        self.assertNotIn(ajeno.id, ids)
