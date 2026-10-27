"""
Historial de mantenimiento y paros de máquina del Jefe de Área
(`GET /api/paros-maquina/historial/` y `POST /api/paros-maquina/imprimir-historial/`).

Responde «qué mantenimientos hubo» y «qué días se detuvo cada máquina»: resumen por máquina y
detalle paro por paro, en un rango de fechas, con el mismo aislamiento por área y sede que el
resto del módulo de máquinas.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): paro cerrado / en curso; dentro del rango / fuera / a caballo.
- Análisis de valor límite (BVA): paro que termina el primer día del rango; rango de un solo día;
  rango invertido; rango mayor que el máximo permitido.
- Tabla de decisión: filtros máquina × categoría × planificado.
"""

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestion.models import Maquina, ParoMaquina
from gestion.tests.factories import AreaFactory, CustomUserFactory, MaquinaFactory, ParoMaquinaFactory, SedeFactory

HISTORIAL = "/api/paros-maquina/historial/"
IMPRIMIR = "/api/paros-maquina/imprimir-historial/"


class HistorialMantenimientoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sede = SedeFactory()
        cls.area = AreaFactory(sede=cls.sede)
        cls.otra_area = AreaFactory(sede=cls.sede)

        cls.jefe = CustomUserFactory(sede=cls.sede, area=cls.area)
        cls.jefe.groups.create(name="jefe_area")

        cls.tejedora = MaquinaFactory(nombre="Tejedora 1", area=cls.area)
        cls.tintorera = MaquinaFactory(nombre="Tintorera 2", area=cls.area)
        cls.ajena = MaquinaFactory(nombre="Máquina de otra área", area=cls.otra_area)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.jefe)
        self.hoy = timezone.now()

    def _paro(self, maquina, dias_atras, horas, **kwargs):
        inicio = self.hoy - timedelta(days=dias_atras)
        fin = None if horas is None else inicio + timedelta(hours=horas)
        return ParoMaquinaFactory(maquina=maquina, inicio=inicio, fin=fin, **kwargs)

    # --- resumen y totales ---------------------------------------------------

    def test_historial_dado_paros_de_dos_maquinas_cuando_consulta_entonces_resume_por_maquina(self):
        self._paro(self.tejedora, 5, 12, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)
        self._paro(self.tejedora, 3, 1.5, categoria="AVERIA")
        self._paro(self.tintorera, 2, 3, categoria="SETUP")

        respuesta = self.client.get(HISTORIAL)

        self.assertEqual(respuesta.status_code, 200)
        resumen = {fila["maquina_nombre"]: fila for fila in respuesta.data["resumen"]}
        self.assertEqual(resumen["Tejedora 1"]["paros"], 2)
        self.assertAlmostEqual(resumen["Tejedora 1"]["horas_total"], 13.5, places=2)
        self.assertAlmostEqual(resumen["Tejedora 1"]["horas_planificadas"], 12.0, places=2)
        self.assertIsNotNone(resumen["Tejedora 1"]["ultimo_mantenimiento"])
        self.assertEqual(resumen["Tintorera 2"]["paros"], 1)
        self.assertIsNone(resumen["Tintorera 2"]["ultimo_mantenimiento"])
        self.assertEqual(respuesta.data["totales"]["paros"], 3)
        self.assertAlmostEqual(respuesta.data["totales"]["horas_total"], 16.5, places=2)

    def test_historial_dado_paro_en_curso_cuando_consulta_entonces_cuenta_horas_hasta_ahora(self):
        self._paro(self.tejedora, 1, None, categoria="AVERIA")

        respuesta = self.client.get(HISTORIAL)

        fila = respuesta.data["resumen"][0]
        self.assertEqual(fila["paros_en_curso"], 1)
        self.assertGreater(fila["horas_total"], 23)
        detalle = respuesta.data["detalle"]["results"][0]
        self.assertTrue(detalle["en_curso"])
        self.assertIsNone(detalle["fin"])

    def test_historial_dado_paro_anterior_al_rango_y_aun_abierto_cuando_consulta_entonces_aparece(self):
        self._paro(self.tejedora, 60, None, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)

        respuesta = self.client.get(HISTORIAL)

        self.assertEqual(respuesta.data["totales"]["paros"], 1)
        # Solo las horas dentro del rango consultado, no las 60 días completas.
        self.assertLess(respuesta.data["totales"]["horas_total"], 31 * 24)

    def test_historial_dado_paro_fuera_del_rango_cuando_consulta_entonces_no_aparece(self):
        self._paro(self.tejedora, 90, 2, categoria="AVERIA")

        respuesta = self.client.get(HISTORIAL)

        self.assertEqual(respuesta.data["totales"]["paros"], 0)
        self.assertEqual(respuesta.data["resumen"], [])

    def test_historial_dado_rango_explicito_cuando_consulta_entonces_lo_respeta(self):
        self._paro(self.tejedora, 40, 2, categoria="AVERIA")
        desde = (self.hoy - timedelta(days=45)).date().isoformat()
        hasta = (self.hoy - timedelta(days=35)).date().isoformat()

        respuesta = self.client.get(HISTORIAL, {"fecha_desde": desde, "fecha_hasta": hasta})

        self.assertEqual(respuesta.data["rango"]["fecha_desde"], desde)
        self.assertEqual(respuesta.data["totales"]["paros"], 1)

    # --- filtros -------------------------------------------------------------

    def test_historial_dado_filtro_de_maquina_cuando_consulta_entonces_solo_esa_maquina(self):
        self._paro(self.tejedora, 2, 1, categoria="AVERIA")
        self._paro(self.tintorera, 2, 1, categoria="AVERIA")

        respuesta = self.client.get(HISTORIAL, {"maquina": self.tintorera.id})

        self.assertEqual(len(respuesta.data["resumen"]), 1)
        self.assertEqual(respuesta.data["resumen"][0]["maquina_id"], self.tintorera.id)

    def test_historial_dado_filtro_de_categoria_cuando_consulta_entonces_solo_esa_categoria(self):
        self._paro(self.tejedora, 2, 1, categoria="AVERIA")
        self._paro(self.tejedora, 2, 4, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)

        respuesta = self.client.get(HISTORIAL, {"categoria": "MANTENIMIENTO_PLANIFICADO"})

        self.assertEqual(respuesta.data["totales"]["paros"], 1)
        self.assertAlmostEqual(respuesta.data["totales"]["horas_total"], 4.0, places=2)

    def test_historial_dado_filtro_planificado_cuando_consulta_entonces_separa_planificados(self):
        self._paro(self.tejedora, 2, 1, categoria="AVERIA", planificado=False)
        self._paro(self.tejedora, 2, 4, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)

        planificados = self.client.get(HISTORIAL, {"planificado": "true"})
        no_planificados = self.client.get(HISTORIAL, {"planificado": "false"})

        self.assertEqual(planificados.data["totales"]["paros"], 1)
        self.assertEqual(no_planificados.data["totales"]["paros"], 1)

    def test_historial_dado_categoria_inexistente_cuando_consulta_entonces_400(self):
        respuesta = self.client.get(HISTORIAL, {"categoria": "NO_EXISTE"})

        self.assertEqual(respuesta.status_code, 400)

    def test_historial_dado_fecha_invalida_cuando_consulta_entonces_400(self):
        respuesta = self.client.get(HISTORIAL, {"fecha_desde": "2026-02-30"})

        self.assertEqual(respuesta.status_code, 400)

    def test_historial_dado_rango_invertido_cuando_consulta_entonces_400(self):
        respuesta = self.client.get(HISTORIAL, {"fecha_desde": "2026-10-10", "fecha_hasta": "2026-10-01"})

        self.assertEqual(respuesta.status_code, 400)

    def test_historial_dado_rango_mayor_al_maximo_cuando_consulta_entonces_400(self):
        respuesta = self.client.get(HISTORIAL, {"fecha_desde": "2024-01-01", "fecha_hasta": "2026-10-01"})

        self.assertEqual(respuesta.status_code, 400)

    def test_historial_dado_maquina_no_numerica_cuando_consulta_entonces_400(self):
        respuesta = self.client.get(HISTORIAL, {"maquina": "abc"})

        self.assertEqual(respuesta.status_code, 400)

    # --- aislamiento ---------------------------------------------------------

    def test_historial_dado_maquina_de_otra_area_cuando_consulta_entonces_no_aparece(self):
        self._paro(self.ajena, 2, 5, categoria="AVERIA")

        respuesta = self.client.get(HISTORIAL)

        self.assertEqual(respuesta.data["totales"]["paros"], 0)

    def test_historial_dado_rol_vendedor_cuando_consulta_entonces_403(self):
        vendedor = CustomUserFactory(sede=self.sede)
        vendedor.groups.create(name="vendedor")
        cliente = APIClient()
        cliente.force_authenticate(user=vendedor)

        respuesta = cliente.get(HISTORIAL)

        self.assertEqual(respuesta.status_code, 403)

    def test_historial_dado_sin_autenticar_cuando_consulta_entonces_401(self):
        respuesta = APIClient().get(HISTORIAL)

        self.assertEqual(respuesta.status_code, 401)

    # --- paginación y rendimiento -------------------------------------------

    def test_historial_dado_muchos_paros_cuando_consulta_entonces_pagina_el_detalle(self):
        for dia in range(1, 13):
            self._paro(self.tejedora, dia, 1, categoria="AVERIA")

        respuesta = self.client.get(HISTORIAL, {"page_size": 5})

        self.assertEqual(respuesta.data["detalle"]["count"], 12)
        self.assertEqual(len(respuesta.data["detalle"]["results"]), 5)
        self.assertIsNotNone(respuesta.data["detalle"]["next"])
        self.assertEqual(respuesta.data["totales"]["paros"], 12)

    def test_historial_dado_mas_paros_cuando_consulta_entonces_las_consultas_no_crecen(self):
        for dia in range(1, 4):
            self._paro(self.tejedora, dia, 1, categoria="AVERIA")
        with self.assertNumQueries(6):
            self.client.get(HISTORIAL)

        for dia in range(4, 16):
            self._paro(self.tintorera, dia, 1, categoria="AVERIA")
        with self.assertNumQueries(6):
            self.client.get(HISTORIAL)

    # --- impresión -----------------------------------------------------------

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_rango_con_paros_cuando_post_entonces_devuelve_pdf(self, mock_pdf):
        mock_pdf.return_value = b"%PDF-1.4 historial"
        self._paro(self.tejedora, 2, 4, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)

        respuesta = self.client.post(IMPRIMIR, {}, format="json")

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertIn("historial_mantenimiento", respuesta["Content-Disposition"])
        datos = mock_pdf.call_args[0][0]
        self.assertEqual(len(datos["detalle"]), 1)
        self.assertEqual(datos["totales"]["paros"], 1)
        self.assertEqual(datos["sede_nombre"], self.sede.nombre)
        self.assertEqual(datos["impreso_por"], self.jefe.username)

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_payload_cuando_se_envia_entonces_es_json_serializable(self, mock_pdf):
        """Defecto 59: `requests.post(json=...)` usa el json de la biblioteca estándar, que no
        serializa `datetime`. El PDF respondía 503 con el servicio de impresión sano."""
        mock_pdf.return_value = b"%PDF-1.4"
        self._paro(self.tejedora, 2, 4, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)
        self._paro(self.tejedora, 1, None, categoria="AVERIA")

        self.client.post(IMPRIMIR, {}, format="json")

        datos = mock_pdf.call_args[0][0]
        json.dumps(datos)  # falla si queda un datetime, un Decimal o un objeto del ORM
        self.assertIsInstance(datos["resumen"][0]["ultimo_mantenimiento"], str)

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_fechas_cuando_arma_el_pdf_entonces_van_legibles_en_hora_local(self, mock_pdf):
        """Defecto 60: el PDF imprimía `2026-10-14T14:54:04.058488+00:00`. Un documento para
        planta lleva la fecha en dd/mm/aaaa y la hora local, sin microsegundos."""
        mock_pdf.return_value = b"%PDF-1.4"
        self._paro(self.tejedora, 2, 4, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)
        self._paro(self.tintorera, 1, None, categoria="AVERIA")

        self.client.post(IMPRIMIR, {}, format="json")

        datos = mock_pdf.call_args[0][0]
        patron_fecha_hora = r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}$"
        for fila in datos["detalle"]:
            with self.subTest(paro=fila["id"]):
                self.assertRegex(fila["inicio"], patron_fecha_hora)
                if fila["en_curso"]:
                    self.assertEqual(fila["fin"], "")
                else:
                    self.assertRegex(fila["fin"], patron_fecha_hora)
        resumen = next(f for f in datos["resumen"] if f["ultimo_mantenimiento"])
        self.assertRegex(resumen["ultimo_mantenimiento"], r"^\d{2}/\d{2}/\d{4}$")

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_paro_a_las_18_23_utc_cuando_arma_el_pdf_entonces_13_23_hora_de_la_planta(self, mock_pdf):
        """El defecto 60 dejó el formato legible pero en UTC (TIME_ZONE): el patrón dd/mm/aaaa
        HH:MM también lo cumple una hora en UTC, así que se fija la hora exacta."""
        from zoneinfo import ZoneInfo

        mock_pdf.return_value = b"%PDF-1.4"
        inicio = (self.hoy - timedelta(days=2)).replace(hour=18, minute=23, second=0, microsecond=0)
        ParoMaquinaFactory(maquina=self.tejedora, inicio=inicio, fin=inicio + timedelta(hours=1), categoria="AVERIA")

        self.client.post(IMPRIMIR, {}, format="json")

        esperado = inicio.astimezone(ZoneInfo("America/Guayaquil")).strftime("%d/%m/%Y %H:%M")
        self.assertTrue(esperado.endswith("13:23"))
        self.assertEqual(mock_pdf.call_args[0][0]["detalle"][0]["inicio"], esperado)

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_servicio_caido_cuando_post_entonces_503(self, mock_pdf):
        mock_pdf.return_value = None

        respuesta = self.client.post(IMPRIMIR, {}, format="json")

        self.assertEqual(respuesta.status_code, 503)

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_filtros_en_el_body_cuando_post_entonces_los_aplica(self, mock_pdf):
        mock_pdf.return_value = b"%PDF-1.4"
        self._paro(self.tejedora, 2, 1, categoria="AVERIA")
        self._paro(self.tejedora, 2, 4, categoria="MANTENIMIENTO_PLANIFICADO", planificado=True)

        respuesta = self.client.post(IMPRIMIR, {"categoria": "AVERIA"}, format="json")

        self.assertEqual(respuesta.status_code, 200)
        datos = mock_pdf.call_args[0][0]
        self.assertEqual(len(datos["detalle"]), 1)
        self.assertEqual(datos["filtros"]["categoria"], "Avería / Falla de Equipo")

    @patch("gestion.views.production_maquina_views.PrintingService.generate_historial_mantenimiento_pdf")
    def test_imprimir_dado_sin_paginar_cuando_post_entonces_incluye_todo_el_rango(self, mock_pdf):
        mock_pdf.return_value = b"%PDF-1.4"
        for dia in range(1, 13):
            self._paro(self.tejedora, dia, 1, categoria="AVERIA")

        self.client.post(IMPRIMIR, {}, format="json")

        self.assertEqual(len(mock_pdf.call_args[0][0]["detalle"]), 12)

    def test_imprimir_dado_rol_vendedor_cuando_post_entonces_403(self):
        vendedor = CustomUserFactory(sede=self.sede)
        vendedor.groups.create(name="vendedor")
        cliente = APIClient()
        cliente.force_authenticate(user=vendedor)

        respuesta = cliente.post(IMPRIMIR, {}, format="json")

        self.assertEqual(respuesta.status_code, 403)


