"""
EventoEtiquetaService: orquesta la numeración y creación de eventos de etiqueta.
SRP: única responsabilidad — mantener la secuencia/version consistentes por lote.
ISO 27001 A.12.4: cada evento es un registro de auditoría inmutable.

secuencia: identificador de cada evento físico de impresión, siempre creciente por lote.
version: versión de los DATOS de la etiqueta — se mantiene igual entre reimpresiones
idénticas y solo se incrementa cuando un REETIQUETADO cambia datos (y anula la anterior).
"""
from django.db import transaction

from gestion.models import EventoEtiqueta, LoteProduccion


def _snapshot_actual(lote: LoteProduccion) -> dict:
    return {
        'peso_neto_producido': str(lote.peso_neto_producido),
        'peso_bruto': str(lote.peso_bruto),
        'tara': str(lote.tara),
        'clasificacion_calidad': lote.clasificacion_calidad,
        'presentacion': lote.presentacion,
        'unidades_empaque': lote.unidades_empaque,
        'cantidad_metros': str(lote.cantidad_metros) if lote.cantidad_metros is not None else None,
    }


class EventoEtiquetaService:

    @staticmethod
    @transaction.atomic
    def registrar_original(lote: LoteProduccion, user) -> EventoEtiqueta:
        return EventoEtiqueta.objects.create(
            lote=lote,
            tipo_evento='ORIGINAL',
            secuencia=1,
            version=1,
            usuario=user,
            formato='ZPL',
            datos_snapshot=_snapshot_actual(lote),
        )

    @staticmethod
    @transaction.atomic
    def registrar_reimpresion(lote: LoteProduccion, user, motivo: str, detalle_motivo: str = '',
                               formato: str = 'ZPL') -> EventoEtiqueta:
        """Copia idéntica: mantiene la version de datos vigente, solo avanza la secuencia."""
        ultimo = lote.etiquetas.select_for_update().order_by('-secuencia').first()
        version_vigente = ultimo.version if ultimo else 1
        siguiente_secuencia = (ultimo.secuencia if ultimo else 0) + 1

        return EventoEtiqueta.objects.create(
            lote=lote,
            tipo_evento='REIMPRESION',
            secuencia=siguiente_secuencia,
            version=version_vigente,
            motivo=motivo,
            detalle_motivo=detalle_motivo,
            usuario=user,
            formato=formato,
            datos_snapshot=_snapshot_actual(lote),
        )

    @staticmethod
    @transaction.atomic
    def registrar_reetiquetado(lote: LoteProduccion, user, motivo: str, detalle_motivo: str = '',
                                formato: str = 'ZPL') -> EventoEtiqueta:
        """Cambio de datos: anula la última etiqueta vigente y emite una nueva version."""
        ultimo = lote.etiquetas.select_for_update().order_by('-secuencia').first()
        version_previa = ultimo.version if ultimo else 1
        siguiente_secuencia = (ultimo.secuencia if ultimo else 0) + 1

        if ultimo and not ultimo.anulada:
            ultimo.anulada = True
            ultimo.save(update_fields=['anulada'])

        return EventoEtiqueta.objects.create(
            lote=lote,
            tipo_evento='REETIQUETADO',
            secuencia=siguiente_secuencia,
            version=version_previa + 1,
            motivo=motivo,
            detalle_motivo=detalle_motivo,
            usuario=user,
            formato=formato,
            datos_snapshot=_snapshot_actual(lote),
            anula_a=ultimo,
        )
