"""
Pruebas complementarias de gestion/views/catalog_views.py — ramas que
test_catalog_views.py no ejercita: auto-asignación de sede en create,
multi-tenancy de ProductoViewSet/ProveedorViewSet, y las distintas fuentes
de justificación en perform_destroy.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): sede propia vs. ajena, producto sin sede
  (global) vs. con sede.
- Caja blanca: rama de fallback de sede en perform_create; las 3 fuentes de
  justificación en perform_destroy (query param, header, body, default).
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import Producto, Proveedor
from gestion.tests.factories import CustomUserFactory, ProductoFactory, ProveedorFactory, SedeFactory


class ChemicalViewSetExtraTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()

    def test_create_dado_admin_sin_sede_explicita_cuando_post_entonces_usa_sede_del_usuario(self):
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)

        resp = self.client.post(reverse('chemical-legacy-list'), {
            'codigo': 'QUIM-QA-1', 'descripcion': 'Quimico QA', 'tipo': 'quimico',
            'unidad_medida': 'kg', 'stock_minimo': '5.000', 'precio_base': '1.000',
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['sede'], self.sede.id)

    def test_list_dado_filtro_sede_id_cuando_get_entonces_filtra(self):
        otra_sede = SedeFactory()
        ProductoFactory(tipo='quimico', sede=self.sede)
        ProductoFactory(tipo='quimico', sede=otra_sede)

        user = CustomUserFactory(sede=self.sede)
        self.client.force_authenticate(user=user)

        resp = self.client.get(reverse('chemical-legacy-list'), {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)


class ProductoViewSetMultiTenancyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()

    def test_list_dado_usuario_de_sede_cuando_get_entonces_ve_su_sede_y_globales(self):
        producto_propio = ProductoFactory(sede=self.sede)
        producto_ajeno = ProductoFactory(sede=self.otra_sede)
        producto_global = ProductoFactory(sede=None)

        user = CustomUserFactory(groups=['bodeguero'], sede=self.sede)
        self.client.force_authenticate(user=user)

        resp = self.client.get(reverse('producto-list'))
        ids = {p['id'] for p in resp.data}

        self.assertIn(producto_propio.id, ids)
        self.assertIn(producto_global.id, ids)
        self.assertNotIn(producto_ajeno.id, ids)

    def test_list_dado_admin_sistemas_cuando_get_entonces_ve_todas_las_sedes(self):
        ProductoFactory(sede=self.sede)
        ProductoFactory(sede=self.otra_sede)

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('producto-list'))
        self.assertGreaterEqual(len(resp.data), 2)

    def test_create_dado_admin_sin_sede_explicita_cuando_post_entonces_usa_sede_del_usuario(self):
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)

        resp = self.client.post(reverse('producto-list'), {
            'codigo': 'PROD-QA-1', 'descripcion': 'Producto QA', 'tipo': 'hilo',
            'unidad_medida': 'kg', 'stock_minimo': '5.000', 'precio_base': '1.000',
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['sede'], self.sede.id)

    def test_destroy_dado_query_param_justificacion_cuando_delete_entonces_204(self):
        producto = ProductoFactory(sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.delete(
            reverse('producto-detail', kwargs={'pk': producto.id}),
            {'_justificacion_auditoria': 'Producto discontinuado QA'},
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Producto.objects.filter(id=producto.id).exists())

    def test_destroy_dado_sin_justificacion_cuando_delete_entonces_usa_default(self):
        producto = ProductoFactory(sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.delete(reverse('producto-detail', kwargs={'pk': producto.id}))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class ProveedorViewSetMultiTenancyTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.otra_sede = SedeFactory()

    def test_list_dado_usuario_de_sede_cuando_get_entonces_ve_su_sede_y_globales(self):
        propio = ProveedorFactory(sede=self.sede)
        ajeno = ProveedorFactory(sede=self.otra_sede)
        global_ = ProveedorFactory(sede=None)

        user = CustomUserFactory(sede=self.sede)
        self.client.force_authenticate(user=user)

        resp = self.client.get(reverse('proveedor-list'))
        ids = {p['id'] for p in resp.data}
        self.assertIn(propio.id, ids)
        self.assertIn(global_.id, ids)
        self.assertNotIn(ajeno.id, ids)

    def test_create_dado_admin_sin_sede_explicita_cuando_post_entonces_usa_sede_del_usuario(self):
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)

        resp = self.client.post(reverse('proveedor-list'), {'nombre': 'Proveedor Auto QA'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['sede'], self.sede.id)

    def test_destroy_dado_header_justificacion_cuando_delete_entonces_204(self):
        proveedor = ProveedorFactory(sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.delete(
            reverse('proveedor-detail', kwargs={'pk': proveedor.id}),
            HTTP_X_JUSTIFICACION_AUDITORIA='Proveedor QA dado de baja',
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Proveedor.objects.filter(id=proveedor.id).exists())
