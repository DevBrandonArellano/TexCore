"""
Hora de la planta para los textos que arma el backend: PDF y mensajes al usuario.

TIME_ZONE es UTC (así se guarda y se calcula todo), pero quien lee un documento o un mensaje
usa el reloj de la planta. ZONA_HORARIA_PLANTA (settings, por defecto America/Guayaquil)
fija esa zona. El frontend convierte las fechas por su cuenta y printing_service convierte las
que recibe en ISO (filtro `fecha_hora`); esto cubre lo que el backend ya manda formateado.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone


def en_hora_planta(instante: datetime) -> datetime:
    return instante.astimezone(ZoneInfo(settings.ZONA_HORARIA_PLANTA))


def fecha_hoy_planta() -> date:
    """El día de hoy en la planta: entre las 19:00 y la medianoche de Ecuador, en UTC ya es mañana."""
    return en_hora_planta(timezone.now()).date()


def texto_fecha_hora(instante: datetime | None) -> str:
    """«dd/mm/aaaa HH:MM» en hora de la planta; vacío si no hay fecha."""
    return f"{en_hora_planta(instante):%d/%m/%Y %H:%M}" if instante else ""


def texto_fecha(valor: datetime | date | None) -> str:
    """«dd/mm/aaaa»; un instante se pasa antes a la hora de la planta (puede cambiar el día)."""
    if not valor:
        return ""
    if isinstance(valor, datetime):
        valor = en_hora_planta(valor)
    return f"{valor:%d/%m/%Y}"
