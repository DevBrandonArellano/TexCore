"""
Tests de endpoints e integración para printing_service.
Cubre: config, main, health.py, pdf.py, zpl.py, output_strategy.py.
"""
import sys
from unittest.mock import MagicMock, patch

# Mock weasyprint ANTES de cualquier import de src.
# PdfOutputStrategy importa `from weasyprint import HTML` de forma tardía (dentro del método render).
# Al registrar weasyprint como mock en sys.modules, ese import se resuelve sin instalar la librería.
_mock_weasyprint = MagicMock()
_mock_weasyprint.HTML.return_value.write_pdf.return_value = b"%PDF-1.4"
sys.modules.setdefault('weasyprint', _mock_weasyprint)

from fastapi import Response  # noqa: E402
from fastapi.responses import PlainTextResponse, StreamingResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.main import app  # noqa: E402
from src.routers.pdf import get_pdf_strategy  # noqa: E402
from src.routers.zpl import get_zpl_strategy  # noqa: E402
from src.database.repository import get_audit_repo  # noqa: E402
from src.services.output_strategy import ZplOutputStrategy, PdfOutputStrategy  # noqa: E402

client = TestClient(app)


class TestHealthEndpoint:

    def test_health_ok_cuando_templates_existen_entonces_retorna_200(self):
        """EP: todos los templates presentes → status ok."""
        with patch("src.routers.health.os.path.exists", return_value=True):
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_health_503_cuando_templates_ausentes_entonces_lanza_503(self):
        """EP: templates faltantes → 503 Service Unavailable con lista de ausentes."""
        with patch("src.routers.health.os.path.exists", return_value=False):
            response = client.get("/health")
        assert response.status_code == 503
        assert "Templates ausentes" in response.json()["detail"]


