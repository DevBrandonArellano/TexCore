"""
Tests Sprint 2: Anticipos de Cliente (P1-002) y Pagos Parciales (P1-003)
Artefacto RUP: Suite de Pruebas
Casos de Uso: CU-RegistroAnticipoCliente, CU-ReconciliacionPagosParciales

Contexto de negocio (Brandon, 10-Jun-2026):
- La facturación SRI la maneja software externo; TexCore solo registra pagos
  y emite el documento de validación (nota de venta).
- Existen clientes que pagan por adelantado (anticipos) — el sistema debe
  aceptarlos explícitamente y aplicarlos a pedidos futuros.
- esta_pagado binario no refleja pagos parciales → monto_pagado por pedido.

Técnicas ISTQB: EP (anticipo marcado/no marcado), BVA (pago == deuda,
parcial - 0.01), STT (anticipo → pedido futuro → pagado; reversión → 0).
"""

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import (
    CustomUser, Cliente, PagoCliente, Sede, PedidoVenta, DetallePedido, Producto
)
from gestion.utils import PaymentReconciler


class _BasePagosTestCase(TestCase):
    """Fixture común para anticipos y pagos parciales."""

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Anticipos', location='Quito')

        self.vendedor = CustomUser.objects.create_user(
            username='vendedor_ant', password='test123'
        )
        grupo, _ = Group.objects.get_or_create(name='vendedor')
        self.vendedor.groups.add(grupo)
        self.vendedor.sede = self.sede
        self.vendedor.save()

        self.cliente = Cliente.objects.create(
            ruc_cedula='1791234567001',
            nombre_razon_social='Hilados del Sur SA',
            direccion_envio='Parque Industrial Sur',
            nivel_precio='normal',
            limite_credito=Decimal('50000.00'),
            plazo_credito_dias=30,
            vendedor_asignado=self.vendedor,
            sede=self.sede,
        )

        self.producto = Producto.objects.create(
            codigo='TELA-ANT',
            descripcion='Tela Pique Test',
            tipo='tela',
            unidad_medida='kg',
            precio_base=Decimal('10.00'),
        )

        self.api = APIClient()
        self.api.force_authenticate(user=self.vendedor)

    def _crear_pedido(self, peso, precio, guia='GR-ANT'):
        pedido = PedidoVenta.objects.create(
            cliente=self.cliente,
            estado='despachado',
            guia_remision=guia,
            vendedor_asignado=self.vendedor,
        )
        DetallePedido.objects.create(
            pedido_venta=pedido,
            producto=self.producto,
            cantidad=int(peso),
            piezas=1,
            peso=Decimal(str(peso)),
            precio_unitario=Decimal(str(precio)),
            incluye_iva=False,
        )
        return pedido


