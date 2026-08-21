"""Helpers compartidos por los módulos de vistas de producción."""
from rest_framework.exceptions import ValidationError


def parse_int_param(value, field_name):
    """
    Valida un query param usado como ID entero positivo (OWASP A03).

    Retorna int, o None si el valor viene vacío/ausente. Lanza
    ValidationError (→ HTTP 400 controlado) si el valor no es un entero
    válido, evitando un 500 no controlado al pasar '?area=abc' a un
    queryset `.filter(id=...)`.
    """
    if value in (None, ''):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: f"'{value}' no es un identificador válido."})
    if parsed <= 0:
        raise ValidationError({field_name: "El identificador debe ser un entero positivo."})
    return parsed
