"""
Pruebas unitarias para vistas de generación de PDFs de producción en internal_api:
  - ReporteAvancePdfView
  - BalanceMasasPdfView
  - Permiso IsInternalServiceOrUser (ServicePrincipal y Usuario Jefe de Planta/Área)
"""
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
import httpx

from gestion.models import Sede, Bodega
from internal_api.authentication import JWTServiceAuthentication
from internal_api.views.pdf_produccion_views import (
    _build_reporte_avance_payload, _build_balance_masas_payload,
)
from gestion.tests.factories import (
    AreaFactory, MaquinaFactory, OrdenProduccionFactory, ProductoFactory,
    LoteProduccionFactory,
)

User = get_user_model()


class TestPdfProduccionViews(APITestCase):

    def setUp(self):
        self.sede = Sede.objects.create(nombre="Sede Central")
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)

        self.group_jefe_planta, _ = Group.objects.get_or_create(name="jefe_planta")
        self.group_operario, _ = Group.objects.get_or_create(name="operario")

        self.user_jefe = User.objects.create_user(
            username="jefe_planta_user",
            email="jefe@texcore.com",
            password="Password123!",
            sede=self.sede,
        )
        self.user_jefe.groups.add(self.group_jefe_planta)

        self.user_sin_permiso = User.objects.create_user(
            username="operario_user",
            email="operario@texcore.com",
            password="Password123!",
            sede=self.sede,
        )
        self.user_sin_permiso.groups.add(self.group_operario)

        self.service_token = JWTServiceAuthentication.generate_token(
            service_name="scanning-service",
            scopes=["reports:read"],
        )

        self.url_avance = reverse("internal_api:reports_produccion_reporte_avance")
        self.url_balance = reverse("internal_api:reports_produccion_reporte_balance")

    def test_reporte_avance_usuario_sin_permiso_retorna_403(self):
        self.client.force_authenticate(user=self.user_sin_permiso)
        response = self.client.post(self.url_avance, {"empresa_nombre": "TexCore"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reporte_balance_servicio_sin_sede_id_retorna_400(self):
        # Un llamador de SERVICIO (ServicePrincipal, sin sede) que no envía
        # sede_id no tiene sede derivable → 400. (Un usuario humano con sede la
        # deriva automáticamente; ver test_reporte_balance_usuario_jefe_deriva_su_sede.)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.service_token}")
        response = self.client.post(self.url_balance, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("httpx.Client.post")
    def test_reporte_balance_usuario_jefe_deriva_su_sede(self, mock_httpx_post):
        # El jefe de planta con sede NO necesita enviar sede_id: se deriva de su
        # identidad autenticada (el frontend ya no la envía, evitando fugas de
        # sede ajena). Con la sede derivada, la vista procede al printing_service.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 balance derivado"
        mock_httpx_post.return_value = mock_response

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(self.url_balance, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("httpx.Client.post")
    def test_reporte_avance_usuario_jefe_exito(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 test avance content"
        mock_httpx_post.return_value = mock_response

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(
            self.url_avance,
            {"empresa_nombre": "TexCore Industrial", "sede_id": self.sede.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=\"reporte_avance_", response["Content-Disposition"])

    @patch("httpx.Client.post")
    def test_reporte_balance_service_token_exito(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4 test balance content"
        mock_httpx_post.return_value = mock_response

        response = self.client.post(
            self.url_balance,
            {"sede_id": self.sede.id, "mes_label": "Agosto 2026", "empresa_nombre": "TexCore"},
            HTTP_AUTHORIZATION=f"Bearer {self.service_token}",
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    @patch("httpx.Client.post")
    def test_reporte_avance_printing_service_error_http_502(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error in printing service"
        mock_httpx_post.side_effect = httpx.HTTPStatusError(
            "Server error", request=MagicMock(), response=mock_response
        )

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(self.url_avance, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch("httpx.Client.post")
    def test_reporte_balance_printing_service_conexion_fallida_503(self, mock_httpx_post):
        mock_httpx_post.side_effect = httpx.RequestError("Connection timeout", request=MagicMock())

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(self.url_balance, {"sede_id": self.sede.id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    # -------------------------------------------------------------------
    # Crítico: _get_printing_url() defaulteaba a 'printing_service', un
    # hostname que no existe en la red de docker-compose (el servicio se
    # llama 'printing'). Ni docker-compose.yml ni .prod.yml setean
    # PRINTING_SERVICE_URL para el backend, así que SIEMPRE se usaba ese
    # default equivocado -> conexión fallida real, oculto porque los tests
    # de arriba mockean httpx.Client.post entero y nunca inspeccionan la URL.
    # -------------------------------------------------------------------

    @patch("httpx.Client.post")
    def test_reporte_avance_dado_setting_no_definido_cuando_llama_entonces_usa_hostname_printing(
        self, mock_httpx_post
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4"
        mock_httpx_post.return_value = mock_response

        self.client.force_authenticate(user=self.user_jefe)
        self.client.post(self.url_avance, {"sede_id": self.sede.id}, format="json")

        called_url = mock_httpx_post.call_args[0][0]
        self.assertEqual(called_url, "http://printing:8001/pdf/reporte-avance")

    @override_settings(PRINTING_SERVICE_URL="http://staging-printing:9001")
    @patch("httpx.Client.post")
    def test_reporte_balance_dado_setting_override_cuando_llama_entonces_usa_ese_dominio(
        self, mock_httpx_post
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4"
        mock_httpx_post.return_value = mock_response

        self.client.force_authenticate(user=self.user_jefe)
        self.client.post(self.url_balance, {"sede_id": self.sede.id}, format="json")

        called_url = mock_httpx_post.call_args[0][0]
        self.assertEqual(called_url, "http://staging-printing:9001/pdf/reporte-balance")

    # -------------------------------------------------------------------
    # _resolve_sede_scope: aislamiento por sede (OWASP A01) — rama global
    # (admin/ejecutivo/superuser puede pedir cualquier sede o ninguna) y
    # rama de sede ajena (usuario no-global forzado a la suya -> 403).
    # -------------------------------------------------------------------

    @patch("httpx.Client.post")
    def test_reporte_avance_dado_usuario_global_con_sede_ajena_cuando_post_entonces_200(self, mock_httpx_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4"
        mock_httpx_post.return_value = mock_response

        otra_sede = Sede.objects.create(nombre="Sede Norte")
        group_ejecutivo, _ = Group.objects.get_or_create(name="ejecutivo")
        ejecutivo = User.objects.create_user(
            username="ejecutivo_user", email="ejecutivo@texcore.com",
            password="Password123!", sede=self.sede,
        )
        ejecutivo.groups.add(group_ejecutivo)

        self.client.force_authenticate(user=ejecutivo)
        response = self.client.post(
            self.url_avance, {"sede_id": otra_sede.id}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_reporte_avance_dado_usuario_no_global_solicita_sede_ajena_cuando_post_entonces_403(self):
        otra_sede = Sede.objects.create(nombre="Sede Sur")
        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(
            self.url_avance, {"sede_id": otra_sede.id}, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("otra sede", response.data["detail"])

    def test_reporte_balance_dado_usuario_sin_sede_asignada_cuando_post_entonces_403(self):
        group_jefe_area, _ = Group.objects.get_or_create(name="jefe_area")
        jefe_sin_sede = User.objects.create_user(
            username="jefe_sin_sede", email="jefe_sin_sede@texcore.com",
            password="Password123!", sede=None,
        )
        jefe_sin_sede.groups.add(group_jefe_area)

        self.client.force_authenticate(user=jefe_sin_sede)
        response = self.client.post(self.url_balance, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------
    # IsInternalServiceOrUser: ServicePrincipal sin el scope requerido.
    # -------------------------------------------------------------------

    def test_reporte_avance_dado_service_principal_sin_scope_reports_read_cuando_post_entonces_403(self):
        token_sin_scope = JWTServiceAuthentication.generate_token(
            service_name="otro-service", scopes=["otro:scope"],
        )
        response = self.client.post(
            self.url_avance, {}, HTTP_AUTHORIZATION=f"Bearer {token_sin_scope}", format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # -------------------------------------------------------------------
    # ReporteAvancePdfView: ramas de filtro (fecha_desde/hasta, sede_id,
    # maquina_id, operario_id) y el mapeo real de _build_reporte_avance_payload
    # con datos (el payload no está vacío).
    # -------------------------------------------------------------------

    @patch("httpx.Client.post")
    def test_reporte_avance_dado_filtros_completos_y_lotes_cuando_post_entonces_incluye_detalle_en_payload(
        self, mock_httpx_post,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"%PDF-1.4"
        mock_httpx_post.return_value = mock_response

        area = AreaFactory(sede=self.sede)
        maquina = MaquinaFactory(area=area)
        producto = ProductoFactory(sede=self.sede)
        orden = OrdenProduccionFactory(sede=self.sede, area=area, producto_salida=producto)
        LoteProduccionFactory(
            orden_produccion=orden, maquina=maquina, operario=self.user_jefe,
            peso_neto_producido=90, hora_inicio="2026-01-01T08:00:00Z",
            hora_final="2026-01-01T16:00:00Z",
        )

        self.client.force_authenticate(user=self.user_jefe)
        response = self.client.post(
            self.url_avance,
            {
                "fecha_desde": "2026-01-01", "fecha_hasta": "2026-01-01",
                "sede_id": self.sede.id, "maquina_id": maquina.id,
                "operario_id": self.user_jefe.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload_enviado = mock_httpx_post.call_args.kwargs["json"]
        self.assertEqual(len(payload_enviado["detalles"]), 1)
        self.assertEqual(payload_enviado["detalles"][0]["kilos"], 90.0)
        self.assertIsNotNone(payload_enviado["maquina_filtro"])
        self.assertIsNotNone(payload_enviado["operario_filtro"])


class BuildReporteAvancePayloadTestCase(APITestCase):
    """
    Función pura (sin ORM en su firma): mapea registros ya materializados
    (dicts) al schema del printing_service. Cero mocks necesarios.
    """

    def test_build_payload_dado_peso_requerido_positivo_cuando_mapea_entonces_calcula_porcentaje(self):
        registros = [{
            "op_codigo": "OP-1", "producto_descripcion": "Tela Azul",
            "codigo_lote": "L1", "maquina_nombre": "M1", "operario_nombre": "op1",
            "peso_neto_producido": 50, "orden_peso_requerido": 100, "op_estado": "en_proceso",
        }]
        payload = _build_reporte_avance_payload(
            registros, "TexCore", "Sede Central", "2026-01-01", "2026-01-31", None, None,
        )
        self.assertEqual(payload["detalles"][0]["porcentaje_avance"], 50.0)
        self.assertEqual(payload["detalles"][0]["kilos"], 50.0)

    def test_build_payload_dado_peso_requerido_cero_cuando_mapea_entonces_porcentaje_cero_sin_dividir(self):
        # BVA: borde peso_requerido == 0 -> evita ZeroDivisionError.
        registros = [{
            "op_codigo": "OP-2", "producto_descripcion": None,
            "codigo_lote": None, "maquina_nombre": None, "operario_nombre": None,
            "peso_neto_producido": 10, "orden_peso_requerido": 0, "op_estado": None,
        }]
        payload = _build_reporte_avance_payload(registros, "TexCore", "Sede", None, None, None, None)
        self.assertEqual(payload["detalles"][0]["porcentaje_avance"], 0.0)
        self.assertEqual(payload["detalles"][0]["producto"], "—")

    def test_build_payload_dado_sin_registros_cuando_mapea_entonces_detalles_vacio(self):
        payload = _build_reporte_avance_payload([], "TexCore", "Sede", None, None, None, None)
        self.assertEqual(payload["detalles"], [])


class BuildBalanceMasasPayloadTestCase(APITestCase):
    """
    Función pura: reconcilia stock actual + movimientos del mes por producto.
    Cubre la clasificación producción/egresos y el flag is_negativo.
    """

    def test_build_payload_dado_movimiento_de_produccion_cuando_mapea_entonces_suma_a_produccion(self):
        stock = [{"producto_id": 1, "cantidad": 100, "producto_codigo": "P1", "producto_descripcion": "Prod 1"}]
        movimientos = [{"producto_id": 1, "cantidad": 30, "tipo_movimiento": "produccion"}]
        payload = _build_balance_masas_payload(stock, movimientos, "TexCore", "Sede", "Enero 2026")
        detalle = payload["detalles"][0]
        self.assertEqual(detalle["produccion"], 30.0)
        self.assertEqual(detalle["egresos"], 0.0)
        self.assertFalse(detalle["is_negativo"])

    def test_build_payload_dado_movimiento_mayuscula_produccion_cuando_mapea_entonces_suma_a_produccion(self):
        # EP: el tipo llega en mayúsculas desde algunas fuentes legadas.
        stock = [{"producto_id": 1, "cantidad": 50, "producto_codigo": "P1", "producto_descripcion": "Prod 1"}]
        movimientos = [{"producto_id": 1, "cantidad": 20, "tipo_movimiento": "ENTRADA"}]
        payload = _build_balance_masas_payload(stock, movimientos, "TexCore", "Sede", "Enero 2026")
        self.assertEqual(payload["detalles"][0]["produccion"], 20.0)

    def test_build_payload_dado_movimiento_de_egreso_cuando_mapea_entonces_suma_a_egresos(self):
        stock = [{"producto_id": 1, "cantidad": 100, "producto_codigo": "P1", "producto_descripcion": "Prod 1"}]
        movimientos = [{"producto_id": 1, "cantidad": 15, "tipo_movimiento": "salida"}]
        payload = _build_balance_masas_payload(stock, movimientos, "TexCore", "Sede", "Enero 2026")
        detalle = payload["detalles"][0]
        self.assertEqual(detalle["egresos"], 15.0)
        self.assertEqual(detalle["produccion"], 0.0)

    def test_build_payload_dado_stock_negativo_cuando_mapea_entonces_flag_is_negativo(self):
        stock = [{"producto_id": 1, "cantidad": -5, "producto_codigo": "P1", "producto_descripcion": "Prod 1"}]
        payload = _build_balance_masas_payload(stock, [], "TexCore", "Sede", "Enero 2026")
        self.assertTrue(payload["detalles"][0]["is_negativo"])

    def test_build_payload_dado_sin_movimientos_cuando_mapea_entonces_produccion_y_egresos_cero(self):
        stock = [{"producto_id": 1, "cantidad": 40, "producto_codigo": "P1", "producto_descripcion": "Prod 1"}]
        payload = _build_balance_masas_payload(stock, [], "TexCore", "Sede", "Enero 2026")
        detalle = payload["detalles"][0]
        self.assertEqual(detalle["produccion"], 0.0)
        self.assertEqual(detalle["egresos"], 0.0)
        self.assertEqual(detalle["inventario_inicial"], 40.0)
