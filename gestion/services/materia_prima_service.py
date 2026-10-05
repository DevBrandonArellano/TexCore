"""
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-TrazabilidadMateriaPrima (F0-001)
Patrón: Service Layer
SOLID: SRP — MateriaPrimaService gestiona entradas/consumos;
       TraceabilityService solo construye la cadena de trazabilidad.

Caso de negocio: cliente reclama defecto → responder "el lote X se produjo
con materia prima del Proveedor Y, lote Z, certificado adjunto".
"""

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from gestion.models import ConsumoMateriaPrima, LoteProduccion, MateriaPrimaLote
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger('gestion.services.materia_prima')


class MateriaPrimaService:
    """Registro de entradas de MP del proveedor y consumo en producción."""

    @staticmethod
    @transaction.atomic
    def registrar_entrada(
        proveedor,
        producto,
        lote_proveedor,
        cantidad_kg,
        costo_unitario,
        bodega_recepcion,
        fecha_recepcion,
        usuario,
        certificado=None,
        numero_documento=None,
        pais='',
        calidad='',
    ) -> MateriaPrimaLote:
        """Registra la recepción de un lote de materia prima del proveedor.

        Crea el MateriaPrimaLote, suma el stock en la bodega de recepción y
        registra el MovimientoInventario tipo COMPRA — todo atómico.
        """
        cantidad_kg = Decimal(str(cantidad_kg)).quantize(Decimal('0.001'))
        costo_unitario = Decimal(str(costo_unitario)).quantize(Decimal('0.001'))

        if cantidad_kg <= 0:
            raise ValidationError('La cantidad recibida debe ser mayor a cero.')
        if costo_unitario < 0:
            raise ValidationError('El costo unitario no puede ser negativo.')

        mp_lote = MateriaPrimaLote(
            producto=producto,
            proveedor=proveedor,
            lote_proveedor=lote_proveedor,
            cantidad_kg=cantidad_kg,
            costo_unitario=costo_unitario,
            bodega_recepcion=bodega_recepcion,
            fecha_recepcion=fecha_recepcion,
            certificado_calidad=certificado,
            numero_documento_entrada=numero_documento or '',
            sede=bodega_recepcion.sede,
        )
        mp_lote._justificacion_auditoria = f'Recepción de MP {lote_proveedor} de {proveedor.nombre}'
        mp_lote.save()

        # Stock en bodega de recepción (thread-safe)
        stock, _ = safe_get_or_create_stock(
            StockBodega,
            bodega=bodega_recepcion,
            producto=producto,
            lote=None,
        )
        stock.cantidad += cantidad_kg
        stock._justificacion_auditoria = f'Entrada MP-{lote_proveedor}'
        stock.save()

        # Kardex: movimiento COMPRA con referencia al lote del proveedor
        MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA',
            producto=producto,
            bodega_origen=None,
            bodega_destino=bodega_recepcion,
            cantidad=cantidad_kg,
            usuario=usuario,
            documento_ref=f'MP-{lote_proveedor}',
            proveedor=proveedor,
            saldo_resultante=stock.cantidad,
            materia_prima_lote=mp_lote,
            pais=pais or '',
            calidad=calidad or '',
        )

        logger.info(
            'MateriaPrimaLote %s registrada: %s (%s kg)',
            mp_lote.id,
            lote_proveedor,
            cantidad_kg,
            extra={'sd': {
                'entity': 'MateriaPrimaLote',
                'action': 'CREATE',
                'proveedor': proveedor.nombre,
                'lote_proveedor': lote_proveedor,
                'user': getattr(usuario, 'username', 'sistema'),
            }},
        )
        return mp_lote

    @staticmethod
    @transaction.atomic
    def consumir_materia_prima(lote_produccion: LoteProduccion, consumos_data: list, usuario) -> list:
        """Registra el consumo de uno o más lotes de MP en un lote producido.

        consumos_data: list[{'materia_prima_lote_id': int, 'cantidad_kg': Decimal}]
        Valida disponibilidad bajo lock pesimista; rollback total si algún
        componente no alcanza.
        """
        consumos_creados = []

        for consumo in consumos_data:
            mp_lote = MateriaPrimaLote.objects.select_for_update().get(
                id=consumo['materia_prima_lote_id']
            )
            cantidad = Decimal(str(consumo['cantidad_kg'])).quantize(Decimal('0.001'))

            if cantidad <= 0:
                raise ValidationError('La cantidad a consumir debe ser mayor a cero.')

            if mp_lote.cantidad_disponible < cantidad:
                raise ValidationError(
                    f'Stock insuficiente del lote de MP {mp_lote.lote_proveedor}. '
                    f'Disponible: {mp_lote.cantidad_disponible} kg, '
                    f'Requerido: {cantidad} kg.'
                )

            registro = ConsumoMateriaPrima.objects.create(
                lote_produccion=lote_produccion,
                materia_prima_lote=mp_lote,
                cantidad_kg=cantidad,
                porcentaje_utilizado=(cantidad / mp_lote.cantidad_kg * 100).quantize(Decimal('0.01')),
                usuario=usuario,
            )
            consumos_creados.append(registro)

            mp_lote.cantidad_consumida += cantidad
            if mp_lote.cantidad_consumida >= mp_lote.cantidad_kg:
                mp_lote.completamente_consumida = True
            mp_lote._justificacion_auditoria = f'Consumo en lote {lote_produccion.codigo_lote}'
            mp_lote.save()

            logger.info(
                'Consumo MP registrado: %s - %s kg en %s',
                mp_lote.lote_proveedor,
                cantidad,
                lote_produccion.codigo_lote,
            )

        return consumos_creados

    @staticmethod
    @transaction.atomic
    def ajustar_cantidad_recibida(mp_lote_id, nueva_cantidad, justificacion) -> MateriaPrimaLote:
        """Corrige la cantidad recibida de un lote de MP (al editar su COMPRA).
        No puede quedar por debajo de lo ya consumido en producción."""
        mp_lote = MateriaPrimaLote.objects.select_for_update().get(pk=mp_lote_id)
        if nueva_cantidad < mp_lote.cantidad_consumida:
            raise ValidationError(
                f'La cantidad recibida no puede ser menor a lo ya consumido '
                f'({mp_lote.cantidad_consumida} kg) del lote {mp_lote.lote_proveedor}.')
        mp_lote.cantidad_kg = nueva_cantidad
        mp_lote.completamente_consumida = mp_lote.cantidad_consumida >= nueva_cantidad
        mp_lote._justificacion_auditoria = justificacion
        mp_lote.save()
        return mp_lote

    @staticmethod
    @transaction.atomic
    def anular_recepcion(mp_lote_id, justificacion):
        """Elimina el lote de MP de una recepción (al borrar su COMPRA). Si ya
        se consumió en producción, la trazabilidad lo necesita: se rechaza."""
        mp_lote = MateriaPrimaLote.objects.select_for_update().get(pk=mp_lote_id)
        if mp_lote.cantidad_consumida > 0 or mp_lote.consumos.exists():
            raise ValidationError(
                f'El lote {mp_lote.lote_proveedor} ya se consumió en producción; '
                f'corrija la cantidad en lugar de eliminar la recepción.')
        mp_lote._justificacion_auditoria = justificacion
        mp_lote.delete()


