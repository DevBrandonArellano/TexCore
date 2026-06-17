"""
Tests de Seguridad y Atomicidad: Flujo de Pagos de Cliente
Artefacto RUP: Suite de Pruebas
Casos de Uso: CU-RegistroPagoCliente, CU-ReversionPagoCliente

Diagnóstico CONTEXTO.md (10-Jun-2026):
- P0-017: revertir/destroy de pagos abierto a cualquier usuario autenticado
- P0-005: perform_create sin transacción atómica ni lock; sin validación monto vs saldo
- Bug reconciliador: PaymentReconciler incluye pedidos anulados en el FIFO
  (saldo_calculado los excluye) → pedidos posteriores nunca se marcan pagados

Técnicas ISTQB: EP (particiones rol permitido/denegado, monto válido/inválido),
BVA (monto == saldo, monto == 0), STT (estado esta_pagado tras reconciliación).
"""

from unittest.mock import patch
from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    CustomUser, Cliente, PagoCliente, Sede, PedidoVenta, DetallePedido, Producto
)
from gestion.utils import PaymentReconciler


def _crear_base(testcase):
    """Fixture común: sede, vendedor, cliente y producto (estilo test_pago_reversion)."""
    testcase.sede = Sede.objects.create(nombre='Sede Pagos Test', location='Quito')

    testcase.vendedor = CustomUser.objects.create_user(
        username='vendedor_pagos', password='test123'
    )
    grupo_vendedor, _ = Group.objects.get_or_create(name='vendedor')
    testcase.vendedor.groups.add(grupo_vendedor)
    testcase.vendedor.sede = testcase.sede
    testcase.vendedor.save()

    testcase.operario = CustomUser.objects.create_user(
        username='operario_pagos', password='test123'
    )
    grupo_operario, _ = Group.objects.get_or_create(name='operario')
    testcase.operario.groups.add(grupo_operario)

    testcase.cliente = Cliente.objects.create(
        ruc_cedula='1790012345001',
        nombre_razon_social='Textiles Andinos SA',
        direccion_envio='Av. Principal 100',
        nivel_precio='normal',
        limite_credito=Decimal('50000.00'),
        plazo_credito_dias=30,
        vendedor_asignado=testcase.vendedor,
        sede=testcase.sede,
    )

    testcase.producto = Producto.objects.create(
        codigo='TELA-P0',
        descripcion='Tela Jersey Test',
        tipo='tela',
        unidad_medida='kg',
        precio_base=Decimal('10.00'),
    )


def _crear_pedido(testcase, peso, precio, anulado=False, guia='GR-P0'):
    """Crea un pedido con un detalle. Deuda = peso × precio (sin IVA)."""
    pedido = PedidoVenta.objects.create(
        cliente=testcase.cliente,
        estado='despachado',
        guia_remision=guia,
        vendedor_asignado=testcase.vendedor,
        anulado=anulado,
    )
    DetallePedido.objects.create(
        pedido_venta=pedido,
        producto=testcase.producto,
        cantidad=int(peso),
        piezas=1,
        peso=Decimal(str(peso)),
        precio_unitario=Decimal(str(precio)),
        incluye_iva=False,
    )
    return pedido


