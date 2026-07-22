"""
Pruebas complementarias de gestion/views/production_views.py — cubre los
ViewSets/acciones que test_production_views.py no ejercita:

- OrdenProduccionViewSet: registrar_transformacion / transformaciones /
  trazabilidad (aislamiento por área/sede) y creación (perform_create).
- ComponenteMezclaOPViewSet, ConsumoLoteDetalleViewSet.
- AreaProcessStepViewSet, EtapaProduccionViewSet.
- TransferenciaInterareaViewSet.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol con permiso / sin permiso, área
  coincide / no coincide con la de la orden.
- Caja blanca: ramas de `_puede_operar_area` (superuser/admin vs. área+sede
  exacta) y de `get_queryset` por rol en cada ViewSet.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    AreaProcessStep, EtapaProduccion, ProcessStep, TransferenciaInterarea,
)
from gestion.tests.factories import (
    AreaFactory, BodegaFactory, ComponenteMezclaOPFactory, ConsumoLoteDetalleFactory,
    CustomUserFactory, MaquinaFactory, OrdenProduccionFactory,
    ProductoFactory, SedeFactory,
)


class RegistrarTransformacionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.producto_entrada = ProductoFactory(sede=self.sede)
        self.producto_salida = ProductoFactory(sede=self.sede)
        self.orden = OrdenProduccionFactory(
            sede=self.sede, area=self.area, producto_entrada=self.producto_entrada,
        )
        self.jefe_area = CustomUserFactory(groups=['jefe_area'], area=self.area, sede=self.sede)
        self.client.force_authenticate(user=self.jefe_area)
        self.url = reverse('ordenproduccion-registrar-transformacion', kwargs={'pk': self.orden.id})

    def _payload(self, **overrides):
        base = {
            'maquina': self.maquina.id,
            'producto_salida': self.producto_salida.id,
            'peso_entrada': '100.000',
            'peso_salida': '95.000',
            'fecha_inicio': '2026-01-01T08:00:00Z',
            'fecha_fin': '2026-01-01T09:00:00Z',
        }
        base.update(overrides)
        return base

    def test_registrar_dado_usuario_de_otra_area_cuando_post_entonces_403(self):
        otra_area = AreaFactory()
        operario_otra_area = CustomUserFactory(groups=['jefe_area'], area=otra_area)
        self.client.force_authenticate(user=operario_otra_area)

        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_registrar_dado_datos_validos_cuando_post_entonces_201(self):
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['numero_secuencia'], 1)

    def test_registrar_dado_maquina_de_otra_area_cuando_post_entonces_400(self):
        maquina_otra_area = MaquinaFactory()
        resp = self.client.post(self.url, self._payload(maquina=maquina_otra_area.id), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transformaciones_dado_op_con_pasos_cuando_get_entonces_lista_ordenada(self):
        self.client.post(self.url, self._payload(), format='json')
        url_list = reverse('ordenproduccion-transformaciones', kwargs={'pk': self.orden.id})

        resp = self.client.get(url_list)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_transformaciones_dado_usuario_de_otra_area_cuando_get_entonces_403(self):
        otra_area = AreaFactory()
        operario_otra_area = CustomUserFactory(groups=['jefe_area'], area=otra_area)
        self.client.force_authenticate(user=operario_otra_area)
        url_list = reverse('ordenproduccion-transformaciones', kwargs={'pk': self.orden.id})

        resp = self.client.get(url_list)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_trazabilidad_dado_op_cuando_get_entonces_200(self):
        url_traza = reverse('ordenproduccion-trazabilidad', kwargs={'pk': self.orden.id})
        resp = self.client.get(url_traza)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_trazabilidad_dado_admin_sistemas_cuando_get_entonces_200(self):
        # Caja blanca: rama admin/superuser de _puede_operar_area (bypass área/sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        url_traza = reverse('ordenproduccion-trazabilidad', kwargs={'pk': self.orden.id})
        resp = self.client.get(url_traza)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class OrdenProduccionCreateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.jefe_planta = CustomUserFactory(groups=['jefe_planta'], sede=self.sede)
        self.client.force_authenticate(user=self.jefe_planta)
        self.url = reverse('ordenproduccion-list')

    def test_create_dado_usuario_sin_permiso_cuando_post_entonces_403(self):
        operario = CustomUserFactory(groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.post(self.url, {
            'codigo': 'OP-CREATE-1', 'producto_entrada': self.producto.id,
            'peso_neto_requerido': '50.00', 'area': self.area.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_jefe_area_cuando_post_entonces_403(self):
        # Regla de negocio: la OP la genera el Jefe de Planta para un área
        # específica; el Jefe de Área solo asigna sus recursos (máquina/operario),
        # no crea órdenes.
        jefe_area = CustomUserFactory(groups=['jefe_area'], sede=self.sede, area=self.area)
        self.client.force_authenticate(user=jefe_area)
        resp = self.client.post(self.url, {
            'codigo': 'OP-CREATE-JEFE-AREA', 'producto_entrada': self.producto.id,
            'peso_neto_requerido': '50.00', 'area': self.area.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_jefe_planta_sin_sede_explicita_cuando_post_entonces_usa_sede_del_usuario(self):
        # Caja blanca: perform_create asigna sede=user.sede si el serializer no la trae
        resp = self.client.post(self.url, {
            'codigo': 'OP-CREATE-2', 'producto_entrada': self.producto.id,
            'peso_neto_requerido': '50.00', 'area': self.area.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['sede'], self.sede.id)


class ComponenteMezclaOPViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.orden = OrdenProduccionFactory(sede=self.sede)
        self.componente = ComponenteMezclaOPFactory(orden=self.orden)
        self.user = CustomUserFactory(groups=['jefe_area'], sede=self.sede)
        self.client.force_authenticate(user=self.user)

    def test_list_dado_usuario_de_la_sede_cuando_get_entonces_filtra_por_sede(self):
        otra_sede = SedeFactory()
        otra_orden = OrdenProduccionFactory(sede=otra_sede)
        ComponenteMezclaOPFactory(orden=otra_orden)

        resp = self.client.get(reverse('componente-mezcla-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [c['id'] for c in resp.data['results']]
        self.assertIn(self.componente.id, ids)

    def test_destroy_dado_sin_justificacion_cuando_delete_entonces_400(self):
        url = reverse('componente-mezcla-detail', kwargs={'pk': self.componente.id})
        resp = self.client.delete(url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destroy_dado_justificacion_cuando_delete_entonces_204(self):
        url = reverse('componente-mezcla-detail', kwargs={'pk': self.componente.id})
        resp = self.client.delete(url, {'justificacion': 'Corrección de mezcla QA'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class ConsumoLoteDetalleViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = CustomUserFactory()
        self.client.force_authenticate(user=self.user)
        self.consumo = ConsumoLoteDetalleFactory()

    def test_list_dado_filtro_lote_produccion_cuando_get_entonces_filtra(self):
        ConsumoLoteDetalleFactory()  # otro consumo, no debe aparecer al filtrar

        resp = self.client.get(
            reverse('consumo-lote-detalle-list'),
            {'lote_produccion': self.consumo.lote_produccion_id},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)
        self.assertEqual(resp.data['results'][0]['id'], self.consumo.id)


class AreaProcessStepViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area = AreaFactory()
        self.proceso = ProcessStep.objects.create(name='Teñido QA')
        self.step = AreaProcessStep.objects.create(area=self.area, proceso=self.proceso, orden=1)

    def test_list_dado_admin_sistemas_cuando_get_entonces_ve_todo(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(reverse('area-process-step-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_list_dado_jefe_de_otra_area_cuando_get_entonces_no_ve_el_step(self):
        otra_area = AreaFactory()
        jefe = CustomUserFactory(groups=['jefe_area'], area=otra_area)
        self.client.force_authenticate(user=jefe)
        resp = self.client.get(reverse('area-process-step-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)

    def test_list_dado_jefe_del_area_correcta_cuando_get_entonces_ve_el_step(self):
        jefe = CustomUserFactory(groups=['jefe_area'], area=self.area)
        self.client.force_authenticate(user=jefe)
        resp = self.client.get(reverse('area-process-step-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)


class EtapaProduccionViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area = AreaFactory()
        self.maquina = MaquinaFactory(area=self.area)
        self.bodega_a = BodegaFactory()
        self.bodega_b = BodegaFactory()
        self.etapa = EtapaProduccion.objects.create(
            area=self.area, nombre='Teñido', orden=1, maquina=self.maquina,
            bodega_entrada=self.bodega_a, bodega_salida=self.bodega_b,
        )

    def test_list_dado_jefe_planta_cuando_get_entonces_ve_todo(self):
        jefe_planta = CustomUserFactory(groups=['jefe_planta'])
        self.client.force_authenticate(user=jefe_planta)
        resp = self.client.get(reverse('etapa-produccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_list_dado_usuario_sin_area_cuando_get_entonces_vacio(self):
        user = CustomUserFactory(groups=['jefe_area'], area=None)
        self.client.force_authenticate(user=user)
        resp = self.client.get(reverse('etapa-produccion-list'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)


class TransferenciaInterareaViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.area_origen = AreaFactory()
        self.area_destino = AreaFactory()
        self.orden_origen = OrdenProduccionFactory(area=self.area_origen)
        self.orden_destino = OrdenProduccionFactory(area=self.area_destino)
        self.bodega_origen = BodegaFactory()
        self.bodega_destino = BodegaFactory()
        self.jefe_planta = CustomUserFactory(groups=['jefe_planta'])

    def _payload(self):
        return {
            'orden_area_origen': self.orden_origen.id,
            'orden_area_destino': self.orden_destino.id,
            'bodega_origen': self.bodega_origen.id,
            'bodega_destino': self.bodega_destino.id,
            'cantidad_transferida': '15.000',
        }

    def test_create_dado_jefe_area_cuando_post_entonces_403(self):
        # Caja blanca: create/update/destroy exigen IsJefePlantaOrAdmin, no IsJefeAreaOrAdmin.
        jefe_area = CustomUserFactory(groups=['jefe_area'], area=self.area_origen)
        self.client.force_authenticate(user=jefe_area)
        resp = self.client.post(reverse('transferencia-interarea-list'), self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_datos_validos_cuando_post_entonces_201_asigna_responsable(self):
        # Regresión del bug QA: orden_area_origen/orden_area_destino eran nested
        # read_only=True pese a ser NOT NULL en el modelo -> POST válido siempre
        # daba 500. Corregido: son PrimaryKeyRelatedField escribibles; el detalle
        # anidado se expone en *_detail para no perder la representación de lectura.
        self.client.force_authenticate(user=self.jefe_planta)
        resp = self.client.post(reverse('transferencia-interarea-list'), self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        transferencia = TransferenciaInterarea.objects.get(id=resp.data['id'])
        self.assertEqual(transferencia.usuario_responsable, self.jefe_planta)
        self.assertEqual(transferencia.orden_area_origen_id, self.orden_origen.id)
        self.assertEqual(resp.data['orden_area_origen_detail']['id'], self.orden_origen.id)

    def test_list_dado_jefe_area_de_area_relacionada_cuando_get_entonces_ve_la_transferencia(self):
        # Se crea directo por ORM (bypass del create roto) para poder probar
        # el filtrado de get_queryset de forma aislada.
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_origen, orden_area_destino=self.orden_destino,
            bodega_origen=self.bodega_origen, bodega_destino=self.bodega_destino,
            cantidad_transferida=Decimal('15.000'), usuario_responsable=self.jefe_planta,
        )

        jefe_area = CustomUserFactory(groups=['jefe_area'], area=self.area_destino)
        self.client.force_authenticate(user=jefe_area)
        resp = self.client.get(reverse('transferencia-interarea-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_list_dado_jefe_area_no_relacionada_cuando_get_entonces_vacio(self):
        TransferenciaInterarea.objects.create(
            orden_area_origen=self.orden_origen, orden_area_destino=self.orden_destino,
            bodega_origen=self.bodega_origen, bodega_destino=self.bodega_destino,
            cantidad_transferida=Decimal('15.000'),
        )

        otra_area = AreaFactory()
        jefe_area = CustomUserFactory(groups=['jefe_area'], area=otra_area)
        self.client.force_authenticate(user=jefe_area)
        resp = self.client.get(reverse('transferencia-interarea-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 0)
