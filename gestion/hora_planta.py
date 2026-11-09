"""
Hora de la planta para los textos que arma el backend: PDF y mensajes al usuario.

TIME_ZONE es la zona de la planta (ZONA_HORARIA_PLANTA, por defecto America/Guayaquil) y la
base guarda en UTC (USE_TZ=True). Estos helpers formatean en la zona activa de Django; el
frontend y printing_service (filtro `fecha_hora`) convierten por su cuenta las fechas ISO.
"""

from datetime import date, datetime

from django.utils import timezone


def en_hora_planta(instante: datetime) -> datetime:
    return timezone.localtime(instante)


def fecha_hoy_planta() -> date:
    """El día de hoy en la planta (entre las 19:00 y la medianoche de Ecuador, en UTC ya es mañana)."""
    return timezone.localdate()


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