class AnticipoClienteP1002TestCase(_BasePagosTestCase):
    """P1-002: sobrepagos legítimos como anticipos explícitos."""

    def test_sobrepago_sin_marca_anticipo_es_rechazado(self):
        """EP no marcado: pago > deuda sin es_anticipo → 400 (previene typos)."""
        self._crear_pedido(peso=100, precio=10)  # deuda 1000
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '1500.00',
            'metodo_pago': 'transferencia',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PagoCliente.objects.count(), 0)

    def test_sobrepago_marcado_como_anticipo_es_aceptado(self):
        """EP marcado: es_anticipo=True permite pago > deuda."""
        self._crear_pedido(peso=100, precio=10)  # deuda 1000
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '1500.00',
            'metodo_pago': 'transferencia',
            'es_anticipo': True,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         f"Anticipo explícito debe aceptarse: {response.data}")

        # El excedente queda como saldo a favor (saldo_calculado negativo)
        cliente = Cliente.objects.get(pk=self.cliente.pk)
        self.assertEqual(cliente.saldo_calculado, Decimal('-500.000'))

    def test_anticipo_a_cliente_sin_deuda(self):
        """BVA deuda 0: anticipo puro (cliente paga antes de pedir)."""
        response = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '800.00',
            'metodo_pago': 'efectivo',
            'es_anticipo': True,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cliente = Cliente.objects.get(pk=self.cliente.pk)
        self.assertEqual(cliente.saldo_calculado, Decimal('-800.000'))

    def test_anticipo_se_aplica_a_pedido_futuro(self):
        """
        STT flujo completo: anticipo 800 → se crea pedido de 300 (vía API de
        detalles) → el pedido debe quedar pagado automáticamente.
        """
        # 1. Anticipo
        self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '800.00',
            'metodo_pago': 'transferencia',
            'es_anticipo': True,
        }, format='json')

        # 2. Pedido nuevo: cabecera + detalle vía API (flujo real del frontend)
        pedido = PedidoVenta.objects.create(
            cliente=self.cliente,
            estado='pendiente',
            guia_remision='GR-FUT',
            vendedor_asignado=self.vendedor,
        )
        response = self.api.post('/api/detalles-pedido/', {
            'pedido_venta': pedido.id,
            'producto': self.producto.id,
            'cantidad': 30,
            'piezas': 1,
            'peso': '30.000',
            'precio_unitario': '10.000',
            'incluye_iva': False,
        }, format='json')
        self.assertIn(response.status_code,
                      (status.HTTP_200_OK, status.HTTP_201_CREATED))

        # 3. El anticipo cubre el pedido sin intervención manual
        pedido.refresh_from_db()
        self.assertTrue(
            pedido.esta_pagado,
            "El anticipo existente debe aplicarse al crear el detalle del pedido",
        )

    def test_saldo_a_favor_visible_en_listado_de_clientes(self):
        """El vendedor ve el saldo a favor de su cliente en el listado."""
        self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '600.00',
            'metodo_pago': 'cheque',
            'es_anticipo': True,
        }, format='json')

        response = self.api.get('/api/clientes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data.get('results', response.data)
        cliente_data = next(c for c in data if c['id'] == self.cliente.id)
        self.assertIn('saldo_a_favor', cliente_data)
        self.assertEqual(Decimal(str(cliente_data['saldo_a_favor'])), Decimal('600.000'))


class PagosParcialesP1003TestCase(_BasePagosTestCase):
    """P1-003: monto_pagado refleja pagos parciales por pedido (FIFO)."""

    def test_pago_parcial_registra_monto_pagado(self):
        """EP parcial: pedido 1000, pago 600 → monto_pagado 600, no pagado."""
        pedido = self._crear_pedido(peso=100, precio=10)  # 1000
        self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '600.00',
            'metodo_pago': 'transferencia',
        }, format='json')

        pedido.refresh_from_db()
        self.assertFalse(pedido.esta_pagado)
        self.assertEqual(pedido.monto_pagado, Decimal('600.000'),
                         "El abono parcial debe quedar registrado en el pedido")

    def test_pago_completo_registra_monto_total(self):
        """BVA exacto: pago == valor → monto_pagado == valor y esta_pagado."""
        pedido = self._crear_pedido(peso=100, precio=10)
        self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '1000.00',
            'metodo_pago': 'transferencia',
        }, format='json')

        pedido.refresh_from_db()
        self.assertTrue(pedido.esta_pagado)
        self.assertEqual(pedido.monto_pagado, Decimal('1000.000'))

    def test_fifo_aplica_parcial_al_segundo_pedido(self):
        """
        STT FIFO: pedido1 (500) + pedido2 (1000); pago 800 →
        pedido1 pagado completo (500), pedido2 parcial (300).
        """
        pedido1 = self._crear_pedido(peso=50, precio=10, guia='GR-F1')
        pedido2 = self._crear_pedido(peso=100, precio=10, guia='GR-F2')

        self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '800.00',
            'metodo_pago': 'transferencia',
        }, format='json')

        pedido1.refresh_from_db()
        pedido2.refresh_from_db()
        self.assertTrue(pedido1.esta_pagado)
        self.assertEqual(pedido1.monto_pagado, Decimal('500.000'))
        self.assertFalse(pedido2.esta_pagado)
        self.assertEqual(pedido2.monto_pagado, Decimal('300.000'),
                         "El remanente FIFO debe aplicarse como abono parcial, no perderse")

    def test_porcentaje_pagado_expuesto_en_api(self):
        """El API de pedidos expone monto_pagado y porcentaje_pagado."""
        pedido = self._crear_pedido(peso=100, precio=10)
        self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '600.00',
            'metodo_pago': 'efectivo',
        }, format='json')

        response = self.api.get(f'/api/pedidos-venta/{pedido.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(response.data['monto_pagado'])), Decimal('600.000'))
        self.assertEqual(Decimal(str(response.data['porcentaje_pagado'])), Decimal('60.00'))

    def test_reversion_de_pago_limpia_monto_pagado(self):
        """STT reversión: revertir el único abono deja monto_pagado en 0."""
        pedido = self._crear_pedido(peso=100, precio=10)
        create_resp = self.api.post('/api/pagos-cliente/', {
            'cliente': self.cliente.id,
            'monto': '600.00',
            'metodo_pago': 'transferencia',
        }, format='json')
        pago_id = create_resp.data['id']

        self.api.post(
            f'/api/pagos-cliente/{pago_id}/revertir/',
            {'justificacion': 'Cheque devuelto por el banco'},
            format='json',
        )

        pedido.refresh_from_db()
        self.assertFalse(pedido.esta_pagado)
        self.assertEqual(pedido.monto_pagado, Decimal('0.000'),
                         "La reconciliación post-reversión debe limpiar el abono")
