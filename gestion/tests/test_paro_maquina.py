"""
Pruebas de ParoMaquina — downtime de máquina con reason codes (Seis Grandes
Pérdidas, OEE for Operators). Alimenta la Disponibilidad del OEE (OeeService).

Técnicas ISTQB: EP (categorías válidas/inválidas), BVA (fin == inicio, fin < inicio),
caja blanca (aislamiento por área/sede en get_queryset), RBAC por rol.
"""
from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import ParoMaquina
from gestion.tests.factories import (
    SedeFactory, AreaFactory, MaquinaFactory, CustomUserFactory, ParoMaquinaFactory,
)


class ParoMaquinaModelTestCase(TestCase):
    """Validación de negocio a nivel de modelo."""

    def setUp(self):
        self.maquina = MaquinaFactory()

    def test_paro_dado_fin_posterior_a_inicio_cuando_guarda_entonces_ok(self):
        paro = ParoMaquina(
            maquina=self.maquina,
            inicio=datetime(2026, 1, 1, 8, 0),
            fin=datetime(2026, 1, 1, 8, 30),
            categoria='AVERIA',
        )
        paro.save()
        self.assertEqual(paro.duracion_minutos, 30.0)

    def test_paro_dado_fin_igual_a_inicio_cuando_guarda_entonces_valueerror(self):
        # BVA: el límite exacto (fin == inicio) es inválido — duración cero no es un paro real
        paro = ParoMaquina(
            maquina=self.maquina,
            inicio=datetime(2026, 1, 1, 8, 0),
            fin=datetime(2026, 1, 1, 8, 0),
            categoria='AVERIA',
        )
        with self.assertRaises(ValidationError):
            paro.save()

    def test_paro_dado_fin_anterior_a_inicio_cuando_guarda_entonces_valueerror(self):
        paro = ParoMaquina(
            maquina=self.maquina,
            inicio=datetime(2026, 1, 1, 8, 30),
            fin=datetime(2026, 1, 1, 8, 0),
            categoria='AVERIA',
        )
        with self.assertRaises(ValidationError):
            paro.save()

    def test_paro_dado_sin_fin_cuando_guarda_entonces_es_un_paro_en_curso(self):
        paro = ParoMaquina(maquina=self.maquina, inicio=datetime(2026, 1, 1, 8, 0), categoria='SETUP')
        paro.save()
        self.assertIsNone(paro.fin)
        self.assertIsNone(paro.duracion_minutos)


class ParoMaquinaViewSetTestCase(TestCase):
    """RBAC y aislamiento por área/sede — mismo patrón que MaquinaViewSet."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.url = reverse('paromaquina-list')

    def test_create_dado_operario_de_la_maquina_cuando_post_entonces_201(self):
        # El operario registra sus propios paros
        operario = CustomUserFactory(groups=['operario'], sede=self.sede, area=self.area)
        self.client.force_authenticate(user=operario)
        resp = self.client.post(self.url, {
            'maquina': self.maquina.id,
            'inicio': '2026-01-01T08:00:00Z',
            'fin': '2026-01-01T08:15:00Z',
            'categoria': 'MICROPARO',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_create_dado_jefe_area_cuando_post_entonces_201(self):
        jefe = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=self.area)
        self.client.force_authenticate(user=jefe)
        resp = self.client.post(self.url, {
            'maquina': self.maquina.id,
            'inicio': '2026-01-01T08:00:00Z',
            'categoria': 'AVERIA',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_create_dado_vendedor_cuando_post_entonces_403(self):
        vendedor = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        self.client.force_authenticate(user=vendedor)
        resp = self.client.post(self.url, {
            'maquina': self.maquina.id,
            'inicio': '2026-01-01T08:00:00Z',
            'categoria': 'AVERIA',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_fin_anterior_a_inicio_cuando_post_entonces_400(self):
        jefe = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=self.area)
        self.client.force_authenticate(user=jefe)
        resp = self.client.post(self.url, {
            'maquina': self.maquina.id,
            'inicio': '2026-01-01T08:30:00Z',
            'fin': '2026-01-01T08:00:00Z',
            'categoria': 'AVERIA',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_dado_jefe_de_otra_area_cuando_get_entonces_no_ve_paros_de_otra_area(self):
        ParoMaquinaFactory(maquina=self.maquina)
        otra_area = AreaFactory(sede=self.sede)
        jefe_otra_area = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=otra_area)
        self.client.force_authenticate(user=jefe_otra_area)

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_list_dado_jefe_del_area_correcta_cuando_get_entonces_ve_sus_paros(self):
        ParoMaquinaFactory(maquina=self.maquina)
        jefe = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=self.area)
        self.client.force_authenticate(user=jefe)

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_list_dado_jefe_area_sin_area_asignada_cuando_get_entonces_lista_vacia(self):
        # Fail-closed: mismo patrón que MaquinaViewSet
        jefe_sin_area = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=None)
        self.client.force_authenticate(user=jefe_sin_area)

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)

    def test_list_dado_admin_sistemas_cuando_get_entonces_ve_todo(self):
        ParoMaquinaFactory(maquina=self.maquina)
        otra_area = AreaFactory(sede=self.sede)
        otra_maquina = MaquinaFactory(area=otra_area)
        ParoMaquinaFactory(maquina=otra_maquina)

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)


class MaquinaOeeActionTestCase(TestCase):
    """@action oee en MaquinaViewSet — desglose de OEE por máquina (R4)."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.jefe = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=self.area)
        self.client.force_authenticate(user=self.jefe)

    def test_oee_dado_maquina_de_su_area_cuando_get_entonces_200_con_bloque_oee(self):
        resp = self.client.get(reverse('maquina-oee', args=[self.maquina.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for clave in ('disponibilidad', 'rendimiento', 'calidad', 'oee', 'downtime_min'):
            self.assertIn(clave, resp.data)

    def test_oee_dado_maquina_de_otra_area_cuando_get_entonces_404(self):
        otra_area = AreaFactory(sede=self.sede)
        otra_maquina = MaquinaFactory(area=otra_area)
        resp = self.client.get(reverse('maquina-oee', args=[otra_maquina.id]))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