class ParoAutomaticoPorPatchDeEstadoTest(TestCase):
    """El PATCH del estado de la máquina abre y cierra el paro (decisión del usuario, 14-oct)."""

    @classmethod
    def setUpTestData(cls):
        cls.sede = SedeFactory()
        cls.area = AreaFactory(sede=cls.sede)
        cls.jefe = CustomUserFactory(sede=cls.sede, area=cls.area)
        cls.jefe.groups.create(name="jefe_area")

    def setUp(self):
        self.maquina = MaquinaFactory(area=self.area, estado="operativa")
        self.client = APIClient()
        self.client.force_authenticate(user=self.jefe)
        self.url = f"/api/maquinas/{self.maquina.id}/"

    def test_maquina_dado_patch_a_mantenimiento_cuando_guarda_entonces_abre_paro_automatico(self):
        respuesta = self.client.patch(self.url, {"estado": "mantenimiento"}, format="json")

        self.assertEqual(respuesta.status_code, 200)
        paro = ParoMaquina.objects.get(maquina=self.maquina, origen="estado")
        self.assertIsNone(paro.fin)
        self.assertTrue(paro.planificado)
        self.assertEqual(paro.usuario, self.jefe)

    def test_maquina_dado_patch_de_vuelta_a_operativa_cuando_guarda_entonces_cierra_el_paro(self):
        self.client.patch(self.url, {"estado": "mantenimiento"}, format="json")

        self.client.patch(self.url, {"estado": "operativa"}, format="json")

        paro = ParoMaquina.objects.get(maquina=self.maquina, origen="estado")
        self.assertIsNotNone(paro.fin)

    def test_maquina_dado_patch_sin_cambiar_estado_cuando_guarda_entonces_no_crea_paro(self):
        self.client.patch(self.url, {"nombre": "Tejedora renombrada"}, format="json")

        self.assertEqual(ParoMaquina.objects.filter(maquina=self.maquina).count(), 0)
        self.assertEqual(Maquina.objects.get(id=self.maquina.id).nombre, "Tejedora renombrada")

    def test_paro_automatico_dado_maquina_en_mantenimiento_cuando_se_lista_el_historial_entonces_aparece(self):
        self.client.patch(self.url, {"estado": "mantenimiento"}, format="json")

        respuesta = self.client.get(HISTORIAL)

        self.assertEqual(respuesta.data["totales"]["paros"], 1)
        fila = respuesta.data["detalle"]["results"][0]
        self.assertEqual(fila["origen"], "estado")
        self.assertTrue(fila["en_curso"])


