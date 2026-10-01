"""
Alcance de lotes de producción y de las transformaciones de una orden (OWASP A01).

- Transformaciones y trazabilidad de una orden de otra sede responden 404,
  también para el Jefe de Planta y el Admin de Sede.
- Editar y rechazar un lote (rechazar lo borra y revierte su stock) solo lo
  hacen el operario dueño del lote, el Jefe de Área, el Jefe de Planta y los
  admins; el empaquetado no. El DELETE genérico no existe.
- El costo del lote (F0-002) lo ven los roles que ven costos de materia prima.
- Los consumos por lote se acotan a la sede del usuario.

Técnicas ISTQB: partición de equivalencia por rol, por dueño del lote y por sede.
"""
from django.test import TestCase
from rest_framework.test import APIClient

from decimal import Decimal

from gestion.models import ComponenteMezclaOP, LoteProduccion
from gestion.tests.factories import (
    AreaFactory, BodegaFactory, ComponenteMezclaOPFactory, ConsumoLoteDetalleFactory, CustomUserFactory,
    LoteProduccionFactory, MaquinaFactory, OrdenProduccionFactory, ProductoFactory, SedeFactory,
)


def _filas(resp):
    return resp.data['results'] if isinstance(resp.data, dict) else resp.data


class _LotesMixin:

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.sede_b = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.area_b = AreaFactory(sede=self.sede_b)
        self.orden = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.orden_b = OrdenProduccionFactory(sede=self.sede_b, area=self.area_b)
        self.duenio = CustomUserFactory(sede=self.sede, area=self.area, groups=['operario'])
        self.lote = LoteProduccionFactory(
            orden_produccion=self.orden, operario=self.duenio, maquina=MaquinaFactory(area=self.area))
        self.lote_b = LoteProduccionFactory(orden_produccion=self.orden_b, maquina=MaquinaFactory(area=self.area_b))

    def _como(self, grupo, area=None):
        user = CustomUserFactory(sede=self.sede, area=area, groups=[grupo])
        self.client.force_authenticate(user=user)
        return user


class TransformacionesAlcanceTestCase(_LotesMixin, TestCase):

    def test_transformaciones_dado_orden_de_otra_sede_cuando_consulta_entonces_404(self):
        for grupo in ('jefe_planta', 'admin_sede'):
            with self.subTest(grupo=grupo):
                self._como(grupo)
                for accion in ('transformaciones', 'trazabilidad'):
                    resp = self.client.get(f'/api/ordenes-produccion/{self.orden_b.id}/{accion}/')
                    self.assertEqual(resp.status_code, 404, accion)

    def test_registrar_transformacion_dado_orden_de_otra_sede_cuando_post_entonces_404(self):
        self._como('jefe_planta')
        resp = self.client.post(
            f'/api/ordenes-produccion/{self.orden_b.id}/registrar-transformacion/', {}, format='json')
        self.assertEqual(resp.status_code, 404)

    def test_transformaciones_dado_jefe_planta_y_orden_de_su_sede_cuando_consulta_entonces_200(self):
        self._como('jefe_planta')
        resp = self.client.get(f'/api/ordenes-produccion/{self.orden.id}/transformaciones/')
        self.assertEqual(resp.status_code, 200)


