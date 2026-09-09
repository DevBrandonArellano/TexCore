"""
Saneamiento de valores de texto antes de interpolarlos en un template ZPL.
SRP: única responsabilidad — neutralizar los prefijos de comando ZPL ('^'
formato, '~' control) en campos de texto libre (ej. producto_desc, empresa)
editables por un usuario/admin, para que no puedan truncar o inyectar
comandos ZPL nuevos y corromper el stream enviado a la impresora térmica.
El template ZPL no usa autoescape de Jinja2 (no es HTML), así que este es
el único punto de saneamiento del pipeline.
"""
from typing import Any


def sanitize_zpl_value(value: Any) -> Any:
    """Elimina '^' y '~' de un string; cualquier otro tipo se retorna intacto."""
    if not isinstance(value, str):
        return value
    return value.replace("^", "").replace("~", "")


def sanitize_zpl_context(context: dict) -> dict:
    """Aplica sanitize_zpl_value a cada valor de nivel superior del contexto."""
    return {key: sanitize_zpl_value(value) for key, value in context.items()}
