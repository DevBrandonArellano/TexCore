"""
Asignación de procesos de tintorería a una máquina (MaquinaProceso).

El Jefe de Área define qué procesos (descrude, lavado reductivo...) ejecuta cada
máquina de su área. La asignación se reemplaza completa en una transacción: o
queda el conjunto nuevo, o queda el anterior (ISO 9001: sin estados intermedios).
"""
import logging

from django.core.exceptions import ValidationError
from django.db import transaction

from gestion.models import MaquinaProceso, ProcesoTintoreria

logger = logging.getLogger('gestion.services')


class ProcesosMaquinaService:

    @staticmethod
    @transaction.atomic
    def reemplazar(maquina, proceso_ids, user):
        """Deja en `maquina` exactamente los procesos `proceso_ids`.

        Solo acepta procesos activos de la sede de la máquina (OWASP A01); un id
        ajeno o inexistente responde igual que uno que no existe.
        """
        ids = set(proceso_ids)
        sede_id = maquina.area.sede_id if maquina.area_id else None
        procesos = list(ProcesoTintoreria.objects.filter(id__in=ids, sede_id=sede_id, activo=True))
        if len(procesos) != len(ids):
            raise ValidationError({'procesos': 'Algún proceso no existe, está inactivo o es de otra sede.'})

        MaquinaProceso.objects.filter(maquina=maquina).exclude(proceso_id__in=ids).delete()
        existentes = set(MaquinaProceso.objects.filter(maquina=maquina).values_list('proceso_id', flat=True))
        for proceso in procesos:
            if proceso.id in existentes:
                continue
            asignacion = MaquinaProceso(maquina=maquina, proceso=proceso)
            asignacion.full_clean()
            asignacion.save()

        logger.info(
            "Procesos de máquina reemplazados",
            extra={"sd": {"entity": "Maquina", "id": maquina.id, "user": user.username,
                          "procesos": sorted(ids)}})
        return ProcesoTintoreria.objects.filter(maquinas_asignadas__maquina=maquina).order_by('codigo')
