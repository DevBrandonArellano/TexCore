import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from gestion.models import CustomUser, LoteProduccion, Maquina
from gestion.services.consumo_mezcla import ConsumoMezclaService
from gestion.services.merma_stock import MermaStockService
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


class RegistroLoteService:
    """
    Orquesta el registro de un lote de producción.
    - Consume producto_entrada de bodega_entrada
    - Delega mezcla a ConsumoMezclaService (SRP)
    - Delega merma vendible a MermaStockService (SRP)
    - Produce producto_salida en bodega_salida
    """

    @staticmethod
    @transaction.atomic
    def registrar_lote(orden, lote_data: dict, user, completar_orden: bool = False):
        peso_neto = Decimal(str(lote_data['peso_neto_producido'])).quantize(Decimal('0.01'))
        peso_merma = Decimal(str(lote_data.get('peso_merma', 0))).quantize(Decimal('0.01'))
        consumo_total = peso_neto + peso_merma

        # Resolver maquina
        maquina = None
        maquina_id = lote_data.get('maquina')
        if maquina_id:
            try:
                maquina = Maquina.objects.get(id=maquina_id)
            except Maquina.DoesNotExist:
                raise ValidationError(
                    f'La máquina con id={maquina_id} no existe. Verifique la asignación de la OP.'
                )

        # Validar campos obligatorios de la OP
        if not getattr(orden, 'producto_entrada_id', None) and not getattr(orden, 'producto_id', None):
            raise ValidationError('La OP debe tener producto_entrada.')
        if not getattr(orden, 'bodega_entrada_id', None) and not getattr(orden, 'bodega_id', None):
            raise ValidationError('La OP debe tener bodega_entrada.')

        # Compatibilidad: si los campos aún se llaman producto/bodega usar esos
        producto_entrada = getattr(orden, 'producto_entrada', None) or getattr(orden, 'producto', None)
        bodega_entrada = getattr(orden, 'bodega_entrada', None) or getattr(orden, 'bodega', None)
        producto_salida = getattr(orden, 'producto_salida', None) or producto_entrada
        bodega_salida = getattr(orden, 'bodega_salida', None) or bodega_entrada

        # Mapear bodegas intermedias correlacionadas con la máquina
        if maquina:
            if getattr(maquina, 'bodega_entrada', None):
                bodega_entrada = maquina.bodega_entrada
            if getattr(maquina, 'bodega_salida', None):
                bodega_salida = maquina.bodega_salida

        # Código de lote
        codigo_lote = lote_data.get('codigo_lote') or orden.generate_next_lote_codigo()

        consumos_mezcla = lote_data.get('consumos')
        tiene_mezcla = bool(consumos_mezcla) and orden.componentes_mezcla.exists()

        if not tiene_mezcla:
            # Consumo simple: descuenta producto_entrada de bodega_entrada
            stock_entrada, _ = safe_get_or_create_stock(
                StockBodega, bodega_entrada, producto_entrada, lote=None
            )
            stock_entrada = StockBodega.objects.select_for_update().get(id=stock_entrada.id)
            if stock_entrada.cantidad < consumo_total:
                raise ValidationError(
                    f'Stock insuficiente en {bodega_entrada.nombre}. '
                    f'Disponible: {stock_entrada.cantidad} kg. Requerido: {consumo_total} kg.'
                )
            stock_entrada.cantidad -= consumo_total
            stock_entrada._justificacion_auditoria = f'Consumo automático OP-{orden.codigo}'
            stock_entrada.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='CONSUMO',
                producto=producto_entrada,
                bodega_origen=bodega_entrada,
                cantidad=peso_neto,
                documento_ref=f'OP-{orden.codigo}',
                usuario=user,
                saldo_resultante=stock_entrada.cantidad,
            )
            if peso_merma > 0:
                MovimientoInventario.objects.create(
                    tipo_movimiento='MERMA',
                    producto=producto_entrada,
                    bodega_origen=bodega_entrada,
                    cantidad=peso_merma,
                    documento_ref=f'MERMA-OP-{orden.codigo}',
                    usuario=user,
                    saldo_resultante=stock_entrada.cantidad,
                )

        # Resolver operario
        operario_id = lote_data.get('operario')
        operario = user
        if operario_id:
            try:
                operario = CustomUser.objects.get(id=operario_id)
            except CustomUser.DoesNotExist:
                operario = user

        # Crear LoteProduccion
        lote = LoteProduccion.objects.create(
            orden_produccion=orden,
            codigo_lote=codigo_lote,
            peso_neto_producido=peso_neto,
            peso_merma=peso_merma,
            tipo_merma=lote_data.get('tipo_merma', ''),
            clasificacion_calidad=lote_data.get('clasificacion_calidad', 'primera'),
            maquina=maquina,
            operario=operario,
            turno=lote_data.get('turno', ''),
            hora_inicio=lote_data.get('hora_inicio'),
            hora_final=lote_data.get('hora_final'),
            unidades_empaque=lote_data.get('unidades_empaque', 1),
            presentacion=lote_data.get('presentacion', 'cono'),
            peso_bruto=lote_data.get('peso_bruto', peso_neto),
            tara=lote_data.get('tara', Decimal('0')),
        )

        # Consumo de mezcla (después de crear lote para tener FK)
        if tiene_mezcla:
            ConsumoMezclaService.consumir(
                orden, lote, consumos_mezcla, user, consumo_total=consumo_total
            )

        # Merma vendible por máquina
        if maquina and peso_merma > 0:
            MermaStockService.registrar(lote, user)

        # Entrada de producto_salida en bodega_salida
        stock_salida, _ = safe_get_or_create_stock(
            StockBodega, bodega_salida, producto_salida, lote=lote
        )
        stock_salida = StockBodega.objects.select_for_update().get(id=stock_salida.id)
        stock_salida.cantidad += peso_neto
        stock_salida._justificacion_auditoria = f'Producción lote {codigo_lote}'
        stock_salida.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION',
            producto=producto_salida,
            lote=lote,
            bodega_destino=bodega_salida,
            cantidad=peso_neto,
            documento_ref=f'OP-{orden.codigo}',
            usuario=user,
            saldo_resultante=stock_salida.cantidad,
        )

        # Actualizar estado OP
        total_producido = orden.lotes.aggregate(
            total=Sum('peso_neto_producido')
        )['total'] or Decimal('0')

        if completar_orden or total_producido >= orden.peso_neto_requerido:
            orden.estado = 'finalizada'
        else:
            orden.estado = 'en_proceso'
        orden.save(update_fields=['estado'])

        logger.info(
            'Lote registrado exitosamente',
            extra={'sd': {
                'lote': codigo_lote,
                'op': orden.codigo,
                'producto_entrada': producto_entrada.codigo,
                'producto_salida': producto_salida.codigo,
                'peso_neto': str(peso_neto),
                'peso_merma': str(peso_merma),
                'tiene_mezcla': tiene_mezcla,
            }},
        )

        return lote
