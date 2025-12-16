from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Sede, Producto, Area

class SedeAPITestCase(APITestCase):
    def setUp(self):
        self.sede1 = Sede.objects.create(nombre='Sede Principal')
        self.sede2 = Sede.objects.create(nombre='Sede Secundaria')

    def test_list_sedes(self):
        """Ensure we can list all sedes."""
        url = reverse('sede-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_sede(self):
        """Ensure we can retrieve a single sede."""
        url = reverse('sede-detail', args=[self.sede1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], self.sede1.nombre)

    def test_create_sede(self):
        """Ensure we can create a new sede."""
        url = reverse('sede-list')
        data = {'nombre': 'Sede Nueva'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Sede.objects.count(), 3)
        self.assertEqual(Sede.objects.get(id=response.data['id']).nombre, 'Sede Nueva')

    def test_update_sede(self):
        """Ensure we can update an existing sede."""
        url = reverse('sede-detail', args=[self.sede1.id])
        data = {'nombre': 'Sede Principal Actualizada'}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sede1.refresh_from_db()
        self.assertEqual(self.sede1.nombre, 'Sede Principal Actualizada')

    def test_delete_sede(self):
        """Ensure we can delete a sede."""
        url = reverse('sede-detail', args=[self.sede1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Sede.objects.count(), 1)

class ProductoAPITestCase(APITestCase):
    def setUp(self):
        self.producto1 = Producto.objects.create(
            codigo='P001',
            descripcion='Hilo de Algodon',
            tipo='hilo',
            unidad_medida='kg'
        )

    def test_list_productos(self):
        """Ensure we can list all productos."""
        url = reverse('producto-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_producto(self):
        """Ensure we can create a new producto."""
        url = reverse('producto-list')
        data = {
            'codigo': 'P002',
            'descripcion': 'Tela de Poliester',
            'tipo': 'tela',
            'unidad_medida': 'metros'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Producto.objects.count(), 2)
        self.assertEqual(Producto.objects.get(id=response.data['id']).codigo, 'P002')

class AreaAPITestCase(APITestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede de Pruebas')
        self.area1 = Area.objects.create(nombre='Area 1', sede=self.sede)

    def test_list_areas(self):
        """Ensure we can list all areas."""
        url = reverse('area-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_area(self):
        """Ensure we can create a new area linked to a sede."""
        url = reverse('area-list')
        data = {'nombre': 'Area 2', 'sede': self.sede.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Area.objects.count(), 2)
        self.assertEqual(response.data['nombre'], 'Area 2')
        self.assertEqual(response.data['sede'], self.sede.id)