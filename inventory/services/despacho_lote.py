"""
Motivo de rechazo de un lote que otro despachador ya se llevó.

Cuando dos despachadores escanean el mismo lote, el primero que confirma se lo lleva y al
segundo se le rechaza el despacho (o el escaneo, si llega después). Sin el motivo, el segundo
solo veía «ya no tiene stock disponible» y no sabía qué hacer. Lo usan el despacho
(inventory/views/despacho_views.py) y la validación del escaneo
(internal_api/views/scanning_views.py), para que los dos digan lo mismo.
"""

from zoneinfo import ZoneInfo

from django.conf import settings

from inventory.models import DetalleHistorialDespacho


def motivo_lote_despachado(lote, ids_bodegas):
    """«El lote X ya fue despachado por <persona> el dd/mm/aaaa a las HH:MM (despacho #N).»

    Devuelve None si el lote no tiene un despacho vigente (una reversión marca sus detalles
    como devolución) o si salió de una bodega fuera de `ids_bodegas`: a un usuario de otra
    sede no se le revela quién despachó (OWASP A01). `ids_bodegas=None` = ve todas.
    """
    detalle = (
        DetalleHistorialDespacho.objects.filter(lote=lote, es_devolucion=False)
        .select_related("historial__usuario", "movimiento_venta")
        .order_by("-historial__fecha_despacho", "-id")
        .first()
    )
    if detalle is None:
        return None
    if ids_bodegas is not None:
        # Sin el movimiento (registros antiguos) no se puede comprobar la bodega: no se revela.
        origen = detalle.movimiento_venta.bodega_origen_id if detalle.movimiento_venta else None
        if origen not in ids_bodegas:
            return None

    historial = detalle.historial
    usuario = historial.usuario
    quien = (usuario.get_full_name() or usuario.username) if usuario else "otro usuario"
    # Hora de la planta: TIME_ZONE es UTC y el despachador lee la hora de su reloj.
    cuando = historial.fecha_despacho.astimezone(ZoneInfo(settings.ZONA_HORARIA_PLANTA))
    return (
        f"El lote {lote.codigo_lote} ya fue despachado por {quien} el {cuando:%d/%m/%Y} "
        f"a las {cuando:%H:%M} (despacho #{historial.id})."
    )
