"""
_fecha_pedido_to_iso_utc: la fecha del pedido viaja al frontend en ISO UTC con `Z`, para que
el navegador la muestre en la hora local correcta.

Regresión (5-oct-2026, detectada al activar las reglas DTZ de Ruff): usaba
`django.utils.timezone.utc`, que Django 5.0 eliminó. El AttributeError quedaba tragado por un
`except Exception` y se devolvía el formato de respaldo: `+00:00` en vez de `Z` y, para un
`date`, solo `AAAA-MM-DD`, que el frontend interpreta como medianoche UTC (el día anterior en
Ecuador).

Técnicas ISTQB: partición de equivalencia (EP) — datetime con zona / datetime sin zona /
date / None / valor no fecha.
"""
from datetime import UTC, date, datetime, timedelta, timezone

from django.test import SimpleTestCase

from gestion.serializers.sales_serializers import _fecha_pedido_to_iso_utc


class FechaPedidoIsoUtcTestCase(SimpleTestCase):

    def test_formato_dado_datetime_utc_cuando_convierte_entonces_iso_con_z(self):
        self.assertEqual(
            _fecha_pedido_to_iso_utc(datetime(2026, 1, 1, 10, 0, tzinfo=UTC)),
            '2026-01-01T10:00:00.000Z',
        )

    def test_formato_dado_datetime_con_otra_zona_cuando_convierte_entonces_lo_pasa_a_utc(self):
        ecuador = timezone(timedelta(hours=-5))
        self.assertEqual(
            _fecha_pedido_to_iso_utc(datetime(2026, 1, 1, 19, 30, tzinfo=ecuador)),
            '2026-01-02T00:30:00.000Z',
        )

    def test_formato_dado_datetime_sin_zona_cuando_convierte_entonces_lo_asume_utc(self):
        self.assertEqual(_fecha_pedido_to_iso_utc(datetime(2026, 1, 1, 10, 0)), '2026-01-01T10:00:00.000Z')  # noqa: DTZ001 — caso de prueba: datetime sin zona

    def test_formato_dado_date_cuando_convierte_entonces_medianoche_utc_con_z(self):
        self.assertEqual(_fecha_pedido_to_iso_utc(date(2026, 1, 1)), '2026-01-01T00:00:00.000Z')

    def test_formato_dado_none_cuando_convierte_entonces_none(self):
        self.assertIsNone(_fecha_pedido_to_iso_utc(None))

    def test_formato_dado_texto_cuando_convierte_entonces_lo_devuelve_como_texto(self):
        self.assertEqual(_fecha_pedido_to_iso_utc('2026-01-01'), '2026-01-01')
