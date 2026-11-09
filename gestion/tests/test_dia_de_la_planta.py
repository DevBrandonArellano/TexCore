"""
El «día» del negocio es el de la planta, no el de UTC.

Hallazgo de la revisión del 9-nov-2026: con TIME_ZONE="UTC", entre las 19:00 y la medianoche de
Ecuador el backend ya calculaba el día siguiente. Un despacho confirmado a las 21:00 quedaba con
fecha de mañana, la producción del día del operario no contaba lo hecho por la tarde y el pulso
del jefe de planta buscaba las órdenes de mañana. TIME_ZONE pasa a ser la zona de la planta
(ZONA_HORARIA_PLANTA); la base sigue guardando en UTC (USE_TZ=True).

Técnicas ISTQB aplicadas (CTFL v4.0):
- Análisis de valores límite (BVA): 21:00 en la planta (02:00 UTC del día siguiente) y 18:30
  en la planta (23:30 UTC, mismo día UTC que la planta).
- Partición de equivalencia (EP): fecha calculada en vista, en serializer y en servicio.
- Revisión estática: ninguna fecha «de hoy» se calcula con `timezone.now().date()`.
"""

import re
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
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
    TarifaOperario,
)
from gestion.services.costeo_service import CostoLoteService
from gestion.tests.factories import (
    AreaFactory,
    CustomUserFactory,
    LoteProduccionFactory,
    OrdenProduccionFactory,
    SedeFactory,
)
from inventory.models import StockBodega

# 02:00 UTC del 28-oct son las 21:00 del 27-oct en la planta (UTC-5).
NOCHE_EN_LA_PLANTA = datetime(2026, 10, 28, 2, 0, tzinfo=UTC)
DIA_DE_LA_PLANTA = date(2026, 10, 27)


def _a_esa_hora():
    return patch("django.utils.timezone.now", return_value=NOCHE_EN_LA_PLANTA)


class ZonaHorariaConfiguradaTest(SimpleTestCase):
    def test_time_zone_dado_zona_de_la_planta_cuando_carga_settings_entonces_es_la_zona_activa(self):
        self.assertEqual(settings.TIME_ZONE, settings.ZONA_HORARIA_PLANTA)

    def test_localdate_dado_21h_en_la_planta_cuando_en_utc_ya_es_manana_entonces_devuelve_el_dia_de_la_planta(self):
        with _a_esa_hora():
            self.assertEqual(timezone.localdate(), DIA_DE_LA_PLANTA)


class ZonaHorariaInvalidaTest(SimpleTestCase):
    """Una zona mal escrita detiene el arranque en vez de romper cada PDF y mensaje."""

    def test_settings_dado_zona_mal_escrita_cuando_arranca_entonces_falla_con_el_motivo(self):
        import os
        import subprocess
        import sys

        entorno = {**os.environ, "ZONA_HORARIA_PLANTA": "America/Guayaquill"}
        proceso = subprocess.run(
            [sys.executable, "-c", "import django; django.setup()"],
            cwd=settings.BASE_DIR,
            env={**entorno, "DJANGO_SETTINGS_MODULE": os.environ.get("DJANGO_SETTINGS_MODULE", "TexCore.settings")},
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn("ZONA_HORARIA_PLANTA inválida: 'America/Guayaquill'", proceso.stderr)


class SinFechaDeHoyEnUtcTest(SimpleTestCase):
    """`timezone.now().date()` devuelve el día UTC aunque TIME_ZONE sea la planta."""

    PATRON = re.compile(r"timezone\.now\(\)\.date\(\)")

    def test_codigo_dado_backend_cuando_busca_fecha_de_hoy_en_utc_entonces_no_hay(self):
        raiz = Path(settings.BASE_DIR)
        culpables = [
            f"{ruta.relative_to(raiz)}:{n}"
            for app in ("gestion", "inventory", "internal_api", "TexCore")
            for ruta in (raiz / app).rglob("*.py")
            if "tests" not in ruta.parts and "migrations" not in ruta.parts
            for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), start=1)
            if self.PATRON.search(linea)
        ]
        self.assertEqual(culpables, [], "Use timezone.localdate(): " + ", ".join(culpables))


class DesempenoOperarioDelDiaTest(TestCase):
    def test_desempeno_dado_lote_terminado_a_las_18_30_en_la_planta_cuando_consulta_a_las_21_entonces_cuenta_hoy(self):
        sede = SedeFactory()
        operario = CustomUserFactory(groups=["operario"], area=AreaFactory(sede=sede), sede=sede)
        LoteProduccionFactory(
            operario=operario,
            hora_inicio=datetime(2026, 10, 27, 20, 0, tzinfo=UTC),
            hora_final=datetime(2026, 10, 27, 23, 30, tzinfo=UTC),
        )
        cliente = APIClient()
        cliente.force_authenticate(user=CustomUserFactory(groups=["admin_sistemas"]))

        with _a_esa_hora():
            resp = cliente.get(reverse("user-desempeno", kwargs={"pk": operario.id}))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["lotes_hoy"], 1)
        self.assertEqual(Decimal(str(resp.data["produccion_hoy_kg"])), Decimal("95.000"))


