"""
Pruebas de TrazabilidadPorCodigoLoteView (gestion/views/production_lote_views.py).

Endpoint destino del QR impreso en la etiqueta de cada lote (ver
TRAZABILIDAD_BASE_URL / LoteProduccionViewSet._build_zpl_payload): resuelve
codigo_lote -> orden_produccion y reutiliza TrazabilidadService.construir.

Técnicas ISTQB aplicadas:
- Partición de equivalencia: código existente / inexistente.
- Caja negra de seguridad: acceso sin autenticar.
- Caso límite de datos: codigo_lote duplicado entre órdenes distintas
  (unique_together = ('codigo_lote', 'orden_produccion'), no es único global).
"""
from datetime import datetime

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import CustomUserFactory, OrdenProduccionFactory, LoteProduccionFactory


class TrazabilidadPorCodigoLoteViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.op = OrdenProduccionFactory()
        self.lote = LoteProduccionFactory(orden_produccion=self.op, codigo_lote='LOT-0001')

    def test_trazabilidad_dado_codigo_existente_cuando_get_entonces_200_con_datos_de_la_orden(self):
        user = CustomUserFactory(sede=self.op.sede, groups=['operario'])
        self.client.force_authenticate(user=user)

        resp = self.client.get(reverse('trazabilidad-por-codigo-lote', args=['LOT-0001']))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['orden_id'], self.op.id)
        self.assertEqual(resp.data['orden_codigo'], self.op.codigo)

    def test_trazabilidad_dado_codigo_inexistente_cuando_get_entonces_404(self):
        user = CustomUserFactory(sede=self.op.sede, groups=['operario'])
        self.client.force_authenticate(user=user)

        resp = self.client.get(reverse('trazabilidad-por-codigo-lote', args=['NO-EXISTE']))

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_trazabilidad_dado_usuario_sin_autenticar_cuando_get_entonces_401_o_403(self):
        resp = self.client.get(reverse('trazabilidad-por-codigo-lote', args=['LOT-0001']))

        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_trazabilidad_dado_codigo_duplicado_en_dos_ordenes_cuando_get_entonces_devuelve_el_mas_reciente(self):
        # codigo_lote solo es unique_together con orden_produccion: dos ordenes
        # distintas pueden compartir el mismo codigo_lote. El endpoint resuelve
        # la ambigüedad devolviendo el lote más reciente por hora_final.
        op_vieja = OrdenProduccionFactory(codigo='OP-VIEJA')
        LoteProduccionFactory(
            orden_produccion=op_vieja, codigo_lote='LOT-DUP',
            hora_inicio=datetime(2026, 1, 1, 8, 0), hora_final=datetime(2026, 1, 1, 9, 0),
        )
        op_reciente = OrdenProduccionFactory(codigo='OP-RECIENTE')
        LoteProduccionFactory(
            orden_produccion=op_reciente, codigo_lote='LOT-DUP',
            hora_inicio=datetime(2026, 6, 1, 8, 0), hora_final=datetime(2026, 6, 1, 9, 0),
        )
        user = CustomUserFactory(sede=op_reciente.sede, groups=['operario'])
        self.client.force_authenticate(user=user)

        resp = self.client.get(reverse('trazabilidad-por-codigo-lote', args=['LOT-DUP']))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['orden_id'], op_reciente.id)
