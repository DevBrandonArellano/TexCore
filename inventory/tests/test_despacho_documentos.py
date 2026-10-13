"""
Pruebas de los documentos imprimibles de Despacho (HistorialDespachoViewSet):
- imprimir: listado del historial de despachos filtrado por fecha, en PDF.
- guia_remision: Guía de Remisión informativa (NO autorizada por el SRI).

Técnicas ISTQB aplicadas:
- Partición de equivalencia: servicio de impresión disponible / caído.
- Caja negra: validación de campos requeridos de la guía de remisión.
"""
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import Bodega, Cliente, CustomUser, LoteProduccion, OrdenProduccion, PedidoVenta, Producto, Sede
from inventory.models import (
    DetalleHistorialDespacho,
    DetalleHistorialDespachoPedido,
    HistorialDespacho,
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
        # Con sede: el historial de despachos se acota a la sede de sus pedidos (OWASP A01).
        self.pedido = PedidoVenta.objects.create(
            cliente=self.cliente, guia_remision='GR-DOC-001', estado='despachado', sede=self.sede,
        )
        orden = OrdenProduccion.objects.create(
            codigo='OP-DOC-001', peso_neto_requerido=Decimal('50.00'), producto_salida=self.producto,
        )
        self.lote = LoteProduccion.objects.create(
            codigo_lote='LOTE-DOC-001', orden_produccion=orden,
            peso_neto_producido=Decimal('50.000'), turno='DIURNO',
            hora_inicio=datetime(2026, 8, 20, 8, 0, tzinfo=UTC), hora_final=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
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

    def test_imprimir_dado_muchos_despachos_cuando_get_entonces_parametros_sql_no_crecen_con_las_filas(self):
        """
        Sin filtro de fechas se imprimen todos los despachos de la sede. Con
        prefetch_related, cada consulta llevaba un IN con un parámetro por
        despacho: en SQL Server, sobre ~26 000 despachos, superaba el límite de
        2100 parámetros y la vista respondía 500. Debe resolverse con subconsultas.
        """
        for i in range(30):
            historial = HistorialDespacho.objects.create(
                usuario=self.usuario, total_bultos=1, total_peso=Decimal('1.000'),
            )
            DetalleHistorialDespachoPedido.objects.create(
                historial=historial, pedido=self.pedido, cantidad_despachada=Decimal(f'{i + 1}.000'),
            )

        parametros_por_consulta = []

        def _contar_parametros(execute, sql, params, many, context):
            parametros_por_consulta.append(len(params or ()))
            return execute(sql, params, many, context)

        with patch(
            'inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf, connection.execute_wrapper(_contar_parametros):
            resp = self.client.get(reverse('historial-despachos-imprimir'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mock_pdf.call_args[0][0]['despachos']), 31)
        self.assertLess(max(parametros_por_consulta), 10)

    def _usuarios_en_pdf(self):
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf:
            self.client.get(reverse('historial-despachos-imprimir'))
        return {d['id']: d['usuario_nombre'] for d in mock_pdf.call_args[0][0]['despachos']}

    def _historial_con_pedido(self, usuario):
        historial = HistorialDespacho.objects.create(usuario=usuario, total_bultos=1, total_peso=Decimal('1.000'))
        DetalleHistorialDespachoPedido.objects.create(
            historial=historial, pedido=self.pedido, cantidad_despachada=Decimal('1.000'),
        )
        return historial

    def test_imprimir_dado_usuario_con_nombre_completo_cuando_get_entonces_usa_el_nombre(self):
        self.usuario.first_name, self.usuario.last_name = 'Ana', 'Pérez'
        self.usuario.save(update_fields=['first_name', 'last_name'])
        self.assertEqual(self._usuarios_en_pdf()[self.historial.id], 'Ana Pérez')

    def test_imprimir_dado_usuario_sin_nombre_cuando_get_entonces_usa_el_username(self):
        self.assertEqual(self._usuarios_en_pdf()[self.historial.id], 'despacho_docs')

    def test_imprimir_dado_despacho_sin_usuario_cuando_get_entonces_usuario_nombre_es_none(self):
        sin_usuario = self._historial_con_pedido(usuario=None)
        self.assertIsNone(self._usuarios_en_pdf()[sin_usuario.id])

    def test_imprimir_dado_pedido_sin_cliente_cuando_get_entonces_muestra_na(self):
        pedido_sin_cliente = PedidoVenta.objects.create(
            cliente=None, guia_remision='GR-SIN-CLI', estado='despachado', sede=self.sede,
        )
        DetalleHistorialDespachoPedido.objects.create(
            historial=self.historial, pedido=pedido_sin_cliente, cantidad_despachada=Decimal('1.000'),
        )
        with patch(
            'inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf',
            return_value=b'%PDF-fake',
        ) as mock_pdf:
            self.client.get(reverse('historial-despachos-imprimir'))
        pedidos = mock_pdf.call_args[0][0]['despachos'][0]['pedidos']
        self.assertEqual(pedidos, 'Cliente Documentos (GR-DOC-001), N/A (GR-SIN-CLI)')

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