class PulsoDiarioDelDiaTest(TestCase):
    def test_pulso_dado_orden_que_termina_hoy_en_la_planta_cuando_consulta_a_las_21_entonces_la_cuenta(self):
        sede = SedeFactory()
        area = AreaFactory(sede=sede)
        OrdenProduccionFactory(
            sede=sede, area=area, fecha_fin_planificada=DIA_DE_LA_PLANTA, peso_neto_requerido=Decimal("100.00")
        )
        cliente = APIClient()
        cliente.force_authenticate(user=CustomUserFactory(sede=sede, groups=["jefe_planta"]))

        with _a_esa_hora():
            resp = cliente.get(reverse("planta-pulso-diario"))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["kg_planificados_hoy"], 100.0)


class DespachoDeNocheTest(TestCase):
    def test_despacho_dado_confirmado_a_las_21_en_la_planta_cuando_procesa_entonces_fecha_del_dia_de_la_planta(self):
        sede = Sede.objects.create(nombre="Sede Noche", location="Quito")
        bodega = Bodega.objects.create(nombre="Bodega Noche", sede=sede)
        usuario = CustomUser.objects.create_user(username="despacho_noche", password="x", sede=sede)
        usuario.groups.add(Group.objects.get_or_create(name="despacho")[0])
        usuario.bodegas_asignadas.add(bodega)
        producto = Producto.objects.create(codigo="TELA-N", descripcion="Tela N", tipo="tela", unidad_medida="kg")
        orden = OrdenProduccion.objects.create(
            codigo="OP-N1", peso_neto_requerido=Decimal("50.00"), producto_salida=producto
        )
        lote = LoteProduccion.objects.create(
            codigo_lote="LOTE-N1",
            orden_produccion=orden,
            peso_neto_producido=Decimal("50.000"),
            turno="DIURNO",
            hora_inicio=datetime(2026, 10, 27, 13, 0, tzinfo=UTC),
            hora_final=datetime(2026, 10, 27, 14, 0, tzinfo=UTC),
        )
        StockBodega.objects.create(bodega=bodega, producto=producto, lote=lote, cantidad=Decimal("50.000"))
        cliente_venta = Cliente.objects.create(
            ruc_cedula="1799999999", nombre_razon_social="Cliente Noche", direccion_envio="Dir", nivel_precio="normal"
        )
        pedido = PedidoVenta.objects.create(cliente=cliente_venta, guia_remision="GR-N", estado="pendiente", sede=sede)
        DetallePedido.objects.create(
            pedido_venta=pedido,
            producto=producto,
            cantidad=1,
            piezas=1,
            peso=Decimal("50.000"),
            precio_unitario=Decimal("10.000"),
        )
        api = APIClient()
        api.force_authenticate(user=usuario)

        with _a_esa_hora():
            resp = api.post(
                "/api/inventory/process-despacho/", {"pedidos": [pedido.id], "lotes": ["LOTE-N1"]}, format="json"
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, getattr(resp, "data", None))
        pedido.refresh_from_db()
        self.assertEqual(pedido.fecha_despacho, DIA_DE_LA_PLANTA)


class VencimientoPedidoDelDiaTest(TestCase):
    def test_crear_pedido_dado_21h_en_la_planta_cuando_calcula_vencimiento_entonces_parte_del_dia_de_la_planta(self):
        from gestion.serializers.sales_serializers import PedidoVentaSerializer

        sede = SedeFactory()
        cliente = Cliente.objects.create(
            ruc_cedula="1788888888",
            nombre_razon_social="Cliente Plazo",
            direccion_envio="Dir",
            nivel_precio="normal",
            plazo_credito_dias=30,
            sede=sede,
        )
        with _a_esa_hora():
            pedido = PedidoVentaSerializer(data={}).create({"cliente": cliente, "sede": sede, "guia_remision": "GR-V"})

        self.assertEqual(pedido.fecha_vencimiento, DIA_DE_LA_PLANTA + timedelta(days=30))


class CosteoConTarifaDelDiaTest(TestCase):
    def test_costeo_dado_lote_terminado_a_las_21_y_tarifa_desde_el_dia_siguiente_cuando_calcula_entonces_no_la_aplica(
        self,
    ):
        # El lote terminó el 27 a las 21:00 en la planta (28 en UTC): la tarifa que rige desde el 28
        # todavía no estaba vigente.
        operario = CustomUser.objects.create_user(username="op_costeo_noche", password="x")
        lote = LoteProduccionFactory(
            operario=operario,
            hora_inicio=NOCHE_EN_LA_PLANTA - timedelta(hours=2),
            hora_final=NOCHE_EN_LA_PLANTA,
        )
        TarifaOperario.objects.create(
            operario=operario,
            tipo_contrato="tiempo",
            tarifa_hora=Decimal("10.00"),
            vigente_desde=DIA_DE_LA_PLANTA + timedelta(days=1),
            sede=lote.orden_produccion.sede,
        )

        costo = CostoLoteService.calcular_costo(lote, operario)

        self.assertEqual(costo.costo_operario, Decimal("0.000"))
