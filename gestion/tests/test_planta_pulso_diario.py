"""
Pruebas de PlantaPulsoDiarioView (gestion/views/kpi_views.py).

Endpoint humano `GET /produccion/pulso-diario/` que alimenta la "Torre de
Control" del Jefe de Planta. Servido desde el backend humano (CookieJWT), NO
desde internal_api — internal_api solo autentica microservicios sin sede y por
eso no puede imponer aislamiento por sede del usuario final.

Técnicas ISTQB aplicadas:
- Caja blanca: ramas de `_resolver_sede` (global vs no-global; sede propia vs
  ajena; sin sede asignada).
- Aislamiento por sede (OWASP A01 — Broken Access Control): un usuario NO ve los
  kilos de otra sede.
- Particiones de equivalencia: sede_id ausente / propio / ajeno / inválido.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, AreaFactory, CustomUserFactory, OrdenProduccionFactory,
)


class PlantaPulsoDiarioSedeIsolationTestCase(TestCase):
    """Aislamiento por sede del Pulso Diario del Jefe de Planta."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('planta-pulso-diario')
        self.hoy = timezone.now().date()

        # Dos sedes con sus áreas y una OP planificada para hoy en cada una.
        self.sede_a = SedeFactory()
        self.sede_b = SedeFactory()
        self.area_a = AreaFactory(sede=self.sede_a)
        self.area_b = AreaFactory(sede=self.sede_b)

        OrdenProduccionFactory(
            sede=self.sede_a, area=self.area_a,
            fecha_fin_planificada=self.hoy, peso_neto_requerido=Decimal('100.00'),
        )
        OrdenProduccionFactory(
            sede=self.sede_b, area=self.area_b,
            fecha_fin_planificada=self.hoy, peso_neto_requerido=Decimal('500.00'),
        )

    def test_pulso_dado_jefe_planta_cuando_get_entonces_solo_ve_su_sede(self):
        # Un jefe de planta de la sede A ve solo los 100 kg de su sede, no los
        # 600 kg del total (evita fuga de datos entre plantas).
        jefe = CustomUserFactory(sede=self.sede_a, groups=['jefe_planta'])
        self.client.force_authenticate(user=jefe)

        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['kg_planificados_hoy'], 100.0)

    def test_pulso_dado_jefe_planta_con_sede_id_ajena_cuando_get_entonces_403(self):
        # Intento explícito de consultar otra sede vía query param → 403.
        jefe = CustomUserFactory(sede=self.sede_a, groups=['jefe_planta'])
        self.client.force_authenticate(user=jefe)

        resp = self.client.get(self.url, {'sede_id': self.sede_b.id})

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_pulso_dado_jefe_planta_con_su_propia_sede_id_cuando_get_entonces_200(self):
        # Pasar el propio sede_id es válido (idempotente con el forzado).
        jefe = CustomUserFactory(sede=self.sede_a, groups=['jefe_planta'])
        self.client.force_authenticate(user=jefe)

        resp = self.client.get(self.url, {'sede_id': self.sede_a.id})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['kg_planificados_hoy'], 100.0)

    def test_pulso_dado_jefe_planta_sin_sede_cuando_get_entonces_403(self):
        # Caja blanca: no-global sin sede asignada → 403.
        jefe = CustomUserFactory(sede=None, groups=['jefe_planta'])
        self.client.force_authenticate(user=jefe)

        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_pulso_dado_admin_con_sede_id_cuando_get_entonces_ve_esa_sede(self):
        # Un rol global (admin_sistemas) puede consultar cualquier sede.
        admin = CustomUserFactory(sede=self.sede_a, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(self.url, {'sede_id': self.sede_b.id})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['kg_planificados_hoy'], 500.0)

    def test_pulso_dado_admin_sin_sede_id_cuando_get_entonces_ve_todas_las_sedes(self):
        # Sin sede_id, el rol global ve el consolidado de todas las sedes.
        admin = CustomUserFactory(sede=self.sede_a, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(self.url)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['kg_planificados_hoy'], 600.0)

    def test_pulso_dado_sede_id_invalido_cuando_get_entonces_400(self):
        # Partición inválida: sede_id no numérico (rol global) → 400 controlado.
        admin = CustomUserFactory(sede=self.sede_a, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(self.url, {'sede_id': 'abc'})

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pulso_dado_no_autenticado_cuando_get_entonces_rechaza(self):
        # Sin autenticación → 401/403 (no expone datos).
        resp = self.client.get(self.url)
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