class TraceabilityService:
    """Cadena completa de trazabilidad: producto final ← MP ← proveedor."""

    @staticmethod
    def obtener_cadena_completa(lote_produccion: LoteProduccion) -> dict:
        consumos = ConsumoMateriaPrima.objects.filter(
            lote_produccion=lote_produccion
        ).select_related('materia_prima_lote__proveedor', 'materia_prima_lote__producto')

        componentes = []
        costo_total = Decimal('0.000')

        for consumo in consumos:
            mp = consumo.materia_prima_lote
            costo_consumo = mp.costo_unitario * consumo.cantidad_kg
            costo_total += costo_consumo

            componentes.append({
                'materia_prima_lote': mp.lote_proveedor,
                'producto': mp.producto.descripcion,
                'proveedor': mp.proveedor.nombre,
                'cantidad_kg': float(consumo.cantidad_kg),
                'costo_unitario': float(mp.costo_unitario),
                'costo_total': float(costo_consumo),
                'certificado': mp.certificado_calidad.url if mp.certificado_calidad else None,
                'numero_documento': mp.numero_documento_entrada,
                'fecha_recepcion': mp.fecha_recepcion.isoformat(),
                'porcentaje_utilizado': float(consumo.porcentaje_utilizado or 0),
            })

        orden = lote_produccion.orden_produccion
        producto_final = (orden.producto_salida or orden.producto_entrada) if orden else None

        return {
            'lote_final': lote_produccion.codigo_lote,
            'producto_final': producto_final.descripcion if producto_final else None,
            'cantidad_producida': float(lote_produccion.peso_neto_producido),
            'componentes': componentes,
            'costo_total_materias_primas': float(costo_total),
            'fecha_produccion': lote_produccion.hora_final.isoformat() if lote_produccion.hora_final else None,
            'clasificacion_calidad': lote_produccion.clasificacion_calidad,
        }
