"""
Pruebas de gestion/views/kpi_views.py.

Vistas: KPIAreaView, KpiEjecutivoView, ProduccionResumenView, ProduccionTendenciaView,
ProduccionPorProductoView, ProduccionHistorialProductoView,
ProduccionPorProductoImprimirView.
Las vistas ejecutivas son fachadas que delegan en el Service Layer.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: ramas de autorización de KPIAreaView
  (admin con/ sin area; no-admin con/ sin area).
- Particiones de equivalencia (EP): sede_id válido / ausente / inválido.
- Análisis de valores límite (BVA): fecha_inicio == fecha_fin (borde válido)
  vs. fecha_inicio > fecha_fin (borde inválido) en _parsear_rango_fechas.
- Caja negra: estructura del contrato JSON de respuesta.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, AreaFactory, CustomUserFactory,
    MaquinaFactory, LoteProduccionFactory, ParoMaquinaFactory,
    OrdenProduccionFactory, ProductoFactory,
)


class KPIAreaViewTestCase(TestCase):
    """Caja blanca de la autorización por área."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.url = reverse('kpi-area')

    def test_kpi_area_dado_admin_con_area_param_cuando_get_entonces_200(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url, {'area': self.area.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['area'], self.area.nombre)
        self.assertIn('total_produccion_kg', resp.data)

    def test_kpi_area_dado_admin_sin_area_ni_param_cuando_get_entonces_400(self):
        # Caja blanca: admin sin area_id y sin user.area -> 400
        admin = CustomUserFactory(sede=self.sede, area=None, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kpi_area_dado_no_admin_con_area_propia_cuando_get_entonces_200(self):
        # No-admin (tintorero) ve estrictamente su propia área
        user = CustomUserFactory(sede=self.sede, area=self.area, groups=['tintorero'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['area'], self.area.nombre)

    def test_kpi_area_dado_no_admin_sin_area_cuando_get_entonces_403(self):
        # Caja blanca: no-admin sin área asignada -> 403
        user = CustomUserFactory(sede=self.sede, area=None, groups=['tintorero'])
        self.client.force_authenticate(user=user)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class KPIAreaCalidadRendimientoTestCase(TestCase):
    """
    KPIs reales de calidad y rendimiento para el Jefe de Área.

    Reemplaza el placeholder `rendimiento_yield = 1.0`. Los datos ya existen en
    LoteProduccion (peso_neto_producido, peso_merma, clasificacion_calidad).

    Fundamento industrial:
    - Rendimiento (Yield) = salida buena / entrada = neto / (neto + merma).
    - First Pass Yield (FPY) = neto de primera calidad / neto total (componente
      "Calidad" de OEE). El retrabajo/segunda cuesta 2-3x, por eso se mide aparte.
    """

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.admin)
        self.url = reverse('kpi-area')

    def _crear_lotes(self):
        # 90 kg primera + 10 merma ; 60 kg segunda + 0 merma
        LoteProduccionFactory(
            maquina=self.maquina, peso_neto_producido=Decimal('90.000'),
            peso_merma=Decimal('10.000'), clasificacion_calidad='primera',
        )
        LoteProduccionFactory(
            maquina=self.maquina, peso_neto_producido=Decimal('60.000'),
            peso_merma=Decimal('0.000'), clasificacion_calidad='segunda',
        )

    def test_rendimiento_yield_dado_lotes_con_merma_cuando_get_entonces_valor_real(self):
        # yield = 150 / (150 + 10) = 0.9375 — NO el placeholder 1.0
        self._crear_lotes()
        resp = self.client.get(self.url, {'area': self.area.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(float(resp.data['rendimiento_yield']), 0.9375, places=4)

    def test_first_pass_yield_dado_mezcla_de_calidad_cuando_get_entonces_ratio_primera(self):
        # FPY = 90 (primera) / 150 (total neto) = 0.6
        self._crear_lotes()
        resp = self.client.get(self.url, {'area': self.area.id})
        self.assertAlmostEqual(float(resp.data['first_pass_yield']), 0.6, places=4)

    def test_distribucion_calidad_dado_lotes_cuando_get_entonces_desglose_kg(self):
        self._crear_lotes()
        resp = self.client.get(self.url, {'area': self.area.id})
        dist = resp.data['distribucion_calidad']
        self.assertAlmostEqual(float(dist['primera']), 90.0, places=2)
        self.assertAlmostEqual(float(dist['segunda']), 60.0, places=2)
        self.assertAlmostEqual(float(dist['saldo']), 0.0, places=2)

    def test_kpis_dado_area_sin_lotes_cuando_get_entonces_cero_sin_dividir_por_cero(self):
        # Borde: sin producción, yield/FPY = 0 (no crash por división por cero)
        resp = self.client.get(self.url, {'area': self.area.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(float(resp.data['rendimiento_yield']), 0.0)
        self.assertEqual(float(resp.data['first_pass_yield']), 0.0)

    def test_oee_dado_lote_y_paro_no_planificado_cuando_get_entonces_bloque_oee_con_disponibilidad_real(self):
        # OEE (R4): 8h run_time + 2h downtime no planificado -> disponibilidad = 0.8
        LoteProduccionFactory(
            maquina=self.maquina,
            hora_inicio='2026-01-01T08:00:00',
            hora_final='2026-01-01T16:00:00',
            peso_neto_producido=Decimal('90.000'),
            peso_merma=Decimal('0.000'),
            clasificacion_calidad='primera',
        )
        ParoMaquinaFactory(
            maquina=self.maquina,
            inicio='2026-01-01T16:00:00',
            fin='2026-01-01T18:00:00',
            categoria='AVERIA',
            planificado=False,
        )
        resp = self.client.get(self.url, {'area': self.area.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        oee = resp.data['oee']
        self.assertAlmostEqual(float(oee['disponibilidad']), 0.8, places=4)
        self.assertIn('rendimiento', oee)
        self.assertIn('calidad', oee)
        self.assertIn('oee', oee)
        self.assertIn('downtime_min', oee)


class KpiEjecutivoViewTestCase(TestCase):
    """Contrato JSON del dashboard ejecutivo + parseo de sede_id."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('kpi-ejecutivo')

    def test_kpi_ejecutivo_dado_autenticado_cuando_get_entonces_estructura_completa(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for clave in ('produccion', 'mrp', 'stock', 'cartera'):
            self.assertIn(clave, resp.data)

    def test_kpi_ejecutivo_dado_sede_id_valido_cuando_get_entonces_200(self):
        # EP: sede_id válido
        resp = self.client.get(self.url, {'sede_id': self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_kpi_ejecutivo_dado_sede_id_invalido_cuando_get_entonces_200(self):
        # EP/caja blanca: sede_id no numérico -> _parsear_sede devuelve None (sin crash)
        resp = self.client.get(self.url, {'sede_id': 'abc'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ProduccionResumenTendenciaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)

    def test_resumen_dado_autenticado_cuando_get_entonces_ops_por_estado(self):
        resp = self.client.get(reverse('produccion-resumen'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('ops_por_estado', resp.data)
        self.assertEqual(len(resp.data['ops_por_estado']), 3)

    def test_tendencia_dado_autenticado_cuando_get_entonces_lista(self):
        resp = self.client.get(reverse('produccion-tendencia'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)


class ParsearRangoFechasTestCase(TestCase):
    """
    Caja blanca de `_parsear_rango_fechas` (helper compartido por los 3
    endpoints de drill-down de producto). Ejercitado vía ProduccionPorProductoView.
    """

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('produccion-por-producto')

    def test_rango_dado_sin_parametros_cuando_get_entonces_default_hoy(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)

    def test_rango_dado_fecha_mal_formada_cuando_get_entonces_400(self):
        resp = self.client.get(self.url, {'fecha_inicio': '01-01-2026'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('formato', resp.data['detail'])

    def test_rango_dado_fecha_inicio_posterior_a_fin_cuando_get_entonces_400(self):
        resp = self.client.get(self.url, {
            'fecha_inicio': '2026-06-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('posterior', resp.data['detail'])

    def test_rango_dado_fecha_inicio_igual_a_fin_cuando_get_entonces_200(self):
        # BVA: borde válido — mismo día es un rango de longitud 1, no error.
        resp = self.client.get(self.url, {
            'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)


class ProduccionPorProductoViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('produccion-por-producto')

    def test_produccion_por_producto_dado_lotes_en_rango_cuando_get_entonces_agrupa_por_producto(self):
        producto = ProductoFactory(codigo='TELA-001', descripcion='Tela Azul')
        orden = OrdenProduccionFactory(producto_salida=producto)
        LoteProduccionFactory(
            orden_produccion=orden, peso_neto_producido=Decimal('50.000'),
        )
        resp = self.client.get(self.url, {
            'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['producto_codigo'], 'TELA-001')
        self.assertEqual(resp.data[0]['num_lotes'], 1)

    def test_produccion_por_producto_dado_sin_lotes_en_rango_cuando_get_entonces_lista_vacia(self):
        resp = self.client.get(self.url, {
            'fecha_inicio': '2020-01-01', 'fecha_fin': '2020-01-02',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, [])


class ProduccionHistorialProductoViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('produccion-historial-producto')

    def test_historial_producto_dado_producto_id_ausente_cuando_get_entonces_400(self):
        resp = self.client.get(self.url, {
            'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('producto_id', resp.data['detail'])

    def test_historial_producto_dado_producto_id_no_numerico_cuando_get_entonces_400(self):
        resp = self.client.get(self.url, {'producto_id': 'abc'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_historial_producto_dado_producto_valido_cuando_get_entonces_serie_diaria(self):
        producto = ProductoFactory(codigo='TELA-002')
        orden = OrdenProduccionFactory(producto_salida=producto)
        LoteProduccionFactory(
            orden_produccion=orden, peso_neto_producido=Decimal('30.000'),
        )
        resp = self.client.get(self.url, {
            'producto_id': producto.id,
            'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(float(resp.data[0]['kg']), 30.0)


class ProduccionPorProductoImprimirViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede, groups=['ejecutivo'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('produccion-por-producto-imprimir')

    def test_imprimir_dado_fecha_mal_formada_cuando_get_entonces_400(self):
        # La misma validación de rango se comparte vía _parsear_rango_fechas.
        resp = self.client.get(self.url, {'fecha_inicio': 'no-es-fecha'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('gestion.views.kpi_views.PrintingService.generate_produccion_por_producto_pdf')
    def test_imprimir_dado_servicio_disponible_cuando_get_entonces_200_pdf(self, mock_pdf):
        mock_pdf.return_value = b'%PDF-produccion-por-producto'
        resp = self.client.get(self.url, {
            'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertEqual(resp.content, b'%PDF-produccion-por-producto')
        mock_pdf.assert_called_once()

    @patch('gestion.views.kpi_views.PrintingService.generate_produccion_por_producto_pdf')
    def test_imprimir_dado_servicio_caido_cuando_get_entonces_503(self, mock_pdf):
        mock_pdf.return_value = None
        resp = self.client.get(self.url, {
            'fecha_inicio': '2026-01-01', 'fecha_fin': '2026-01-01',
        })
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