class TestPdfEndpoint:

    def test_nota_venta_dado_request_valido_cuando_genera_entonces_retorna_200(self):
        """EP: datos válidos de nota de venta → PDF generado (strategy mockeado)."""
        mock_strategy = MagicMock()
        mock_strategy.render.return_value = Response(
            content=b"%PDF-1.4",
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=nota_001.pdf"},
        )
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {
                "id": 1,
                "guia_remision": "GR-001",
                "fecha_pedido": "2026-01-15T10:00:00Z",
                "cliente_nombre": "Cliente Test",
                "detalles": [
                    {
                        "producto_descripcion": "Hilo Nylon 40/1",
                        "cantidad": 10.0,
                        "piezas": 5,
                        "peso": 50.0,
                        "precio_unitario": 12.50,
                        "incluye_iva": False,
                    }
                ],
                "valor_retencion": 0.0,
            }
            response = client.post("/pdf/nota-venta", json=payload)
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_nota_venta_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        """EP: fallo interno del strategy → 500 Internal Server Error."""
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Fallo al generar PDF")
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {
                "id": 2,
                "fecha_pedido": "2026-01-15T10:00:00Z",
                "detalles": [],
                "valor_retencion": 0.0,
            }
            response = client.post("/pdf/nota-venta", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()

    def test_etiqueta_pdf_dado_request_valido_cuando_genera_entonces_retorna_200(self):
        """F5: fallback universal — etiqueta en PDF para impresoras no-Zebra."""
        mock_strategy = MagicMock()
        mock_strategy.render.return_value = Response(
            content=b"%PDF-1.4", media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=L-001.pdf"},
        )
        mock_audit = MagicMock()
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        app.dependency_overrides[get_audit_repo] = lambda: mock_audit
        try:
            payload = {
                "producto_desc": "Hilo Nylon 40/1",
                "lote_codigo": "L-2026-003",
                "peso_neto": 45.5,
                "qr_data": "https://texcore.ec/lote/L-2026-003",
            }
            response = client.post("/pdf/etiqueta", json=payload)
            assert response.status_code == 200
            mock_strategy.render.assert_called_once()
            args, _ = mock_strategy.render.call_args
            assert args[0] == "etiqueta_label.html"
        finally:
            app.dependency_overrides.clear()

    def test_etiqueta_pdf_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Fallo al generar etiqueta PDF")
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {
                "producto_desc": "Hilo Nylon",
                "lote_codigo": "L-002",
                "peso_neto": 10.0,
                "qr_data": "test",
            }
            response = client.post("/pdf/etiqueta", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()


class TestPdfReporteEndpoints:
    """
    P0: /pdf/reporte-avance y /pdf/reporte-balance eran llamados por
    internal_api/views/pdf_produccion_views.py pero nunca existieron como
    rutas en printing_service (schemas y templates sí, router no) — toda
    llamada real terminaba en 404 -> 502 para el cliente.

    Estos tests NO sobreescriben get_pdf_strategy: usan el Environment real
    de Jinja2 contra los templates reales en disco. Solo WeasyPrint está
    mockeado (a nivel de módulo, arriba de este archivo) porque sus
    dependencias nativas (libpango/libcairo) no están disponibles en este
    entorno — así una variable no definida en el template sí rompe el test.
    """

    def test_reporte_avance_dado_request_valido_cuando_genera_entonces_retorna_pdf_real(self):
        payload = {
            "empresa_nombre": "TexCore Industrial",
            "sede_nombre": "Planta Quito",
            "fecha_desde": "2026-08-01",
            "fecha_hasta": "2026-08-18",
            "maquina_filtro": None,
            "operario_filtro": None,
            "generado_en": "2026-08-19T10:00:00Z",
            "detalles": [
                {
                    "orden": "OP-001",
                    "producto": "Hilo Nylon 40/1",
                    "lote": "LOT-001",
                    "maquina": "Telar 3",
                    "operario": "jperez",
                    "kilos": 120.5,
                    "porcentaje_avance": 85.3,
                    "estado": "en_proceso",
                }
            ],
        }
        response = client.post("/pdf/reporte-avance", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4"

    def test_reporte_avance_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Fallo al generar reporte avance")
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {"generado_en": "2026-08-19T10:00:00Z", "detalles": []}
            response = client.post("/pdf/reporte-avance", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()

    def test_historial_despachos_dado_request_valido_cuando_genera_entonces_retorna_pdf_real(self):
        payload = {
            "empresa_nombre": "TexCore Industrial",
            "sede_nombre": "Planta Quito",
            "fecha_desde": "2026-08-01",
            "fecha_hasta": "2026-08-25",
            "generado_en": "2026-08-25T10:00:00Z",
            "despachos": [
                {
                    "id": 2,
                    "fecha_despacho": "20/08/2026 09:15",
                    "usuario_nombre": "Despacho Demo",
                    "pedidos": "Cliente A (GR-001), Cliente B (GR-002)",
                    "total_bultos": 5,
                    "total_peso": 120.5,
                }
            ],
        }
        response = client.post("/pdf/historial-despachos", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4"

    def test_historial_despachos_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Fallo al generar historial")
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {"generado_en": "2026-08-25T10:00:00Z", "despachos": []}
            response = client.post("/pdf/historial-despachos", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()

    def test_guia_remision_dado_request_valido_cuando_genera_entonces_retorna_pdf_real(self):
        payload = {
            "numero": "001-001-000000002",
            "fecha_emision": "25/08/2026",
            "empresa_nombre": "TexCore Industrial",
            "empresa_ruc": "1790000000001",
            "punto_partida": "Planta Quito, Av. Industrial s/n",
            "motivo_traslado": "Venta",
            "fecha_inicio_transporte": "25/08/2026",
            "fecha_fin_transporte": "25/08/2026",
            "transporte_propio": False,
            "transportista_nombre": "Transportes Andinos S.A.",
            "transportista_ruc": "1790000000002",
            "placa_vehiculo": "PBX-1234",
            "destinatarios": [
                {
                    "identificacion": "1790000000003",
                    "razon_social": "Cliente Demo",
                    "direccion": "Av. Siempre Viva 123",
                    "documento_sustento": "GR-001",
                }
            ],
            "detalles": [
                {"codigo": "HN-40-1", "descripcion": "Hilo Nylon 40/1", "cantidad": 50.0, "unidad": "kg"}
            ],
        }
        response = client.post("/pdf/guia-remision", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4"

    def test_guia_remision_dado_transporte_propio_cuando_genera_entonces_omite_datos_transportista(self):
        # transportista_nombre/ruc son None -> el template no debe romper con
        # el bloque condicional {% if not transporte_propio %}
        payload = {
            "numero": "001-001-000000003",
            "fecha_emision": "25/08/2026",
            "punto_partida": "Planta Quito",
            "motivo_traslado": "Transferencia entre bodegas propias",
            "fecha_inicio_transporte": "25/08/2026",
            "fecha_fin_transporte": "25/08/2026",
            "transporte_propio": True,
            "placa_vehiculo": "PBX-5678",
            "destinatarios": [{"razon_social": "Bodega Sede Sur"}],
            "detalles": [{"descripcion": "Rollo de tela azul", "cantidad": 12.0}],
        }
        response = client.post("/pdf/guia-remision", json=payload)
        assert response.status_code == 200
        assert response.content == b"%PDF-1.4"

    def test_guia_remision_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Fallo al generar guía")
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {
                "numero": "001-001-000000004",
                "fecha_emision": "25/08/2026",
                "punto_partida": "Planta Quito",
                "motivo_traslado": "Venta",
                "fecha_inicio_transporte": "25/08/2026",
                "fecha_fin_transporte": "25/08/2026",
                "destinatarios": [],
                "detalles": [],
            }
            response = client.post("/pdf/guia-remision", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()

    def test_reporte_balance_dado_request_valido_cuando_genera_entonces_retorna_pdf_real(self):
        payload = {
            "empresa_nombre": "TexCore Industrial",
            "sede_nombre": "Planta Quito",
            "mes": "Agosto 2026",
            "generado_en": "2026-08-19T10:00:00Z",
            "detalles": [
                {
                    "codigo": "HN-40-1",
                    "descripcion": "Hilo Nylon 40/1",
                    "inventario_inicial": 500.0,
                    "produccion": 120.5,
                    "egresos": 80.0,
                    "stock_actual": 540.5,
                    "is_negativo": False,
                }
            ],
        }
        response = client.post("/pdf/reporte-balance", json=payload)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == b"%PDF-1.4"

    def test_reporte_balance_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Fallo al generar balance masas")
        app.dependency_overrides[get_pdf_strategy] = lambda: mock_strategy
        try:
            payload = {"mes": "Agosto 2026", "generado_en": "2026-08-19T10:00:00Z", "detalles": []}
            response = client.post("/pdf/reporte-balance", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()


class TestZplEndpoint:

    def test_etiqueta_dado_request_valido_cuando_genera_entonces_retorna_200(self):
        """EP: datos válidos de etiqueta → ZPL generado (strategy mockeado)."""
        mock_strategy = MagicMock()
        mock_strategy.render.return_value = PlainTextResponse("^XA^FO50,50^FDHilo Nylon^FS^XZ")
        app.dependency_overrides[get_zpl_strategy] = lambda: mock_strategy
        try:
            payload = {
                "producto_desc": "Hilo Nylon 40/1",
                "lote_codigo": "L-2026-001",
                "peso_neto": 45.5,
                "qr_data": "https://texcore.ec/lote/L-2026-001",
            }
            response = client.post("/zpl/etiqueta", json=payload)
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_etiqueta_dado_error_en_strategy_cuando_genera_entonces_retorna_500(self):
        """EP: fallo interno del strategy → 500 Internal Server Error."""
        mock_strategy = MagicMock()
        mock_strategy.render.side_effect = RuntimeError("Error de plantilla ZPL")
        app.dependency_overrides[get_zpl_strategy] = lambda: mock_strategy
        try:
            payload = {
                "producto_desc": "Hilo Nylon",
                "lote_codigo": "L-001",
                "peso_neto": 10.0,
                "qr_data": "test",
            }
            response = client.post("/zpl/etiqueta", json=payload)
            assert response.status_code == 500
        finally:
            app.dependency_overrides.clear()

    def test_etiqueta_dado_producto_con_caret_cuando_genera_entonces_zpl_saneado(self):
        """
        Medio: producto_desc/empresa son texto libre editable y se interpolan
        sin autoescape en etiqueta.zpl. Un '^' sin sanear rompería el stream
        ZPL (el interpretador de la Zebra lo lee como inicio de un comando
        nuevo). No se sobreescribe get_zpl_strategy: se usa el Environment y
        el template reales para probar el saneamiento de punta a punta.
        """
        payload = {
            "empresa": "Sede~Norte",
            "producto_desc": "Hilo^Malicioso",
            "lote_codigo": "L-2026-004",
            "peso_neto": 10.0,
            "qr_data": "https://texcore.ec/lote/L-2026-004",
        }
        response = client.post("/zpl/etiqueta", json=payload)
        assert response.status_code == 200
        assert "Hilo^Malicioso" not in response.text
        assert "HiloMalicioso" in response.text
        assert "Sede~Norte" not in response.text
        assert "SedeNorte" in response.text

    def test_etiqueta_dado_reimpresion_cuando_genera_entonces_audita_gobernanza(self):
        """F2: motivo/tipo_evento/version/usuario se propagan al registro de auditoría."""
        mock_strategy = MagicMock()
        mock_strategy.render.return_value = PlainTextResponse("^XA^FDREIMPRESION v1^FS^XZ")
        mock_audit = MagicMock()
        mock_audit.save = MagicMock(return_value=None)
        app.dependency_overrides[get_zpl_strategy] = lambda: mock_strategy
        app.dependency_overrides[get_audit_repo] = lambda: mock_audit
        try:
            payload = {
                "producto_desc": "Hilo Nylon 40/1",
                "lote_codigo": "L-2026-002",
                "peso_neto": 45.5,
                "qr_data": "https://texcore.ec/lote/L-2026-002",
                "tipo_evento": "REIMPRESION",
                "version": 1,
                "motivo": "DANIADA",
                "usuario": "empacador1",
                "reimpreso": True,
            }
            response = client.post("/zpl/etiqueta", json=payload)
            assert response.status_code == 200
            mock_audit.save.assert_called_once()
            record = mock_audit.save.call_args[0][0]
            assert record.tipo_evento == "REIMPRESION"
            assert record.version == 1
            assert record.motivo == "DANIADA"
            assert record.usuario == "empacador1"
        finally:
            app.dependency_overrides.clear()


class TestGetStrategyFunctions:

    def test_get_pdf_strategy_retorna_instancia_pdf_output_strategy(self):
        """Cubre get_pdf_strategy: crea Environment y PdfOutputStrategy."""
        strategy = get_pdf_strategy()
        assert isinstance(strategy, PdfOutputStrategy)

    def test_get_zpl_strategy_retorna_instancia_zpl_output_strategy(self):
        """Cubre get_zpl_strategy: crea Environment y ZplOutputStrategy."""
        strategy = get_zpl_strategy()
        assert isinstance(strategy, ZplOutputStrategy)


class TestZplOutputStrategy:

    def test_dado_zpl_strategy_cuando_render_entonces_retorna_plain_text(self):
        """Cubre ZplOutputStrategy.__init__ y render: renderiza template ZPL."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "^XA^FO50,50^FDHilo Nylon^FS^XZ"
        mock_env.get_template.return_value = mock_template

        strategy = ZplOutputStrategy(mock_env)
        result = strategy.render("etiqueta.zpl", {"lote_codigo": "L-001"}, "L-001")

        assert isinstance(result, PlainTextResponse)
        mock_env.get_template.assert_called_once_with("etiqueta.zpl")
        mock_template.render.assert_called_once_with(lote_codigo="L-001")


class TestPdfOutputStrategy:

    def test_dado_pdf_strategy_cuando_render_entonces_retorna_streaming_response(self):
        """Cubre PdfOutputStrategy.__init__ y render con WeasyPrint mockeado."""
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body><p>Nota de venta</p></body></html>"
        mock_env.get_template.return_value = mock_template

        strategy = PdfOutputStrategy(mock_env)
        result = strategy.render("nota_venta.html", {"cliente": "Test"}, "nota_001")

        assert isinstance(result, StreamingResponse)
        assert result.media_type == "application/pdf"
        mock_env.get_template.assert_called_once_with("nota_venta.html")
