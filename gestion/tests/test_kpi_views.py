"""
Pruebas de gestion/views/kpi_views.py.

Vistas: KPIAreaView, KpiEjecutivoView, ProduccionResumenView, ProduccionTendenciaView.
Las vistas ejecutivas son fachadas que delegan en el Service Layer.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: ramas de autorización de KPIAreaView
  (admin con/ sin area; no-admin con/ sin area).
- Particiones de equivalencia (EP): sede_id válido / ausente / inválido.
- Caja negra: estructura del contrato JSON de respuesta.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, AreaFactory, CustomUserFactory,
)


class KPIAreaViewTestCase(TestCase):
    """Caja blanca de la autorización por área."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.url = reverse('kpi-area')

    def test_kpi_area_dado_admin_con_area_param_cuando_get_entonces_200(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url, {'area': self.area.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['area'], self.area.nombre)
        self.assertIn('total_produccion_kg', resp.data)

    def test_kpi_area_dado_admin_sin_area_ni_param_cuando_get_entonces_400(self):
        # Caja blanca: admin sin area_id y sin user.area -> 400
        admin = CustomUserFactory(sede=self.sede, area=None, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kpi_area_dado_no_admin_con_area_propia_cuando_get_entonces_200(self):
        # No-admin (tintorero) ve estrictamente su propia área
        user = CustomUserFactory(sede=self.sede, area=self.area, groups=['tintorero'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['area'], self.area.nombre)

    def test_kpi_area_dado_no_admin_sin_area_cuando_get_entonces_403(self):
        # Caja blanca: no-admin sin área asignada -> 403
        user = CustomUserFactory(sede=self.sede, area=None, groups=['tintorero'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class KpiEjecutivoViewTestCase(TestCase):
    """Contrato JSON del dashboard ejecutivo + parseo de sede_id."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('kpi-ejecutivo')

    def test_kpi_ejecutivo_dado_autenticado_cuando_get_entonces_estructura_completa(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for clave in ('produccion', 'mrp', 'stock', 'cartera'):
            self.assertIn(clave, resp.data)

    def test_kpi_ejecutivo_dado_sede_id_valido_cuando_get_entonces_200(self):
        # EP: sede_id válido
        resp = self.client.get(self.url, {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_kpi_ejecutivo_dado_sede_id_invalido_cuando_get_entonces_200(self):
        # EP/caja blanca: sede_id no numérico -> _parsear_sede devuelve None (sin crash)
        resp = self.client.get(self.url, {'sede_id': 'abc'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ProduccionResumenTendenciaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)

    def test_resumen_dado_autenticado_cuando_get_entonces_ops_por_estado(self):
        resp = self.client.get(reverse('produccion-resumen'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('ops_por_estado', resp.data)
        self.assertEqual(len(resp.data['ops_por_estado']), 3)

    def test_tendencia_dado_autenticado_cuando_get_entonces_lista(self):
        resp = self.client.get(reverse('produccion-tendencia'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
