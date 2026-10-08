"""
GET/PUT /api/configuracion-empaque/ — TEX-43 (equivalencias de empaque por sede).

Decisión del usuario (7-oct-2026): las configura el Administrador de Sede para SU sede;
el Administrador de Sistemas, cualquier sede (con sede_id). Es un dato maestro: cada
cambio exige justificación y queda en la auditoría (TEX-10).

Técnicas ISTQB: partición de equivalencia por rol (OWASP A01), valores límite en las
equivalencias y transición de estados (sin configurar → configurada → modificada).
"""
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import AuditLog, ConfiguracionEmpaqueSede
from gestion.tests.factories import CustomUserFactory, SedeFactory

URL = '/api/configuracion-empaque/'
JUSTIFICACION = 'Nuevo proveedor de conos con otra capacidad'


class ConfiguracionEmpaqueApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory(nombre='Sede Norte')
        self.otra_sede = SedeFactory()
        self.admin_sede = CustomUserFactory(sede=self.sede, groups=['admin_sede'])
        self.admin_sistemas = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])

    def _como(self, usuario):
        self.client.force_authenticate(user=usuario)

    def _put(self, datos, **params):
        url = URL + (f"?sede_id={params['sede_id']}" if 'sede_id' in params else '')
        return self.client.put(url, datos, format='json')

    # --- lectura -----------------------------------------------------------------
    def test_get_dado_sede_sin_configurar_cuando_consulta_entonces_lo_informa(self):
        self._como(self.admin_sede)
        resp = self.client.get(URL)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['sede_id'], self.sede.id)
        self.assertEqual(resp.data['sede_nombre'], 'Sede Norte')
        self.assertFalse(resp.data['configurada'])
        self.assertIsNone(resp.data['conos_por_bano'])

    def test_get_dado_sede_configurada_cuando_consulta_entonces_devuelve_equivalencias(self):
        ConfiguracionEmpaqueSede.objects.create(sede=self.sede, fundas_por_bano=10, conos_por_funda=20)
        self._como(self.admin_sede)
        resp = self.client.get(URL)
        self.assertTrue(resp.data['configurada'])
        self.assertEqual((resp.data['fundas_por_bano'], resp.data['conos_por_funda'], resp.data['conos_por_bano']),
                         (10, 20, 200))

    # --- escritura del admin de sede (CA-1) -----------------------------------------
    def test_put_dado_admin_sede_sin_configuracion_cuando_guarda_entonces_la_crea(self):
        self._como(self.admin_sede)
        resp = self._put({'fundas_por_bano': 12, 'conos_por_funda': 18, 'justificacion': JUSTIFICACION})
        self.assertEqual(resp.status_code, 201, resp.data)
        config = ConfiguracionEmpaqueSede.objects.get(sede=self.sede)
        self.assertEqual(config.conos_por_bano, 216)

    def test_put_dado_configuracion_existente_cuando_modifica_entonces_audita_con_justificacion(self):
        config = ConfiguracionEmpaqueSede.objects.create(sede=self.sede, fundas_por_bano=15, conos_por_funda=15)
        self._como(self.admin_sede)
        resp = self._put({'fundas_por_bano': 12, 'conos_por_funda': 15, 'justificacion': JUSTIFICACION})
        self.assertEqual(resp.status_code, 200, resp.data)
        log = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(ConfiguracionEmpaqueSede), object_id=config.pk,
            accion='UPDATE').get()
        self.assertEqual(log.justificacion, JUSTIFICACION)
        self.assertEqual(log.object_sede_id, self.sede.id)
        self.assertEqual(log.valor_nuevo, {'fundas_por_bano': 12})

    def test_put_dado_justificacion_corta_cuando_guarda_entonces_400(self):
        self._como(self.admin_sede)
        resp = self._put({'fundas_por_bano': 12, 'conos_por_funda': 18, 'justificacion': 'corta'})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('justificacion', resp.data['error']['fields'])

    def test_put_dado_equivalencia_cero_cuando_guarda_entonces_400(self):
        self._como(self.admin_sede)
        resp = self._put({'fundas_por_bano': 0, 'conos_por_funda': 18, 'justificacion': JUSTIFICACION})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ConfiguracionEmpaqueSede.objects.filter(sede=self.sede).exists())

    # --- alcance por sede (OWASP A01, CA-2) ------------------------------------------
    def test_put_dado_admin_sede_cuando_pide_otra_sede_entonces_404_sin_cambios(self):
        self._como(self.admin_sede)
        resp = self._put({'fundas_por_bano': 12, 'conos_por_funda': 18, 'justificacion': JUSTIFICACION},
                         sede_id=self.otra_sede.id)
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(ConfiguracionEmpaqueSede.objects.exists())

    def test_get_dado_admin_sede_cuando_pide_otra_sede_entonces_404(self):
        self._como(self.admin_sede)
        self.assertEqual(self.client.get(URL, {'sede_id': self.otra_sede.id}).status_code, 404)

    def test_put_dado_admin_sistemas_con_sede_id_cuando_guarda_entonces_configura_esa_sede(self):
        self._como(self.admin_sistemas)
        resp = self._put({'fundas_por_bano': 20, 'conos_por_funda': 10, 'justificacion': JUSTIFICACION},
                         sede_id=self.otra_sede.id)
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(ConfiguracionEmpaqueSede.objects.get(sede=self.otra_sede).conos_por_bano, 200)
        self.assertFalse(ConfiguracionEmpaqueSede.objects.filter(sede=self.sede).exists())

    def test_get_dado_admin_sistemas_sin_sede_id_cuando_consulta_entonces_400(self):
        self._como(CustomUserFactory(sede=None, groups=['admin_sistemas']))
        self.assertEqual(self.client.get(URL).status_code, 400)

    def test_get_dado_admin_sistemas_con_sede_inexistente_cuando_consulta_entonces_404(self):
        self._como(self.admin_sistemas)
        self.assertEqual(self.client.get(URL, {'sede_id': 999999}).status_code, 404)

    def test_get_dado_admin_sede_sin_sede_cuando_consulta_entonces_404(self):
        self._como(CustomUserFactory(sede=None, groups=['admin_sede']))
        self.assertEqual(self.client.get(URL).status_code, 404)

    # --- roles sin permiso -----------------------------------------------------------
    def test_get_y_put_dado_roles_operativos_cuando_acceden_entonces_403(self):
        for rol in ('vendedor', 'operario', 'bodeguero', 'ejecutivo', 'jefe_planta'):
            with self.subTest(rol=rol):
                self._como(CustomUserFactory(sede=self.sede, groups=[rol]))
                self.assertEqual(self.client.get(URL).status_code, 403)
                resp = self._put({'fundas_por_bano': 1, 'conos_por_funda': 1, 'justificacion': JUSTIFICACION})
                self.assertEqual(resp.status_code, 403)


class AvisoMRPSinConfiguracionTestCase(TestCase):
    """CA-3 en el MRP: el motor corre en segundo plano, así que la respuesta de
    ejecutar-mrp avisa qué sedes (visibles para el usuario) no se convertirán."""

    def test_ejecutar_mrp_dado_sede_sin_configuracion_cuando_post_entonces_la_avisa(self):
        from unittest.mock import patch
        sede = SedeFactory(nombre='Sede Sin Empaque')
        configurada = SedeFactory()
        ConfiguracionEmpaqueSede.objects.create(sede=configurada, fundas_por_bano=15, conos_por_funda=15)
        otra = SedeFactory(nombre='Sede Ajena')
        client = APIClient()
        client.force_authenticate(user=CustomUserFactory(sede=sede, groups=['bodeguero']))

        with patch('inventory.views.mrp_views.MRPEngine'):
            resp = client.post('/api/inventory/sugerencias-compra/ejecutar-mrp/')

        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.data['sedes_sin_configuracion_empaque'], ['Sede Sin Empaque'])
        self.assertNotIn(otra.nombre, resp.data['sedes_sin_configuracion_empaque'])
