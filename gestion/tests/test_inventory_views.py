"""
Pruebas de gestion/views/inventory_views.py — BodegaViewSet.

Cubre el filtrado por rol (RBAC), el filtrado por sede, la auto-asignación de
sede al crear y el borrado con justificación de auditoría.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: ramas de get_queryset (admin ve todo vs
  bodeguero ve solo asignadas) y get_permissions (lectura vs escritura).
- Particiones de equivalencia (EP): rol admin / bodeguero; con y sin sede_id.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, BodegaFactory, CustomUserFactory,
)


class BodegaViewSetQuerysetTestCase(TestCase):
    """Caja blanca de get_queryset: admin ve todo, bodeguero solo asignadas."""

    def setUp(self):
        self.client = APIClient()
        self.sede_a = SedeFactory()
        self.sede_b = SedeFactory()
        self.bodega_a1 = BodegaFactory(sede=self.sede_a)
        self.bodega_a2 = BodegaFactory(sede=self.sede_a)
        self.bodega_b1 = BodegaFactory(sede=self.sede_b)
        self.url = reverse('bodega-list')

    def test_bodega_dado_admin_sistemas_cuando_lista_entonces_ve_todas(self):
        admin = CustomUserFactory(sede=self.sede_a, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 3)

    def test_bodega_dado_admin_con_filtro_sede_cuando_lista_entonces_filtra(self):
        # EP: sede_id presente -> solo bodegas de esa sede
        admin = CustomUserFactory(sede=self.sede_a, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url, {'sede_id': self.sede_a.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_bodega_dado_bodeguero_cuando_lista_entonces_solo_asignadas(self):
        # Caja blanca: rama no-admin -> filtra por bodegas_asignadas
        bodeguero = CustomUserFactory(sede=self.sede_a, groups=['bodeguero'])
        bodeguero.bodegas_asignadas.add(self.bodega_a1)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['id'], self.bodega_a1.id)

    def test_bodega_dado_bodeguero_sin_asignaciones_cuando_lista_entonces_vacio(self):
        bodeguero = CustomUserFactory(sede=self.sede_a, groups=['bodeguero'])
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_bodega_dado_no_autenticado_cuando_lista_entonces_401(self):
        resp = self.client.get(self.url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class BodegaViewSetWriteTestCase(TestCase):
    """get_permissions: escritura exige admin_sistemas/admin_sede."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.url = reverse('bodega-list')

    def test_bodega_dado_admin_sede_cuando_crea_entonces_201(self):
        # El serializer exige sede; admin_sede tiene permiso de escritura
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sede'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(self.url, {'nombre': 'Bodega Nueva', 'sede': self.sede.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")
        self.assertEqual(resp.data['sede'], self.sede.id)

    def test_bodega_dado_bodeguero_cuando_crea_entonces_403(self):
        # EP: rol sin permiso de escritura -> 403
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.post(self.url, {'nombre': 'X', 'sede': self.sede.id}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_bodega_dado_justificacion_en_header_cuando_elimina_entonces_204(self):
        # perform_destroy: usa la justificación del header de auditoría
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        bodega = BodegaFactory(sede=self.sede)
        self.client.force_authenticate(user=admin)
        resp = self.client.delete(
            reverse('bodega-detail', args=[bodega.id]),
            HTTP_X_JUSTIFICACION_AUDITORIA='Cierre de bodega por inventario'
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
