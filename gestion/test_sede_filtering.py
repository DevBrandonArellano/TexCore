from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import Group
from gestion.models import Sede, Cliente, CustomUser

class SedeFilteringTestCase(APITestCase):
    def setUp(self):
        # Sedes
        self.sede1 = Sede.objects.create(nombre="Sede 1", location="Quito")
        self.sede2 = Sede.objects.create(nombre="Sede 2", location="Guayaquil")

        # Groups
        self.vendedor_group, _ = Group.objects.get_or_create(name='vendedor')
        self.admin_group, _ = Group.objects.get_or_create(name='admin_sistemas')

        # Users
        self.v1_s1 = CustomUser.objects.create_user(username='v1_s1', password='password', sede=self.sede1)
        self.v1_s1.groups.add(self.vendedor_group)

        self.v2_s2 = CustomUser.objects.create_user(username='v2_s2', password='password', sede=self.sede2)
        self.v2_s2.groups.add(self.vendedor_group)

        self.admin = CustomUser.objects.create_user(username='admin_user', password='password', sede=self.sede1)
        self.admin.groups.add(self.admin_group)

        # Clients
        self.c1 = Cliente.objects.create(ruc_cedula="1", nombre_razon_social="C1 S1", vendedor_asignado=self.v1_s1)
        self.c2 = Cliente.objects.create(ruc_cedula="2", nombre_razon_social="C2 S2", vendedor_asignado=self.v2_s2)

    def test_admin_filters_by_sede(self):
        """Admin should be able to see all but also filter by sede_id."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('cliente-list')

        # Unfiltered: sees both
        response = self.client.get(url)
        self.assertEqual(len(response.data), 2)

        # Filter by Sede 1
        response = self.client.get(url, {'sede_id': self.sede1.id})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.c1.id)

        # Filter by Sede 2
        response = self.client.get(url, {'sede_id': self.sede2.id})
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.c2.id)

    def test_salesman_restricted_and_can_filter_further(self):
        """Salesman is restricted to their assigned clients, and can filter by sede (though usually they only have one sede)."""
        self.client.force_authenticate(user=self.v1_s1)
        url = reverse('cliente-list')

        # Vendedor 1 only sees C1 (assigned to them)
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.c1.id)

        # Vendedor 1 filters by Sede 1 (their own sede)
        response = self.client.get(url, {'sede_id': self.sede1.id})
        self.assertEqual(len(response.data), 1)

        # Vendedor 1 filters by Sede 2 (should see nothing because C1 is in Sede 1)
        response = self.client.get(url, {'sede_id': self.sede2.id})
        self.assertEqual(len(response.data), 0)
