"""
Pruebas de los documentos imprimibles de Despacho (HistorialDespachoViewSet):
- imprimir: listado del historial de despachos filtrado por fecha, en PDF.
- guia_remision: Guía de Remisión informativa (NO autorizada por el SRI).

Técnicas ISTQB aplicadas:
- Partición de equivalencia: servicio de impresión disponible / caído.
- Caja negra: validación de campos requeridos de la guía de remisión.
"""
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    CustomUser, Bodega, Producto, LoteProduccion, OrdenProduccion,
    PedidoVenta, Sede, Cliente
)
from inventory.models import (
    HistorialDespacho, DetalleHistorialDespacho, DetalleHistorialDespachoPedido,
)


class HistorialDespachosDocumentosTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = Sede.objects.create(nombre='Sede Test Documentos', location='Quito')
        self.usuario = CustomUser.objects.create_user(
            username='despacho_docs', password='test123', sede=self.sede,
        )
        despacho_group, _ = Group.objects.get_or_create(name='despacho')
        self.usuario.groups.add(despacho_group)
        self.client.force_authenticate(user=self.usuario)

        self.bodega = Bodega.objects.create(nombre='Bodega Test', sede=self.sede)
        self.producto = Producto.objects.create(
            codigo='TELA-DOC', descripcion='Tela de prueba', tipo='tela',
            stock_minimo=Decimal('0.00'), unidad_medida='kg',
        )
        self.cliente = Cliente.objects.create(
            ruc_cedula='1790000000001', nombre_razon_social='Cliente Documentos',
            direccion_envio='Av. Prueba 123', nivel_precio='normal',
        )
        self.pedido = PedidoVenta.objects.create(
            cliente=self.cliente, guia_remision='GR-DOC-001', estado='despachado',
        )
        orden = OrdenProduccion.objects.create(
            codigo='OP-DOC-001', peso_neto_requerido=Decimal('50.00'), producto_salida=self.producto,
        )
        self.lote = LoteProduccion.objects.create(
            codigo_lote='LOTE-DOC-001', orden_produccion=orden,
            peso_neto_producido=Decimal('50.000'), turno='DIURNO',
            hora_inicio=datetime(2026, 8, 20, 8, 0), hora_final=datetime(2026, 8, 20, 9, 0),
        )
        self.historial = HistorialDespacho.objects.create(
            usuario=self.usuario, total_bultos=1, total_peso=Decimal('50.000'),
        )
        DetalleHistorialDespachoPedido.objects.create(
            historial=self.historial, pedido=self.pedido, cantidad_despachada=Decimal('50.000'),
        )
        DetalleHistorialDespacho.objects.create(
            historial=self.historial, lote=self.lote, producto=self.producto,
            peso=Decimal('50.000'), pedido=self.pedido,
        )

    # ------------------------------------------------------------------ imprimir

    def test_imprimir_dado_servicio_disponible_cuando_get_entonces_200_pdf(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf:
            resp = self.client.get(reverse('historial-despachos-imprimir'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(len(data_enviada['despachos']), 1)
        self.assertEqual(data_enviada['despachos'][0]['id'], self.historial.id)
        self.assertIn('Cliente Documentos', data_enviada['despachos'][0]['pedidos'])

    def test_imprimir_dado_filtro_de_fecha_fuera_de_rango_cuando_get_entonces_lista_vacia(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf:
            resp = self.client.get(
                reverse('historial-despachos-imprimir'),
                {'fecha_desde': '2020-01-01', 'fecha_hasta': '2020-01-02'},
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(data_enviada['despachos'], [])
        self.assertEqual(data_enviada['fecha_desde'], '2020-01-01')

    def test_imprimir_dado_servicio_caido_cuando_get_entonces_503(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf',
            return_value=None,
        ):
            resp = self.client.get(reverse('historial-despachos-imprimir'))
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    # -------------------------------------------------------------- guia_remision

    def _payload_guia_valido(self, **overrides):
        payload = {
            'motivo_traslado': 'Venta',
            'punto_partida': 'Planta Quito, Av. Industrial s/n',
            'fecha_inicio_transporte': '20/08/2026',
            'fecha_fin_transporte': '20/08/2026',
            'transporte_propio': True,
            'placa_vehiculo': 'PBX-1234',
        }
        payload.update(overrides)
        return payload

    def test_guia_remision_dado_datos_validos_cuando_post_entonces_200_pdf(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf:
            resp = self.client.post(
                reverse('historial-despachos-guia-remision', args=[self.historial.id]),
                self._payload_guia_valido(), format='json',
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {getattr(resp, 'data', None)}")
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(data_enviada['numero'], f'001-001-{self.historial.id:09d}')
        self.assertEqual(len(data_enviada['destinatarios']), 1)
        self.assertEqual(data_enviada['destinatarios'][0]['razon_social'], 'Cliente Documentos')
        self.assertEqual(data_enviada['destinatarios'][0]['identificacion'], '1790000000001')
        self.assertEqual(len(data_enviada['detalles']), 1)
        self.assertEqual(data_enviada['detalles'][0]['cantidad'], 50.0)
        self.assertTrue(data_enviada['transporte_propio'])

    def test_guia_remision_dado_transporte_tercero_sin_transportista_cuando_post_entonces_400(self):
        resp = self.client.post(
            reverse('historial-despachos-guia-remision', args=[self.historial.id]),
            self._payload_guia_valido(transporte_propio=False), format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('transportista_nombre', resp.data)

    def test_guia_remision_dado_transporte_tercero_con_transportista_cuando_post_entonces_200(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf:
            resp = self.client.post(
                reverse('historial-despachos-guia-remision', args=[self.historial.id]),
                self._payload_guia_valido(
                    transporte_propio=False,
                    transportista_nombre='Transportes Andinos S.A.',
                    transportista_ruc='1790000000099',
                ), format='json',
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(data_enviada['transportista_nombre'], 'Transportes Andinos S.A.')

    def test_guia_remision_dado_motivo_faltante_cuando_post_entonces_400(self):
        payload = self._payload_guia_valido()
        del payload['motivo_traslado']
        resp = self.client.post(
            reverse('historial-despachos-guia-remision', args=[self.historial.id]),
            payload, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('motivo_traslado', resp.data)

    def test_guia_remision_dado_servicio_caido_cuando_post_entonces_503(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf',
            return_value=None,
        ):
            resp = self.client.post(
                reverse('historial-despachos-guia-remision', args=[self.historial.id]),
                self._payload_guia_valido(), format='json',
            )
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
