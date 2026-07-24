"""
TrazabilidadService — reconstruye el flujo completo de producción de una OP.

Arma la cadena de transformaciones (máquina a máquina) con su merma por paso y
acumulada, y enlaza a la OP de la siguiente área vía TransferenciaInterarea para
reconstruir el recorrido del producto a través de toda la planta.

SRP: única responsabilidad — consultar y estructurar la trazabilidad (solo
lectura). No modifica estado.
"""
from decimal import Decimal

from gestion.models import TransferenciaInterarea

_CERO = Decimal('0.000')
_CERO_PCT = Decimal('0.00')


class TrazabilidadService:
    """Servicio de lectura que estructura la trazabilidad de una OP."""

    @staticmethod
    def construir(orden, profundidad: int = 5, _visitadas=None) -> dict:
        """
        Devuelve un dict con los pasos de transformación, mermas y el enlace a la
        siguiente área. ``profundidad`` acota la recursión entre áreas y
        ``_visitadas`` corta ciclos en cadenas mal configuradas (defensa en
        profundidad). Solo se consideran transformaciones COMPLETADAS: las
        rechazadas son intentos fallidos y no forman parte del flujo válido.
        """
        if _visitadas is None:
            _visitadas = set()
        _visitadas.add(orden.id)

        transformaciones = list(
            orden.transformaciones
            .filter(estado='completada')
            .select_related('producto_entrada', 'producto_salida', 'maquina', 'operario')
            .order_by('numero_secuencia')
        )

        pasos = [TrazabilidadService._serializar_paso(t) for t in transformaciones]

        merma_total = sum((t.merma for t in transformaciones), _CERO).quantize(Decimal('0.001'))

        peso_inicial = transformaciones[0].peso_entrada if transformaciones else _CERO
        peso_final = transformaciones[-1].peso_salida if transformaciones else _CERO

        if peso_inicial > 0:
            merma_porcentaje = (merma_total / peso_inicial * Decimal('100')).quantize(Decimal('0.01'))
        else:
            merma_porcentaje = _CERO_PCT

        return {
            'orden_codigo': orden.codigo,
            'orden_id': orden.id,
            'area': orden.area.nombre if orden.area else None,
            'sede_id': orden.sede_id,
            'producto_inicial': TrazabilidadService._producto_dict(
                transformaciones[0].producto_entrada if transformaciones else orden.producto_entrada
            ),
            'producto_final': TrazabilidadService._producto_dict(
                transformaciones[-1].producto_salida if transformaciones else orden.producto_salida
            ),
            'peso_inicial': peso_inicial,
            'peso_final': peso_final,
            'merma_total': merma_total,
            'merma_porcentaje': merma_porcentaje,
            'pasos': pasos,
            'siguiente': TrazabilidadService._siguiente(orden, profundidad, _visitadas),
        }

    # ----------------------------------------------------------------- helpers

    @staticmethod
    def _siguiente(orden, profundidad, visitadas):
        """Encadena con la OP de la siguiente área vía TransferenciaInterarea.

        Corta si se agota la profundidad o si la siguiente OP ya fue visitada
        (evita recursión infinita ante transferencias circulares).
        """
        if profundidad <= 0:
            return None
        transferencia = (
            TransferenciaInterarea.objects
            .filter(orden_area_origen=orden)
            .exclude(orden_area_destino_id__in=visitadas)
            .select_related('orden_area_destino')
            .order_by('-fecha_transferencia')
            .first()
        )
        if not transferencia:
            return None
        return TrazabilidadService.construir(
            transferencia.orden_area_destino, profundidad=profundidad - 1, _visitadas=visitadas
        )

    @staticmethod
    def _serializar_paso(t):
        return {
            'numero_secuencia': t.numero_secuencia,
            'producto_entrada': TrazabilidadService._producto_dict(t.producto_entrada),
            'producto_salida': TrazabilidadService._producto_dict(t.producto_salida),
            'maquina': t.maquina.nombre if t.maquina else None,
            'operario': t.operario.get_full_name() or t.operario.username if t.operario else None,
            'peso_entrada': t.peso_entrada,
            'peso_salida': t.peso_salida,
            'merma': t.merma,
            'estado': t.estado,
            'fecha_inicio': t.fecha_inicio,
            'fecha_fin': t.fecha_fin,
            'observaciones': t.observaciones,
        }

    @staticmethod
    def _producto_dict(producto):
        if not producto:
            return None
        return {'id': producto.id, 'codigo': producto.codigo, 'descripcion': producto.descripcion}
