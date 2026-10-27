"""
Rechazo por lote ya despachado: el segundo despachador sabe quién lo despachó, cuándo y en
qué despacho, en vez de un «ya no tiene stock disponible» sin explicación.

Pasa cuando dos despachadores escanean el mismo lote: el primero que confirma se lo lleva
(select_for_update) y el segundo es rechazado. El motivo solo nombra a la persona si el lote
salió de una bodega que el segundo puede ver (OWASP A01: nada de otra sede).

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): lote despachado por otro / sin stock por otra causa /
  despachado desde una bodega de otra sede; usuario con nombre / sin nombre.
- Transición de estados (STT): lote con stock → despachado por A → rechazado para B.
"""

from datetime import UTC, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import (
    Bodega,
    Cliente,
    CustomUser,
    DetallePedido,
    LoteProduccion,
    OrdenProduccion,
    PedidoVenta,
    Producto,
    Sede,
)
from inventory.models import HistorialDespacho, StockBodega
from inventory.services.despacho_lote import motivo_lote_despachado

URL = "/api/inventory/process-despacho/"


class LoteYaDespachadoTestCase(TestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Despacho QA", location="Quito")
        self.bodega = Bodega.objects.create(nombre="Bodega Despacho QA", sede=self.sede)
        grupo, _ = Group.objects.get_or_create(name="despacho")
        self.ana = self._despachador("ana_qa", first_name="Ana", last_name="Pérez")
        self.beto = self._despachador("beto_qa", first_name="Beto", last_name="Ruiz")
        for usuario in (self.ana, self.beto):
            usuario.groups.add(grupo)

        self.producto = Producto.objects.create(
            codigo="TELA-QA", descripcion="Tela QA", tipo="tela", stock_minimo=Decimal("0"), unidad_medida="kg"
        )
        self.cliente = Cliente.objects.create(
            ruc_cedula="0999999999", nombre_razon_social="Cliente QA", direccion_envio="Dir", nivel_precio="normal"
        )
        self.orden = OrdenProduccion.objects.create(
            codigo="OP-QA", peso_neto_requerido=Decimal("40"), producto_salida=self.producto
        )
        self.lote = self._lote("LOTE-QA-1", self.bodega)

    def _despachador(self, username, bodega=None, **nombre):
        usuario = CustomUser.objects.create_user(username=username, password="x", sede=self.sede, **nombre)
        usuario.bodegas_asignadas.add(bodega or self.bodega)
        return usuario

    def _lote(self, codigo, bodega):
        lote = LoteProduccion.objects.create(
            codigo_lote=codigo,
            orden_produccion=self.orden,
            peso_neto_producido=Decimal("20"),
            turno="DIURNO",
            hora_inicio=datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
            hora_final=datetime(2026, 1, 1, 9, 0, tzinfo=UTC),
        )
        StockBodega.objects.create(bodega=bodega, producto=self.producto, lote=lote, cantidad=Decimal("20"))
        return lote

    def _pedido(self):
        pedido = PedidoVenta.objects.create(
            cliente=self.cliente, guia_remision="GR-QA", estado="pendiente", sede=self.sede
        )
        DetallePedido.objects.create(
            pedido_venta=pedido,
            producto=self.producto,
            cantidad=1,
            piezas=1,
            peso=Decimal("20"),
            precio_unitario=Decimal("10"),
        )
        return pedido

    def _despachar(self, usuario, codigo):
        cliente = APIClient()
        cliente.force_authenticate(user=usuario)
        return cliente.post(URL, {"pedidos": [self._pedido().id], "lotes": [codigo]}, format="json")

    def test_despacho_dado_lote_ya_despachado_por_otro_cuando_confirma_entonces_400_con_quien_cuando_y_que_hacer(self):
        primero = self._despachar(self.ana, "LOTE-QA-1")
        self.assertEqual(primero.status_code, status.HTTP_200_OK)
        historial = HistorialDespacho.objects.get(id=primero.data["despacho_id"])
        local = historial.fecha_despacho.astimezone(ZoneInfo("America/Guayaquil"))  # hora de la planta, no UTC

        resp = self._despachar(self.beto, "LOTE-QA-1")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["codigo"], "lote_ya_despachado")
        self.assertEqual(resp.data["lote"], "LOTE-QA-1")
        self.assertEqual(
            resp.data["error"],
            f"El lote LOTE-QA-1 ya fue despachado por Ana Pérez el {local:%d/%m/%Y} a las {local:%H:%M} "
            f"(despacho #{historial.id}). Quítelo de la lista y escanee otro lote.",
        )

    def test_despacho_dado_lote_sin_stock_que_nadie_despacho_cuando_confirma_entonces_motivo_generico(self):
        StockBodega.objects.filter(lote=self.lote).update(cantidad=0)

        resp = self._despachar(self.beto, "LOTE-QA-1")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["codigo"], "lote_sin_stock")
        self.assertEqual(resp.data["lote"], "LOTE-QA-1")
        self.assertEqual(resp.data["error"], "El lote LOTE-QA-1 ya no tiene stock disponible.")

    def test_despacho_dado_lote_despachado_desde_bodega_de_otra_sede_cuando_confirma_entonces_no_revela_quien(self):
        otra_sede = Sede.objects.create(nombre="Otra Sede QA", location="Cuenca")
        otra_bodega = Bodega.objects.create(nombre="Bodega Otra QA", sede=otra_sede)
        self._lote("LOTE-QA-OTRA", otra_bodega)
        carla = self._despachador("carla_qa", bodega=otra_bodega, first_name="Carla", last_name="Mora")
        carla.groups.add(Group.objects.get(name="despacho"))
        self.assertEqual(self._despachar(carla, "LOTE-QA-OTRA").status_code, status.HTTP_200_OK)

        resp = self._despachar(self.beto, "LOTE-QA-OTRA")

        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["codigo"], "lote_sin_stock")
        self.assertNotIn("Carla", resp.data["error"])

    def test_motivo_dado_despachador_sin_nombre_cuando_se_arma_entonces_usa_su_usuario(self):
        sin_nombre = self._despachador("despacho_sin_nombre")
        sin_nombre.groups.add(Group.objects.get(name="despacho"))
        self.assertEqual(self._despachar(sin_nombre, "LOTE-QA-1").status_code, status.HTTP_200_OK)

        motivo = motivo_lote_despachado(self.lote, ids_bodegas=None)

        self.assertIn("ya fue despachado por despacho_sin_nombre el ", motivo)

    def test_motivo_dado_lote_nunca_despachado_cuando_se_arma_entonces_none(self):
        self.assertIsNone(motivo_lote_despachado(self.lote, ids_bodegas=None))

    def test_lote_y_filas_dado_carrera_dentro_de_la_transaccion_cuando_otro_ya_confirmo_entonces_mismo_motivo(self):
        # Los dos pasan la comprobación previa sin bloqueo; el segundo encuentra el stock ya
        # tomado al bloquear las filas (select_for_update) y recibe el mismo motivo.
        from inventory.models import DetalleHistorialDespacho
        from inventory.views.despacho_views import LoteRechazado
        from inventory.views.despacho_views import ProcessDespachoAPIView as Vista

        historial = HistorialDespacho.objects.create(usuario=self.ana, total_bultos=1, total_peso=Decimal("20"))
        DetalleHistorialDespacho.objects.create(
            historial=historial, lote=self.lote, producto=self.producto, peso=Decimal("20")
        )

        with self.assertRaises(LoteRechazado) as rechazo:
            Vista._lote_y_filas("LOTE-QA-1", {}, set(), ids_bodegas=None)

        self.assertEqual(rechazo.exception.codigo, "lote_ya_despachado")
        self.assertIn("ya fue despachado por Ana Pérez", str(rechazo.exception.detail[0]))
        self.assertIn(f"(despacho #{historial.id}). Quítelo de la lista", str(rechazo.exception.detail[0]))
