"""
Pruebas de ClienteViewSet.get_queryset — filtrado multi-tenant por sede.

Migrado desde gestion/test_sede_filtering.py (Fase 6.3 del barrido de higiene,
2026-09-02): mismo archivo suelto en la raíz de gestion/, renombrado a
convención ISTQB y con factories en vez de creación manual de fixtures.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol admin (ve todas las sedes) vs. rol
  vendedor (acotado a sus clientes asignados).
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from gestion.tests.factories import ClienteFactory, CustomUserFactory, SedeFactory


def _results(response):
    """Extrae los items de una respuesta paginada o de lista plana."""
    data = response.data
    if isinstance(data, dict) and 'results' in data:
        return data['results']
    return data


class ClienteSedeFilteringTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede1 = SedeFactory()
        self.sede2 = SedeFactory()

        self.vendedor1 = CustomUserFactory(sede=self.sede1, groups=['vendedor'])
        self.vendedor2 = CustomUserFactory(sede=self.sede2, groups=['vendedor'])
        self.admin = CustomUserFactory(sede=self.sede1, groups=['admin_sistemas'])

        self.cliente1 = ClienteFactory(sede=self.sede1, vendedor_asignado=self.vendedor1)
        self.cliente2 = ClienteFactory(sede=self.sede2, vendedor_asignado=self.vendedor2)

    def test_cliente_dado_admin_cuando_lista_sin_filtro_entonces_ve_todas_las_sedes(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('cliente-list'))
        self.assertEqual(len(_results(resp)), 2)

    def test_cliente_dado_admin_cuando_filtra_por_sede_entonces_solo_esa_sede(self):
        self.client.force_authenticate(user=self.admin)
        url = reverse('cliente-list')

        resp = self.client.get(url, {'sede_id': self.sede1.id})
        items = _results(resp)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['id'], self.cliente1.id)

        resp = self.client.get(url, {'sede_id': self.sede2.id})
        items = _results(resp)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['id'], self.cliente2.id)

    def test_cliente_dado_vendedor_cuando_lista_entonces_solo_sus_clientes_asignados(self):
        self.client.force_authenticate(user=self.vendedor1)
        resp = self.client.get(reverse('cliente-list'))
        items = _results(resp)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['id'], self.cliente1.id)

    def test_cliente_dado_vendedor_cuando_filtra_por_otra_sede_entonces_no_ve_nada(self):
        # El vendedor ya está acotado a sus clientes asignados (todos en su sede);
        # filtrar además por una sede ajena no debe devolver resultados.
        self.client.force_authenticate(user=self.vendedor1)
        resp = self.client.get(reverse('cliente-list'), {'sede_id': self.sede2.id})
        self.assertEqual(len(_results(resp)), 0)
