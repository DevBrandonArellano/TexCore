"""
Pruebas complementarias de internal_api/views/reporting_views.py — cubre
las 14 vistas que test_reporting_views.py no ejercita (solo cubría
productos, stock-actual, tendencia y ordenes).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con y sin filtros opcionales (sede_id,
  fecha_desde/hasta, producto_id), bodega_id requerido vs. ausente.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import Bodega, Cliente, PagoCliente, PedidoVenta, Producto, Sede
from gestion.tests.factories import (
    CustomUserFactory, LoteProduccionFactory, OrdenProduccionFactory, StockBodegaFactory,
)
from inventory.models import MovimientoInventario


def _make_service_token(scopes=None):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore",
        "sub": "reporting_excel",
        "scope": scopes or ["reports:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=900),
        "type": "service_access",
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class ReportingViewsExtraTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {_make_service_token()}")
        self.sede = Sede.objects.create(nombre="Sede QA")
        self.bodega = Bodega.objects.create(nombre="Bodega QA", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="QA-001", descripcion="Producto QA", tipo="hilo",
            unidad_medida="kg", sede=self.sede,
        )
        self.vendedor = CustomUserFactory(groups=['vendedor'], sede=self.sede)
        self.cliente = Cliente.objects.create(
            ruc_cedula="1799999999", nombre_razon_social="Cliente QA",
            direccion_envio="Calle QA", nivel_precio="normal", sede=self.sede,
            vendedor_asignado=self.vendedor, is_active=True,
        )

    # ── Inventario ──────────────────────────────────────────────────────

    def test_kardex_dado_sin_bodega_id_cuando_get_entonces_400(self):
        resp = self.client.get("/api/internal/v1/reports/kardex/")
        self.assertEqual(resp.status_code, 400)

    def test_kardex_dado_bodega_valida_y_filtros_cuando_get_entonces_200(self):
        MovimientoInventario.objects.create(
            tipo_movimiento='AJUSTE', producto=self.producto, bodega_origen=self.bodega,
            cantidad=Decimal('10.000'),
        )
        resp = self.client.get(
            f"/api/internal/v1/reports/kardex/?bodega_id={self.bodega.id}"
            f"&producto_id={self.producto.id}&fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_kardex_dado_movimiento_entrada_con_bodega_destino_cuando_get_entonces_200_lo_incluye(self):
        # Regresión: toda entrada real (COMPRA/PRODUCCION/DEVOLUCION/AJUSTE)
        # se crea con bodega_destino, nunca bodega_origen — ver
        # MovimientoInventarioViewSet.create() en inventory/views/movimiento_views.py.
        # Antes del fix, KardexView filtraba solo por bodega_origen_id y este
        # movimiento nunca aparecía, aunque sí fuera visible en el Kardex de pantalla.
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, bodega_destino=self.bodega,
            cantidad=Decimal('25.000'),
        )
        resp = self.client.get(f"/api/internal/v1/reports/kardex/?bodega_id={self.bodega.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['tipo_movimiento'], 'COMPRA')

    def test_usuarios_dado_filtro_sede_id_cuando_get_entonces_200(self):
        resp = self.client.get(f"/api/internal/v1/reports/usuarios/?sede_id={self.sede.id}")
        self.assertEqual(resp.status_code, 200)
        usernames = {u['username'] for u in resp.data}
        self.assertIn(self.vendedor.username, usernames)

    def test_valorizacion_dado_sin_bodega_id_cuando_get_entonces_400(self):
        resp = self.client.get("/api/internal/v1/reports/valorizacion/")
        self.assertEqual(resp.status_code, 400)

    def test_valorizacion_dado_bodega_valida_cuando_get_entonces_200_con_valor_total(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, cantidad=Decimal('4.000'))
        resp = self.client.get(f"/api/internal/v1/reports/valorizacion/?bodega_id={self.bodega.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertIn('valor_total', resp.data[0])

    def test_aging_dado_sin_bodega_id_cuando_get_entonces_400(self):
        resp = self.client.get("/api/internal/v1/reports/aging/")
        self.assertEqual(resp.status_code, 400)

    def test_aging_dado_stock_sin_movimiento_reciente_cuando_get_entonces_200_lo_incluye(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, cantidad=Decimal('3.000'))
        resp = self.client.get(
            f"/api/internal/v1/reports/aging/?bodega_id={self.bodega.id}&dias_minimos=15",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_aging_dado_producto_con_entrada_reciente_via_bodega_destino_cuando_get_entonces_200_lo_excluye(self):
        # Regresión: una COMPRA reciente (bodega_destino) no debe clasificar
        # el producto como "envejecido" — antes del fix, la subconsulta de
        # AgingView solo miraba bodega_origen_id y nunca detectaba esta entrada.
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, cantidad=Decimal('5.000'))
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, bodega_destino=self.bodega,
            cantidad=Decimal('5.000'),
        )
        resp = self.client.get(
            f"/api/internal/v1/reports/aging/?bodega_id={self.bodega.id}&dias_minimos=15",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_rotacion_dado_sin_bodega_id_cuando_get_entonces_400(self):
        resp = self.client.get("/api/internal/v1/reports/rotacion/")
        self.assertEqual(resp.status_code, 400)

    def test_rotacion_dado_bodega_valida_cuando_get_entonces_200_totaliza_salidas(self):
        MovimientoInventario.objects.create(
            tipo_movimiento='CONSUMO', producto=self.producto, bodega_origen=self.bodega,
            cantidad=Decimal('7.000'),
        )
        resp = self.client.get(
            f"/api/internal/v1/reports/rotacion/?bodega_id={self.bodega.id}"
            f"&fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['total_salidas'], Decimal('7.000'))

    def test_rotacion_dado_movimiento_entrada_con_bodega_destino_cuando_get_entonces_200_no_lo_totaliza(self):
        # Regresión inversa a Kardex/Resumen: una entrada (bodega_destino) NO
        # debe sumarse en total_salidas. Fija el comportamiento correcto para
        # que un fix futuro no aplique por error el mismo OR de Kardex aquí.
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, bodega_destino=self.bodega,
            cantidad=Decimal('9.000'),
        )
        resp = self.client.get(
            f"/api/internal/v1/reports/rotacion/?bodega_id={self.bodega.id}"
            f"&fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_stock_cero_dado_sin_bodega_id_cuando_get_entonces_400(self):
        resp = self.client.get("/api/internal/v1/reports/stock-cero/")
        self.assertEqual(resp.status_code, 400)

    def test_stock_cero_dado_stock_en_cero_cuando_get_entonces_200_lo_incluye(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, cantidad=Decimal('0.000'))
        resp = self.client.get(f"/api/internal/v1/reports/stock-cero/?bodega_id={self.bodega.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_resumen_movimientos_dado_sin_bodega_id_cuando_get_entonces_400(self):
        resp = self.client.get("/api/internal/v1/reports/resumen-movimientos/")
        self.assertEqual(resp.status_code, 400)

    def test_resumen_movimientos_dado_bodega_valida_cuando_get_entonces_200_agrupa_por_tipo(self):
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, bodega_origen=self.bodega,
            cantidad=Decimal('12.000'),
        )
        resp = self.client.get(
            f"/api/internal/v1/reports/resumen-movimientos/?bodega_id={self.bodega.id}"
            f"&fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['tipo_movimiento'], 'COMPRA')

    def test_resumen_movimientos_dado_movimiento_entrada_con_bodega_destino_cuando_get_entonces_200_lo_incluye(self):
        # Regresión: una COMPRA real (bodega_destino) debe aparecer en el
        # resumen igual que en el test anterior (que usa bodega_origen, algo
        # que la API real nunca permite para COMPRA — ver movimiento_views.py).
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, bodega_destino=self.bodega,
            cantidad=Decimal('12.000'),
        )
        resp = self.client.get(
            f"/api/internal/v1/reports/resumen-movimientos/?bodega_id={self.bodega.id}"
            f"&fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['tipo_movimiento'], 'COMPRA')
        self.assertEqual(resp.data[0]['total'], Decimal('12.000'))

    # ── Vendedores ──────────────────────────────────────────────────────

    def test_ventas_vendedor_dado_pedidos_cuando_get_entonces_200_excluye_anulados(self):
        PedidoVenta.objects.create(
            cliente=self.cliente, sede=self.sede, vendedor_asignado=self.vendedor,
            guia_remision='GR-QA-1',
        )
        PedidoVenta.objects.create(
            cliente=self.cliente, sede=self.sede, vendedor_asignado=self.vendedor,
            guia_remision='GR-QA-2', anulado=True,
        )
        resp = self.client.get(f"/api/internal/v1/vendedores/{self.vendedor.id}/ventas/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['guia_remision'], 'GR-QA-1')

    def test_ventas_vendedor_dado_filtro_fechas_cuando_get_entonces_200(self):
        resp = self.client.get(
            f"/api/internal/v1/vendedores/{self.vendedor.id}/ventas/"
            f"?fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)

    def test_top_clientes_vendedor_dado_pedidos_cuando_get_entonces_200_top_10(self):
        PedidoVenta.objects.create(
            cliente=self.cliente, sede=self.sede, vendedor_asignado=self.vendedor,
            guia_remision='GR-QA-3',
        )
        resp = self.client.get(f"/api/internal/v1/vendedores/{self.vendedor.id}/top-clientes/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['cliente_id'], self.cliente.id)

    def test_deudores_vendedor_dado_cliente_activo_cuando_get_entonces_200_con_total_pagado(self):
        PagoCliente.objects.create(cliente=self.cliente, sede=self.sede, monto=Decimal('50.000'))
        resp = self.client.get(f"/api/internal/v1/vendedores/{self.vendedor.id}/deudores/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['total_pagado'], Decimal('50.000'))

    # ── Gerencial ───────────────────────────────────────────────────────

    def test_ventas_gerencial_dado_filtro_sede_cuando_get_entonces_200(self):
        PedidoVenta.objects.create(
            cliente=self.cliente, sede=self.sede, vendedor_asignado=self.vendedor,
            guia_remision='GR-QA-GER-1',
        )
        resp = self.client.get(f"/api/internal/v1/gerencial/ventas/?sede_id={self.sede.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_ventas_gerencial_dado_filtro_fechas_cuando_get_entonces_200(self):
        resp = self.client.get(
            "/api/internal/v1/gerencial/ventas/?fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)

    def test_top_clientes_gerencial_dado_pedidos_cuando_get_entonces_200_top_20(self):
        PedidoVenta.objects.create(
            cliente=self.cliente, sede=self.sede, vendedor_asignado=self.vendedor,
            guia_remision='GR-QA-GER-2',
        )
        resp = self.client.get("/api/internal/v1/gerencial/top-clientes/?sede_id=" + str(self.sede.id))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_deudores_gerencial_dado_filtro_sede_cuando_get_entonces_200(self):
        PagoCliente.objects.create(cliente=self.cliente, sede=self.sede, monto=Decimal('20.000'))
        resp = self.client.get(f"/api/internal/v1/gerencial/deudores/?sede_id={self.sede.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data[0]['total_pagado'], Decimal('20.000'))

    def test_deudores_gerencial_dado_sin_filtro_sede_cuando_get_entonces_200_ve_todo(self):
        resp = self.client.get("/api/internal/v1/gerencial/deudores/")
        self.assertEqual(resp.status_code, 200)

    # ── Producción ──────────────────────────────────────────────────────

    def test_lotes_produccion_dado_filtros_cuando_get_entonces_200(self):
        orden = OrdenProduccionFactory(sede=self.sede)
        LoteProduccionFactory(
            orden_produccion=orden,
            hora_inicio=datetime(2026, 1, 1, 8, 0), hora_final=datetime(2026, 1, 1, 16, 0),
        )
        resp = self.client.get(
            "/api/internal/v1/produccion/lotes/"
            f"?sede_id={self.sede.id}&fecha_desde=2020-01-01&fecha_hasta=2030-01-01",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
