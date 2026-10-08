"""Tests para endpoint de validación de lote. EP + BVA."""
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import (
    Area,
    Bodega,
    CustomUser,
    LoteProduccion,
    Maquina,
    OrdenProduccion,
    Producto,
    Sede,
)
from inventory.models import StockBodega


def _make_service_token(service="scanning_service", scopes=None):
    now = datetime.now(UTC)
    payload = {
        "iss": "texcore",
        "sub": service,
        "scope": scopes or ["lotes:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=900),
        "type": "service_access",
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class _LoteConStockMixin:
    def setUp(self):
        self.client = APIClient()
        self.token = _make_service_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.sede = Sede.objects.create(nombre="Sede Test")
        self.area = Area.objects.create(nombre="Area Test", sede=self.sede)
        self.bodega = Bodega.objects.create(nombre="Bodega Test", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="P-001",
            descripcion="Hilo Test",
            tipo="hilo",
            unidad_medida="kg",
            sede=self.sede,
        )
        self.operario = CustomUser.objects.create_user(
            username="operario_test", password="test123", sede=self.sede
        )
        self.maquina = Maquina.objects.create(
            nombre="Maq-01",
            capacidad_maxima=100,
            eficiencia_ideal="0.90",
            area=self.area,
        )
        self.op = OrdenProduccion.objects.create(
            codigo="OP-001",
            producto_entrada=self.producto,
            producto_salida=self.producto,
            peso_neto_requerido=100,
            sede=self.sede,
        )
        self.lote = LoteProduccion.objects.create(
            orden_produccion=self.op,
            codigo_lote="LOT-2026-001",
            peso_neto_producido=95,
            operario=self.operario,
            maquina=self.maquina,
            turno="mañana",
            hora_inicio="2026-05-01T08:00:00Z",
            hora_final="2026-05-01T16:00:00Z",
        )
        self.stock = StockBodega.objects.create(
            bodega=self.bodega,
            producto=self.producto,
            lote=self.lote,
            cantidad=95,
        )


class TestValidateLoteView(_LoteConStockMixin, TestCase):
    # EP: lote válido con stock → 200 con datos completos
    def test_validate_lote_dado_lote_con_stock_cuando_valida_entonces_retorna_200(self):
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["codigo_lote"], "LOT-2026-001")
        self.assertEqual(resp.data["producto"]["descripcion"], "Hilo Test")
        self.assertIsNotNone(resp.data["peso_kg"])
        self.assertEqual(resp.data["bodega"]["nombre"], "Bodega Test")

    # EP: lote inexistente → 404
    def test_validate_lote_dado_codigo_inexistente_cuando_valida_entonces_retorna_404(self):
        resp = self.client.get("/api/internal/v1/lotes/NO-EXISTE/validate/")
        self.assertEqual(resp.status_code, 404)

    # BVA: lote existe pero stock=0 → 200 con peso_kg=None
    def test_validate_lote_dado_stock_cero_cuando_valida_entonces_retorna_peso_nulo(self):
        self.stock.cantidad = 0
        self.stock._justificacion_auditoria = "Test stock cero"
        self.stock.save()
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["peso_kg"])

    # EP: sin token → 401
    def test_validate_lote_dado_sin_token_cuando_valida_entonces_retorna_403(self):
        self.client.credentials()
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 401)

    # EP: scope incorrecto → 403
    def test_validate_lote_dado_scope_incorrecto_cuando_valida_entonces_retorna_403(self):
        token = _make_service_token(scopes=["reports:read"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 403)

    # EP: código con caracteres fuera del patrón permitido → 404 (no matchea la URL)
    def test_validate_lote_dado_codigo_con_caracteres_invalidos_cuando_valida_entonces_retorna_404(self):
        resp = self.client.get("/api/internal/v1/lotes/LOTE%20CON%20ESPACIOS/validate/")
        self.assertEqual(resp.status_code, 404)

    # BVA: código de 51 caracteres (límite+1) → 404 (no matchea la URL)
    def test_validate_lote_dado_codigo_de_51_caracteres_cuando_valida_entonces_retorna_404(self):
        codigo_largo = "A" * 51
        resp = self.client.get(f"/api/internal/v1/lotes/{codigo_largo}/validate/")
        self.assertEqual(resp.status_code, 404)

    # BVA: código de exactamente 50 caracteres (límite) → matchea la URL (404 por no
    # existir el lote, pero desde la vista, no desde el router — confirma el límite superior)
    def test_validate_lote_dado_codigo_de_50_caracteres_cuando_valida_entonces_llega_a_la_vista(self):
        codigo_limite = "A" * 50
        resp = self.client.get(f"/api/internal/v1/lotes/{codigo_limite}/validate/")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data["detail"], "Lote no encontrado.")


