"""
Alertas de stock del bodeguero: filtro por bodega y búsqueda de productos.

Sin búsqueda, el endpoint devuelve solo los productos bajo el mínimo (las alertas).
Con búsqueda, devuelve todos los productos que coinciden con su estado, para que el
bodeguero verifique si un producto está bajo o no.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con / sin búsqueda; bodega propia / ajena.
- Análisis de valores límite (BVA): stock igual al mínimo, por debajo, mínimo en 0.
"""

from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from gestion.tests.factories import (
    BodegaFactory,
    CustomUserFactory,
    LoteProduccionFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    SedeFactory,
)
from inventory.models import StockBodega

URL = "/api/inventory/alertas-stock/"


class AlertasStockFiltrosTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory(nombre="Sede Filtros Alertas")
        self.bodega_a = BodegaFactory(sede=self.sede, nombre="Bodega A")
        self.bodega_b = BodegaFactory(sede=self.sede, nombre="Bodega B")
        self.bodeguero = CustomUserFactory(sede=self.sede, groups=["bodeguero"])
        self.bodeguero.bodegas_asignadas.add(self.bodega_a, self.bodega_b)
        self.client.force_authenticate(user=self.bodeguero)

        self.hilo_bajo = ProductoFactory(codigo="HILO-BAJO", descripcion="Hilo azul", stock_minimo=Decimal("100"))
        self.hilo_ok = ProductoFactory(codigo="HILO-OK", descripcion="Hilo rojo", stock_minimo=Decimal("100"))
        self.tela_sin_minimo = ProductoFactory(codigo="TELA-LIBRE", descripcion="Tela cruda", stock_minimo=Decimal("0"))
        self._stock(self.bodega_a, self.hilo_bajo, "40")
        self._stock(self.bodega_b, self.hilo_bajo, "10")
        self._stock(self.bodega_a, self.hilo_ok, "100")  # límite: igual al mínimo no es bajo
        self._stock(self.bodega_a, self.tela_sin_minimo, "5")

    @staticmethod
    def _stock(bodega, producto, cantidad):
        StockBodega.objects.create(bodega=bodega, producto=producto, cantidad=Decimal(cantidad))

    def _filas(self, **params):
        resp = self.client.get(URL, params)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return {(f["bodega"], f["producto_codigo"]): f for f in resp.data}

    def test_alertas_dado_sin_busqueda_cuando_consulta_entonces_solo_productos_bajo_minimo(self):
        filas = self._filas()
        self.assertEqual(set(filas), {("Bodega A", "HILO-BAJO"), ("Bodega B", "HILO-BAJO")})
        self.assertTrue(all(f["estado"] == "bajo" for f in filas.values()))

    def test_alertas_dado_bodega_id_cuando_consulta_entonces_solo_esa_bodega(self):
        filas = self._filas(bodega_id=self.bodega_b.id)
        self.assertEqual(set(filas), {("Bodega B", "HILO-BAJO")})
        self.assertEqual(filas[("Bodega B", "HILO-BAJO")]["bodega_id"], self.bodega_b.id)

    def test_alertas_dado_busqueda_cuando_consulta_entonces_incluye_productos_sin_alerta_con_su_estado(self):
        filas = self._filas(search="hilo", bodega_id=self.bodega_a.id)
        self.assertEqual(filas[("Bodega A", "HILO-BAJO")]["estado"], "bajo")
        self.assertEqual(filas[("Bodega A", "HILO-OK")]["estado"], "ok")
        self.assertEqual(filas[("Bodega A", "HILO-OK")]["faltante"], 0)
        self.assertNotIn(("Bodega A", "TELA-LIBRE"), filas)

    def test_alertas_dado_busqueda_por_codigo_de_producto_sin_minimo_cuando_consulta_entonces_estado_sin_minimo(self):
        filas = self._filas(search="TELA-LIB")
        self.assertEqual(set(filas), {("Bodega A", "TELA-LIBRE")})
        self.assertEqual(filas[("Bodega A", "TELA-LIBRE")]["estado"], "sin_minimo")

    def test_alertas_dado_bodega_no_asignada_cuando_consulta_entonces_lista_vacia(self):
        ajena = BodegaFactory(sede=self.sede, nombre="Bodega ajena")
        self._stock(ajena, self.hilo_bajo, "1")
        self.assertEqual(self._filas(bodega_id=ajena.id), {})
        self.assertEqual(self._filas(bodega_id=ajena.id, search="hilo"), {})

    def test_alertas_dado_bodega_id_no_numerico_cuando_consulta_entonces_400(self):
        resp = self.client.get(URL, {"bodega_id": "abc"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_alertas_dado_busqueda_solo_con_espacios_cuando_consulta_entonces_se_comporta_como_sin_busqueda(self):
        self.assertEqual(set(self._filas(search="   ")), {("Bodega A", "HILO-BAJO"), ("Bodega B", "HILO-BAJO")})

    def test_alertas_dado_lotes_en_la_misma_bodega_cuando_busca_entonces_suma_y_devuelve_una_fila(self):
        orden = OrdenProduccionFactory(sede=self.sede)
        for codigo in ("LOT-FIL-1", "LOT-FIL-2"):
            StockBodega.objects.create(
                bodega=self.bodega_a,
                producto=self.hilo_ok,
                cantidad=Decimal("15"),
                lote=LoteProduccionFactory(orden_produccion=orden, codigo_lote=codigo),
            )
        filas = self._filas(search="HILO-OK")
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[("Bodega A", "HILO-OK")]["stock_actual"], Decimal("130"))
