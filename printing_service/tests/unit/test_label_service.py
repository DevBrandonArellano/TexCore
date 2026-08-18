"""
Tests unitarios de LabelService.
No requieren HTTP ni WeasyPrint — solo qrcode/python-barcode.
"""
import base64
from unittest.mock import patch

from src.schemas.printing import EtiquetaRequest
from src.services.label_service import LabelService

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _make_request(**overrides) -> EtiquetaRequest:
    data = {
        "producto_desc": "Hilo Nylon 40/1",
        "lote_codigo": "LOT-2026-001",
        "peso_neto": 45.5,
        "qr_data": "https://texcore.ec/lote/LOT-2026-001",
    }
    data.update(overrides)
    return EtiquetaRequest(**data)


class TestLabelService_GenerarCodigoBarras:
    def test_codigo_barras_dado_lote_valido_cuando_genera_entonces_retorna_png_base64(self):
        b64 = LabelService.generar_codigo_barras("LOT-2026-001")
        raw = base64.b64decode(b64)
        assert raw.startswith(PNG_SIGNATURE)

    def test_codigo_barras_dado_mismo_lote_cuando_genera_dos_veces_entonces_es_determinista(self):
        assert LabelService.generar_codigo_barras("LOT-2026-001") == LabelService.generar_codigo_barras("LOT-2026-001")


class TestLabelService_GenerarQr:
    def test_qr_dado_data_valida_cuando_genera_entonces_retorna_png_base64(self):
        b64 = LabelService.generar_qr("https://texcore.ec/lote/LOT-2026-001")
        raw = base64.b64decode(b64)
        assert raw.startswith(PNG_SIGNATURE)

    def test_qr_dado_data_distinta_cuando_genera_entonces_produce_imagenes_distintas(self):
        img_a = LabelService.generar_qr("A")
        img_b = LabelService.generar_qr("B")
        assert img_a != img_b


class TestLabelService_ConstruirContexto:
    def test_contexto_dado_request_valido_cuando_construir_entonces_incluye_ambas_imagenes(self):
        contexto = LabelService.construir_contexto(_make_request())
        assert contexto.barcode_image is not None
        assert contexto.qr_image is not None
        assert base64.b64decode(contexto.barcode_image).startswith(PNG_SIGNATURE)
        assert base64.b64decode(contexto.qr_image).startswith(PNG_SIGNATURE)

    def test_contexto_dado_request_valido_cuando_construir_entonces_conserva_campos_originales(self):
        contexto = LabelService.construir_contexto(_make_request(lote_codigo="LOT-XYZ"))
        assert contexto.lote_codigo == "LOT-XYZ"
        assert contexto.producto_desc == "Hilo Nylon 40/1"

    def test_contexto_dado_fallo_generando_barcode_cuando_construir_entonces_no_propaga_y_deja_none(self):
        with patch.object(LabelService, "generar_codigo_barras", side_effect=RuntimeError("boom")):
            contexto = LabelService.construir_contexto(_make_request())
        assert contexto.barcode_image is None
        assert contexto.qr_image is not None  # el QR sí se genera con normalidad

    def test_contexto_dado_fallo_generando_qr_cuando_construir_entonces_no_propaga_y_deja_none(self):
        with patch.object(LabelService, "generar_qr", side_effect=RuntimeError("boom")):
            contexto = LabelService.construir_contexto(_make_request())
        assert contexto.qr_image is None
        assert contexto.barcode_image is not None
