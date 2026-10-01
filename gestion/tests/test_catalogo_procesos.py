"""
Catálogo de procesos de producción (`/api/process-steps/`), que usan las
operaciones MES (OperacionProduccion.proceso).

Lectura para cualquier rol autenticado; alta, edición y baja solo del
Administrador de Sistemas. Un proceso usado por una operación no se borra
(409). Técnicas ISTQB: partición de equivalencia por rol y valores únicos.
"""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestion.models import OperacionProduccion, ProcessStep
from gestion.tests.factories import CorridaProduccionFactory, CustomUserFactory, MaquinaFactory

URL = '/api/process-steps/'


class CatalogoProcesosTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.proceso = ProcessStep.objects.create(name='Tejido', description='Tejido de punto')

    def _como(self, grupo):
        self.client.force_authenticate(user=CustomUserFactory(groups=[grupo]))

    def test_procesos_dado_operario_cuando_lista_entonces_200(self):
        self._como('operario')
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        filas = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertIn('Tejido', [p['name'] for p in filas])

    def test_proceso_dado_admin_sistemas_cuando_crea_entonces_201(self):
        self._como('admin_sistemas')
        resp = self.client.post(URL, {'name': 'Teñido', 'description': ''}, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_proceso_dado_jefe_planta_cuando_crea_entonces_403(self):
        self._como('jefe_planta')
        self.assertEqual(self.client.post(URL, {'name': 'Teñido'}, format='json').status_code, 403)

    def test_proceso_dado_nombre_repetido_cuando_crea_entonces_400(self):
        self._como('admin_sistemas')
        self.assertEqual(self.client.post(URL, {'name': 'Tejido'}, format='json').status_code, 400)

    def test_proceso_dado_usado_por_una_operacion_cuando_borra_entonces_409_y_se_conserva(self):
        corrida = CorridaProduccionFactory()
        OperacionProduccion.objects.create(
            corrida=corrida, maquina=MaquinaFactory(area=corrida.area), proceso=self.proceso,
            operario=CustomUserFactory(groups=['operario']), hora_inicio=timezone.now())
        self._como('admin_sistemas')
        resp = self.client.delete(f'{URL}{self.proceso.id}/')
        self.assertEqual(resp.status_code, 409)
        self.assertTrue(ProcessStep.objects.filter(pk=self.proceso.pk).exists())

    def test_proceso_dado_sin_uso_cuando_admin_borra_entonces_204(self):
        self._como('admin_sistemas')
        self.assertEqual(self.client.delete(f'{URL}{self.proceso.id}/').status_code, 204)
