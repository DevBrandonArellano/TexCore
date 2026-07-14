"""
Pruebas de gestion/views/materia_prima_views.py — MateriaPrimaLoteViewSet
y TraceabilityViewSet. test_materia_prima_f0_001.py cubre el servicio
(MateriaPrimaService) directamente; este archivo cubre la capa HTTP/API.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol bodeguero con/sin bodega asignada,
  filtros opcionales presentes/ausentes.
- Caja blanca: rama de filtrado por bodegas_asignadas del bodeguero.
"""
from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import LoteProduccion, MateriaPrimaLote
from gestion.tests.factories import (
    BodegaFactory, CustomUserFactory, LoteProduccionFactory, ProductoFactory,
    ProveedorFactory, SedeFactory,
)


class MateriaPrimaLoteViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.proveedor = ProveedorFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.bodega = BodegaFactory(sede=self.sede)
        self.otra_bodega = BodegaFactory(sede=self.sede)

    def _crear_lote_directo(self, bodega, proveedor=None, lote_proveedor='LOTE-QA-1'):
        return MateriaPrimaLote.objects.create(
            producto=self.producto, proveedor=proveedor or self.proveedor,
            lote_proveedor=lote_proveedor, cantidad_kg='100.000',
            costo_unitario='2.000', bodega_recepcion=bodega, sede=self.sede,
            fecha_recepcion=date(2026, 1, 1),
        )

    def test_list_dado_operario_sin_permiso_cuando_get_entonces_403(self):
        # Caja blanca: permission_classes exige IsBodegueroOrAdmin
        operario = CustomUserFactory(groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.get(reverse('materia-prima-list'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_dado_bodeguero_cuando_get_entonces_solo_sus_bodegas_asignadas(self):
        self._crear_lote_directo(self.bodega, lote_proveedor='LOTE-QA-1')
        self._crear_lote_directo(self.otra_bodega, lote_proveedor='LOTE-QA-2')

        bodeguero = CustomUserFactory(groups=['bodeguero'])
        bodeguero.bodegas_asignadas.set([self.bodega])
        self.client.force_authenticate(user=bodeguero)

        resp = self.client.get(reverse('materia-prima-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 1)

    def test_list_dado_admin_cuando_get_entonces_ve_todo(self):
        self._crear_lote_directo(self.bodega, lote_proveedor='LOTE-QA-3')
        self._crear_lote_directo(self.otra_bodega, lote_proveedor='LOTE-QA-4')

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('materia-prima-list'))
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 2)

    def test_list_dado_filtro_disponibles_cuando_get_entonces_excluye_consumidas(self):
        consumido = self._crear_lote_directo(self.bodega, lote_proveedor='LOTE-QA-CONSUMIDO')
        consumido.completamente_consumida = True
        consumido._justificacion_auditoria = 'Consumo total QA'
        consumido.save(update_fields=['completamente_consumida'])
        self._crear_lote_directo(self.bodega, lote_proveedor='LOTE-QA-DISPONIBLE')

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('materia-prima-list'), {'disponibles': 'true'})
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 1)

    def test_registrar_entrada_dado_datos_validos_cuando_post_entonces_201(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'])
        bodeguero.bodegas_asignadas.set([self.bodega])
        self.client.force_authenticate(user=bodeguero)

        resp = self.client.post(reverse('materia-prima-registrar-entrada'), {
            'proveedor': self.proveedor.id, 'producto': self.producto.id,
            'lote_proveedor': 'LOTE-ENTRADA-QA', 'cantidad_kg': '50.000',
            'costo_unitario': '3.500', 'bodega_recepcion': self.bodega.id,
            'fecha_recepcion': '2026-02-01',
        }, format='multipart')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MateriaPrimaLote.objects.filter(lote_proveedor='LOTE-ENTRADA-QA').exists())

    def test_registrar_entrada_dado_datos_invalidos_cuando_post_entonces_400(self):
        bodeguero = CustomUserFactory(groups=['bodeguero'])
        self.client.force_authenticate(user=bodeguero)

        resp = self.client.post(reverse('materia-prima-registrar-entrada'), {
            'proveedor': self.proveedor.id,
        }, format='multipart')

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class TraceabilityViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.lote = LoteProduccionFactory()

    def test_lote_produccion_dado_sin_lote_id_cuando_get_entonces_400(self):
        user = CustomUserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('trazabilidad-lote-produccion'))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lote_produccion_dado_lote_inexistente_cuando_get_entonces_404(self):
        user = CustomUserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('trazabilidad-lote-produccion'), {'lote_id': 999999})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_lote_produccion_dado_lote_existente_cuando_get_entonces_200(self):
        user = CustomUserFactory()
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('trazabilidad-lote-produccion'), {'lote_id': self.lote.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_lote_produccion_dado_no_autenticado_cuando_get_entonces_401(self):
        resp = self.client.get(reverse('trazabilidad-lote-produccion'), {'lote_id': self.lote.id})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
