"""
Configuración centralizada del printing_service.
Elimina dependencias de cwd (fragilidad operacional).
"""
from pathlib import Path

_SRC_DIR = Path(__file__).parent

TEMPLATES_DIR = str(_SRC_DIR / "templates")

REQUIRED_TEMPLATES = ["nota_venta.html", "etiqueta.zpl"]
