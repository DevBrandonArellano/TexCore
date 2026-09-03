"""
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-CosteoLoteProduccion (F0-002)
Patrón: Service Layer
SOLID: SRP — solo calcula costos de producción por lote.

Costo total = MP (trazabilidad F0-001) + químicos (DescargaQuimicoOP ×
precio_base) + operario (TarifaOperario × horas) + máquina (CostoHoraMaquina
× horas) + otros. Las horas reales provienen de hora_inicio/hora_final del
LoteProduccion.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from gestion.models import CostoLoteProduccion, TarifaOperario, CostoHoraMaquina
from gestion.services.materia_prima_service import TraceabilityService

logger = logging.getLogger('gestion.services.costeo')


class CostoLoteService:
    """Calcula y persiste el desglose de costos de un lote de producción."""

    @staticmethod
    @transaction.atomic
    def calcular_costo(lote_produccion, usuario) -> CostoLoteProduccion:
        costo, _created = CostoLoteProduccion.objects.get_or_create(
            lote_produccion=lote_produccion
        )
        orden = lote_produccion.orden_produccion

        # 1. COSTO MATERIA PRIMA (cadena de trazabilidad F0-001)
        cadena = TraceabilityService.obtener_cadena_completa(lote_produccion)
        costo.costo_materia_prima = Decimal(
            str(cadena.get('costo_total_materias_primas', 0))
        ).quantize(Decimal('0.001'))

        # 2. COSTO QUÍMICOS (descargas aplicadas de la OP × precio_base)
        costo_quimicos = Decimal('0.000')
        if orden:
            descargas = orden.descargas_quimicos.filter(estado='aplicada').select_related('producto')
            for descarga in descargas:
                cantidad = descarga.cantidad_real_kg or descarga.cantidad_calculada_kg
                costo_quimicos += cantidad * descarga.producto.precio_base
        costo.costo_quimicos = costo_quimicos.quantize(Decimal('0.001'))

        # Horas reales del lote (hora_inicio → hora_final)
        horas = Decimal('0')
        if lote_produccion.hora_inicio and lote_produccion.hora_final:
            segundos = (lote_produccion.hora_final - lote_produccion.hora_inicio).total_seconds()
            if segundos > 0:
                horas = Decimal(str(segundos)) / Decimal('3600')

        # 3. COSTO OPERARIO (tarifa vigente por tiempo × horas)
        costo.costo_operario = Decimal('0.000')
        operario = lote_produccion.operario or (orden.operario_asignado if orden else None)
        if operario and horas > 0:
            tarifa = CostoLoteService._obtener_tarifa_operario(
                operario=operario,
                sede=orden.sede if orden else None,
                fecha=lote_produccion.hora_final.date(),
            )
            if tarifa and tarifa.tipo_contrato == 'tiempo' and tarifa.tarifa_hora:
                costo.costo_operario = (horas * tarifa.tarifa_hora).quantize(Decimal('0.001'))
            elif tarifa and tarifa.tipo_contrato == 'pieza':
                # El costeo por pieza aún no está implementado — costo_operario queda en 0,
                # dejar constancia en logs para que no se lea como "sin costo de mano de obra".
                logger.warning(
                    f"Lote {lote_produccion.codigo_lote}: operario con tarifa tipo 'pieza' "
                    f"(tarifa_pieza={tarifa.tarifa_pieza}) — costeo por pieza no implementado, "
                    f"costo_operario queda en 0."
                )

        # 4. COSTO MÁQUINA (costo por hora vigente × horas)
        costo.costo_maquina = Decimal('0.000')
        maquina = lote_produccion.maquina or (orden.maquina_asignada if orden else None)
        if maquina and horas > 0:
            costo_hora = CostoLoteService._obtener_costo_hora_maquina(
                maquina=maquina,
                fecha=lote_produccion.hora_final.date(),
            )
            if costo_hora:
                costo.costo_maquina = (horas * costo_hora.costo_hora).quantize(Decimal('0.001'))

        # 5. TOTAL
        costo.total_costo = (
            costo.costo_materia_prima
            + costo.costo_quimicos
            + costo.costo_operario
            + costo.costo_maquina
            + costo.otros_costos
        ).quantize(Decimal('0.001'))

        costo.recalculado_en = timezone.now()
        costo._justificacion_auditoria = 'Cálculo automático de costo de producción'
        costo.save()

        logger.info(
            f'Costo calculado para {lote_produccion.codigo_lote}: ${costo.total_costo}',
            extra={'sd': {
                'entity': 'CostoLoteProduccion',
                'lote': lote_produccion.codigo_lote,
                'total': str(costo.total_costo),
                'user': getattr(usuario, 'username', 'sistema'),
            }},
        )
        return costo

    @staticmethod
    def _obtener_tarifa_operario(operario, sede, fecha):
        """Tarifa vigente a la fecha; vigente_hasta NULL = contrato abierto."""
        qs = TarifaOperario.objects.filter(
            operario=operario,
            vigente_desde__lte=fecha,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)
        )
        if sede:
            qs = qs.filter(sede=sede)
        return qs.order_by('-vigente_desde').first()

    @staticmethod
    def _obtener_costo_hora_maquina(maquina, fecha):
        """Costo/hora vigente a la fecha; vigente_hasta NULL = sin fecha fin."""
        return CostoHoraMaquina.objects.filter(
            maquina=maquina,
            vigente_desde__lte=fecha,
        ).filter(
            Q(vigente_hasta__isnull=True) | Q(vigente_hasta__gte=fecha)
        ).order_by('-vigente_desde').first()
