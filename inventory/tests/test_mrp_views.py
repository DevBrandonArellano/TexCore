"""
API del MRP por sede (TEX-27, ADR-012).

- POST /api/inventory/sugerencias-compra/ejecutar-mrp/ con {sede_id} o {todas: true}.
  El bodeguero y el administrador de sede ejecutan solo su sede; el ejecutivo y el
  administrador de sistemas, cualquiera o todas.
- GET .../ultima-ejecucion/ y .../necesidades-produccion/ por sede.
- Las listas de requerimientos y sugerencias se filtran por sede.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): rol global / de sede / sin MRP; sede propia / ajena.
- Tabla de decisión (TD): sede_id × todas × rol.
"""

from decimal import Decimal
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import Sede
from gestion.tests.factories import CustomUserFactory, ProductoFactory, SedeFactory
from inventory.models import MRPEjecucion, OrdenCompraSugerida, RequerimientoMaterial, StockBodega
from inventory.services.mrp import MRPEngine
from inventory.tests.test_mrp import _EscenarioMRP

EJECUTAR = reverse("sugerencia-compra-ejecutar-mrp")
ULTIMA = reverse("sugerencia-compra-ultima-ejecucion")
NECESIDADES = reverse("sugerencia-compra-necesidades-produccion")


class EjecutarMRPAPITestCase(_EscenarioMRP):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.otra_sede = SedeFactory(nombre="Otra Sede")

    def _como(self, grupo, sede="propia"):
        usuario = CustomUserFactory(sede=self.sede if sede == "propia" else sede, groups=[grupo])
        self.client.force_authenticate(user=usuario)
        return usuario

    def test_ejecutar_dado_bodeguero_sin_sede_id_cuando_post_entonces_calcula_su_sede(self):
        bodeguero = self._como("bodeguero")

        resp = self.client.post(EJECUTAR, {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        (ejecucion,) = resp.data["ejecuciones"]
        self.assertEqual(ejecucion["sede"], self.sede.id)
        self.assertEqual(ejecucion["estado"], "completada")
        self.assertEqual(ejecucion["sugerencias_compra"], 3)
        self.assertEqual(ejecucion["iniciada_por_nombre"], bodeguero.username)

    def test_ejecutar_dado_bodeguero_con_sede_ajena_cuando_post_entonces_403_sin_calcular(self):
        self._como("bodeguero")
        resp = self.client.post(EJECUTAR, {"sede_id": self.otra_sede.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(MRPEjecucion.objects.exists())

    def test_ejecutar_dado_admin_sede_con_todas_cuando_post_entonces_403(self):
        self._como("admin_sede")
        resp = self.client.post(EJECUTAR, {"todas": True}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_ejecutar_dado_ejecutivo_con_todas_cuando_post_entonces_una_ejecucion_por_sede_activa(self):
        inactiva = SedeFactory(status="inactivo")
        self._como("ejecutivo")

        resp = self.client.post(EJECUTAR, {"todas": True}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        calculadas = {e["sede"] for e in resp.data["ejecuciones"]}
        self.assertEqual(calculadas, set(Sede.objects.filter(status="activo").values_list("id", flat=True)))
        self.assertTrue({self.sede.id, self.otra_sede.id} <= calculadas)
        self.assertNotIn(inactiva.id, calculadas)

    def test_ejecutar_dado_ejecutivo_con_otra_sede_cuando_post_entonces_calcula_esa_sede(self):
        self._como("ejecutivo")
        resp = self.client.post(EJECUTAR, {"sede_id": self.otra_sede.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["ejecuciones"][0]["sede"], self.otra_sede.id)

    def test_ejecutar_dado_sede_inexistente_cuando_post_entonces_404(self):
        self._como("admin_sistemas", sede=None)
        resp = self.client.post(EJECUTAR, {"sede_id": 999999}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_ejecutar_dado_usuario_global_sin_sede_ni_sede_id_cuando_post_entonces_400(self):
        self._como("admin_sistemas", sede=None)
        resp = self.client.post(EJECUTAR, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ejecutar_dado_sede_id_no_numerico_cuando_post_entonces_400(self):
        self._como("ejecutivo")
        resp = self.client.post(EJECUTAR, {"sede_id": "abc"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ejecutar_dado_rol_sin_mrp_cuando_post_entonces_403(self):
        for grupo in ("operario", "vendedor", "despacho", "jefe_planta"):
            with self.subTest(grupo=grupo):
                self._como(grupo)
                self.assertEqual(self.client.post(EJECUTAR, {}, format="json").status_code, status.HTTP_403_FORBIDDEN)

    def test_ejecutar_dado_fallo_del_motor_cuando_post_entonces_500_con_la_ejecucion_fallida(self):
        self._como("bodeguero")
        with (
            patch("inventory.services.mrp.motor.requerimientos_de_orden", side_effect=RuntimeError("boom")),
            self.assertLogs("inventory.mrp", level="ERROR"),
        ):
            resp = self.client.post(EJECUTAR, {}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        (ejecucion,) = resp.data["ejecuciones"]
        self.assertEqual(ejecucion["estado"], "fallida")
        self.assertNotIn("boom", ejecucion["mensaje_error"])

    def test_ejecutar_dado_bodeguero_y_ejecutivo_cuando_calculan_la_misma_sede_entonces_resultados_identicos(self):
        # TEX-27 CA-4: ambos comparten el mismo motor.
        def sugerencias():
            filas = OrdenCompraSugerida.objects.filter(sede=self.sede)
            return sorted((s.producto_id, s.cantidad_sugerida) for s in filas)

        self._como("bodeguero")
        self.client.post(EJECUTAR, {}, format="json")
        del_bodeguero = sugerencias()
        self._como("ejecutivo")
        self.client.post(EJECUTAR, {"sede_id": self.sede.id}, format="json")

        self.assertEqual(sugerencias(), del_bodeguero)


class ConsultasMRPAPITestCase(_EscenarioMRP):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.otra_sede = SedeFactory(nombre="Otra Sede")
        StockBodega.objects.create(bodega=self.bodega_mp, producto=self.materia_prima, cantidad=Decimal("10"))
        MRPEngine.ejecutar(self.sede)
        otra = MRPEngine.ejecutar(self.otra_sede)
        producto_otra = ProductoFactory(sede=self.otra_sede, tipo="quimico")
        OrdenCompraSugerida.objects.create(
            ejecucion=otra,
            producto=producto_otra,
            sede=self.otra_sede,
            requerido=Decimal("1"),
            stock_minimo=Decimal("0"),
            stock_disponible=Decimal("0"),
            cantidad_sugerida=Decimal("1"),
        )

    def _como(self, grupo, sede=None):
        self.client.force_authenticate(user=CustomUserFactory(sede=sede or self.sede, groups=[grupo]))

    def test_sugerencias_dado_bodeguero_cuando_lista_entonces_solo_su_sede_con_desglose(self):
        self._como("bodeguero")
        filas = self.client.get(reverse("sugerencia-compra-list")).data["results"]
        self.assertEqual({f["sede"] for f in filas}, {self.sede.id})
        mp = next(f for f in filas if f["producto_codigo"] == "MP-ALG")
        self.assertEqual(
            (mp["requerido"], mp["stock_minimo"], mp["stock_disponible"], mp["cantidad_sugerida"]),
            ("100.000", "20.000", "10.000", "110.000"),
        )

    def test_sugerencias_dado_ejecutivo_con_filtro_de_sede_cuando_lista_entonces_esa_sede(self):
        self._como("ejecutivo")
        filas = self.client.get(reverse("sugerencia-compra-list"), {"sede": self.otra_sede.id}).data["results"]
        self.assertEqual({f["sede"] for f in filas}, {self.otra_sede.id})

    def test_requerimientos_dado_bodeguero_cuando_lista_entonces_trae_la_orden_de_origen(self):
        self._como("bodeguero")
        filas = self.client.get(reverse("requerimiento-material-list")).data["results"]
        self.assertEqual(len(filas), RequerimientoMaterial.objects.filter(sede=self.sede).count())
        self.assertEqual({f["orden_codigo"] for f in filas}, {self.orden.codigo})

    def test_sugerencias_dado_page_size_cuando_lista_entonces_pagina_en_el_servidor(self):
        self._como("bodeguero")
        resp = self.client.get(reverse("sugerencia-compra-list"), {"page_size": 1})
        self.assertEqual(len(resp.data["results"]), 1)
        self.assertEqual(resp.data["count"], OrdenCompraSugerida.objects.filter(sede=self.sede).count())

    def test_requerimientos_dado_rol_sin_mrp_cuando_lista_entonces_403(self):
        self._como("operario")
        self.assertEqual(self.client.get(reverse("requerimiento-material-list")).status_code, status.HTTP_403_FORBIDDEN)

    def test_sugerencia_dado_admin_cuando_edita_o_borra_entonces_405_o_404_y_se_conserva(self):
        # Las sugerencias las genera el motor; son informativas y no se editan a mano.
        sugerencia = OrdenCompraSugerida.objects.filter(sede=self.sede).first()
        self._como("admin_sistemas")
        url = f"/api/inventory/sugerencias-compra/{sugerencia.id}/"
        self.assertIn(self.client.patch(url, {"cantidad_sugerida": "1"}, format="json").status_code, (404, 405))
        self.assertIn(self.client.delete(url).status_code, (404, 405))
        self.assertTrue(OrdenCompraSugerida.objects.filter(pk=sugerencia.pk).exists())

    def test_ultima_ejecucion_dado_bodeguero_cuando_consulta_entonces_la_de_su_sede(self):
        self._como("bodeguero")
        (ultima,) = self.client.get(ULTIMA).data
        self.assertEqual(ultima["sede"], self.sede.id)
        self.assertEqual(ultima["estado"], "completada")

    def test_ultima_ejecucion_dado_ejecutivo_cuando_consulta_entonces_una_por_sede(self):
        MRPEngine.ejecutar(self.sede)  # la más reciente de la sede
        self._como("ejecutivo")
        filas = self.client.get(ULTIMA).data
        self.assertEqual(sorted(f["sede"] for f in filas), sorted([self.sede.id, self.otra_sede.id]))
        ultima_sede = MRPEjecucion.objects.filter(sede=self.sede).order_by("-inicio", "-id").first()
        self.assertIn(ultima_sede.id, [f["id"] for f in filas])

    def test_necesidades_produccion_dado_bodeguero_cuando_consulta_entonces_las_de_su_sede(self):
        self.hilo.stock_minimo = Decimal("500")
        self.hilo.save()
        self._como("bodeguero")

        filas = self.client.get(NECESIDADES).data

        hilo = next(f for f in filas if f["producto_codigo"] == "HI-AZ")
        self.assertEqual(hilo["deficit"], Decimal("400.0000"))  # 500 mínimo − 100 en producción

    def test_necesidades_produccion_dado_bodeguero_con_sede_ajena_cuando_consulta_entonces_usa_la_suya(self):
        self._como("bodeguero")
        with patch("inventory.views.mrp_views.necesidades_produccion", return_value=[]) as calcular:
            self.client.get(NECESIDADES, {"sede": self.otra_sede.id})
        calcular.assert_called_once_with(self.sede.id)
