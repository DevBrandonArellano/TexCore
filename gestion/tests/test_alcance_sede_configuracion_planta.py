"""
Control de acceso por sede en la configuración de planta (OWASP A01).

Etapas de producción, transferencias interárea, máquinas, líneas y paros: la
lectura queda acotada a la sede (y al área, para el Jefe de Área), y las
escrituras rechazan área, máquina, órdenes, bodegas u operarios de otra sede
igual que un id inexistente. Paros y transferencias son registros históricos:
no se editan ni se borran. Técnicas ISTQB: partición de equivalencia por rol y
por sede (propia / ajena) y valores límite (usuario sin sede).
"""
from datetime import datetime
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import EtapaProduccion, LineaProduccion, ParoMaquina, TransferenciaInterarea
from gestion.tests.factories import (
    AreaFactory, BodegaFactory, CustomUserFactory, LineaProduccionFactory, MaquinaFactory,
    OrdenProduccionFactory, ParoMaquinaFactory, SedeFactory,
)


def _campos_con_error(resp):
    """Campos con error dentro del envoltorio de errores del proyecto."""
    return resp.data.get('error', {}).get('fields', resp.data)


def _filas(resp):
    return resp.data['results'] if isinstance(resp.data, dict) else resp.data


class _PlantaDosSedesMixin:
    """Sede A (la del usuario) y sede B (ajena), cada una con área, máquina,
    bodegas y orden de producción."""

    @classmethod
    def setUpTestData(cls):
        cls.sede_a = SedeFactory()
        cls.sede_b = SedeFactory()
        cls.area_a = AreaFactory(sede=cls.sede_a)
        cls.area_a2 = AreaFactory(sede=cls.sede_a)
        cls.area_b = AreaFactory(sede=cls.sede_b)
        cls.maquina_a = MaquinaFactory(area=cls.area_a)
        cls.maquina_b = MaquinaFactory(area=cls.area_b)
        cls.bodega_a = BodegaFactory(sede=cls.sede_a)
        cls.bodega_a2 = BodegaFactory(sede=cls.sede_a)
        cls.bodega_b = BodegaFactory(sede=cls.sede_b)
        cls.orden_a = OrdenProduccionFactory(sede=cls.sede_a, area=cls.area_a)
        cls.orden_a2 = OrdenProduccionFactory(sede=cls.sede_a, area=cls.area_a2)
        cls.orden_b = OrdenProduccionFactory(sede=cls.sede_b, area=cls.area_b)

    def setUp(self):
        self.client = APIClient()

    def _como(self, grupo, sede=None, area=None):
        user = CustomUserFactory(sede=sede or self.sede_a, area=area, groups=[grupo])
        self.client.force_authenticate(user=user)
        return user


