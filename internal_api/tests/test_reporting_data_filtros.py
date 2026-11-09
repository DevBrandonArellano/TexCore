"""
Filtros de sede y de rango de fechas de internal_api/services/reporting_data.py.

El rango es inclusivo en el día de fin: `fecha_hasta` se convierte en «< día siguiente» para que
un registro de las 23:00 del último día entre. Con TIME_ZONE en la zona de la planta, el día es
el de la planta.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): con / sin sede; dentro / fuera del rango; producto filtrado.
- Análisis de valores límite (BVA): registro a las 23:00 del último día del rango (entra) y a
  las 00:30 del día siguiente (no entra), en hora de la planta.
"""

from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from gestion.models import LoteProduccion, OrdenProduccion, PedidoVenta
from gestion.tests.factories import (
    BodegaFactory,
    ClienteFactory,
    CustomUserFactory,
    OrdenProduccionFactory,
    PedidoVentaFactory,
    ProductoFactory,
    SedeFactory,
    StockBodegaFactory,
)
from internal_api.services import reporting_data as rd
from inventory.models import MovimientoInventario

ULTIMO_DIA = date(2026, 10, 27)


def _a_la_hora(dia, hora, minuto=0):
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


DENTRO = _a_la_hora(ULTIMO_DIA, 23)  # 23:00 del último día: entra
FUERA = _a_la_hora(date(2026, 10, 28), 0, 30)  # 00:30 del día siguiente: no entra
RANGO = {"fecha_desde": "2026-10-20", "fecha_hasta": "2026-10-27"}


class FiltrosPorSedeTest(TestCase):
    def setUp(self):
        self.sede, self.otra = SedeFactory(), SedeFactory()

    def test_productos_y_usuarios_dado_sede_cuando_filtra_entonces_solo_los_de_esa_sede(self):
        propio = ProductoFactory(sede=self.sede)
        ProductoFactory(sede=self.otra)
        usuario = CustomUserFactory(sede=self.sede)
        CustomUserFactory(sede=self.otra)

        self.assertEqual([p["id"] for p in rd.get_productos(self.sede.id)], [propio.id])
        self.assertEqual([u["id"] for u in rd.get_usuarios(self.sede.id)], [usuario.id])

    def test_deudores_gerencial_dado_sede_cuando_filtra_entonces_solo_sus_clientes(self):
        propio = ClienteFactory(sede=self.sede)
        ClienteFactory(sede=self.otra)
        self.assertEqual([c["id"] for c in rd.get_deudores_gerencial(self.sede.id)], [propio.id])

    def test_stock_actual_dado_producto_cuando_filtra_entonces_solo_ese_producto(self):
        bodega = BodegaFactory(sede=self.sede)
        fila = StockBodegaFactory(bodega=bodega, cantidad=Decimal("5"))
        StockBodegaFactory(bodega=bodega, cantidad=Decimal("7"))
        self.assertEqual([s["id"] for s in rd.get_stock_actual(bodega.id, producto_id=fila.producto_id)], [fila.id])


class FiltrosDeRangoVentasTest(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.vendedor = CustomUserFactory(sede=self.sede)
        self.dentro = self._pedido(DENTRO, self.sede)
        self._pedido(FUERA, self.sede)
        self._pedido(DENTRO, SedeFactory())

    def _pedido(self, cuando, sede):
        pedido = PedidoVentaFactory(sede=sede, vendedor_asignado=self.vendedor)
        PedidoVenta.objects.filter(pk=pedido.pk).update(fecha_pedido=cuando)
        return pedido

    def test_ventas_gerencial_dado_rango_y_sede_cuando_filtra_entonces_incluye_las_23_del_ultimo_dia(self):
        self.assertEqual([p["id"] for p in rd.get_ventas_gerencial(sede_id=self.sede.id, **RANGO)], [self.dentro.id])

    def test_top_clientes_gerencial_dado_rango_y_sede_cuando_filtra_entonces_solo_el_cliente_del_rango(self):
        top = rd.get_top_clientes_gerencial(sede_id=self.sede.id, **RANGO)
        self.assertEqual([(c["cliente_id"], c["total_pedidos"]) for c in top], [(self.dentro.cliente_id, 1)])

    def test_top_clientes_vendedor_dado_rango_cuando_filtra_entonces_cuenta_solo_lo_del_rango(self):
        top = rd.get_top_clientes_vendedor(self.vendedor.id, **RANGO)
        self.assertEqual(sum(c["total_pedidos"] for c in top), 2)  # los dos «DENTRO», de dos sedes


class FiltrosDeRangoInventarioTest(TestCase):
    def setUp(self):
        self.bodega = BodegaFactory()
        self.producto = ProductoFactory()
        self._salida(DENTRO, "4")
        self._salida(FUERA, "9")

    def _salida(self, cuando, cantidad):
        mov = MovimientoInventario.objects.create(
            tipo_movimiento="VENTA", producto=self.producto, bodega_origen=self.bodega, cantidad=Decimal(cantidad)
        )
        MovimientoInventario.objects.filter(pk=mov.pk).update(fecha=cuando)

    def test_rotacion_dado_rango_cuando_filtra_entonces_suma_solo_las_salidas_del_rango(self):
        self.assertEqual([r["total_salidas"] for r in rd.get_rotacion(self.bodega.id, **RANGO)], [Decimal("4")])

    def test_resumen_movimientos_dado_rango_cuando_filtra_entonces_suma_solo_lo_del_rango(self):
        self.assertEqual(
            rd.get_resumen_movimientos(self.bodega.id, **RANGO), [{"tipo_movimiento": "VENTA", "total": Decimal("4")}]
        )


class FiltrosDeRangoProduccionTest(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.op = OrdenProduccionFactory(sede=self.sede)
        self.dentro = self._lote("LOT-RD-DENTRO", DENTRO, self.op)
        self._lote("LOT-RD-FUERA", FUERA, self.op)
        self._lote("LOT-RD-OTRA", DENTRO, OrdenProduccionFactory(sede=SedeFactory()))

    def _lote(self, codigo, cuando, op):
        return LoteProduccion.objects.create(
            codigo_lote=codigo,
            orden_produccion=op,
            peso_neto_producido=Decimal("10.000"),
            turno="Mañana",
            hora_inicio=cuando,
            hora_final=cuando,
        )

    def test_lotes_dado_rango_y_sede_cuando_filtra_entonces_solo_el_lote_del_rango_y_la_sede(self):
        self.assertEqual(
            [lote["id"] for lote in rd.get_lotes_produccion(sede_id=self.sede.id, **RANGO)], [self.dentro.id]
        )

    def test_tendencia_dado_rango_y_sede_cuando_agrupa_entonces_un_dia_de_la_planta_con_un_lote(self):
        tendencia = rd.get_tendencia_produccion(sede_id=self.sede.id, **RANGO)
        self.assertEqual([(t["fecha"], t["total_lotes"]) for t in tendencia], [(ULTIMO_DIA, 1)])

    def test_ordenes_dado_rango_y_sede_cuando_filtra_entonces_incluye_las_creadas_el_ultimo_dia(self):
        OrdenProduccion.objects.filter(pk=self.op.pk).update(fecha_creacion=ULTIMO_DIA)
        OrdenProduccion.objects.exclude(pk=self.op.pk).update(fecha_creacion=date(2026, 10, 28))
        self.assertEqual([o["id"] for o in rd.get_ordenes_produccion(sede_id=self.sede.id, **RANGO)], [self.op.id])
