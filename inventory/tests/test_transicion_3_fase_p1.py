"""
Tests Sprint 6: Protocolo 3-Fase para transiciones entre bodegas.
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-TransicionBodegas

Antes: Bodega A → (desaparece) → Bodega B
Ahora: Bodega A → Bodega Tránsito (visible, estado en_transito) → Bodega B

Técnicas ISTQB: EP (stock suficiente/insuficiente, estado válido/inválido),
STT (en_transito → completado, en_transito → revertido).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from gestion.models import CustomUser, Sede, Producto, Bodega
from inventory.models import StockBodega, MovimientoInventario
from inventory.services.transicion_bodega_service import TransicionBodegaService


class TransicionTresFasesTestCase(TestCase):

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede 3F', location='Quito')
        self.usuario = CustomUser.objects.create_user(username='bodeguero_3f', password='pass')
        self.producto = Producto.objects.create(
            codigo='Q-3F', descripcion='Químico 3F', tipo='quimico',
            unidad_medida='kg', precio_base=Decimal('5.00'), sede=self.sede,
        )
        self.bodega_a = Bodega.objects.create(nombre='Bodega A', sede=self.sede)
        self.bodega_transito = Bodega.objects.create(nombre='Bodega Tránsito', sede=self.sede)
        self.bodega_b = Bodega.objects.create(nombre='Bodega B', sede=self.sede)

        stock = StockBodega(bodega=self.bodega_a, producto=self.producto, cantidad=Decimal('100.000'))
        stock._justificacion_auditoria = 'Stock inicial test 3-fase'
        stock.save()

    def _stock(self, bodega):
        item = StockBodega.objects.filter(bodega=bodega, producto=self.producto).first()
        return item.cantidad if item else Decimal('0.000')

    def _iniciar(self, cantidad='30.000'):
        return TransicionBodegaService.iniciar_transicion(
            producto=self.producto,
            bodega_origen=self.bodega_a,
            bodega_destino=self.bodega_b,
            bodega_transicion=self.bodega_transito,
            cantidad=Decimal(cantidad),
            usuario=self.usuario,
            documento_ref='TEST-3F',
        )

    def test_iniciar_descuenta_origen_y_carga_transito(self):
        """FASE 1+2: origen 100→70, tránsito 0→30, estado en_transito."""
        mov = self._iniciar()

        self.assertEqual(mov.estado_movimiento, 'en_transito')
        self.assertEqual(mov.bodega_transicion, self.bodega_transito)
        self.assertEqual(self._stock(self.bodega_a), Decimal('70.000'))
        self.assertEqual(self._stock(self.bodega_transito), Decimal('30.000'))
        self.assertEqual(self._stock(self.bodega_b), Decimal('0.000'))

    def test_iniciar_sin_stock_suficiente_falla(self):
        """EP insuficiente: 150 > 100 disponibles → error, nada cambia."""
        with self.assertRaises(ValidationError):
            self._iniciar(cantidad='150.000')
        self.assertEqual(self._stock(self.bodega_a), Decimal('100.000'))
        self.assertEqual(self._stock(self.bodega_transito), Decimal('0.000'))

    def test_completar_mueve_de_transito_a_destino(self):
        """FASE 3: tránsito 30→0, destino 0→30, estado completado (sin duplicar)."""
        mov = self._iniciar()
        TransicionBodegaService.completar_transicion(mov, self.usuario)

        mov.refresh_from_db()
        self.assertEqual(mov.estado_movimiento, 'completado')
        self.assertEqual(self._stock(self.bodega_transito), Decimal('0.000'),
                         'El material NO debe quedar duplicado en tránsito')
        self.assertEqual(self._stock(self.bodega_b), Decimal('30.000'))
        # Balance total del sistema se conserva: 70 + 0 + 30 = 100
        total = self._stock(self.bodega_a) + self._stock(self.bodega_transito) + self._stock(self.bodega_b)
        self.assertEqual(total, Decimal('100.000'))

    def test_completar_movimiento_no_en_transito_falla(self):
        """EP estado inválido: completar dos veces → ValidationError."""
        mov = self._iniciar()
        TransicionBodegaService.completar_transicion(mov, self.usuario)
        mov.refresh_from_db()
        with self.assertRaises(ValidationError):
            TransicionBodegaService.completar_transicion(mov, self.usuario)

    def test_revertir_en_transito_restaura_origen_y_limpia_transito(self):
        """STT reversión: origen vuelve a 100, tránsito a 0, estado revertido."""
        mov = self._iniciar()
        TransicionBodegaService.revertir_transicion(
            mov, self.usuario, justificacion='Falla en tintorería'
        )

        mov.refresh_from_db()
        self.assertEqual(mov.estado_movimiento, 'revertido')
        self.assertEqual(self._stock(self.bodega_a), Decimal('100.000'))
        self.assertEqual(self._stock(self.bodega_transito), Decimal('0.000'))
        self.assertEqual(self._stock(self.bodega_b), Decimal('0.000'))

    def test_revertir_sin_justificacion_falla(self):
        """EP justificación vacía → ValidationError (auditoría obligatoria)."""
        mov = self._iniciar()
        with self.assertRaises(ValidationError):
            TransicionBodegaService.revertir_transicion(mov, self.usuario, justificacion='')

    def test_movimientos_historicos_son_completados(self):
        """Compatibilidad: un movimiento creado sin protocolo queda 'completado'."""
        mov = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=self.producto,
            bodega_destino=self.bodega_a,
            cantidad=Decimal('10.000'),
            usuario=self.usuario,
            documento_ref='LEGACY',
            saldo_resultante=Decimal('110.000'),
        )
        self.assertEqual(mov.estado_movimiento, 'completado')
