"""
Reglas de negocio de los componentes de mezcla de una OP (Jefe de Área).

- Solo se definen, editan o eliminan mientras la orden está `pendiente`: una vez
  iniciada, los lotes registrados ya consumieron según la mezcla vigente
  (`RegistroLoteService`), y cambiarla distorsiona la trazabilidad (ISO 9001).
- La suma de porcentajes de una orden no supera el 100 % (COBIT DSS06).
- Eliminar exige justificación, que queda en el AuditLog (ISO 27001 A.12.4).

Técnicas ISTQB: transición de estados de la orden (pendiente → en_proceso →
finalizada), valores límite sobre la suma de porcentajes (100 / 100,01) y
partición de equivalencia por rol.
"""
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import AuditLog, ComponenteMezclaOP
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    ComponenteMezclaOPFactory,
    CustomUserFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    SedeFactory,
)

URL = '/api/componentes-mezcla/'


class _MezclaMixin:

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.bodega = BodegaFactory(sede=self.sede)
        self.orden = OrdenProduccionFactory(
            sede=self.sede, area=self.area, estado='pendiente', peso_neto_requerido=Decimal('200.00'))
        self.jefe_area = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=self.jefe_area)

    def _payload(self, porcentaje='50.00', orden=None):
        return {
            'orden': (orden or self.orden).id, 'producto': ProductoFactory(sede=self.sede).id,
            'bodega': self.bodega.id, 'porcentaje': porcentaje,
        }

    def _componente(self, porcentaje='40.00'):
        return ComponenteMezclaOPFactory(
            orden=self.orden, producto=ProductoFactory(sede=self.sede), bodega=self.bodega,
            porcentaje=Decimal(porcentaje))

    def _iniciar_orden(self, estado):
        type(self.orden).objects.filter(pk=self.orden.pk).update(estado=estado)


class EstadoOrdenComponentesTestCase(_MezclaMixin, TestCase):

    def test_componente_dado_orden_pendiente_cuando_crea_entonces_201_y_calcula_kg(self):
        resp = self.client.post(URL, self._payload('25.00'), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(Decimal(resp.data['cantidad_kg']), Decimal('50.000'))

    def test_componente_dado_orden_iniciada_o_finalizada_cuando_crea_entonces_400_sin_crear(self):
        for estado in ('en_proceso', 'finalizada'):
            with self.subTest(estado=estado):
                self._iniciar_orden(estado)
                resp = self.client.post(URL, self._payload(), format='json')
                self.assertEqual(resp.status_code, 400)
                self.assertFalse(ComponenteMezclaOP.objects.filter(orden=self.orden).exists())

    def test_componente_dado_orden_en_proceso_cuando_edita_entonces_400_y_no_cambia(self):
        componente = self._componente('40.00')
        self._iniciar_orden('en_proceso')
        resp = self.client.patch(f'{URL}{componente.id}/', {'porcentaje': '30.00'}, format='json')
        self.assertEqual(resp.status_code, 400)
        componente.refresh_from_db()
        self.assertEqual(componente.porcentaje, Decimal('40.00'))

    def test_componente_dado_orden_en_proceso_cuando_elimina_entonces_400_y_sigue(self):
        componente = self._componente()
        self._iniciar_orden('en_proceso')
        resp = self.client.delete(f'{URL}{componente.id}/', {'justificacion': 'Cambio de mezcla'}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(ComponenteMezclaOP.objects.filter(pk=componente.pk).exists())

    def test_componente_dado_orden_pendiente_y_justificacion_cuando_elimina_entonces_204_y_audita(self):
        componente = self._componente()
        resp = self.client.delete(f'{URL}{componente.id}/', {'justificacion': '  Cambio de mezcla  '}, format='json')
        self.assertEqual(resp.status_code, 204)
        log = AuditLog.objects.get(
            content_type=ContentType.objects.get_for_model(ComponenteMezclaOP),
            object_id=componente.id, accion='DELETE')
        self.assertEqual(log.justificacion, 'Cambio de mezcla')

    def test_componente_dado_justificacion_solo_espacios_cuando_elimina_entonces_400(self):
        componente = self._componente()
        resp = self.client.delete(f'{URL}{componente.id}/', {'justificacion': '   '}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertTrue(ComponenteMezclaOP.objects.filter(pk=componente.pk).exists())

    def test_componente_dado_operario_cuando_crea_entonces_403(self):
        self.client.force_authenticate(
            user=CustomUserFactory(sede=self.sede, area=self.area, groups=['operario']))
        resp = self.client.post(URL, self._payload(), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_componentes_dado_filtro_por_orden_cuando_lista_entonces_solo_los_de_esa_orden(self):
        propio = self._componente('40.00')
        otra = OrdenProduccionFactory(sede=self.sede, area=self.area, estado='pendiente')
        ComponenteMezclaOPFactory(orden=otra, producto=ProductoFactory(sede=self.sede), bodega=self.bodega)
        resp = self.client.get(URL, {'orden': self.orden.id})
        self.assertEqual(resp.status_code, 200)
        filas = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual([c['id'] for c in filas], [propio.id])

    def test_componente_dado_producto_de_otra_sede_cuando_crea_entonces_400(self):
        datos = self._payload()
        datos['producto'] = ProductoFactory(sede=SedeFactory()).id
        resp = self.client.post(URL, datos, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ComponenteMezclaOP.objects.filter(orden=self.orden).exists())


class SumaPorcentajesComponentesTestCase(_MezclaMixin, TestCase):

    def test_componente_dado_suma_exacta_100_cuando_crea_entonces_201(self):
        self._componente('60.00')
        resp = self.client.post(URL, self._payload('40.00'), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_componente_dado_suma_mayor_a_100_cuando_crea_entonces_400(self):
        self._componente('60.00')
        resp = self.client.post(URL, self._payload('40.01'), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(ComponenteMezclaOP.objects.filter(orden=self.orden).count(), 1)

    def test_componente_dado_edicion_que_supera_100_cuando_edita_entonces_400(self):
        self._componente('40.00')
        propio = self._componente('60.00')
        resp = self.client.patch(f'{URL}{propio.id}/', {'porcentaje': '60.01'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_componente_dado_edicion_que_no_supera_100_cuando_edita_entonces_200(self):
        # El porcentaje propio no se cuenta dos veces al editar.
        self._componente('40.00')
        propio = self._componente('60.00')
        resp = self.client.patch(f'{URL}{propio.id}/', {'porcentaje': '55.00'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
