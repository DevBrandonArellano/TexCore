"""
Configuración centralizada del printing_service.
Elimina dependencias de cwd (fragilidad operacional).
"""
from pathlib import Path

_SRC_DIR = Path(__file__).parent

TEMPLATES_DIR = str(_SRC_DIR / "templates")

REQUIRED_TEMPLATES = [
    "nota_venta.html",
    "etiqueta.zpl",
    "etiqueta_label.html",
    "reporte_avance.html",    # Fase 2: avance operativo (A4 landscape)
    "reporte_balance.html",   # Fase 2: balance de masas mensual (portrait)
]
