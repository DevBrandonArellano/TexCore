"""
Pruebas de gestion/views/core_views.py — SedeViewSet, AreaViewSet,
CustomUserViewSet (sin test dedicado previo).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol con visión gerencial / restringido a
  su sede o área, con y sin filtros opcionales.
- Caja blanca: rama de auto-asignación de sede en perform_create, rama
  `qs.none()` cuando falta área/sede.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    AreaFactory, CustomUserFactory, LoteProduccionFactory, MaquinaFactory, SedeFactory,
)


class SedeViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()

    def test_list_dado_usuario_autenticado_cuando_get_entonces_200_con_anotaciones(self):
        user = CustomUserFactory(sede=self.sede)
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('sede-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        sede_data = next(s for s in results if s['id'] == self.sede.id)
        self.assertIn('num_areas', sede_data)
        self.assertIn('num_users', sede_data)

    def test_create_dado_usuario_no_admin_cuando_post_entonces_403(self):
        user = CustomUserFactory(groups=['vendedor'])
        self.client.force_authenticate(user=user)
        resp = self.client.post(reverse('sede-list'), {'nombre': 'Sede QA', 'location': 'Quito'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_admin_sistemas_cuando_post_entonces_201(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(reverse('sede-list'), {'nombre': 'Sede QA 2', 'location': 'Quito'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class AreaViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)

    def test_create_dado_jefe_planta_sin_sede_explicita_cuando_post_entonces_403(self):
        # Caja blanca: crear área exige IsSystemAdmin (no está en la lista de acciones abiertas)
        jefe_planta = CustomUserFactory(groups=['jefe_planta'], sede=self.sede)
        self.client.force_authenticate(user=jefe_planta)
        resp = self.client.post(reverse('area-list'), {'nombre': 'Area QA'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_admin_sin_sede_cuando_post_entonces_400(self):
        # HALLAZGO QA (menor): Area.sede no tiene blank=True, por lo que DRF lo
        # exige en el serializer -> la rama de fallback en perform_create
        # (`if not serializer.validated_data.get('sede')...`) es inalcanzable:
        # is_valid() ya rechaza el payload antes de llegar a perform_create.
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)
        resp = self.client.post(reverse('area-list'), {'nombre': 'Area Auto QA'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dado_admin_con_sede_explicita_cuando_post_entonces_201(self):
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)
        resp = self.client.post(
            reverse('area-list'), {'nombre': 'Area Explicita QA', 'sede': self.sede.id}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['sede'], self.sede.id)

    def test_list_dado_filtro_sede_id_cuando_get_entonces_filtra(self):
        otra_sede = SedeFactory()
        AreaFactory(sede=otra_sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('area-list'), {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_reporte_eficiencia_dado_area_sin_produccion_cuando_get_entonces_200_vacio(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('area-reporte-eficiencia', kwargs={'pk': self.area.id}))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['area_id'], self.area.id)
        self.assertEqual(resp.data['maquinas'], [])
        self.assertEqual(resp.data['produccion_total_area'], 0)

    def test_reporte_eficiencia_dado_maquina_con_produccion_hoy_cuando_get_entonces_calcula_eficiencia(self):
        from datetime import datetime
        maquina = MaquinaFactory(area=self.area, capacidad_maxima='100.00')
        LoteProduccionFactory(
            maquina=maquina, peso_neto_producido='50.000',
            hora_inicio=datetime.now(), hora_final=datetime.now(),
        )
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('area-reporte-eficiencia', kwargs={'pk': self.area.id}))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['maquinas']), 1)
        self.assertEqual(resp.data['maquinas'][0]['eficiencia'], 50.0)


class CustomUserViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)

    def test_list_dado_jefe_area_sin_area_asignada_cuando_get_entonces_vacio(self):
        jefe = CustomUserFactory(groups=['jefe_area'], area=None, sede=self.sede)
        self.client.force_authenticate(user=jefe)
        resp = self.client.get(reverse('user-list'))
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual(len(results), 0)

    def test_list_dado_jefe_area_cuando_get_entonces_solo_su_area(self):
        CustomUserFactory(area=self.area, sede=self.sede)
        otra_area = AreaFactory(sede=self.sede)
        CustomUserFactory(area=otra_area, sede=self.sede)

        jefe = CustomUserFactory(groups=['jefe_area'], area=self.area, sede=self.sede)
        self.client.force_authenticate(user=jefe)

        resp = self.client.get(reverse('user-list'))
        results = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        ids_areas = {u['area'] for u in results}
        self.assertEqual(ids_areas, {self.area.id})

    def test_vendedores_dado_usuario_no_autorizado_cuando_get_entonces_403(self):
        user = CustomUserFactory(groups=['operario'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('user-vendedores'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_vendedores_dado_admin_sistemas_cuando_get_entonces_200_ve_todas_las_sedes(self):
        otra_sede = SedeFactory()
        CustomUserFactory(groups=['vendedor'], sede=self.sede, username='vend_qa_a')
        CustomUserFactory(groups=['vendedor'], sede=otra_sede, username='vend_qa_b')

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('user-vendedores'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        usernames = {v['username'] for v in resp.data}
        self.assertIn('vend_qa_a', usernames)
        self.assertIn('vend_qa_b', usernames)

    def test_desempeno_dado_operario_sin_lotes_hoy_cuando_get_entonces_200_ceros(self):
        operario = CustomUserFactory(groups=['operario'], area=self.area, sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('user-desempeno', kwargs={'pk': operario.id}))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['produccion_hoy_kg'], 0)
        self.assertEqual(resp.data['lotes_hoy'], 0)
