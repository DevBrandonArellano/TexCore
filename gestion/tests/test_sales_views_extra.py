"""
Pruebas complementarias de gestion/views/sales_views.py — cubre ramas que
test_pago_seguridad_p0.py, test_pedido_venta_anulacion.py y
test_anticipos_pagos_parciales_p1.py no ejercitan: filtros de queryset por
vendedor, auto-asignación en create, exportación de PDF, y las ramas de
error de PagoClienteViewSet.destroy.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol con visión gerencial / vendedor propio,
  microservicio de impresión disponible / caído.
- Caja blanca: ramas de auto-asignación de vendedor/sede en perform_create,
  ramas except ValueError / except Exception en destroy.
"""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    ClienteFactory, CustomUserFactory, ProductoFactory, SedeFactory,
)
from gestion.models import Cliente, DetallePedido, PagoCliente, PedidoVenta


class ClienteViewSetExtraTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()

    def test_create_dado_vendedor_cuando_post_entonces_autoasigna_vendedor_y_sede(self):
        vendedor = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        self.client.force_authenticate(user=vendedor)

        resp = self.client.post(reverse('cliente-list'), {
            'nombre_razon_social': 'Cliente Auto QA', 'ruc_cedula': '1799999999',
            'direccion_envio': 'Calle QA', 'limite_credito': '500.00', 'nivel_precio': 'normal',
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cliente = Cliente.objects.get(id=resp.data['id'])
        self.assertEqual(cliente.vendedor_asignado, vendedor)
        self.assertEqual(cliente.sede, self.sede)

    def test_create_dado_admin_cuando_post_con_sede_explicita_entonces_no_sobreescribe(self):
        otra_sede = SedeFactory()
        admin = CustomUserFactory(groups=['admin_sistemas'], sede=self.sede)
        self.client.force_authenticate(user=admin)

        resp = self.client.post(reverse('cliente-list'), {
            'nombre_razon_social': 'Cliente Sede Explicita', 'ruc_cedula': '1788888888',
            'direccion_envio': 'Calle QA', 'limite_credito': '500.00', 'sede': otra_sede.id,
            'nivel_precio': 'normal',
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        cliente = Cliente.objects.get(id=resp.data['id'])
        self.assertEqual(cliente.sede, otra_sede)
        self.assertIsNone(cliente.vendedor_asignado)

    def test_list_dado_admin_filtra_por_vendedor_username_cuando_get_entonces_filtra(self):
        vendedor1 = CustomUserFactory(groups=['vendedor'], sede=self.sede, username='vendedor_qa1')
        vendedor2 = CustomUserFactory(groups=['vendedor'], sede=self.sede, username='vendedor_qa2')
        ClienteFactory(sede=self.sede, vendedor_asignado=vendedor1)
        ClienteFactory(sede=self.sede, vendedor_asignado=vendedor2)

        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('cliente-list'), {'vendedor_username': 'vendedor_qa1'})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_list_dado_vendedor_id_no_numerico_cuando_get_entonces_ignora_filtro(self):
        # Caja blanca: rama `except (TypeError, ValueError): pass`
        ClienteFactory(sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.get(reverse('cliente-list'), {'vendedor_id': 'abc'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_destroy_dado_sin_justificacion_explicita_cuando_delete_entonces_usa_default(self):
        # Caja blanca: fallback "Eliminación desde panel de administración"
        cliente = ClienteFactory(sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.delete(reverse('cliente-detail', kwargs={'pk': cliente.id}))

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Cliente.objects.filter(id=cliente.id).exists())

    def test_destroy_dado_header_justificacion_cuando_delete_entonces_la_usa(self):
        cliente = ClienteFactory(sede=self.sede)
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        resp = self.client.delete(
            reverse('cliente-detail', kwargs={'pk': cliente.id}),
            HTTP_X_JUSTIFICACION_AUDITORIA='Cliente duplicado QA',
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)


class PedidoVentaViewSetExtraTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede, limite_credito='10000.00')
        self.producto = ProductoFactory(sede=self.sede, precio_base='1.000')
        self.admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.admin)

    def _crear_pedido(self, **overrides):
        overrides.setdefault('guia_remision', 'GR-EXTRA-QA')
        pedido = PedidoVenta.objects.create(cliente=self.cliente, sede=self.sede, **overrides)
        DetallePedido.objects.create(
            pedido_venta=pedido, producto=self.producto, cantidad=1, piezas=1,
            peso='10.000', precio_unitario='2.000', incluye_iva=False,
        )
        return pedido

    def test_list_dado_vendedor_username_cuando_get_entonces_filtra(self):
        vendedor = CustomUserFactory(groups=['vendedor'], sede=self.sede, username='vend_pedido_qa')
        self._crear_pedido(vendedor_asignado=vendedor)
        self._crear_pedido()

        resp = self.client.get(reverse('pedidoventa-list'), {'vendedor_username': 'vend_pedido_qa'})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data['results']), 1)

    def test_list_dado_limit_invalido_cuando_get_entonces_usa_default_100(self):
        self._crear_pedido()
        resp = self.client.get(reverse('pedidoventa-list'), {'limit': 'no-numero'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_list_dado_estado_valido_cuando_get_entonces_filtra(self):
        # Despacho pide ?estado=pendiente y antes el backend lo ignoraba
        # silenciosamente, devolviendo pedidos de cualquier estado.
        self._crear_pedido(guia_remision='GR-FILTRO-PEND', estado='pendiente')
        self._crear_pedido(guia_remision='GR-FILTRO-DESP', estado='despachado')
        self._crear_pedido(guia_remision='GR-FILTRO-FACT', estado='facturado')

        resp = self.client.get(reverse('pedidoventa-list'), {'estado': 'pendiente'})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        guias = [p['guia_remision'] for p in resp.data['results']]
        self.assertIn('GR-FILTRO-PEND', guias)
        self.assertNotIn('GR-FILTRO-DESP', guias)
        self.assertNotIn('GR-FILTRO-FACT', guias)

    def test_list_dado_estado_invalido_cuando_get_entonces_400(self):
        resp = self.client.get(reverse('pedidoventa-list'), {'estado': 'no-es-un-estado'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_dado_sin_estado_cuando_get_entonces_devuelve_todos(self):
        # Retrocompatibilidad: sin el parámetro, el comportamiento previo se mantiene.
        self._crear_pedido(guia_remision='GR-SIN-FILTRO-1', estado='pendiente')
        self._crear_pedido(guia_remision='GR-SIN-FILTRO-2', estado='despachado')

        resp = self.client.get(reverse('pedidoventa-list'))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        guias = [p['guia_remision'] for p in resp.data['results']]
        self.assertIn('GR-SIN-FILTRO-1', guias)
        self.assertIn('GR-SIN-FILTRO-2', guias)

    def test_list_dado_estado_multiple_cuando_get_entonces_filtra_por_ambos(self):
        # Despacho necesita ver 'pendiente' Y 'despachado_parcial' a la vez
        # (un pedido parcialmente despachado sigue en la cola por completar).
        self._crear_pedido(guia_remision='GR-MULTI-PEND', estado='pendiente')
        self._crear_pedido(guia_remision='GR-MULTI-PARCIAL', estado='despachado_parcial')
        self._crear_pedido(guia_remision='GR-MULTI-FACT', estado='facturado')

        resp = self.client.get(reverse('pedidoventa-list'), {'estado': 'pendiente,despachado_parcial'})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        guias = [p['guia_remision'] for p in resp.data['results']]
        self.assertIn('GR-MULTI-PEND', guias)
        self.assertIn('GR-MULTI-PARCIAL', guias)
        self.assertNotIn('GR-MULTI-FACT', guias)

    def test_download_pdf_dado_servicio_disponible_cuando_get_entonces_200_pdf(self):
        pedido = self._crear_pedido()
        with patch('gestion.views.sales_views.PrintingService.generate_nota_venta_pdf', return_value=b'%PDF-fake'):
            resp = self.client.get(reverse('pedidoventa-download-pdf', kwargs={'pk': pedido.id}))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/pdf')

    def test_download_pdf_dado_servicio_caido_cuando_get_entonces_503(self):
        pedido = self._crear_pedido()
        with patch('gestion.views.sales_views.PrintingService.generate_nota_venta_pdf', return_value=None):
            resp = self.client.get(reverse('pedidoventa-download-pdf', kwargs={'pk': pedido.id}))
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_download_pdf_dado_historial_id_cuando_get_entonces_acota_a_lo_despachado_en_ese_evento(self):
        # F5 (despacho parcial): la nota de venta de un despacho específico
        # NO debe listar todo el pedido — solo lo que ese historial despachó.
        from inventory.models import HistorialDespacho, DetalleHistorialDespacho

        pedido = self._crear_pedido()  # 10.000 kg requeridos por _crear_pedido
        historial = HistorialDespacho.objects.create(
            usuario=self.admin, total_bultos=1, total_peso='4.000',
        )
        DetalleHistorialDespacho.objects.create(
            historial=historial, producto=self.producto, peso='4.000',
            pedido=pedido, es_devolucion=False,
        )
        # Detalle de OTRO historial ya revertido — no debe contarse.
        historial_revertido = HistorialDespacho.objects.create(
            usuario=self.admin, total_bultos=1, total_peso='6.000',
        )
        DetalleHistorialDespacho.objects.create(
            historial=historial_revertido, producto=self.producto, peso='6.000',
            pedido=pedido, es_devolucion=True,
        )

        with patch('gestion.views.sales_views.PrintingService.generate_nota_venta_pdf',
                   return_value=b'%PDF-fake') as mock_pdf:
            resp = self.client.get(
                reverse('pedidoventa-download-pdf', kwargs={'pk': pedido.id}),
                {'historial_id': historial.id},
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(len(data_enviada['detalles']), 1)
        self.assertEqual(data_enviada['detalles'][0]['peso'], 4.0)

    def test_download_pdf_dado_sin_historial_id_cuando_get_entonces_lista_pedido_completo(self):
        # Retrocompatibilidad: el flujo actual del vendedor (reimprimir) sigue
        # mostrando el pedido completo cuando no se pasa historial_id.
        from inventory.models import HistorialDespacho, DetalleHistorialDespacho

        pedido = self._crear_pedido()
        historial = HistorialDespacho.objects.create(usuario=self.admin, total_bultos=1, total_peso='4.000')
        DetalleHistorialDespacho.objects.create(
            historial=historial, producto=self.producto, peso='4.000', pedido=pedido, es_devolucion=False,
        )

        with patch('gestion.views.sales_views.PrintingService.generate_nota_venta_pdf',
                   return_value=b'%PDF-fake') as mock_pdf:
            resp = self.client.get(reverse('pedidoventa-download-pdf', kwargs={'pk': pedido.id}))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(len(data_enviada['detalles']), 1)
        self.assertEqual(data_enviada['detalles'][0]['peso'], 10.0)  # el detalle original del pedido, no 4.0

    def test_create_dado_vendedor_cuando_post_entonces_autoasigna_y_reconcilia(self):
        vendedor = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        self.client.force_authenticate(user=vendedor)

        resp = self.client.post(reverse('pedidoventa-list'), {
            'cliente': self.cliente.id, 'guia_remision': 'GR-QA-001', 'esta_pagado': True,
        }, format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        pedido = PedidoVenta.objects.get(id=resp.data['id'])
        self.assertEqual(pedido.vendedor_asignado, vendedor)
        self.assertEqual(pedido.sede, self.sede)


class DetallePedidoViewSetExtraTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede, precio_base='1.000')
        self.pedido = PedidoVenta.objects.create(
            cliente=self.cliente, sede=self.sede, esta_pagado=True, guia_remision='GR-DETALLE-QA',
        )
        self.detalle = DetallePedido.objects.create(
            pedido_venta=self.pedido, producto=self.producto, cantidad=1, piezas=1,
            peso='5.000', precio_unitario='2.000',
        )

    def test_update_dado_usuario_autenticado_cuando_patch_entonces_reconcilia_cliente(self):
        user = CustomUserFactory(sede=self.sede)
        self.client.force_authenticate(user=user)

        with patch(
            'gestion.views.sales_views.PaymentReconciler.reconcile_client_orders',
        ) as mock_reconcile:
            resp = self.client.patch(
                reverse('detallepedido-detail', kwargs={'pk': self.detalle.id}),
                {'peso': '7.000'}, format='json',
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        mock_reconcile.assert_called_once_with(self.cliente)

    def test_destroy_dado_usuario_admin_cuando_delete_entonces_reconcilia_cliente(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)

        with patch(
            'gestion.views.sales_views.PaymentReconciler.reconcile_client_orders',
        ) as mock_reconcile:
            resp = self.client.delete(reverse('detallepedido-detail', kwargs={'pk': self.detalle.id}))

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        mock_reconcile.assert_called_once_with(self.cliente)

    def test_destroy_dado_usuario_no_admin_cuando_delete_entonces_403(self):
        # Caja blanca: get_permissions exige IsAdminSistemasOrSede fuera de list/retrieve/create/update
        user = CustomUserFactory(groups=['vendedor'])
        self.client.force_authenticate(user=user)
        resp = self.client.delete(reverse('detallepedido-detail', kwargs={'pk': self.detalle.id}))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class PagoClienteDestroyExtraTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        self.admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.admin)
        self.pago = PagoCliente.objects.create(cliente=self.cliente, sede=self.sede, monto='50.000')

    def test_destroy_dado_sin_justificacion_cuando_delete_entonces_400(self):
        resp = self.client.delete(
            reverse('pagocliente-detail', kwargs={'pk': self.pago.id}), {}, format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_destroy_dado_servicio_lanza_valueerror_cuando_delete_entonces_400(self):
        # Caja blanca: rama `except ValueError as e` -> 400 con el detalle
        with patch(
            'gestion.views.sales_views.PagoReversionService.revertir_pago',
            side_effect=ValueError('Pago ya revertido'),
        ):
            resp = self.client.delete(
                reverse('pagocliente-detail', kwargs={'pk': self.pago.id}),
                {'justificacion': 'Corrección QA'}, format='json',
            )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Pago ya revertido', resp.data['justificacion'])

    def test_destroy_dado_servicio_lanza_excepcion_generica_cuando_delete_entonces_500(self):
        # Caja blanca: rama `except Exception` -> 500 genérico
        with patch(
            'gestion.views.sales_views.PagoReversionService.revertir_pago',
            side_effect=RuntimeError('fallo inesperado'),
        ):
            resp = self.client.delete(
                reverse('pagocliente-detail', kwargs={'pk': self.pago.id}),
                {'justificacion': 'Corrección QA'}, format='json',
            )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