class EtapaProduccionAlcanceTestCase(_PlantaDosSedesMixin, TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.etapa_a = EtapaProduccion.objects.create(
            area=cls.area_a, nombre='Teñido', orden=1, maquina=cls.maquina_a,
            bodega_entrada=cls.bodega_a, bodega_salida=cls.bodega_a2)
        cls.etapa_b = EtapaProduccion.objects.create(
            area=cls.area_b, nombre='Teñido B', orden=1, maquina=cls.maquina_b,
            bodega_entrada=cls.bodega_b, bodega_salida=cls.bodega_b)

    def _payload(self, **extra):
        return {'area': self.area_a.id, 'nombre': 'Secado', 'orden': 2, 'maquina': self.maquina_a.id,
                'bodega_entrada': self.bodega_a.id, 'bodega_salida': self.bodega_a2.id, **extra}

    def _ids(self, resp):
        return {e['id'] for e in _filas(resp)}

    def test_etapas_dado_jefe_planta_cuando_lista_entonces_solo_ve_su_sede(self):
        self._como('jefe_planta')
        ids = self._ids(self.client.get('/api/etapas-produccion/'))
        self.assertIn(self.etapa_a.id, ids)
        self.assertNotIn(self.etapa_b.id, ids)

    def test_etapas_dado_admin_sistemas_cuando_lista_entonces_ve_todas_las_sedes(self):
        self._como('admin_sistemas')
        ids = self._ids(self.client.get('/api/etapas-produccion/'))
        self.assertTrue({self.etapa_a.id, self.etapa_b.id} <= ids)

    def test_etapa_dado_jefe_planta_y_area_ajena_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/etapas-produccion/', self._payload(area=self.area_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('area', _campos_con_error(resp))

    def test_etapa_dado_maquina_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/etapas-produccion/', self._payload(maquina=self.maquina_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('maquina', _campos_con_error(resp))

    def test_etapa_dado_bodega_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/etapas-produccion/', self._payload(bodega_salida=self.bodega_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('bodega_salida', _campos_con_error(resp))

    def test_etapa_dado_jefe_area_y_otra_area_de_su_sede_cuando_crea_entonces_400(self):
        self._como('jefe_area', area=self.area_a)
        resp = self.client.post('/api/etapas-produccion/', self._payload(area=self.area_a2.id), format='json')
        self.assertEqual(resp.status_code, 400)

    def test_etapa_dado_jefe_area_y_su_area_cuando_crea_entonces_201(self):
        self._como('jefe_area', area=self.area_a)
        resp = self.client.post('/api/etapas-produccion/', self._payload(), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_etapa_dado_bodega_ajena_cuando_edita_parcial_entonces_400_y_no_cambia(self):
        self._como('jefe_planta')
        resp = self.client.patch(
            f'/api/etapas-produccion/{self.etapa_a.id}/', {'bodega_entrada': self.bodega_b.id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.etapa_a.refresh_from_db()
        self.assertEqual(self.etapa_a.bodega_entrada_id, self.bodega_a.id)


class TransferenciaInterareaAlcanceTestCase(_PlantaDosSedesMixin, TestCase):

    def _payload(self, **extra):
        return {'orden_area_origen': self.orden_a.id, 'orden_area_destino': self.orden_a2.id,
                'bodega_origen': self.bodega_a.id, 'bodega_destino': self.bodega_a2.id,
                'cantidad_transferida': '25.000', **extra}

    def test_transferencias_dado_jefe_planta_cuando_lista_entonces_solo_ve_su_sede(self):
        propia = TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_a, orden_area_destino=self.orden_a2,
            bodega_origen=self.bodega_a, bodega_destino=self.bodega_a2, cantidad_transferida=Decimal('5'))
        ajena = TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_b, orden_area_destino=self.orden_b,
            bodega_origen=self.bodega_b, bodega_destino=self.bodega_b, cantidad_transferida=Decimal('5'))
        self._como('jefe_planta')
        ids = {t['id'] for t in _filas(self.client.get('/api/transferencias-interarea/'))}
        self.assertIn(propia.id, ids)
        self.assertNotIn(ajena.id, ids)

    def test_transferencias_dado_admin_sede_cuando_lista_entonces_200_solo_su_sede(self):
        # Decisión del usuario (1-oct-2026): el Admin de Sede es un rol de monitoreo.
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_a, orden_area_destino=self.orden_a2,
            bodega_origen=self.bodega_a, bodega_destino=self.bodega_a2, cantidad_transferida=Decimal('5'))
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_b, orden_area_destino=self.orden_b,
            bodega_origen=self.bodega_b, bodega_destino=self.bodega_b, cantidad_transferida=Decimal('5'))
        self._como('admin_sede')
        resp = self.client.get('/api/transferencias-interarea/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(_filas(resp)), 1)

    def test_transferencia_dado_admin_sede_cuando_crea_entonces_403(self):
        self._como('admin_sede')
        resp = self.client.post('/api/transferencias-interarea/', self._payload(), format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(TransferenciaInterarea.objects.exists())

    def test_transferencia_dado_jefe_planta_y_ordenes_de_su_sede_cuando_crea_entonces_201(self):
        user = self._como('jefe_planta')
        resp = self.client.post('/api/transferencias-interarea/', self._payload(), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(TransferenciaInterarea.objects.get(pk=resp.data['id']).usuario_responsable, user)

    def test_transferencia_dado_orden_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/transferencias-interarea/', self._payload(orden_area_destino=self.orden_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('orden_area_destino', _campos_con_error(resp))

    def test_transferencia_dado_bodega_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/transferencias-interarea/', self._payload(bodega_destino=self.bodega_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('bodega_destino', _campos_con_error(resp))

    def test_transferencia_dado_admin_sistemas_y_ordenes_de_sedes_distintas_cuando_crea_entonces_400(self):
        self._como('admin_sistemas')
        resp = self.client.post(
            '/api/transferencias-interarea/', self._payload(orden_area_destino=self.orden_b.id), format='json')
        self.assertEqual(resp.status_code, 400)

    def test_transferencia_dado_origen_igual_a_destino_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/transferencias-interarea/', self._payload(orden_area_destino=self.orden_a.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('orden_area_destino', _campos_con_error(resp))

    def test_transferencia_dado_existente_cuando_edita_o_borra_entonces_404_y_se_conserva(self):
        transferencia = TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_a, orden_area_destino=self.orden_a2,
            bodega_origen=self.bodega_a, bodega_destino=self.bodega_a2, cantidad_transferida=Decimal('5'))
        self._como('admin_sistemas')
        url = f'/api/transferencias-interarea/{transferencia.id}/'
        self.assertEqual(self.client.patch(url, {'cantidad_transferida': '1'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(TransferenciaInterarea.objects.filter(pk=transferencia.pk).exists())


class MaquinaYLineaAlcanceTestCase(_PlantaDosSedesMixin, TestCase):

    def _payload_maquina(self, **extra):
        return {'nombre': 'Rama nueva', 'capacidad_maxima': '100.00', 'eficiencia_ideal': '0.85',
                'estado': 'operativa', 'area': self.area_a.id, **extra}

    def test_maquinas_dado_usuario_sin_sede_cuando_lista_entonces_no_ve_maquinas_sin_area(self):
        MaquinaFactory(nombre='Huérfana', area=None)
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=['jefe_planta']))
        self.assertEqual(self.client.get('/api/maquinas/').data, [])

    def test_maquina_dado_jefe_planta_y_area_ajena_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/maquinas/', self._payload_maquina(area=self.area_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('area', _campos_con_error(resp))

    def test_maquina_dado_bodega_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/maquinas/', self._payload_maquina(bodega_entrada=self.bodega_b.id), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('bodega_entrada', _campos_con_error(resp))

    def test_maquina_dado_operario_de_otra_sede_cuando_crea_entonces_400(self):
        operario_b = CustomUserFactory(sede=self.sede_b, groups=['operario'])
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/maquinas/', self._payload_maquina(operarios=[operario_b.id]), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('operarios', _campos_con_error(resp))

    def test_maquina_dado_jefe_planta_sin_area_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post('/api/maquinas/', self._payload_maquina(area=None), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('area', _campos_con_error(resp))

    def test_maquina_dado_jefe_planta_y_datos_de_su_sede_cuando_crea_entonces_201(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/maquinas/', self._payload_maquina(bodega_entrada=self.bodega_a.id), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

    def test_maquina_dado_area_ajena_cuando_edita_entonces_400_y_no_cambia(self):
        self._como('jefe_planta')
        resp = self.client.patch(f'/api/maquinas/{self.maquina_a.id}/', {'area': self.area_b.id}, format='json')
        self.assertEqual(resp.status_code, 400)
        self.maquina_a.refresh_from_db()
        self.assertEqual(self.maquina_a.area_id, self.area_a.id)

    def test_linea_dado_jefe_planta_y_area_ajena_cuando_crea_entonces_400(self):
        self._como('jefe_planta')
        resp = self.client.post(
            '/api/lineas-produccion/', {'nombre': 'Línea B', 'estado': 'activa', 'area': self.area_b.id},
            format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(LineaProduccion.objects.filter(nombre='Línea B').exists())

    def test_lineas_dado_jefe_planta_cuando_lista_entonces_solo_ve_su_sede(self):
        propia = LineaProduccionFactory(area=self.area_a)
        ajena = LineaProduccionFactory(area=self.area_b)
        self._como('jefe_planta')
        ids = {linea['id'] for linea in _filas(self.client.get('/api/lineas-produccion/'))}
        self.assertIn(propia.id, ids)
        self.assertNotIn(ajena.id, ids)


class ParoMaquinaAlcanceTestCase(_PlantaDosSedesMixin, TestCase):

    def _payload(self, maquina):
        return {'maquina': maquina.id, 'inicio': datetime(2026, 1, 1, 8, 0).isoformat(),
                'fin': datetime(2026, 1, 1, 8, 30).isoformat(), 'categoria': 'AVERIA',
                'planificado': False, 'turno': 'Dia'}

    def test_paro_dado_operario_y_maquina_de_otra_sede_cuando_crea_entonces_400(self):
        self._como('operario')
        resp = self.client.post('/api/paros-maquina/', self._payload(self.maquina_b), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('maquina', _campos_con_error(resp))
        self.assertFalse(ParoMaquina.objects.filter(maquina=self.maquina_b).exists())

    def test_paro_dado_operario_y_maquina_de_su_sede_cuando_crea_entonces_201(self):
        user = self._como('operario')
        resp = self.client.post('/api/paros-maquina/', self._payload(self.maquina_a), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(ParoMaquina.objects.get(pk=resp.data['id']).usuario, user)

    def test_paro_dado_existente_cuando_edita_o_borra_entonces_404_y_se_conserva(self):
        paro = ParoMaquinaFactory(maquina=self.maquina_a)
        self._como('admin_sistemas')
        url = f'/api/paros-maquina/{paro.id}/'
        self.assertEqual(self.client.patch(url, {'categoria': 'OTRO'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        paro.refresh_from_db()
        self.assertEqual(paro.categoria, 'AVERIA')
