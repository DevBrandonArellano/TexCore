"""
Tests Sprint 3 (P1-007): Vínculo FK entre despacho y movimiento de inventario.
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-ReversionDespacho

Diagnóstico CONTEXTO.md: DespachoReversionService localizaba el movimiento
VENTA original con documento_ref__contains=f"Despacho #{id}" — si el formato
del string cambia, la reversión salta el lote EN SILENCIO y el stock queda
inconsistente. Fix: FK directa DetalleHistorialDespacho.movimiento_venta, con
fallback al string para registros históricos, y error explícito si no hay
forma de localizar el movimiento (fail-loud en lugar de fail-silent).

Técnicas ISTQB: EP (con FK / sin FK con string válido / sin nada),
STT (reversión restaura stock vía FK).
"""

from decimal import Decimal

from django.test import TestCase
from django.contrib.auth.models import Group
from django.utils import timezone

from gestion.models import CustomUser, Sede, Producto, Bodega, OrdenProduccion, LoteProduccion
from inventory.models import (
    HistorialDespacho, DetalleHistorialDespacho, StockBodega, MovimientoInventario
)
from inventory.services.despacho_reversion import DespachoReversionService


class DespachoReversionFKTestCase(TestCase):
    """La reversión debe usar la FK al movimiento original, no un string."""

    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Despacho FK', location='Quito')
        self.user = CustomUser.objects.create_user(username='despacho_fk', password='test123')
        grupo, _ = Group.objects.get_or_create(name='despacho')
        self.user.groups.add(grupo)

        self.producto = Producto.objects.create(
            codigo='TELA-FK', descripcion='Tela FK Test', tipo='tela',
            unidad_medida='kg', precio_base=Decimal('10.00'), sede=self.sede,
        )
        self.bodega = Bodega.objects.create(nombre='Bodega PT FK', sede=self.sede)

        self.orden = OrdenProduccion.objects.create(
            codigo='OP-FK-1',
            producto_salida=self.producto,
            peso_neto_requerido=Decimal('100.00'),
            sede=self.sede,
        )
        ahora = timezone.now()
        self.lote = LoteProduccion.objects.create(
            orden_produccion=self.orden,
            codigo_lote='LOTE-FK-1',
            peso_neto_producido=Decimal('80.00'),
            operario=self.user,
            turno='diurno',
            hora_inicio=ahora,
            hora_final=ahora,
        )

    def _crear_despacho_con_movimiento(self, documento_ref=None, con_fk=True):
        """Simula un despacho procesado: movimiento VENTA + historial + detalle."""
        historial = HistorialDespacho.objects.create(
            usuario=self.user, total_bultos=1, total_peso=Decimal('80.00'),
        )
        mov = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA',
            producto=self.producto,
            lote=self.lote,
            bodega_origen=self.bodega,
            cantidad=Decimal('80.00'),
            usuario=self.user,
            documento_ref=documento_ref if documento_ref is not None
            else f"Despacho #{historial.id}",
            saldo_resultante=Decimal('0.00'),
        )
        detalle = DetalleHistorialDespacho.objects.create(
            historial=historial,
            lote=self.lote,
            producto=self.producto,
            peso=Decimal('80.00'),
            movimiento_venta=mov if con_fk else None,
        )
        return historial, mov, detalle

    def test_detalle_guarda_fk_al_movimiento_venta(self):
        """EP con FK: el detalle del despacho referencia su movimiento VENTA."""
        historial, mov, detalle = self._crear_despacho_con_movimiento()
        self.assertEqual(detalle.movimiento_venta_id, mov.id)

    def test_reversion_usa_fk_aunque_documento_ref_cambie(self):
        """
        STT crítico: documento_ref con formato DISTINTO al esperado — con la
        búsqueda por string la reversión saltaba el lote en silencio; con la
        FK debe restaurar el stock correctamente.
        """
        historial, mov, detalle = self._crear_despacho_con_movimiento(
            documento_ref='FORMATO-NUEVO-XYZ',  # rompe el __contains
            con_fk=True,
        )

        resultado = DespachoReversionService.revertir_despacho(
            historial, self.user, justificacion='Reversión vía FK'
        )

        self.assertEqual(resultado['lotes_revertidos'], 1,
                         'Con FK la reversión no depende del formato del string')
        stock = StockBodega.objects.get(
            bodega=self.bodega, producto=self.producto, lote=self.lote
        )
        self.assertEqual(stock.cantidad, Decimal('80.00'))

    def test_reversion_fallback_a_string_para_registros_historicos(self):
        """EP legado: detalle sin FK (datos pre-migración) usa el string."""
        historial, mov, detalle = self._crear_despacho_con_movimiento(con_fk=False)

        resultado = DespachoReversionService.revertir_despacho(
            historial, self.user, justificacion='Reversión legado'
        )

        self.assertEqual(resultado['lotes_revertidos'], 1)
        stock = StockBodega.objects.get(
            bodega=self.bodega, producto=self.producto, lote=self.lote
        )
        self.assertEqual(stock.cantidad, Decimal('80.00'))

    def test_reversion_sin_movimiento_localizable_falla_explicitamente(self):
        """
        EP sin nada: ni FK ni string válido → la reversión debe FALLAR con
        error claro (no saltar el lote en silencio dejando stock inconsistente).
        """
        historial, mov, detalle = self._crear_despacho_con_movimiento(
            documento_ref='SIN-RELACION', con_fk=False,
        )

        with self.assertRaises(ValueError):
            DespachoReversionService.revertir_despacho(
                historial, self.user, justificacion='Debe fallar'
            )

        # Fail-loud + atomicidad: nada se marcó como devuelto
        detalle.refresh_from_db()
        self.assertFalse(detalle.es_devolucion,
                         'La transacción debe revertirse completa si un lote no es localizable')