class LoteEdicionYRechazoTestCase(_LotesMixin, TestCase):

    def _patch(self):
        return self.client.patch(f'/api/lotes-produccion/{self.lote.id}/', {'unidades_empaque': 3}, format='json')

    def _rechazar(self):
        return self.client.post(f'/api/lotes-produccion/{self.lote.id}/rechazar/',
                                {'justificacion': 'Prueba de alcance'}, format='json')

    def test_lote_dado_operario_que_no_es_el_duenio_cuando_edita_o_rechaza_entonces_403(self):
        self._como('operario', area=self.area)
        self.assertEqual(self._patch().status_code, 403)
        self.assertEqual(self._rechazar().status_code, 403)
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.unidades_empaque, 1)

    def test_lote_dado_empaquetado_cuando_edita_o_rechaza_entonces_403_y_se_conserva(self):
        self._como('empaquetado')
        self.assertEqual(self._patch().status_code, 403)
        self.assertEqual(self._rechazar().status_code, 403)
        self.assertTrue(LoteProduccion.objects.filter(pk=self.lote.pk).exists())

    def test_lote_dado_operario_duenio_cuando_edita_entonces_200(self):
        self.client.force_authenticate(user=self.duenio)
        self.assertEqual(self._patch().status_code, 200)

    def test_lote_dado_admin_cuando_delete_entonces_405_y_se_conserva(self):
        self._como('admin_sistemas')
        resp = self.client.delete(f'/api/lotes-produccion/{self.lote.id}/')
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(LoteProduccion.objects.filter(pk=self.lote.pk).exists())

    def test_costo_dado_operario_o_empaquetado_cuando_consulta_entonces_403(self):
        for grupo in ('operario', 'empaquetado'):
            with self.subTest(grupo=grupo):
                self._como(grupo, area=self.area)
                self.assertEqual(
                    self.client.get(f'/api/lotes-produccion/{self.lote.id}/obtener-costo/').status_code, 403)

    def test_costo_dado_bodeguero_cuando_consulta_entonces_200_con_desglose(self):
        self._como('bodeguero')
        resp = self.client.get(f'/api/lotes-produccion/{self.lote.id}/obtener-costo/')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('total_costo', resp.data)


class ConsumoLoteAlcanceTestCase(_LotesMixin, TestCase):

    def test_consumos_dado_usuario_de_sede_cuando_lista_entonces_no_ve_los_de_otra_sede(self):
        propio = ConsumoLoteDetalleFactory(lote_produccion=self.lote, lote_origen=LoteProduccionFactory(
            orden_produccion=self.orden, maquina=MaquinaFactory(area=self.area)))
        ajeno = ConsumoLoteDetalleFactory(lote_produccion=self.lote_b, lote_origen=LoteProduccionFactory(
            orden_produccion=self.orden_b, maquina=MaquinaFactory(area=self.area_b)))
        self._como('jefe_planta')
        ids = {c['id'] for c in _filas(self.client.get('/api/consumo-lote-detalle/'))}
        self.assertIn(propio.id, ids)
        self.assertNotIn(ajeno.id, ids)
        self.assertEqual(self.client.get(f'/api/consumo-lote-detalle/{propio.id}/').status_code, 404)


class ComponentesMezclaAlcanceTestCase(_LotesMixin, TestCase):

    def test_componentes_dado_usuario_sin_sede_cuando_lista_entonces_no_ve_nada(self):
        ComponenteMezclaOPFactory(orden=self.orden_b)
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=['jefe_planta']))
        self.assertEqual(_filas(self.client.get('/api/componentes-mezcla/')), [])

    def test_componente_dado_orden_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/componentes-mezcla/', {
            'orden': self.orden_b.id, 'producto': ProductoFactory(sede=self.sede_b).id,
            'bodega': BodegaFactory(sede=self.sede_b).id, 'porcentaje': '50.00',
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ComponenteMezclaOP.objects.filter(orden=self.orden_b).exists())

    def test_componente_dado_bodega_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/componentes-mezcla/', {
            'orden': self.orden.id, 'producto': ProductoFactory(sede=self.sede).id,
            'bodega': BodegaFactory(sede=self.sede_b).id, 'porcentaje': '50.00',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_componente_dado_datos_de_su_sede_cuando_crea_entonces_201(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/componentes-mezcla/', {
            'orden': self.orden.id, 'producto': ProductoFactory(sede=self.sede).id,
            'bodega': BodegaFactory(sede=self.sede).id, 'porcentaje': Decimal('50.00'),
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
