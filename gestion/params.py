"""
Validación de parámetros de entrada (query params y cuerpos de petición).

Vive fuera de `gestion/views/` porque también lo usan los servicios: importarlo desde
`gestion.views._common` arrastraba `gestion/views/__init__.py`, y un servicio importado
por un serializer cerraba el círculo serializers → services → views → serializers.
"""

from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError


def parse_int_param(value, field_name):
    """
    Valida un query param usado como ID entero positivo (OWASP A03).

    Retorna int, o None si el valor viene vacío/ausente. Lanza
    ValidationError (→ HTTP 400 controlado) si el valor no es un entero
    válido, evitando un 500 no controlado al pasar '?area=abc' a un
    queryset `.filter(id=...)`.
    """
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: f"'{value}' no es un identificador válido."}) from None
    if parsed <= 0:
        raise ValidationError({field_name: "El identificador debe ser un entero positivo."})
    return parsed


def parse_date_param(params, nombre):
    """Query param de fecha `YYYY-MM-DD` (OWASP A03): None si viene vacío; 400 si no es
    una fecha válida (formato incorrecto o día inexistente, p. ej. 2026-02-30)."""
    crudo = params.get(nombre)
    if not crudo:
        return None
    try:
        fecha = parse_date(crudo)
    except ValueError:
        fecha = None
    if not fecha:
        raise ValidationError({nombre: "Formato de fecha inválido (usar YYYY-MM-DD)."})
    return fecha


def parse_rango_fechas(params, desde="fecha_desde", hasta="fecha_hasta"):
    """Par (desde, hasta) validado: cada fecha con parse_date_param y el orden del rango."""
    fecha_desde = parse_date_param(params, desde)
    fecha_hasta = parse_date_param(params, hasta)
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValidationError({desde: f"{desde} no puede ser posterior a {hasta}."})
    return fecha_desde, fecha_hasta
