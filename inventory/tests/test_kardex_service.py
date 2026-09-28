"""
Pruebas de KardexService — fuente única de la consulta del kárdex (pantalla y
export Excel). RNF-03 · TEX-22: el saldo lo calcula la base de datos (SUM para
el saldo inicial, SUM() OVER para el saldo corrido), no Python fila a fila, para
que el costo no crezca con el historial de la bodega.

Técnicas ISTQB:
- Particiones de equivalencia (EP): entrada / salida / transferencia entrante y
  saliente; con y sin producto; filtro tipo entrada / salida / ninguno.
- Análisis de valores límite (BVA): movimiento a las 00:00 del día inicio
  (entra al rango, no al saldo inicial); a las 23:59 del día fin (entra) y a las
  00:00 del día siguiente (queda fuera).
- Caja blanca (CB-D): el saldo corrido sobrevive a la paginación (slice).
"""
from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from inventory.models import MovimientoInventario
from inventory.services.kardex_service import FiltroKardexInvalido, KardexService
from gestion.tests.factories import SedeFactory, BodegaFactory, ProductoFactory


def _en(dia, hora=time(12, 0)):
    return timezone.make_aware(datetime.combine(dia, hora))


class KardexServiceTestCase(TestCase):
    def setUp(self):
        sede = SedeFactory()
        self.bodega = BodegaFactory(sede=sede)
        self.otra_bodega = BodegaFactory(sede=sede)
        self.producto = ProductoFactory(sede=sede)
        self.otro_producto = ProductoFactory(sede=sede)

    def _mov(self, fecha, cantidad, destino=None, origen=None, producto=None, tipo='COMPRA'):
        mov = MovimientoInventario.objects.create(
            tipo_movimiento=tipo, producto=producto or self.producto,
            bodega_destino=destino, bodega_origen=origen, cantidad=Decimal(cantidad),
        )
        # auto_now_add ignora la fecha pasada al crear: se fija después.
        MovimientoInventario.objects.filter(pk=mov.pk).update(fecha=fecha)
        return mov

    def _servicio(self, **kwargs):
        kwargs.setdefault('producto_id', self.producto.id)
        return KardexService(bodega_id=self.bodega.id, **kwargs)

    # --- saldo inicial ---
    def test_saldo_inicial_dado_entradas_y_salidas_previas_cuando_calcula_entonces_suma_con_signo(self):
        self._mov(_en(date(2026, 1, 1)), '100.000', destino=self.bodega)
        self._mov(_en(date(2026, 1, 2)), '30.000', origen=self.bodega, tipo='VENTA')
        self._mov(_en(date(2026, 1, 3)), '5.000', destino=self.otra_bodega)  # otra bodega
        self._mov(_en(date(2026, 1, 3)), '7.000', destino=self.bodega, producto=self.otro_producto)
        self._mov(_en(date(2026, 2, 1)), '50.000', destino=self.bodega)  # dentro del rango

        servicio = self._servicio(fecha_inicio=date(2026, 2, 1))

        self.assertEqual(servicio.saldo_inicial(), Decimal('70.000'))

    def test_saldo_inicial_dado_sin_fecha_inicio_cuando_calcula_entonces_cero(self):
        self._mov(_en(date(2026, 1, 1)), '100.000', destino=self.bodega)
        self.assertEqual(self._servicio().saldo_inicial(), Decimal('0'))

    def test_saldo_inicial_dado_movimiento_a_las_0000_del_dia_inicio_cuando_calcula_entonces_no_lo_incluye(self):
        self._mov(_en(date(2026, 2, 1), time(0, 0)), '50.000', destino=self.bodega)
        servicio = self._servicio(fecha_inicio=date(2026, 2, 1))
        self.assertEqual(servicio.saldo_inicial(), Decimal('0'))
        self.assertEqual(len(servicio.movimientos()), 1)

    # --- saldo corrido ---
    def test_movimientos_dado_rango_cuando_consulta_entonces_saldo_corre_desde_el_saldo_inicial(self):
        self._mov(_en(date(2026, 1, 1)), '100.000', destino=self.bodega)
        self._mov(_en(date(2026, 2, 1)), '20.000', origen=self.bodega, tipo='VENTA')
        self._mov(_en(date(2026, 2, 2)), '5.000', destino=self.bodega)

        filas = list(self._servicio(fecha_inicio=date(2026, 2, 1)).movimientos())

        self.assertEqual([f['saldo'] for f in filas], [Decimal('80.000'), Decimal('85.000')])
        self.assertEqual(filas[0]['entrada'], Decimal('0'))
        self.assertEqual(filas[0]['salida'], Decimal('20.000'))
        self.assertEqual(filas[1]['entrada'], Decimal('5.000'))

    def test_movimientos_dado_misma_fecha_cuando_consulta_entonces_desempata_por_id(self):
        misma = _en(date(2026, 2, 1))
        primero = self._mov(misma, '10.000', destino=self.bodega)
        segundo = self._mov(misma, '4.000', origen=self.bodega, tipo='VENTA')

        filas = list(self._servicio().movimientos())

        self.assertEqual([f['id'] for f in filas], [primero.id, segundo.id])
        self.assertEqual([f['saldo'] for f in filas], [Decimal('10.000'), Decimal('6.000')])

    def test_movimientos_dado_transferencias_cuando_consulta_entonces_entrada_o_salida_segun_la_bodega(self):
        self._mov(_en(date(2026, 2, 1)), '40.000', origen=self.otra_bodega, destino=self.bodega,
                  tipo='TRANSFERENCIA')
        self._mov(_en(date(2026, 2, 2)), '15.000', origen=self.bodega, destino=self.otra_bodega,
                  tipo='TRANSFERENCIA')

        filas = list(self._servicio().movimientos())

        self.assertEqual((filas[0]['entrada'], filas[0]['salida']), (Decimal('40.000'), Decimal('0')))
        self.assertEqual((filas[1]['entrada'], filas[1]['salida']), (Decimal('0'), Decimal('15.000')))
        self.assertEqual(filas[1]['saldo'], Decimal('25.000'))
        self.assertEqual(filas[1]['bodega_origen_nombre'], self.bodega.nombre)
        self.assertEqual(filas[1]['bodega_destino_nombre'], self.otra_bodega.nombre)

    def test_movimientos_dado_slice_de_pagina_cuando_consulta_entonces_el_saldo_continua(self):
        for i in range(6):
            self._mov(_en(date(2026, 2, 1 + i)), '10.000', destino=self.bodega)

        pagina_2 = list(self._servicio().movimientos()[2:4])

        self.assertEqual([f['saldo'] for f in pagina_2], [Decimal('30.000'), Decimal('40.000')])

    # --- límites de fecha_fin ---
    def test_movimientos_dado_fecha_fin_cuando_consulta_entonces_incluye_todo_ese_dia_y_excluye_el_siguiente(self):
        dentro = self._mov(_en(date(2026, 2, 10), time(23, 59, 59)), '1.000', destino=self.bodega)
        self._mov(_en(date(2026, 2, 11), time(0, 0)), '1.000', destino=self.bodega)

        filas = list(self._servicio(fecha_fin=date(2026, 2, 10)).movimientos())

        self.assertEqual([f['id'] for f in filas], [dentro.id])

    # --- filtro por tipo ---
    def test_movimientos_dado_tipo_entrada_cuando_consulta_entonces_solo_entradas_con_saldo_real(self):
        self._mov(_en(date(2026, 2, 1)), '100.000', destino=self.bodega)
        self._mov(_en(date(2026, 2, 2)), '30.000', origen=self.bodega, tipo='VENTA')
        entrada = self._mov(_en(date(2026, 2, 3)), '10.000', destino=self.bodega)

        filas = list(self._servicio(tipo='entrada').movimientos())

        self.assertEqual(len(filas), 2)
        # El saldo de la última entrada refleja la salida oculta: 100 - 30 + 10.
        self.assertEqual(filas[1]['id'], entrada.id)
        self.assertEqual(filas[1]['saldo'], Decimal('80.000'))

    def test_movimientos_dado_tipo_salida_cuando_consulta_entonces_solo_salidas(self):
        self._mov(_en(date(2026, 2, 1)), '100.000', destino=self.bodega)
        salida = self._mov(_en(date(2026, 2, 2)), '30.000', origen=self.bodega, tipo='VENTA')

        filas = list(self._servicio(tipo='salida').movimientos())

        self.assertEqual([f['id'] for f in filas], [salida.id])
        self.assertEqual(filas[0]['saldo'], Decimal('70.000'))

    # --- sin producto (export de toda la bodega) ---
    def test_movimientos_dado_sin_producto_cuando_consulta_entonces_sin_saldo_y_todos_los_productos(self):
        self._mov(_en(date(2026, 2, 1)), '10.000', destino=self.bodega)
        self._mov(_en(date(2026, 2, 2)), '7.000', destino=self.bodega, producto=self.otro_producto)

        filas = list(KardexService(bodega_id=self.bodega.id).movimientos())

        self.assertEqual(len(filas), 2)
        self.assertNotIn('saldo', filas[0])

    def test_saldo_inicial_dado_sin_producto_cuando_calcula_entonces_none(self):
        # Un saldo que mezcla productos distintos no tiene sentido físico.
        servicio = KardexService(bodega_id=self.bodega.id, fecha_inicio=date(2026, 2, 1))
        self.assertIsNone(servicio.saldo_inicial())

    def test_servicio_dado_fechas_como_texto_cuando_consulta_entonces_las_interpreta(self):
        self._mov(_en(date(2026, 1, 1)), '100.000', destino=self.bodega)
        self._mov(_en(date(2026, 2, 1)), '1.000', destino=self.bodega)

        servicio = self._servicio(fecha_inicio='2026-02-01', fecha_fin='2026-02-01')

        self.assertEqual(servicio.saldo_inicial(), Decimal('100.000'))
        self.assertEqual(len(servicio.movimientos()), 1)

    def test_servicio_dado_fecha_con_formato_valido_pero_imposible_cuando_construye_entonces_filtro_invalido(self):
        # BVA: mes 13 — parse_date lanza su propio ValueError en vez de devolver None.
        with self.assertRaises(FiltroKardexInvalido):
            self._servicio(fecha_inicio='2026-13-45')

    def test_servicio_dado_fecha_sin_formato_cuando_construye_entonces_filtro_invalido(self):
        with self.assertRaises(FiltroKardexInvalido):
            self._servicio(fecha_fin='ayer')

    def test_servicio_dado_tipo_desconocido_cuando_construye_entonces_filtro_invalido(self):
        with self.assertRaises(FiltroKardexInvalido):
            self._servicio(tipo='transferencia')

    # --- filtros por lote y entradas restantes ---
    def _lote(self):
        from gestion.tests.factories import LoteProduccionFactory, OrdenProduccionFactory
        return LoteProduccionFactory(orden_produccion=OrdenProduccionFactory(sede=self.bodega.sede))

    def test_movimientos_dado_lote_id_cuando_consulta_entonces_solo_ese_lote(self):
        lote = self._lote()
        del_lote = self._mov(_en(date(2026, 2, 1)), '5.000', destino=self.bodega)
        MovimientoInventario.objects.filter(pk=del_lote.pk).update(lote=lote)
        self._mov(_en(date(2026, 2, 2)), '7.000', destino=self.bodega)

        filas = list(self._servicio(lote_id=lote.id).movimientos())

        self.assertEqual([f['id'] for f in filas], [del_lote.id])
        self.assertEqual(filas[0]['lote_codigo'], lote.codigo_lote)

    def test_movimientos_dado_lote_codigo_cuando_consulta_entonces_solo_ese_lote(self):
        lote = self._lote()
        del_lote = self._mov(_en(date(2026, 2, 1)), '5.000', destino=self.bodega)
        MovimientoInventario.objects.filter(pk=del_lote.pk).update(lote=lote)
        self._mov(_en(date(2026, 2, 2)), '7.000', destino=self.bodega)

        filas = list(self._servicio(lote_codigo=lote.codigo_lote).movimientos())

        self.assertEqual([f['id'] for f in filas], [del_lote.id])

    def test_servicio_dado_fecha_como_datetime_cuando_construye_entonces_usa_su_dia(self):
        # EP: datetime (no solo date o texto) se normaliza a su fecha.
        self._mov(_en(date(2026, 1, 1)), '100.000', destino=self.bodega)
        servicio = self._servicio(fecha_inicio=_en(date(2026, 2, 1), time(15, 30)))
        self.assertEqual(servicio.saldo_inicial(), Decimal('100.000'))

    def test_movimientos_dado_indice_entero_cuando_accede_entonces_fila_con_saldo(self):
        self._mov(_en(date(2026, 2, 1)), '10.000', destino=self.bodega)
        self._mov(_en(date(2026, 2, 2)), '3.000', destino=self.bodega)

        movimientos = self._servicio().movimientos()

        self.assertEqual(len(movimientos), 2)
        self.assertEqual(movimientos[1]['saldo'], Decimal('13.000'))
