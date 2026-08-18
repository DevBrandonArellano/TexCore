"""Tests para endpoint de validación de lote. EP + BVA."""
import uuid
from datetime import datetime, timedelta, timezone

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
    now = datetime.now(timezone.utc)
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


class TestValidateLoteView(TestCase):
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
