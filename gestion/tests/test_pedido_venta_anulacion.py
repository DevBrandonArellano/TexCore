"""
Tests de PedidoVenta — Anulación y Modificación (vendedor).

ISTQB:
  - EP (Partición de Equivalencia): permisos, estados, validaciones
  - BVA (Valores Límite): motivo de 9 vs 10 caracteres
Convención: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
"""
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import AuditLog, PedidoVenta
from gestion.tests.factories import (
    ClienteFactory,
    CustomUserFactory,
    SedeFactory,
)


def _make_pedido(sede, cliente, estado='pendiente', vendedor=None):
    return PedidoVenta.objects.create(
        cliente=cliente,
        guia_remision=f'GR-{PedidoVenta.objects.count():04d}',
        sede=sede,
        estado=estado,
        vendedor_asignado=vendedor,
    )


class TestAnulacionPedido_Permisos(TestCase):
    """RBAC — solo grupos permitidos pueden anular."""

    def setUp(self):
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        # Use admin_sistemas so pedido is visible regardless of vendedor_asignado
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.pedido = _make_pedido(self.sede, self.cliente)
        self.url = f'/api/pedidos-venta/{self.pedido.pk}/anular/'
        self.payload = {'motivo_anulacion': 'Motivo valido con mas de diez chars'}
        self.client = APIClient()

    def test_pedido_dado_usuario_vendedor_cuando_anular_entonces_200(self):
        # Vendedor must own the pedido to see it in queryset
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        pedido = _make_pedido(self.sede, self.cliente, vendedor=vendedor)
        self.client.force_authenticate(user=vendedor)
        r = self.client.post(f'/api/pedidos-venta/{pedido.pk}/anular/', self.payload, format='json')
        self.assertEqual(r.status_code, 200)

    def test_pedido_dado_usuario_admin_sistemas_cuando_anular_entonces_200(self):
        self.client.force_authenticate(user=self.admin)
        r = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(r.status_code, 200)

    def test_pedido_dado_usuario_sin_grupo_cuando_anular_entonces_403(self):
        user = CustomUserFactory(sede=self.sede)
        self.client.force_authenticate(user=user)
        # superuser=False, no groups → 403 before queryset check
        r = self.client.post(self.url, self.payload, format='json')
        self.assertIn(r.status_code, [403, 404])

    def test_pedido_dado_no_autenticado_cuando_anular_entonces_401(self):
        r = self.client.post(self.url, self.payload, format='json')
        self.assertEqual(r.status_code, 401)


