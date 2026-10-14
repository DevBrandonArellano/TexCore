"""
Paros de máquina derivados del estado (decisión del usuario, 14-oct-2026).

El estado de una máquina (`operativa` / `mantenimiento` / `inactiva`) solo guardaba el valor
nuevo, sin fechas: un mantenimiento hecho con el cambio de estado no dejaba rastro y el
historial del Jefe de Área no podía decir qué días estuvo detenida. Ahora el cambio de estado
abre y cierra un `ParoMaquina` de origen `estado`.

Los paros de origen `manual` no se tocan: son históricos, alimentan el OEE y el ViewSet no
permite editarlos ni borrarlos.
"""

from django.db import transaction
from django.utils import timezone

from gestion.models import ParoMaquina

# Estado que detiene la máquina → (categoría del paro, planificado).
# `mantenimiento` es un paro planificado y no penaliza la Disponibilidad del OEE; una máquina
# `inactiva` sí la penaliza, porque está parada sin mantenimiento programado (OEE for Operators).
PARO_POR_ESTADO = {
    "mantenimiento": ("MANTENIMIENTO_PLANIFICADO", True),
    "inactiva": ("OTRO", False),
}

DESCRIPCION_POR_ESTADO = {
    "mantenimiento": "Apertura automática: la máquina pasó a mantenimiento.",
    "inactiva": "Apertura automática: la máquina pasó a inactiva.",
}


class ParoPorEstadoService:
    @staticmethod
    @transaction.atomic
    def sincronizar(maquina, estado_anterior, estado_nuevo, usuario=None):
        """Cierra el paro automático abierto y abre el que corresponda al estado nuevo.

        Devuelve el paro abierto (o None). Es idempotente: si el estado no cambió, o si ya hay
        un paro automático abierto del mismo tipo, no registra nada.
        """
        if estado_anterior == estado_nuevo:
            return None

        abierto = (
            ParoMaquina.objects.select_for_update()
            .filter(maquina=maquina, origen="estado", fin__isnull=True)
            .order_by("-inicio")
            .first()
        )

        categoria_planificado = PARO_POR_ESTADO.get(estado_nuevo)

        # Ya hay un paro automático abierto del mismo tipo: nada que hacer (reintento o
        # dos peticiones seguidas con el mismo estado destino).
        if abierto and categoria_planificado and abierto.categoria == categoria_planificado[0]:
            return abierto

        ahora = timezone.now()
        if abierto:
            abierto.fin = ahora
            abierto.save(update_fields=["fin"])

        if not categoria_planificado:
            return None

        categoria, planificado = categoria_planificado
        return ParoMaquina.objects.create(
            maquina=maquina,
            inicio=ahora,
            categoria=categoria,
            planificado=planificado,
            descripcion=DESCRIPCION_POR_ESTADO[estado_nuevo],
            usuario=usuario,
            origen="estado",
        )
