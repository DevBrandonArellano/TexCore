"""
Indicadores de producción (OWASP A01): reporte de eficiencia del área y
desempeño del operario.

- Las áreas se acotan a la sede del usuario (admin_sistemas ve todas).
- El reporte de eficiencia lo ven el Jefe de Área (solo su área), el Jefe de
  Planta y los admins.
- El desempeño de un operario lo ven el propio operario (solo el suyo), su
  Jefe de Área (los de su área) y el Jefe de Planta y los admins (su sede).
  Decisión del usuario del 1-oct-2026.

Técnicas ISTQB: partición de equivalencia por rol, por sede y por área, y el
caso límite «consultarse a sí mismo».
"""
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.tests.factories import AreaFactory, CustomUserFactory, SedeFactory


def _filas(resp):
    return resp.data['results'] if isinstance(resp.data, dict) else resp.data


class _IndicadoresMixin:

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.sede_b = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.otra_area = AreaFactory(sede=self.sede)
        self.area_b = AreaFactory(sede=self.sede_b)
        self.operario = CustomUserFactory(sede=self.sede, area=self.area, groups=['operario'])
        self.operario_otra_area = CustomUserFactory(sede=self.sede, area=self.otra_area, groups=['operario'])

    def _como(self, grupo, area=None, sede=None):
        user = CustomUserFactory(sede=sede or self.sede, area=area, groups=[grupo])
        self.client.force_authenticate(user=user)
        return user


class AreasYReporteEficienciaTestCase(_IndicadoresMixin, TestCase):

    def test_areas_dado_jefe_planta_cuando_lista_entonces_solo_las_de_su_sede(self):
        self._como('jefe_planta')
        ids = {a['id'] for a in _filas(self.client.get('/api/areas/'))}
        self.assertTrue({self.area.id, self.otra_area.id} <= ids)
        self.assertNotIn(self.area_b.id, ids)

    def test_areas_dado_admin_sistemas_cuando_lista_entonces_ve_todas(self):
        self._como('admin_sistemas')
        ids = {a['id'] for a in _filas(self.client.get('/api/areas/'))}
        self.assertIn(self.area_b.id, ids)

    def test_reporte_dado_jefe_planta_y_area_de_otra_sede_cuando_consulta_entonces_404(self):
        self._como('jefe_planta')
        self.assertEqual(self.client.get(f'/api/areas/{self.area_b.id}/reporte-eficiencia/').status_code, 404)

    def test_reporte_dado_jefe_area_y_otra_area_de_su_sede_cuando_consulta_entonces_403(self):
        self._como('jefe_area', area=self.area)
        self.assertEqual(self.client.get(f'/api/areas/{self.otra_area.id}/reporte-eficiencia/').status_code, 403)

    def test_reporte_dado_jefe_area_y_su_area_cuando_consulta_entonces_200_con_maquinas_y_operarios(self):
        self._como('jefe_area', area=self.area)
        resp = self.client.get(f'/api/areas/{self.area.id}/reporte-eficiencia/')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn(self.operario.id, [o['operario_id'] for o in resp.data['operarios']])

    def test_reporte_dado_operario_o_vendedor_cuando_consulta_entonces_403(self):
        for grupo in ('operario', 'vendedor'):
            with self.subTest(grupo=grupo):
                self._como(grupo, area=self.area)
                self.assertEqual(
                    self.client.get(f'/api/areas/{self.area.id}/reporte-eficiencia/').status_code, 403)


class DesempenoOperarioTestCase(_IndicadoresMixin, TestCase):

    def _desempeno(self, user):
        return self.client.get(f'/api/users/{user.id}/desempeno/')

    def test_desempeno_dado_operario_cuando_consulta_el_suyo_entonces_200(self):
        self.client.force_authenticate(user=self.operario)
        self.assertEqual(self._desempeno(self.operario).status_code, 200)

    def test_desempeno_dado_operario_cuando_consulta_el_de_un_companero_entonces_403(self):
        companero = CustomUserFactory(sede=self.sede, area=self.area, groups=['operario'])
        self.client.force_authenticate(user=self.operario)
        self.assertEqual(self._desempeno(companero).status_code, 403)

    def test_desempeno_dado_vendedor_cuando_consulta_un_operario_entonces_403(self):
        self._como('vendedor')
        self.assertEqual(self._desempeno(self.operario).status_code, 403)

    def test_desempeno_dado_jefe_area_cuando_consulta_su_area_y_otra_entonces_200_y_404(self):
        self._como('jefe_area', area=self.area)
        self.assertEqual(self._desempeno(self.operario).status_code, 200)
        self.assertEqual(self._desempeno(self.operario_otra_area).status_code, 404)

    def test_desempeno_dado_jefe_planta_cuando_consulta_su_sede_y_otra_entonces_200_y_404(self):
        operario_b = CustomUserFactory(sede=self.sede_b, area=self.area_b, groups=['operario'])
        self._como('jefe_planta')
        self.assertEqual(self._desempeno(self.operario_otra_area).status_code, 200)
        self.assertEqual(self._desempeno(operario_b).status_code, 404)
