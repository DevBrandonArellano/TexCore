"""
Tests unitarios de zpl_sanitizer.
Medio: campos de texto libre (producto_desc, empresa) interpolados sin
autoescape en templates ZPL pueden corromper el stream si contienen '^'
(prefijo de comando de formato) o '~' (prefijo de comando de control).
"""
from src.services.zpl_sanitizer import sanitize_zpl_context, sanitize_zpl_value


class TestSanitizeZplValue:
    def test_dado_texto_con_caret_cuando_sanea_entonces_lo_elimina(self):
        assert sanitize_zpl_value("Hilo^Nylon") == "HiloNylon"

    def test_dado_texto_con_tilde_cuando_sanea_entonces_lo_elimina(self):
        assert sanitize_zpl_value("Sede~Norte") == "SedeNorte"

    def test_dado_texto_normal_cuando_sanea_entonces_no_cambia(self):
        assert sanitize_zpl_value("Hilo Nylon 40/1") == "Hilo Nylon 40/1"

    def test_dado_valor_no_string_cuando_sanea_entonces_lo_retorna_intacto(self):
        assert sanitize_zpl_value(45.5) == 45.5
        assert sanitize_zpl_value(None) is None
        assert sanitize_zpl_value(True) is True


class TestSanitizeZplContext:
    def test_dado_dict_mixto_cuando_sanea_entonces_solo_transforma_strings(self):
        context = {
            "producto_desc": "Hilo^Malicioso",
            "peso_neto": 45.5,
            "tara": None,
            "empresa": "Sede~Norte",
        }
        saneado = sanitize_zpl_context(context)
        assert saneado == {
            "producto_desc": "HiloMalicioso",
            "peso_neto": 45.5,
            "tara": None,
            "empresa": "SedeNorte",
        }
