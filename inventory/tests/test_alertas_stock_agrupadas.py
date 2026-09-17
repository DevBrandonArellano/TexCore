from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory,
    LoteProduccionFactory, StockBodegaFactory, OrdenProduccionFactory
)
from inventory.models import StockBodega


class AlertasStockAgrupadasTestCase(TestCase):
    """
    Pruebas unitarias para AlertasStockAPIView con agregación de múltiples lotes.
    Estándar ISTQB CTFL v4.0:
    test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
    """

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory(nombre="Sede Alertas Test")
        self.bodega = BodegaFactory(sede=self.sede, nombre="Bodega Principal")
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.admin)
        self.url = '/api/inventory/alertas-stock/'

    def test_alerta_stock_dado_producto_con_multiples_lotes_que_superan_minimo_cuando_se_consulta_alerta_entonces_no_aparece(self):
        """
        GIVEN: Un producto con stock mínimo de 100 kg y 3 lotes de 40 kg cada uno (total 120 kg en bodega)
        WHEN: Se consulta el endpoint de alertas de stock
        THEN: No debe figurar en la lista de alertas, porque el stock total supera el mínimo
        """
        op = OrdenProduccionFactory(sede=self.sede, codigo="OP-ALT-01", peso_neto_requerido=Decimal("200.00"))
        producto = ProductoFactory(
            codigo="HILO-30-1",
            descripcion="Hilo 30/1 Algodón",
            stock_minimo=Decimal("100.000"),
            sede=self.sede,
        )

        lote1 = LoteProduccionFactory(orden_produccion=op, codigo_lote="LOT-ALT-01")
        lote2 = LoteProduccionFactory(orden_produccion=op, codigo_lote="LOT-ALT-02")
        lote3 = LoteProduccionFactory(orden_produccion=op, codigo_lote="LOT-ALT-03")

        # 3 lotes de 40 kg = 120 kg en la misma bodega
        StockBodega.objects.create(bodega=self.bodega, producto=producto, lote=lote1, cantidad=Decimal("40.000"))
        StockBodega.objects.create(bodega=self.bodega, producto=producto, lote=lote2, cantidad=Decimal("40.000"))
        StockBodega.objects.create(bodega=self.bodega, producto=producto, lote=lote3, cantidad=Decimal("40.000"))

        response = self.client.get(self.url, {'sede_id': self.sede.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # No debe haber alerta para HILO-30-1
        codigos_en_alerta = [item['producto_codigo'] for item in response.data]
        self.assertNotIn("HILO-30-1", codigos_en_alerta)

    def test_alerta_stock_dado_producto_con_multiples_lotes_que_no_superan_minimo_cuando_se_consulta_alerta_entonces_aparece_agrupado(self):
        """
        GIVEN: Un producto con stock mínimo de 100 kg y 2 lotes de 30 kg cada uno (total 60 kg en bodega, faltan 40 kg)
        WHEN: Se consulta el endpoint de alertas de stock
        THEN: Debe figurar exactamente UNA vez con stock_actual=60.000 y faltante=40.000
        """
        op = OrdenProduccionFactory(sede=self.sede, codigo="OP-ALT-02", peso_neto_requerido=Decimal("200.00"))
        producto = ProductoFactory(
            codigo="TELA-PIQUE-01",
            descripcion="Tela Piqué Azul",
            stock_minimo=Decimal("100.000"),
            sede=self.sede,
        )

        lote1 = LoteProduccionFactory(orden_produccion=op, codigo_lote="LOT-PIQ-01")
        lote2 = LoteProduccionFactory(orden_produccion=op, codigo_lote="LOT-PIQ-02")

        # 2 lotes de 30 kg = 60 kg en la misma bodega
        StockBodega.objects.create(bodega=self.bodega, producto=producto, lote=lote1, cantidad=Decimal("30.000"))
        StockBodega.objects.create(bodega=self.bodega, producto=producto, lote=lote2, cantidad=Decimal("30.000"))

        response = self.client.get(self.url, {'sede_id': self.sede.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        alertas_producto = [item for item in response.data if item['producto_codigo'] == "TELA-PIQUE-01"]
        # Debe aparecer exactamente una vez (no duplicado por lote)
        self.assertEqual(len(alertas_producto), 1)

        alerta = alertas_producto[0]
        self.assertEqual(alerta['stock_actual'], Decimal("60.000"))
        self.assertEqual(alerta['stock_minimo'], Decimal("100.000"))
        self.assertEqual(alerta['faltante'], Decimal("40.000"))