class PagoPermisosP017TestCase(TestCase):
    """
    P0-017: Solo vendedor (de sus clientes), ejecutivo y admins pueden
    gestionar pagos. Operario/bodeguero NO deben poder crear ni revertir.
    """

    def setUp(self):
        _crear_base(self)
        self.api = APIClient()

    def test_operario_no_puede_listar_pagos(self):
        """EP rol denegado: operario autenticado recibe 403 al listar pagos."""
        self.api.force_authenticate(user=self.operario)
        response = self.api.get('/api/pagos-cliente/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operario_no_puede_crear_pago(self):
        """EP rol denegado: operario no puede registrar pagos."""
        self.api.force_authenticate(user=self.operario)
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '100.00',
            'metodo_pago': 'efectivo',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(PagoCliente.objects.count(), 0)

    def test_operario_no_puede_revertir_pago(self):
        """EP rol denegado: operario no puede revertir un pago existente."""
        pago = PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('500.00'),
            metodo_pago='efectivo', sede=self.sede,
        )
        self.api.force_authenticate(user=self.operario)
        response = self.api.post(
            f'/api/pagos-cliente/{pago.id}/revertir/',
            {'justificacion': 'Intento no autorizado'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            PagoCliente.objects.filter(id=pago.id).exists(),
            "El pago NO debe eliminarse ante un intento no autorizado",
        )

    def test_operario_no_puede_eliminar_pago(self):
        """EP rol denegado: DELETE también debe estar restringido."""
        pago = PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('500.00'),
            metodo_pago='efectivo', sede=self.sede,
        )
        self.api.force_authenticate(user=self.operario)
        response = self.api.delete(
            f'/api/pagos-cliente/{pago.id}/',
            {'justificacion': 'Intento no autorizado'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(PagoCliente.objects.filter(id=pago.id).exists())

    def test_vendedor_puede_revertir_pago_de_su_cliente(self):
        """EP rol permitido: vendedor revierte pagos de SUS clientes."""
        _crear_pedido(self, peso=100, precio=10)  # deuda 1000
        pago = PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('500.00'),
            metodo_pago='transferencia', sede=self.sede,
        )
        self.api.force_authenticate(user=self.vendedor)
        response = self.api.post(
            f'/api/pagos-cliente/{pago.id}/revertir/',
            {'justificacion': 'Error en registro'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(PagoCliente.objects.filter(id=pago.id).exists())

    def test_vendedor_no_puede_revertir_pago_de_otro_vendedor(self):
        """EP aislamiento: vendedor no ve ni revierte pagos de clientes ajenos (404)."""
        otro_vendedor = CustomUser.objects.create_user(
            username='vendedor_ajeno', password='test123'
        )
        grupo_vendedor, _ = Group.objects.get_or_create(name='vendedor')
        otro_vendedor.groups.add(grupo_vendedor)

        pago = PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('500.00'),
            metodo_pago='efectivo', sede=self.sede,
        )
        self.api.force_authenticate(user=otro_vendedor)
        response = self.api.post(
            f'/api/pagos-cliente/{pago.id}/revertir/',
            {'justificacion': 'No es mi cliente'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(PagoCliente.objects.filter(id=pago.id).exists())

    def test_admin_sistemas_puede_revertir_pago(self):
        """EP rol permitido: admin_sistemas gestiona pagos de cualquier cliente."""
        admin = CustomUser.objects.create_user(
            username='admin_pagos', password='test123'
        )
        grupo_admin, _ = Group.objects.get_or_create(name='admin_sistemas')
        admin.groups.add(grupo_admin)

        pago = PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('300.00'),
            metodo_pago='cheque', sede=self.sede,
        )
        self.api.force_authenticate(user=admin)
        response = self.api.post(
            f'/api/pagos-cliente/{pago.id}/revertir/',
            {'justificacion': 'Corrección administrativa'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PagoValidacionMontoP005TestCase(TestCase):
    """
    P0-005 (validación): el monto del pago debe validarse contra el saldo
    del cliente al momento de crear, dentro de la misma transacción.
    """

    def setUp(self):
        _crear_base(self)
        self.api = APIClient()
        self.api.force_authenticate(user=self.vendedor)

    def test_pago_que_excede_saldo_es_rechazado(self):
        """EP monto inválido: pago > deuda → 400 y no se persiste."""
        _crear_pedido(self, peso=100, precio=10)  # deuda 1000
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '5000.00',
            'metodo_pago': 'transferencia',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PagoCliente.objects.count(), 0)

    def test_pago_igual_al_saldo_es_aceptado(self):
        """BVA límite exacto: pago == deuda → 201 y pedido queda pagado."""
        pedido = _crear_pedido(self, peso=100, precio=10)  # deuda 1000
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '1000.00',
            'metodo_pago': 'transferencia',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pedido.refresh_from_db()
        self.assertTrue(pedido.esta_pagado, "Reconciliación debe marcar el pedido pagado")

    def test_pago_monto_cero_es_rechazado(self):
        """BVA límite inferior: monto == 0 → 400."""
        _crear_pedido(self, peso=100, precio=10)
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '0.00',
            'metodo_pago': 'efectivo',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PagoCliente.objects.count(), 0)

    def test_pago_monto_negativo_es_rechazado(self):
        """EP monto inválido: monto negativo → 400."""
        _crear_pedido(self, peso=100, precio=10)
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '-100.00',
            'metodo_pago': 'efectivo',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PagoCliente.objects.count(), 0)


class PagoAtomicidadP005TestCase(TransactionTestCase):
    """
    P0-005 (atomicidad): pago + reconciliación deben ser una sola unidad
    transaccional. Si la reconciliación falla, el pago NO debe persistir.
    Usa TransactionTestCase para verificar rollback real.
    """

    def setUp(self):
        _crear_base(self)
        self.api = APIClient()
        self.api.force_authenticate(user=self.vendedor)

    def test_fallo_en_reconciliacion_revierte_el_pago(self):
        """STT: error post-save → rollback total, sin pago huérfano sin reconciliar."""
        _crear_pedido(self, peso=100, precio=10)  # deuda 1000

        with patch(
            'gestion.views.sales_views.PaymentReconciler.reconcile_client_orders',
            side_effect=Exception('Fallo simulado de reconciliación'),
        ):
            try:
                self.api.post('/api/pagos-cliente/', {
                    'cliente': self.cliente.id,
                    'monto': '500.00',
                    'metodo_pago': 'transferencia',
                }, format='json')
            except Exception:
                pass  # la excepción puede propagarse en el test client

        self.assertEqual(
            PagoCliente.objects.count(), 0,
            "Si la reconciliación falla, el pago debe revertirse (transacción atómica). "
            "Un pago persistido sin reconciliar deja esta_pagado desincronizado.",
        )


class ReconciliadorPedidosAnuladosTestCase(TestCase):
    """
    Bug raíz de 'colas de facturas y valores pendientes':
    PaymentReconciler incluye pedidos ANULADOS en el FIFO mientras que
    Cliente.saldo_calculado los excluye. Un pedido anulado consume el saldo
    y los pedidos activos posteriores nunca se marcan como pagados.
    """

    def setUp(self):
        _crear_base(self)

    def test_pedido_anulado_no_consume_saldo_en_fifo(self):
        """
        STT: pedido1 ANULADO (1000) + pedido2 activo (500); pago de 500.
        El pago debe cubrir pedido2 (el anulado no existe para la cartera).
        """
        pedido_anulado = _crear_pedido(self, peso=100, precio=10, anulado=True, guia='GR-ANUL')
        pedido_activo = _crear_pedido(self, peso=50, precio=10, anulado=False, guia='GR-ACT')

        PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('500.00'),
            metodo_pago='transferencia', sede=self.sede,
        )

        PaymentReconciler.reconcile_client_orders(self.cliente)

        pedido_activo.refresh_from_db()
        pedido_anulado.refresh_from_db()
        self.assertTrue(
            pedido_activo.esta_pagado,
            "El pedido activo debe quedar pagado: el anulado no debe consumir saldo. "
            "saldo_calculado excluye anulados; el reconciliador debe hacer lo mismo.",
        )
        self.assertFalse(
            pedido_anulado.esta_pagado,
            "Un pedido anulado jamás debe marcarse como pagado",
        )

    def test_saldo_calculado_y_reconciliador_son_consistentes(self):
        """
        STT: si saldo_calculado dice deuda 0, todos los pedidos activos
        deben estar esta_pagado=True (consistencia entre ambas vistas).
        """
        _crear_pedido(self, peso=100, precio=10, anulado=True, guia='GR-ANUL-2')
        pedido_activo = _crear_pedido(self, peso=80, precio=10, anulado=False, guia='GR-ACT-2')

        PagoCliente.objects.create(
            cliente=self.cliente, monto=Decimal('800.00'),
            metodo_pago='efectivo', sede=self.sede,
        )
        PaymentReconciler.reconcile_client_orders(self.cliente)

        cliente_anotado = Cliente.objects.get(pk=self.cliente.pk)
        self.assertEqual(cliente_anotado.saldo_calculado, Decimal('0.000'))

        pedido_activo.refresh_from_db()
        self.assertTrue(
            pedido_activo.esta_pagado,
            "Deuda 0 según saldo_calculado pero pedido activo sin marcar pagado: "
            "esta es la inconsistencia reportada en valores pendientes",
        )
