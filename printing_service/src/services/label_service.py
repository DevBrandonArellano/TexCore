"""
LabelService: lógica de negocio del dominio de etiquetas de producción.
Responsabilidad única (SRP): generar las imágenes de trazabilidad (código de
barras Code128 y código QR) que el template PDF necesita para incrustar como
<img>, y construir el contexto enriquecido para el render. No conoce HTTP,
Jinja2 ni WeasyPrint.

El PDF (WeasyPrint) no dibuja símbolos de barcode/QR por sí mismo — a
diferencia de ZPL, donde el propio printer Zebra interpreta ^BCN/^BQN y
dibuja el símbolo a partir del texto, aquí hay que rasterizar la imagen
nosotros mismos y embeberla en base64.
"""
import base64
import io
import logging

import qrcode
from barcode import Code128
from barcode.writer import ImageWriter

from ..schemas.printing import EtiquetaContexto, EtiquetaRequest

logger = logging.getLogger(__name__)


class LabelService:
    """Genera las imágenes de código de barras y QR de una etiqueta de lote."""

    @staticmethod
    def generar_codigo_barras(codigo: str) -> str:
        """
        Code128 (misma simbología que ^BCN en ZPL) como PNG en base64.
        `write_text=False` porque el código ya se imprime como texto aparte
        en la etiqueta (evita duplicarlo justo debajo del símbolo).
        """
        buffer = io.BytesIO()
        Code128(codigo, writer=ImageWriter()).write(
            buffer,
            options={"write_text": False, "module_height": 10.0, "quiet_zone": 2.0},
        )
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @staticmethod
    def generar_qr(data: str) -> str:
        """QR (misma corrección de errores 'M' que ^BQN,2,5 en ZPL) como PNG en base64."""
        img = qrcode.make(data, error_correction=qrcode.constants.ERROR_CORRECT_M)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("ascii")

    @classmethod
    def construir_contexto(cls, request: EtiquetaRequest) -> EtiquetaContexto:
        """
        Construye el contexto para el template PDF, con las imágenes ya
        generadas. Un fallo generando UNA imagen no debe tumbar la etiqueta
        completa (mejor una etiqueta con un símbolo faltante que un 500).
        """
        try:
            barcode_image = cls.generar_codigo_barras(request.lote_codigo)
        except Exception:
            logger.exception(
                "Fallo al generar código de barras para lote %s", request.lote_codigo
            )
            barcode_image = None

        try:
            qr_image = cls.generar_qr(request.qr_data)
        except Exception:
            logger.exception("Fallo al generar QR para lote %s", request.lote_codigo)
            qr_image = None

        return EtiquetaContexto(
            **request.model_dump(),
            barcode_image=barcode_image,
            qr_image=qr_image,
        )
