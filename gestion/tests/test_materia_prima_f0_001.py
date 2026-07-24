"""
Tests Sprint 6 (F0-001): Trazabilidad de Materia Prima.
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-TrazabilidadMateriaPrima

Técnicas ISTQB: EP (cantidad válida/cero/negativa, consumo suficiente o no),
BVA (consumo == disponible), STT (cadena completa proveedor → producto final).
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from gestion.models import (
    CustomUser, Sede, Producto, Proveedor, Bodega,
    OrdenProduccion, LoteProduccion, MateriaPrimaLote, ConsumoMateriaPrima,
)
from gestion.services.materia_prima_service import MateriaPrimaService, TraceabilityService
from inventory.models import StockBodega, MovimientoInventario


def _fixtures(tc):
    tc.sede = Sede.objects.create(nombre='Sede MP', location='Quito')
    tc.usuario = CustomUser.objects.create_user(username='bodeguero_mp', password='pass')
    tc.proveedor = Proveedor.objects.create(nombre='Hilos Andinos SA', sede=tc.sede)
    tc.producto_hilo = Producto.objects.create(
        codigo='H001', descripcion='Hilo Crudo 30/1', tipo='hilo',
        unidad_medida='kg', precio_base=Decimal('8.00'), sede=tc.sede,
    )
    tc.producto_tela = Producto.objects.create(
        codigo='T001', descripcion='Tela Jersey', tipo='tela',
        unidad_medida='kg', precio_base=Decimal('15.00'), sede=tc.sede,
    )
    tc.bodega = Bodega.objects.create(nombre='Bodega MP', sede=tc.sede)


def _crear_lote_produccion(tc, codigo='LP-MP-1'):
    orden = OrdenProduccion.objects.create(
        codigo=f'OP-{codigo}',
        producto_entrada=tc.producto_hilo,
        producto_salida=tc.producto_tela,
        peso_neto_requerido=Decimal('100.00'),
        sede=tc.sede,
    )
    ahora = timezone.now()
    return LoteProduccion.objects.create(
        orden_produccion=orden,
        codigo_lote=codigo,
        peso_neto_producido=Decimal('95.000'),
        operario=tc.usuario,
        turno='diurno',
        hora_inicio=ahora - timedelta(hours=2),
        hora_final=ahora,
    )


class MateriaPrimaRegistroTestCase(TestCase):
    """Registro de entradas de MP — EP + BVA."""

    def setUp(self):
        _fixtures(self)

    def _registrar(self, lote='MP-2026-001', cantidad='100.000', costo='10.500'):
        return MateriaPrimaService.registrar_entrada(
            proveedor=self.proveedor,
            producto=self.producto_hilo,
            lote_proveedor=lote,
            cantidad_kg=Decimal(cantidad),
            costo_unitario=Decimal(costo),
            bodega_recepcion=self.bodega,
            fecha_recepcion=date.today(),
            usuario=self.usuario,
        )

    def test_registrar_entrada_valida(self):
        """EP válida: crea MP, suma stock y registra movimiento COMPRA."""
        mp = self._registrar()

        self.assertEqual(mp.cantidad_kg, Decimal('100.000'))
        self.assertEqual(mp.cantidad_disponible, Decimal('100.000'))
        self.assertEqual(mp.sede, self.sede)

        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto_hilo)
        self.assertEqual(stock.cantidad, Decimal('100.000'))

        mov = MovimientoInventario.objects.get(documento_ref='MP-MP-2026-001')
        self.assertEqual(mov.tipo_movimiento, 'COMPRA')
        self.assertEqual(mov.proveedor, self.proveedor)
        self.assertEqual(mov.bodega_destino, self.bodega)

    def test_cantidad_cero_rechazada(self):
        """BVA límite: cantidad == 0 → ValidationError, nada persiste."""
        with self.assertRaises(ValidationError):
            self._registrar(lote='MP-CERO', cantidad='0.000')
        self.assertEqual(MateriaPrimaLote.objects.count(), 0)

    def test_costo_negativo_rechazado(self):
        """EP inválida: costo < 0 → ValidationError."""
        with self.assertRaises(ValidationError):
            self._registrar(lote='MP-NEG', costo='-1.000')
        self.assertEqual(MateriaPrimaLote.objects.count(), 0)

    def test_lote_proveedor_duplicado_rechazado(self):
        """EP duplicado: mismo (proveedor, lote, fecha) viola unique_together."""
        self._registrar(lote='MP-DUP')
        with self.assertRaises(ValidationError):
            self._registrar(lote='MP-DUP')
        self.assertEqual(MateriaPrimaLote.objects.count(), 1)


class ConsumoMateriaPrimaTestCase(TestCase):
    """Consumo de MP en producción — EP + BVA + trazabilidad STT."""

    def setUp(self):
        _fixtures(self)
        self.mp = MateriaPrimaService.registrar_entrada(
            proveedor=self.proveedor,
            producto=self.producto_hilo,
            lote_proveedor='MP-CONS-001',
            cantidad_kg=Decimal('100.000'),
            costo_unitario=Decimal('10.000'),
            bodega_recepcion=self.bodega,
            fecha_recepcion=date.today(),
            usuario=self.usuario,
        )
        self.lote = _crear_lote_produccion(self)

    def test_consumo_valido_registra_trazabilidad(self):
        """EP válida: consumo crea relación con porcentaje y descuenta disponible."""
        MateriaPrimaService.consumir_materia_prima(
            lote_produccion=self.lote,
            consumos_data=[{'materia_prima_lote_id': self.mp.id, 'cantidad_kg': Decimal('40.000')}],
            usuario=self.usuario,
        )

        consumo = ConsumoMateriaPrima.objects.get(lote_produccion=self.lote)
        self.assertEqual(consumo.cantidad_kg, Decimal('40.000'))
        self.assertEqual(consumo.porcentaje_utilizado, Decimal('40.00'))

        self.mp.refresh_from_db()
        self.assertEqual(self.mp.cantidad_disponible, Decimal('60.000'))
        self.assertFalse(self.mp.completamente_consumida)

    def test_consumo_total_marca_agotada(self):
        """BVA exacto: consumir el 100% marca completamente_consumida."""
        MateriaPrimaService.consumir_materia_prima(
            lote_produccion=self.lote,
            consumos_data=[{'materia_prima_lote_id': self.mp.id, 'cantidad_kg': Decimal('100.000')}],
            usuario=self.usuario,
        )
        self.mp.refresh_from_db()
        self.assertTrue(self.mp.completamente_consumida)
        self.assertEqual(self.mp.cantidad_disponible, Decimal('0.000'))

    def test_consumo_insuficiente_rechazado_con_rollback(self):
        """EP insuficiente: 150 > 100 disponible → error y nada persiste."""
        with self.assertRaises(ValidationError) as ctx:
            MateriaPrimaService.consumir_materia_prima(
                lote_produccion=self.lote,
                consumos_data=[{'materia_prima_lote_id': self.mp.id, 'cantidad_kg': Decimal('150.000')}],
                usuario=self.usuario,
            )
        self.assertIn('insuficiente', str(ctx.exception).lower())
        self.assertEqual(ConsumoMateriaPrima.objects.count(), 0)
        self.mp.refresh_from_db()
        self.assertEqual(self.mp.cantidad_consumida, Decimal('0.000'))

    def test_trazabilidad_cadena_completa(self):
        """STT: la cadena responde proveedor, lote, certificado y costo."""
        MateriaPrimaService.consumir_materia_prima(
            lote_produccion=self.lote,
            consumos_data=[{'materia_prima_lote_id': self.mp.id, 'cantidad_kg': Decimal('50.000')}],
            usuario=self.usuario,
        )

        cadena = TraceabilityService.obtener_cadena_completa(self.lote)

        self.assertEqual(cadena['lote_final'], self.lote.codigo_lote)
        self.assertEqual(cadena['producto_final'], 'Tela Jersey')
        self.assertEqual(len(cadena['componentes']), 1)
        componente = cadena['componentes'][0]
        self.assertEqual(componente['proveedor'], 'Hilos Andinos SA')
        self.assertEqual(componente['materia_prima_lote'], 'MP-CONS-001')
        self.assertEqual(componente['cantidad_kg'], 50.0)
        # 50 kg × $10 = $500
        self.assertEqual(cadena['costo_total_materias_primas'], 500.0)


class MateriaPrimaAtomicidadTestCase(TransactionTestCase):
    """STT: registrar_entrada es todo-o-nada."""

    def setUp(self):
        _fixtures(self)

    def test_fallo_en_movimiento_revierte_todo(self):
        """Si el movimiento de Kardex falla, ni MP ni stock persisten."""
        with patch(
            'gestion.services.materia_prima_service.MovimientoInventario.objects.create',
            side_effect=Exception('DB error simulado'),
        ):
            with self.assertRaises(Exception):
                MateriaPrimaService.registrar_entrada(
                    proveedor=self.proveedor,
                    producto=self.producto_hilo,
                    lote_proveedor='MP-ATOMIC',
                    cantidad_kg=Decimal('50.000'),
                    costo_unitario=Decimal('10.000'),
                    bodega_recepcion=self.bodega,
                    fecha_recepcion=date.today(),
                    usuario=self.usuario,
                )

        self.assertEqual(MateriaPrimaLote.objects.count(), 0,
                         'El lote de MP no debe persistir si el Kardex falló')
        stock = StockBodega.objects.filter(bodega=self.bodega, producto=self.producto_hilo).first()
        if stock:
            self.assertEqual(stock.cantidad, Decimal('0.000'))
