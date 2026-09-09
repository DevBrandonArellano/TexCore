"""
Strategy Pattern para formatos de salida del printing_service.
OCP: agregar un nuevo formato (HTML, PNG) solo requiere crear una nueva clase
que implemente OutputStrategy, sin modificar los routers ni el servicio.
"""
import io
import logging
from typing import Protocol, runtime_checkable

from fastapi.responses import StreamingResponse, PlainTextResponse, Response
from jinja2 import Environment

from .zpl_sanitizer import sanitize_zpl_context

logger = logging.getLogger(__name__)


@runtime_checkable
class OutputStrategy(Protocol):
    """Contrato para estrategias de generación de documentos."""

    def render(self, template_name: str, context: dict, filename: str) -> Response:
        """
        Renderiza el template con el contexto dado y retorna la Response HTTP.

        Args:
            template_name: Nombre del archivo de template (ej: "nota_venta.html").
            context: Diccionario con variables para el template.
            filename: Nombre base del archivo de descarga (sin extensión).
        """
        ...


class PdfOutputStrategy:
    """Genera PDF a partir de un template HTML con WeasyPrint."""

    def __init__(self, jinja_env: Environment) -> None:
        self._env = jinja_env

    def render(self, template_name: str, context: dict, filename: str) -> StreamingResponse:
        from weasyprint import HTML  # Import tardío: WeasyPrint no disponible en tests
        template = self._env.get_template(template_name)
        html_content = template.render(**context)
        pdf_bytes = HTML(string=html_content).write_pdf()
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
        )


class ZplOutputStrategy:
    """Genera texto ZPL a partir de un template Jinja2."""

    def __init__(self, jinja_env: Environment) -> None:
        self._env = jinja_env

    def render(self, template_name: str, context: dict, filename: str) -> PlainTextResponse:
        template = self._env.get_template(template_name)
        # ZPL no tiene autoescape (no es HTML): un '^'/'~' sin sanear en texto
        # libre (producto_desc, empresa) rompería el stream ZPL, ver zpl_sanitizer.
        zpl_content = template.render(**sanitize_zpl_context(context))
        return PlainTextResponse(zpl_content)
