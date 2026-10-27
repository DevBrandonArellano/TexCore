"""
Hora de la planta en los textos que arma el backend (PDF y mensajes).

TIME_ZONE es UTC; quien lee un documento o un mensaje usa el reloj de la planta
(ZONA_HORARIA_PLANTA, por defecto America/Guayaquil, UTC-5).

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): fecha con hora / solo fecha / ahora.
- Análisis de valores límite (BVA): justo después de la medianoche UTC sigue siendo el día
  anterior en la planta.
"""

from datetime import UTC, datetime
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from gestion.hora_planta import fecha_hoy_planta, texto_fecha, texto_fecha_hora


class HoraPlantaTest(SimpleTestCase):
    def test_texto_fecha_hora_dado_instante_utc_cuando_formatea_entonces_hora_de_la_planta(self):
        self.assertEqual(texto_fecha_hora(datetime(2026, 10, 27, 18, 23, tzinfo=UTC)), "27/10/2026 13:23")

    def test_texto_fecha_dado_madrugada_utc_cuando_formatea_entonces_fecha_del_dia_anterior(self):
        self.assertEqual(texto_fecha(datetime(2026, 10, 28, 2, 0, tzinfo=UTC)), "27/10/2026")

    def test_fecha_hoy_planta_dado_madrugada_utc_cuando_consulta_entonces_dia_de_la_planta(self):
        with patch("gestion.hora_planta.timezone.now", return_value=datetime(2026, 10, 28, 2, 0, tzinfo=UTC)):
            self.assertEqual(fecha_hoy_planta().isoformat(), "2026-10-27")

    @override_settings(ZONA_HORARIA_PLANTA="America/Bogota")
    def test_texto_fecha_hora_dado_otra_zona_configurada_cuando_formatea_entonces_la_respeta(self):
        self.assertEqual(texto_fecha_hora(datetime(2026, 10, 27, 18, 23, tzinfo=UTC)), "27/10/2026 13:23")

    @override_settings(ZONA_HORARIA_PLANTA="Europe/Madrid")
    def test_texto_fecha_hora_dado_zona_con_horario_de_verano_cuando_formatea_entonces_aplica_su_desfase(self):
        self.assertEqual(texto_fecha_hora(datetime(2026, 7, 1, 10, 0, tzinfo=UTC)), "01/07/2026 12:00")

    def test_texto_fecha_hora_dado_none_cuando_formatea_entonces_vacio(self):
        self.assertEqual(texto_fecha_hora(None), "")
