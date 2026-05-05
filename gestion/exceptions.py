"""
Manejo de excepciones centralizado para TexCore.

Formato de respuesta de error estándar para toda la API:
{
    "success": false,
    "error": {
        "code": 400,
        "message": "Descripción legible del error",
        "fields": { "campo": ["mensaje"] }  // Solo en errores de validación (400)
    }
}
"""
import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.conf import settings

logger = logging.getLogger(__name__)


def _extract_message(data) -> str:
    """Extrae un mensaje legible de la estructura de datos del error DRF."""
    if isinstance(data, str):
        return data
    if isinstance(data, list) and data:
        first = data[0]
        return str(first) if not isinstance(first, dict) else _extract_message(first)
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        if 'non_field_errors' in data:
            val = data['non_field_errors']
            return str(val[0]) if isinstance(val, list) and val else str(val)
        first_key = next(iter(data))
        val = data[first_key]
        msg = str(val[0]) if isinstance(val, list) and val else str(val)
        return f"{first_key}: {msg}"
    return "Error en la solicitud"


def texcore_exception_handler(exc, context):
    """
    Handler de excepciones unificado.
    Reemplaza los 4 patrones distintos que existían en el proyecto.

    Registro en settings.py:
        REST_FRAMEWORK = {
            'EXCEPTION_HANDLER': 'gestion.exceptions.texcore_exception_handler',
        }
    """
    response = exception_handler(exc, context)

    if response is None:
        # Excepción no manejada por DRF — loguear y retornar 500 genérico
        view = context.get('view')
        view_name = view.__class__.__name__ if view is not None else 'unknown'
        logger.exception("Excepción no manejada en %s", view_name)
        return Response(
            {"success": False, "error": {"code": 500, "message": "Error interno del servidor"}},
            status=500,
        )

    error_body: dict = {
        "code": response.status_code,
        "message": _extract_message(response.data),
    }

    # Incluir detalle de campos solo en errores de validación (400)
    if response.status_code == 400 and isinstance(response.data, dict):
        # Filtrar claves internas de DRF que no son campos reales
        fields = {k: v for k, v in response.data.items() if k not in ('detail', 'non_field_errors')}
        if fields:
            error_body["fields"] = fields

    # En modo DEBUG incluir el detalle completo para facilitar el desarrollo
    if settings.DEBUG and response.status_code >= 500:
        error_body["detail"] = response.data

    response.data = {"success": False, "error": error_body}
    return response
