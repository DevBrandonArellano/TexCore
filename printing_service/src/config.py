"""
Configuración centralizada del printing_service.
Elimina dependencias de cwd (fragilidad operacional).
"""

import os
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_SRC_DIR = Path(__file__).parent

TEMPLATES_DIR = str(_SRC_DIR / "templates")


def cargar_zona(nombre: str) -> ZoneInfo:
    """La zona de la planta, validada al arrancar: una mal escrita detiene el servicio en
    lugar de romper cada PDF (ZoneInfoNotFoundError es un KeyError, no un ValueError)."""
    try:
        return ZoneInfo(nombre)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RuntimeError(f"ZONA_HORARIA_PLANTA inválida: {nombre!r}") from exc


# Las fechas llegan en UTC o con su desfase; los documentos se leen con el reloj de la planta.
ZONA_HORARIA_PLANTA = os.environ.get("ZONA_HORARIA_PLANTA", "America/Guayaquil")
ZONA_PLANTA = cargar_zona(ZONA_HORARIA_PLANTA)

REQUIRED_TEMPLATES = [
    "nota_venta.html",
    "etiqueta.zpl",
    "etiqueta_label.html",
    "reporte_avance.html",  # Fase 2: avance operativo (A4 landscape)
    "reporte_balance.html",  # Fase 2: balance de masas mensual (portrait)
    "historial_despachos.html",  # F7: listado impreso de despachos (Despacho)
    "guia_remision.html",  # F7: guía de remisión informativa (Despacho)
    "produccion_por_producto.html",  # F8: producción por producto (Ejecutivo)
    "formula_dosificacion.html",  # hoja de dosificación de una fórmula (Tintorero)
    "historial_mantenimiento.html",  # historial de mantenimiento y paros de máquina (Jefe de Área)
]