class TestAnulacionPedido_Validaciones(TestCase):
    """EP/BVA — validaciones de estado, motivo y doble anulación."""

    def setUp(self):
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        # Use admin_sistemas to bypass vendedor queryset filter
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _url(self, pedido_pk):
        return f'/api/pedidos-venta/{pedido_pk}/anular/'

    def test_pedido_dado_motivo_9_chars_cuando_anular_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.post(self._url(pedido.pk), {'motivo_anulacion': 'x' * 9}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_motivo_exactamente_10_chars_cuando_anular_entonces_200(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.post(self._url(pedido.pk), {'motivo_anulacion': 'x' * 10}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_pedido_dado_estado_despachado_cuando_anular_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente, estado='despachado')
        r = self.client.post(self._url(pedido.pk), {'motivo_anulacion': 'motivo suficientemente largo'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_estado_facturado_cuando_anular_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente, estado='facturado')
        r = self.client.post(self._url(pedido.pk), {'motivo_anulacion': 'motivo suficientemente largo'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_ya_anulado_cuando_anular_de_nuevo_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente)
        payload = {'motivo_anulacion': 'primera anulacion valida'}
        self.client.post(self._url(pedido.pk), payload, format='json')
        r = self.client.post(self._url(pedido.pk), payload, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_motivo_vacio_cuando_anular_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.post(self._url(pedido.pk), {'motivo_anulacion': ''}, format='json')
        self.assertEqual(r.status_code, 400)


class TestAnulacionPedido_Efectos(TestCase):
    """Verifica efectos secundarios de la anulación."""

    def setUp(self):
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_pedido_dado_pendiente_cuando_anular_entonces_campos_persistidos(self):
        pedido = _make_pedido(self.sede, self.cliente)
        motivo = 'cliente cancelo el pedido urgente'
        self.client.post(f'/api/pedidos-venta/{pedido.pk}/anular/', {'motivo_anulacion': motivo}, format='json')
        pedido.refresh_from_db()
        self.assertTrue(pedido.anulado)
        self.assertEqual(pedido.motivo_anulacion, motivo)
        self.assertEqual(pedido.anulado_por, self.user)
        self.assertIsNotNone(pedido.fecha_anulacion)

    def test_pedido_dado_anulacion_cuando_ocurre_entonces_crea_auditlog(self):
        pedido = _make_pedido(self.sede, self.cliente)
        self.client.post(
            f'/api/pedidos-venta/{pedido.pk}/anular/',
            {'motivo_anulacion': 'motivo de auditoria completo'},
            format='json',
        )
        log = AuditLog.objects.filter(object_id=pedido.pk, accion='UPDATE').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.usuario, self.user)
        self.assertIn('anulado', log.valor_nuevo)

    def test_pedido_dado_anulacion_cuando_consultar_api_entonces_aparece_anulado_true(self):
        pedido = _make_pedido(self.sede, self.cliente)
        self.client.post(
            f'/api/pedidos-venta/{pedido.pk}/anular/',
            {'motivo_anulacion': 'anulacion de prueba completa'},
            format='json',
        )
        r = self.client.get(f'/api/pedidos-venta/{pedido.pk}/')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['anulado'])


class TestModificacionPedido_Validaciones(TestCase):
    """EP/BVA — validaciones del endpoint modificar."""

    def setUp(self):
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _url(self, pk):
        return f'/api/pedidos-venta/{pk}/modificar/'

    def test_pedido_dado_motivo_9_chars_cuando_modificar_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.patch(self._url(pedido.pk), {'guia_remision': 'GR-NEW', 'motivo': 'x' * 9}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_motivo_10_chars_cuando_modificar_entonces_200(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.patch(self._url(pedido.pk), {'guia_remision': 'GR-UPD-001', 'motivo': 'x' * 10}, format='json')
        self.assertEqual(r.status_code, 200)

    def test_pedido_dado_estado_despachado_cuando_modificar_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente, estado='despachado')
        r = self.client.patch(self._url(pedido.pk), {'guia_remision': 'GR-X',
                              'motivo': 'motivo valido largo'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_anulado_cuando_modificar_entonces_400(self):
        pedido = _make_pedido(self.sede, self.cliente)
        pedido.anulado = True
        pedido.save()
        r = self.client.patch(self._url(pedido.pk), {'guia_remision': 'GR-X',
                              'motivo': 'motivo valido largo'}, format='json')
        self.assertEqual(r.status_code, 400)

    def test_pedido_dado_sin_cambios_reales_cuando_modificar_entonces_200_sin_cambios(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.patch(
            self._url(pedido.pk),
            {'guia_remision': pedido.guia_remision, 'motivo': 'motivo valido completo'},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('No se detectaron cambios', r.data.get('message', ''))

    def test_pedido_dado_usuario_vendedor_sin_ownership_cuando_modificar_entonces_404(self):
        pedido = _make_pedido(self.sede, self.cliente)  # no vendedor_asignado
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.client.force_authenticate(user=vendedor)
        r = self.client.patch(self._url(pedido.pk), {'guia_remision': 'GR-NEW',
                              'motivo': 'motivo valido largo'}, format='json')
        # Vendedor no ve el pedido ajeno → 404 del queryset
        self.assertEqual(r.status_code, 404)


class TestModificacionPedido_Efectos(TestCase):
    """Verifica que los cambios se persisten y se registra auditoría."""

    def setUp(self):
        self.sede = SedeFactory()
        self.cliente = ClienteFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_pedido_dado_nueva_guia_remision_cuando_modificar_entonces_persiste(self):
        pedido = _make_pedido(self.sede, self.cliente)
        nueva_guia = 'GR-MODIFICADA-001'
        self.client.patch(
            f'/api/pedidos-venta/{pedido.pk}/modificar/',
            {'guia_remision': nueva_guia, 'motivo': 'corrección de guía de remisión'},
            format='json',
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.guia_remision, nueva_guia)

    def test_pedido_dado_modificacion_cuando_ocurre_entonces_crea_auditlog(self):
        pedido = _make_pedido(self.sede, self.cliente)
        self.client.patch(
            f'/api/pedidos-venta/{pedido.pk}/modificar/',
            {'guia_remision': 'GR-AUDIT-TEST', 'motivo': 'modificacion con auditoria'},
            format='json',
        )
        log = AuditLog.objects.filter(
            object_id=pedido.pk,
            accion='UPDATE',
            justificacion__icontains='modificacion').first()
        self.assertIsNotNone(log)
        self.assertIn('guia_remision', log.valor_nuevo)

    def test_pedido_dado_esta_pagado_cambiado_cuando_modificar_entonces_persiste(self):
        pedido = _make_pedido(self.sede, self.cliente)
        self.assertFalse(pedido.esta_pagado)
        self.client.patch(
            f'/api/pedidos-venta/{pedido.pk}/modificar/',
            {'esta_pagado': True, 'motivo': 'pago confirmado por transferencia'},
            format='json',
        )
        pedido.refresh_from_db()
        self.assertTrue(pedido.esta_pagado)

    def test_pedido_dado_modificacion_cuando_response_entonces_incluye_campos_cambiados(self):
        pedido = _make_pedido(self.sede, self.cliente)
        r = self.client.patch(
            f'/api/pedidos-venta/{pedido.pk}/modificar/',
            {'guia_remision': 'GR-RESP-CHECK', 'motivo': 'verificacion de respuesta api'},
            format='json',
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn('guia_remision', r.data.get('cambios', []))