class TestValidateLoteFilasVendibles(_LoteConStockMixin, TestCase):
    """
    El escáner de producción llega aquí vía scanning_service. Defecto encontrado al revisar
    la ruta (2026-10-07): esta vista tomaba la primera fila de stock del lote, que podía ser
    la merma vendible (el mismo defecto que fc403f0 corrigió en ValidateLoteAPIView), y
    exigía el producto de la OP. Ahora informa la fila del producto del lote y, aparte,
    todas las filas vendibles (productos agregados a mano), nunca la merma.
    """

    def setUp(self):
        super().setUp()
        self.bodega_merma = Bodega.objects.create(nombre="Bodega Merma", sede=self.sede)
        self.merma = Producto.objects.create(codigo="M-001", descripcion="Merma", tipo="subproducto",
                                             unidad_medida="kg", sede=self.sede)
        self.cono = Producto.objects.create(codigo="C-001", descripcion="Cono", tipo="hilo",
                                            unidad_medida="kg", sede=self.sede)

    def _registrar_merma(self):
        from inventory.models import MovimientoInventario
        StockBodega.objects.create(bodega=self.bodega_merma, producto=self.merma, lote=self.lote, cantidad=5)
        MovimientoInventario.objects.create(
            tipo_movimiento="PRODUCCION", producto=self.merma, lote=self.lote, bodega_destino=self.bodega_merma,
            cantidad=5, documento_ref=f"MERMA-{self.lote.codigo_lote}", usuario=self.operario, saldo_resultante=5)

    def _validar(self):
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 200)
        return resp.data

    def test_validate_lote_dado_merma_creada_antes_cuando_valida_entonces_informa_el_producto_del_lote(self):
        StockBodega.objects.filter(pk=self.stock.pk).delete()
        self._registrar_merma()
        self.stock = StockBodega.objects.create(bodega=self.bodega, producto=self.producto, lote=self.lote,
                                                cantidad=95)
        data = self._validar()
        self.assertEqual((data["producto"]["id"], data["peso_kg"], data["bodega"]["id"]),
                         (self.producto.id, "95.000", self.bodega.id))
        self.assertEqual(data["stock_id"], self.stock.id)

    def test_validate_lote_dado_producto_manual_cuando_valida_entonces_lo_lista_sin_la_merma(self):
        self._registrar_merma()
        StockBodega.objects.create(bodega=self.bodega, producto=self.cono, lote=self.lote, cantidad=30)
        data = self._validar()
        self.assertEqual(data["peso_total_kg"], "125.000")
        self.assertEqual(
            [(p["producto_id"], p["descripcion"], p["peso_kg"], p["bodega"]["id"]) for p in data["productos"]],
            [(self.producto.id, "Hilo Test", "95.000", self.bodega.id),
             (self.cono.id, "Cono", "30.000", self.bodega.id)],
        )

    def test_validate_lote_dado_solo_producto_manual_cuando_valida_entonces_es_el_producto_informado(self):
        StockBodega.objects.filter(pk=self.stock.pk).delete()
        StockBodega.objects.create(bodega=self.bodega, producto=self.cono, lote=self.lote, cantidad=30)
        data = self._validar()
        self.assertEqual((data["producto"]["id"], data["peso_kg"]), (self.cono.id, "30.000"))

    def test_validate_lote_dado_solo_merma_cuando_valida_entonces_sin_stock_vendible(self):
        StockBodega.objects.filter(pk=self.stock.pk).delete()
        self._registrar_merma()
        data = self._validar()
        self.assertIsNone(data["peso_kg"])
        self.assertEqual(data["productos"], [])
