"""
Tests de API de transformaciones de producto (endpoints de OrdenProduccionViewSet).

Técnicas ISTQB:
- Caja negra: códigos de respuesta de la API (201, 400, 401/403, 200).
- Tabla de decisión RBAC: rol × acción.
- Aislamiento multi-sede: un jefe de otra área/sede no puede registrar.

Endpoints:
  POST ordenproduccion-registrar-transformacion
  GET  ordenproduccion-transformaciones
  GET  ordenproduccion-trazabilidad
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import TransformacionProducto
from gestion.tests.factories import (
    SedeFactory, AreaFactory, ProductoFactory, CustomUserFactory,
    MaquinaFactory, OrdenProduccionFactory,
)


def _payload(maquina, salida, **overrides):
    base = {
        'maquina': maquina.id,
        'producto_salida': salida.id,
        'peso_entrada': '100.000',
        'peso_salida': '95.000',
        'fecha_inicio': '2026-01-01T08:00:00Z',
        'fecha_fin': '2026-01-01T12:00:00Z',
        'observaciones': 'Proceso normal',
    }
    base.update(overrides)
    return base


class RegistrarTransformacionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.orden = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.maquina = MaquinaFactory(area=self.area)
        self.salida = ProductoFactory(codigo='LANA-REC', sede=self.sede)
        self.url = reverse('ordenproduccion-registrar-transformacion', args=[self.orden.id])

    def test_api_dado_jefe_area_cuando_registrar_transformacion_entonces_201(self):
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TransformacionProducto.objects.filter(orden_produccion=self.orden).count(), 1)

    def test_api_dado_operario_cuando_registrar_transformacion_entonces_201(self):
        operario = CustomUserFactory(sede=self.sede, area=self.area, groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_api_dado_admin_sistemas_cuando_registrar_transformacion_entonces_201(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_api_dado_bodeguero_cuando_registrar_transformacion_entonces_403(self):
        bodeguero = CustomUserFactory(sede=self.sede, area=self.area, groups=['bodeguero'])
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_dado_anonimo_cuando_registrar_transformacion_entonces_no_autorizado(self):
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_api_dado_jefe_de_otra_area_cuando_registrar_entonces_403(self):
        # Aislamiento: jefe de área distinta (incluso otra sede) no puede registrar
        otra_sede = SedeFactory()
        otra_area = AreaFactory(sede=otra_sede)
        jefe_otro = CustomUserFactory(sede=otra_sede, area=otra_area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe_otro)
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_dado_peso_salida_mayor_cuando_registrar_entonces_400(self):
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        resp = self.client.post(
            self.url,
            _payload(self.maquina, self.salida, peso_entrada='90.000', peso_salida='95.000'),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_dado_operario_sin_area_cuando_registrar_entonces_403(self):
        # Un operario sin área asignada no puede operar ninguna orden.
        operario = CustomUserFactory(sede=self.sede, area=None, groups=['operario'])
        self.client.force_authenticate(user=operario)
        resp = self.client.post(self.url, _payload(self.maquina, self.salida), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_dado_producto_salida_inexistente_cuando_registrar_entonces_400(self):
        jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=jefe)
        payload = _payload(self.maquina, self.salida)
        payload['producto_salida'] = 999999
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_dado_anonimo_cuando_get_trazabilidad_entonces_no_autorizado(self):
        url = reverse('ordenproduccion-trazabilidad', args=[self.orden.id])
        resp = self.client.get(url)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


class ConsultarTransformacionesAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.orden = OrdenProduccionFactory(sede=self.sede, area=self.area)
        self.maquina = MaquinaFactory(area=self.area)
        self.jefe = CustomUserFactory(sede=self.sede, area=self.area, groups=['jefe_area'])
        self.client.force_authenticate(user=self.jefe)

    def _registrar(self, salida_codigo, peso_e, peso_s):
        from gestion.services.transformacion import TransformacionService
        salida = ProductoFactory(codigo=salida_codigo, sede=self.sede)
        return TransformacionService.registrar(
            self.orden,
            {
                'maquina': self.maquina.id,
                'producto_salida': salida.id,
                'peso_entrada': Decimal(peso_e),
                'peso_salida': Decimal(peso_s),
                'fecha_inicio': '2026-01-01T08:00:00Z',
                'fecha_fin': '2026-01-01T12:00:00Z',
            },
            self.jefe,
        )

    def test_api_dado_transformaciones_cuando_get_lista_entonces_200_ordenada(self):
        self._registrar('LANA-REC', '100.000', '95.000')
        self._registrar('LANA-TOPS', '95.000', '90.000')
        url = reverse('ordenproduccion-transformaciones', args=[self.orden.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # La acción devuelve la lista completa de pasos (sin paginar).
        data = resp.data
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['numero_secuencia'], 1)

    def test_api_dado_op_con_flujo_cuando_get_trazabilidad_entonces_200_con_merma(self):
        self._registrar('LANA-REC', '100.000', '95.000')
        self._registrar('LANA-TOPS', '95.000', '90.000')
        url = reverse('ordenproduccion-trazabilidad', args=[self.orden.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['pasos']), 2)
        self.assertEqual(Decimal(str(resp.data['merma_total'])), Decimal('10.000'))

    def test_api_dado_jefe_de_otra_area_cuando_get_trazabilidad_entonces_403(self):
        # Aislamiento de lectura: un jefe de otra área/sede no ve la trazabilidad.
        otra_sede = SedeFactory()
        otra_area = AreaFactory(sede=otra_sede)
        intruso = CustomUserFactory(sede=otra_sede, area=otra_area, groups=['jefe_area'])
        self.client.force_authenticate(user=intruso)
        url = reverse('ordenproduccion-trazabilidad', args=[self.orden.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_dado_jefe_de_otra_area_cuando_get_transformaciones_entonces_403(self):
        otra_sede = SedeFactory()
        otra_area = AreaFactory(sede=otra_sede)
        intruso = CustomUserFactory(sede=otra_sede, area=otra_area, groups=['jefe_area'])
        self.client.force_authenticate(user=intruso)
        url = reverse('ordenproduccion-transformaciones', args=[self.orden.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