class HistorialRangoPorOmisionTest(TestCase):
    """BVA del rango por omisión: 30 días hacia atrás, incluyendo hoy."""

    @classmethod
    def setUpTestData(cls):
        cls.sede = SedeFactory()
        cls.area = AreaFactory(sede=cls.sede)
        cls.jefe = CustomUserFactory(sede=cls.sede, area=cls.area)
        cls.jefe.groups.create(name="jefe_area")
        cls.maquina = MaquinaFactory(area=cls.area)

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.jefe)

    def test_rango_dado_sin_parametros_cuando_consulta_entonces_son_los_ultimos_30_dias(self):
        respuesta = self.client.get(HISTORIAL)

        hoy = timezone.localdate()
        self.assertEqual(respuesta.data["rango"]["fecha_hasta"], hoy.isoformat())
        self.assertEqual(respuesta.data["rango"]["fecha_desde"], (hoy - timedelta(days=30)).isoformat())

    def test_historial_dado_paro_que_termina_el_primer_dia_del_rango_cuando_consulta_entonces_aparece(self):
        desde = timezone.localdate() - timedelta(days=5)
        inicio = datetime.combine(desde - timedelta(days=1), datetime.min.time(), tzinfo=UTC) + timedelta(hours=22)
        ParoMaquinaFactory(maquina=self.maquina, inicio=inicio, fin=inicio + timedelta(hours=4), categoria="AVERIA")

        respuesta = self.client.get(HISTORIAL, {"fecha_desde": desde.isoformat()})

        self.assertEqual(respuesta.data["totales"]["paros"], 1)
