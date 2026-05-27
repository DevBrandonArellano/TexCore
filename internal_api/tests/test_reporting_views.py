"""Tests para endpoints de reporting. EP por endpoint representativo."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import Bodega, Producto, Sede


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


class TestReportingEndpoints(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {_make_service_token()}")
        self.sede = Sede.objects.create(nombre="Sede R")
        self.bodega = Bodega.objects.create(nombre="Bodega R", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="R-001",
            descripcion="Prod Report",
            tipo="hilo",
            unidad_medida="kg",
            sede=self.sede,
        )

    # EP: productos → 200 retorna lista JSON
    def test_productos_dado_token_valido_cuando_solicita_entonces_retorna_200(self):
        resp = self.client.get("/api/internal/v1/reports/productos/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    # EP: stock-actual requiere bodega_id
    def test_stock_actual_dado_bodega_valida_cuando_solicita_entonces_retorna_200(self):
        resp = self.client.get(
            f"/api/internal/v1/reports/stock-actual/?bodega_id={self.bodega.id}"
        )
        self.assertEqual(resp.status_code, 200)

    # EP: stock-actual sin bodega_id → 400
    def test_stock_actual_dado_sin_bodega_cuando_solicita_entonces_retorna_400(self):
        resp = self.client.get("/api/internal/v1/reports/stock-actual/")
        self.assertEqual(resp.status_code, 400)

    # EP: scope incorrecto → 403
    def test_productos_dado_scope_incorrecto_cuando_solicita_entonces_retorna_403(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {_make_service_token(scopes=['lotes:read'])}"
        )
        resp = self.client.get("/api/internal/v1/reports/productos/")
        self.assertEqual(resp.status_code, 403)

    # EP: tendencia retorna 200
    def test_tendencia_produccion_dado_token_valido_cuando_solicita_entonces_retorna_200(self):
        resp = self.client.get("/api/internal/v1/produccion/tendencia/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    # EP: ordenes produccion retorna 200
    def test_ordenes_produccion_dado_token_valido_cuando_solicita_entonces_retorna_200(self):
        resp = self.client.get("/api/internal/v1/produccion/ordenes/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)
