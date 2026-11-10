"""
ReservaService (inventory/services/reserva_service.py): ramas de validación y de liberación
que no cubrían las pruebas del flujo MTO.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): detalle / lote / pedido válido o sin guardar; detalle
  del pedido explícito / tomado de la OP / sin detalle; reserva del mismo pedido / de otro.
- Análisis de valores límite (BVA): peso solicitado 0; código de OP de más de 100
  caracteres; lo liberado deja la cantidad fabricada por encima, igual o por debajo del peso.
- Transición de estados (STT): estado de fabricación fabricado / en_proceso / pendiente al liberar.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestion.models import DetallePedido, LoteProduccion, PedidoVenta
from gestion.tests.factories import (
    DetallePedidoFactory,
    OrdenProduccionFactory,
    PedidoVentaFactory,
)
from inventory.services.reserva_service import ReservaService


def _lote(codigo, peso="40.000", **extra):
    ahora = timezone.now()
    return LoteProduccion.objects.create(
        codigo_lote=codigo,
        peso_neto_producido=Decimal(peso),
        turno="Mañana",
        hora_inicio=ahora,
        hora_final=ahora,
        **extra,
    )


class CrearOrdenDesdePedidoValidacionesTest(TestCase):
    def setUp(self):
        self.detalle = DetallePedidoFactory()

    def test_crear_dado_detalle_sin_guardar_cuando_crea_entonces_validation_error(self):
        with self.assertRaisesMessage(ValidationError, "detalle de pedido válido"):
            ReservaService.crear_orden_desde_pedido(DetallePedido())

    def test_crear_dado_detalle_sin_pedido_cuando_crea_entonces_validation_error(self):
        huerfano = DetallePedido(pk=self.detalle.pk)
        with self.assertRaisesMessage(ValidationError, "no pertenece a ningún pedido"):
            ReservaService.crear_orden_desde_pedido(huerfano)

    def test_crear_dado_item_sin_producto_cuando_crea_entonces_validation_error(self):
        self.detalle.producto = None
        with self.assertRaisesMessage(ValidationError, "no tiene producto asignado"):
            ReservaService.crear_orden_desde_pedido(self.detalle)

    def test_crear_dado_peso_solicitado_cero_cuando_crea_entonces_validation_error(self):
        with self.assertRaisesMessage(ValidationError, "mayor a 0"):
            ReservaService.crear_orden_desde_pedido(self.detalle, peso_solicitado=Decimal("0"))

    def test_crear_dado_codigo_de_mas_de_100_caracteres_cuando_crea_entonces_lo_recorta_a_100(self):
        # «MTO-PED-<id>-<código>-1» con exactamente 101 caracteres: el límite justo.
        pedido_id = self.detalle.pedido_venta_id
        producto = self.detalle.producto
        producto.codigo = "X" * (101 - len(f"MTO-PED-{pedido_id}--1"))
        producto.save()

        op = ReservaService.crear_orden_desde_pedido(self.detalle)

        self.assertEqual(op.codigo, f"MTO-PED-{pedido_id}-{producto.codigo}-1"[:100])


class ReservarLoteRamasTest(TestCase):
    def setUp(self):
        self.detalle = DetallePedidoFactory(peso=Decimal("100.000"))
        self.pedido = self.detalle.pedido_venta

    def test_reservar_dado_lote_o_pedido_sin_guardar_cuando_reserva_entonces_validation_error(self):
        lote = _lote("LOT-RES-1")
        with self.assertRaisesMessage(ValidationError, "lote válido"):
            ReservaService.reservar_lote_para_pedido(LoteProduccion(), self.pedido)
        with self.assertRaisesMessage(ValidationError, "pedido válido"):
            ReservaService.reservar_lote_para_pedido(lote, PedidoVenta())

    def test_reservar_dado_detalle_de_la_op_cuando_no_lo_envia_entonces_suma_a_ese_detalle(self):
        op = OrdenProduccionFactory(sede=self.pedido.sede, detalle_pedido=self.detalle, pedido_venta=self.pedido)
        lote = _lote("LOT-RES-OP", orden_produccion=op)

        ReservaService.reservar_lote_para_pedido(lote, self.pedido, cantidad=Decimal("40"))

        self.detalle.refresh_from_db()
        self.assertEqual(
            (self.detalle.cantidad_fabricada, self.detalle.estado_fabricacion), (Decimal("40.000"), "en_proceso")
        )

    def test_reservar_dado_lote_ya_reservado_para_el_mismo_pedido_cuando_reserva_entonces_suma_sin_error(self):
        lote = _lote("LOT-RES-MISMO", pedido_venta_reserva=self.pedido)

        ReservaService.reservar_lote_para_pedido(
            lote, self.pedido, detalle_pedido=self.detalle, cantidad=Decimal("100")
        )

        self.detalle.refresh_from_db()
        self.assertEqual(self.detalle.estado_fabricacion, "fabricado")

    def test_reservar_dado_lote_sin_producto_ni_detalle_cuando_reserva_entonces_solo_marca_la_reserva(self):
        lote = _lote("LOT-RES-SOLO")

        ReservaService.reservar_lote_para_pedido(lote, self.pedido)

        lote.refresh_from_db()
        self.detalle.refresh_from_db()
        self.assertEqual(lote.pedido_venta_reserva_id, self.pedido.id)
        self.assertEqual(self.detalle.cantidad_fabricada, Decimal("0.000"))


class LiberarReservaRamasTest(TestCase):
    def setUp(self):
        self.detalle = DetallePedidoFactory(peso=Decimal("100.000"))
        self.pedido = self.detalle.pedido_venta
        self.producto = self.detalle.producto

    def _liberar_con_fabricado(self, fabricado, peso_lote="40.000"):
        DetallePedido.objects.filter(pk=self.detalle.pk).update(cantidad_fabricada=Decimal(fabricado))
        lote = _lote(
            f"LOT-LIB-{fabricado.replace('.', '_')}",
            peso=peso_lote,
            producto=self.producto,
            pedido_venta_reserva=self.pedido,
        )
        ReservaService.liberar_reserva_lote(lote, justificacion="Calidad rechazada")
        self.detalle.refresh_from_db()
        lote.refresh_from_db()
        return lote

    def test_liberar_dado_lote_sin_reserva_cuando_libera_entonces_no_hace_nada(self):
        lote = _lote("LOT-LIB-SIN")
        self.assertIsNone(ReservaService.liberar_reserva_lote(lote))
        self.assertIsNone(ReservaService.liberar_reserva_lote(LoteProduccion(pedido_venta_reserva=self.pedido)))

    def test_liberar_dado_lo_que_queda_supera_el_peso_cuando_libera_entonces_sigue_fabricado(self):
        lote = self._liberar_con_fabricado("150.000")
        self.assertEqual(
            (self.detalle.cantidad_fabricada, self.detalle.estado_fabricacion), (Decimal("110.000"), "fabricado")
        )
        self.assertIsNone(lote.pedido_venta_reserva_id)

    def test_liberar_dado_que_queda_algo_bajo_el_peso_cuando_libera_entonces_en_proceso(self):
        self._liberar_con_fabricado("60.000")
        self.assertEqual(
            (self.detalle.cantidad_fabricada, self.detalle.estado_fabricacion), (Decimal("20.000"), "en_proceso")
        )

    def test_liberar_dado_que_no_queda_nada_cuando_libera_entonces_pendiente_sin_negativos(self):
        self._liberar_con_fabricado("30.000")
        self.assertEqual(
            (self.detalle.cantidad_fabricada, self.detalle.estado_fabricacion), (Decimal("0.000"), "pendiente")
        )

    def test_liberar_dado_lote_sin_producto_ni_detalle_cuando_libera_entonces_solo_quita_la_reserva(self):
        lote = _lote("LOT-LIB-HUERFANO", pedido_venta_reserva=self.pedido)
        ReservaService.liberar_reserva_lote(lote)
        lote.refresh_from_db()
        self.assertIsNone(lote.pedido_venta_reserva_id)


class ValidarDespachoLoteTest(TestCase):
    def test_validar_dado_lote_reservado_para_otro_pedido_cuando_valida_entonces_rechaza_con_el_cliente(self):
        pedido = PedidoVentaFactory()
        lote = _lote("LOT-VAL-OTRO", pedido_venta_reserva=pedido)
        with self.assertRaisesMessage(ValidationError, pedido.cliente.nombre_razon_social):
            ReservaService.validar_despacho_lote(lote, pedido.id + 1000)

    def test_validar_dado_lote_del_mismo_pedido_o_sin_reserva_cuando_valida_entonces_lo_permite(self):
        pedido = PedidoVentaFactory()
        self.assertIsNone(
            ReservaService.validar_despacho_lote(_lote("LOT-VAL-MISMO", pedido_venta_reserva=pedido), pedido.id)
        )
        self.assertIsNone(ReservaService.validar_despacho_lote(_lote("LOT-VAL-LIBRE"), pedido.id))
