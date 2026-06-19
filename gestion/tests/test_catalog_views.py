"""
Pruebas de gestion/views/catalog_views.py — ChemicalViewSet, ProductoViewSet, ProveedorViewSet.

Cubre el filtrado por tipo, la seguridad multi-tenant (sede) y el filtro de
seguridad que impide a los vendedores ver químicos/insumos.

Técnicas ISTQB aplicadas:
- Particiones de equivalencia (EP): tipo de producto, rol del usuario.
- Tabla de decisión / caja blanca: ramas de get_queryset y get_permissions.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, AreaFactory, CustomUserFactory, ProductoFactory, ProveedorFactory,
)


class ChemicalViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        self.insumo = ProductoFactory(tipo='insumo', sede=self.sede)
        self.hilo = ProductoFactory(tipo='hilo', sede=self.sede)
        self.url = reverse('chemical-list')

    def test_chemical_dado_autenticado_cuando_lista_entonces_solo_quimicos_e_insumos(self):
        # EP: el queryset filtra tipo in (quimico, insumo) — excluye hilo
        user = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tipos = {item['tipo'] for item in resp.data}
        self.assertTrue(tipos.issubset({'quimico', 'insumo'}))
        self.assertEqual(len(resp.data), 2)

    def test_chemical_dado_no_admin_cuando_crea_entonces_403(self):
        user = CustomUserFactory(sede=self.sede, groups=['tintorero'])
        self.client.force_authenticate(user=user)
        resp = self.client.post(self.url, {'codigo': 'Q1', 'descripcion': 'X',
                                'tipo': 'quimico', 'unidad_medida': 'kg'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class ProductoViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.tela = ProductoFactory(tipo='tela', sede=self.sede)
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede)
        self.url = reverse('producto-list')

    def test_producto_dado_vendedor_cuando_lista_entonces_excluye_quimicos(self):
        # Caja blanca: filtro de seguridad para vendedores (solo hilo/tela/subproducto)
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.client.force_authenticate(user=vendedor)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        tipos = {item['tipo'] for item in resp.data}
        self.assertNotIn('quimico', tipos)

    def test_producto_dado_filtro_tipo_cuando_lista_entonces_filtra(self):
        # EP: query param tipo=tela
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url, {'tipo': 'tela'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(all(item['tipo'] == 'tela' for item in resp.data))

    def test_producto_dado_admin_cuando_elimina_con_justificacion_entonces_204(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.delete(
            reverse('producto-detail', args=[self.tela.id]),
            HTTP_X_JUSTIFICACION_AUDITORIA='Producto descontinuado'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class AreaViewSetTestCase(TestCase):
    """
    Pruebas para AreaViewSet.

    Cubre la ausencia de paginación (pagination_class=None), el acceso
    autenticado y el filtrado por sede_id.

    Técnicas ISTQB aplicadas:
    - Caja blanca: response es array plano (no envelope {count, results}).
    - Particiones de equivalencia (EP): sin filtro vs. filtro sede_id.
    """

    def setUp(self):
        self.client = APIClient()
        self.sede1 = SedeFactory()
        self.sede2 = SedeFactory()
        self.area1 = AreaFactory(sede=self.sede1)
        self.area2 = AreaFactory(sede=self.sede1)
        self.area3 = AreaFactory(sede=self.sede2)
        # List action solo requiere IsAuthenticated — cualquier usuario sirve
        self.user = CustomUserFactory(sede=self.sede1)
        self.client.force_authenticate(user=self.user)
        self.url = reverse('area-list')

    def test_area_dado_autenticado_cuando_lista_entonces_respuesta_es_array_plano(self):
        # Caja blanca: pagination_class=None → lista plana, no objeto {count, results, …}
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_area_dado_sin_filtro_cuando_lista_entonces_devuelve_todas_las_areas(self):
        # EP: sin query params → todas las áreas de la base de datos
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in resp.data}
        self.assertIn(self.area1.id, ids)
        self.assertIn(self.area2.id, ids)
        self.assertIn(self.area3.id, ids)

    def test_area_dado_filtro_sede_id_cuando_lista_entonces_solo_areas_de_esa_sede(self):
        # EP: sede_id=sede1 incluye area1/area2, excluye area3 (pertenece a sede2)
        resp = self.client.get(self.url, {'sede_id': self.sede1.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {item['id'] for item in resp.data}
        self.assertIn(self.area1.id, ids)
        self.assertIn(self.area2.id, ids)
        self.assertNotIn(self.area3.id, ids)

    def test_area_dado_no_autenticado_cuando_lista_entonces_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class ProveedorViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.proveedor = ProveedorFactory(sede=self.sede)
        self.url = reverse('proveedor-list')

    def test_proveedor_dado_autenticado_cuando_lista_entonces_200(self):
        user = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_proveedor_dado_admin_cuando_crea_entonces_201(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(self.url, {'nombre': 'Nuevo Proveedor', 'sede': self.sede.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")

    def test_proveedor_dado_no_admin_cuando_crea_entonces_403(self):
        # Caja blanca: escritura exige IsSystemAdmin
        user = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=user)
        resp = self.client.post(self.url, {'nombre': 'X', 'sede': self.sede.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
