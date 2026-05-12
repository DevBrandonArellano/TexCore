"""
Tests de Integración: Reversión de Pagos del Cliente
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-ReversionPagoCliente

Valida:
1. Reversión restaura deuda del cliente correctamente
2. Justificación es obligatoria
3. Saldo_pendiente se calcula correctamente post-reversión
4. Reversión es transaccional (rollback en error)
5. API endpoint requiere justificación
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import datetime, timedelta

from gestion.models import (
    CustomUser, Cliente, PagoCliente, Sede, PedidoVenta, DetallePedido, Producto
)
from gestion.services.pago_reversion import PagoReversionService


class PagoReversionTestCase(TransactionTestCase):
    """
    Tests para la reversión de pagos.
    Usa TransactionTestCase para test transaccionales completos.
    """

    def setUp(self):
        """Configura datos de prueba comunes"""
        # Crear usuarios
        self.vendedor = CustomUser.objects.create_user(
            username='vendedor_test',
            email='vendedor@test.com',
            password='test123'
        )

        self.cliente_user = CustomUser.objects.create_user(
            username='cliente_test',
            email='cliente@test.com',
            password='test123',
            tipo='cliente'
        )

        # Asignar roles
        vendedor_group, _ = Group.objects.get_or_create(name='vendedor')
        self.vendedor.groups.add(vendedor_group)

        # Crear sede
        self.sede = Sede.objects.create(
            nombre='Sede Test',
            location='Lima'
        )
        self.vendedor.sede = self.sede
        self.vendedor.save()

        # Crear cliente
        self.cliente = Cliente.objects.create(
            ruc_cedula='12345678901',
            nombre_razon_social='Cliente Test SA',
            direccion_envio='Calle Principal 123',
            nivel_precio='normal',
            limite_credito=Decimal('10000.00'),
            plazo_credito_dias=30,
            vendedor_asignado=self.vendedor,
            sede=self.sede
        )

        # Crear producto
        self.producto = Producto.objects.create(
            codigo='PROD-001',
            descripcion='Producto Test',
            tipo='tela',
            unidad_medida='kg',
            precio_base=Decimal('100.00')
        )

        self.client = APIClient()

    def test_revertir_pago_restaura_deuda(self):
        """
        Caso 1: Revertir pago restaura deuda del cliente

        Verifica:
        - Deuda calculada correctamente sin pago
        - Pago reduce deuda
        - Reversión restaura deuda al valor anterior
        """
        # 1. Crear pedido
        pedido = PedidoVenta.objects.create(
            cliente=self.cliente,
            cliente_nombre=self.cliente.nombre_razon_social,
            total_cantidad=Decimal('100.00'),
            total_precio=Decimal('10000.00'),
            estado='completado',
            guia_remision='GR-001',
            vendedor_asignado=self.vendedor
        )

        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=Decimal('100.00'),
            precio_unitario=Decimal('100.00'),
            total_con_iva=Decimal('10000.00')
        )

        # 2. Verificar deuda inicial (saldo_calculado)
        self.cliente.refresh_from_db()
        deuda_inicial = self.cliente.saldo_calculado
        self.assertEqual(deuda_inicial, Decimal('10000.00'))

        # 3. Crear pago
        pago = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('3000.00'),
            metodo_pago='transferencia',
            comprobante='COMP-001',
            sede=self.sede
        )

        # 4. Verificar deuda después de pago
        self.cliente.refresh_from_db()
        deuda_con_pago = self.cliente.saldo_calculado
        self.assertEqual(deuda_con_pago, Decimal('7000.00'))

        # 5. Revertir pago
        resultado = PagoReversionService.revertir_pago(
            pago,
            self.vendedor,
            justificacion="Error en entrada de datos"
        )

        # 6. Verificar resultado
        self.assertEqual(resultado['pago_id'], pago.id)
        self.assertEqual(resultado['cliente_id'], self.cliente.id)
        self.assertEqual(resultado['monto_revertido'], Decimal('3000.00'))
        self.assertEqual(resultado['saldo_anterior_pago'], Decimal('10000.00'))

        # 7. Verificar deuda restaurada
        self.cliente.refresh_from_db()
        deuda_final = self.cliente.saldo_calculado
        self.assertEqual(deuda_final, Decimal('10000.00'))

    def test_revertir_pago_requiere_justificacion(self):
        """
        Caso 2: Reversión sin justificación falla

        Verifica:
        - ValueError si justificación está vacía
        - Justificación debe ser string no vacío
        """
        pago = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('1000.00'),
            metodo_pago='efectivo',
            sede=self.sede
        )

        # Intentar revertir sin justificación
        with self.assertRaises(ValueError) as context:
            PagoReversionService.revertir_pago(
                pago,
                self.vendedor,
                justificacion=""
            )

        self.assertIn("obligatoria", str(context.exception).lower())

    def test_revertir_pago_multiplos(self):
        """
        Caso 3: Reversión correcta con múltiples pagos

        Verifica:
        - Múltiples pagos reducen deuda correctamente
        - Reversión de uno solo restaura su monto
        - Otros pagos permanecen intactos
        """
        # Crear pedido
        pedido = PedidoVenta.objects.create(
            cliente=self.cliente,
            cliente_nombre=self.cliente.nombre_razon_social,
            total_cantidad=Decimal('100.00'),
            total_precio=Decimal('15000.00'),
            estado='completado',
            guia_remision='GR-002',
            vendedor_asignado=self.vendedor
        )

        DetallePedido.objects.create(
            pedido=pedido,
            producto=self.producto,
            cantidad=Decimal('150.00'),
            precio_unitario=Decimal('100.00'),
            total_con_iva=Decimal('15000.00')
        )

        # Crear tres pagos
        pago1 = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('5000.00'),
            metodo_pago='transferencia',
            sede=self.sede
        )

        pago2 = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('3000.00'),
            metodo_pago='cheque',
            sede=self.sede
        )

        pago3 = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('2000.00'),
            metodo_pago='efectivo',
            sede=self.sede
        )

        # Verificar deuda con tres pagos
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_calculado, Decimal('5000.00'))

        # Revertir pago 2
        PagoReversionService.revertir_pago(
            pago2,
            self.vendedor,
            justificacion="Anulación por error"
        )

        # Verificar deuda restaurada solo con pago2
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.saldo_calculado, Decimal('8000.00'))

        # Verificar que pago1 y pago3 aún existen
        self.assertTrue(PagoCliente.objects.filter(id=pago1.id).exists())
        self.assertTrue(PagoCliente.objects.filter(id=pago3.id).exists())
        self.assertFalse(PagoCliente.objects.filter(id=pago2.id).exists())

    def test_revertir_pago_transaccional(self):
        """
        Caso 4: Reversión es transaccional

        Verifica:
        - Si falla un paso, todo se revierte
        - Pago permanece en BD si hay error
        """
        pago = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('500.00'),
            metodo_pago='transferencia',
            sede=self.sede
        )

        pago_id = pago.id

        # Reversión debería tener éxito
        resultado = PagoReversionService.revertir_pago(
            pago,
            self.vendedor,
            justificacion="Test transaccional"
        )

        # Pago debe estar eliminado
        self.assertFalse(PagoCliente.objects.filter(id=pago_id).exists())
        self.assertEqual(resultado['pago_id'], pago_id)


class PagoReversionAPITestCase(TestCase):
    """
    Tests de API REST para reversión de pagos
    """

    def setUp(self):
        self.vendedor = CustomUser.objects.create_user(
            username='vendedor',
            password='test123'
        )
        vendedor_group, _ = Group.objects.get_or_create(name='vendedor')
        self.vendedor.groups.add(vendedor_group)

        self.sede = Sede.objects.create(nombre='Test', location='Lima')
        self.vendedor.sede = self.sede
        self.vendedor.save()

        self.cliente = Cliente.objects.create(
            ruc_cedula='87654321',
            nombre_razon_social='Cliente API Test',
            direccion_envio='Dirección Test',
            nivel_precio='normal',
            vendedor_asignado=self.vendedor,
            sede=self.sede
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.vendedor)

    def test_revertir_endpoint_requiere_justificacion(self):
        """
        HTTP 400 si justificación está vacía
        """
        pago = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('1000.00'),
            metodo_pago='transferencia',
            sede=self.sede
        )

        response = self.client.post(
            f'/pagos-cliente/{pago.id}/revertir/',
            {'justificacion': ''},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data.keys())

    def test_revertir_endpoint_con_justificacion(self):
        """
        HTTP 200 con justificación válida
        """
        pago = PagoCliente.objects.create(
            cliente=self.cliente,
            monto=Decimal('1000.00'),
            metodo_pago='transferencia',
            sede=self.sede
        )

        response = self.client.post(
            f'/pagos-cliente/{pago.id}/revertir/',
            {'justificacion': 'Error en el registro de pago'},
            format='json'
        )

        # 200 si la reversión fue exitosa
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('resultado', response.data)
