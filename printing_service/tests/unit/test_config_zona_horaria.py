"""
Zona horaria de la planta del printing_service.

Hallazgo de la revisión del 9-nov-2026: una zona mal escrita en ZONA_HORARIA_PLANTA lanzaba
ZoneInfoNotFoundError (subclase de KeyError) dentro del filtro `fecha_hora`, que solo atrapaba
ValueError: todos los PDF respondían 500. Ahora se valida una vez, al cargar la configuración,
y el servicio no arranca con una zona inválida.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): zona válida / zona inexistente / texto vacío.
"""

from zoneinfo import ZoneInfo

import pytest

from src.config import ZONA_PLANTA, cargar_zona


def test_cargar_zona_dado_zona_valida_cuando_carga_entonces_devuelve_esa_zona():
    assert cargar_zona("America/Guayaquil") == ZoneInfo("America/Guayaquil")


@pytest.mark.parametrize("nombre", ["America/Guayaquill", ""])
def test_cargar_zona_dado_zona_invalida_cuando_carga_entonces_falla_con_el_nombre(nombre):
    with pytest.raises(RuntimeError, match="ZONA_HORARIA_PLANTA"):
        cargar_zona(nombre)


def test_zona_planta_dado_configuracion_por_omision_cuando_carga_entonces_es_guayaquil():
    assert str(ZONA_PLANTA) == "America/Guayaquil"
