import logging
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from gestion.models import CustomUser, LoteProduccion, Maquina, OrdenProduccion
from gestion.services.consumo_mezcla import ConsumoMezclaService
from gestion.services.evento_etiqueta_service import EventoEtiquetaService
from gestion.services.merma_stock import MermaStockService
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


@dataclass
class _Flujo:
    """Productos y bodegas que intervienen en el registro del lote."""
    producto_entrada: object
    bodega_entrada: object
    producto_salida: object
    bodega_salida: object


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
        # Lock de la orden para serializar registros concurrentes de lotes:
        # generate_next_lote_codigo() (más abajo) lee lotes.count() sin lock;
        # sin esto, dos requests concurrentes podrían calcular el mismo código.
        OrdenProduccion.objects.select_for_update().get(pk=orden.pk)

        peso_neto = Decimal(str(lote_data['peso_neto_producido'])).quantize(Decimal('0.01'))
        peso_merma = Decimal(str(lote_data.get('peso_merma', 0))).quantize(Decimal('0.01'))
        RegistroLoteService._validar_merma(orden, peso_merma)
        consumo_total = peso_neto + peso_merma

        maquina = RegistroLoteService._resolver_maquina(orden, lote_data)
        flujo = RegistroLoteService._resolver_flujo(orden, maquina)
        codigo_lote = lote_data.get('codigo_lote') or orden.generate_next_lote_codigo()

        consumos_mezcla = lote_data.get('consumos')
        tiene_mezcla = bool(consumos_mezcla) and orden.componentes_mezcla.exists()
        RegistroLoteService._consumir_entrada_simple(orden, flujo, peso_neto, peso_merma, user, tiene_mezcla)

        operario = RegistroLoteService._resolver_operario(lote_data, user)
        lote = LoteProduccion.objects.create(
            orden_produccion=orden,
            codigo_lote=codigo_lote,
            peso_neto_producido=peso_neto,
            peso_merma=peso_merma,
            tipo_merma=lote_data.get('tipo_merma') or '',
            clasificacion_calidad=lote_data.get('clasificacion_calidad', 'primera'),
            maquina=maquina,
            operario=operario,
            turno=lote_data.get('turno', ''),
            # Obligatorias (NOT NULL): RegistrarLoteProduccionSerializer las exige.
            hora_inicio=lote_data['hora_inicio'],
            hora_final=lote_data['hora_final'],
            unidades_empaque=lote_data.get('unidades_empaque', 1),
            presentacion=lote_data.get('presentacion', 'cono'),
            peso_bruto=lote_data.get('peso_bruto', peso_neto),
            tara=lote_data.get('tara', Decimal('0')),
            cantidad_metros=lote_data.get('cantidad_metros'),
        )

        # F1: snapshot ORIGINAL v1 — ancla del historial de etiquetas del lote.
        EventoEtiquetaService.registrar_original(lote, user)

        # Consumo de mezcla (después de crear lote para tener FK)
        if tiene_mezcla and consumos_mezcla:
            ConsumoMezclaService.consumir(orden, lote, consumos_mezcla, user, consumo_total=consumo_total)

        # Merma vendible por máquina
        if maquina and peso_merma > 0:
            MermaStockService.registrar(lote, user)

        RegistroLoteService._ingresar_salida(orden, flujo, lote, peso_neto, user)
        RegistroLoteService._actualizar_estado_orden(orden, completar_orden)

        logger.info(
            'Lote registrado exitosamente',
            extra={'sd': {
                'lote': codigo_lote,
                'op': orden.codigo,
                'producto_entrada': flujo.producto_entrada.codigo if flujo.producto_entrada else 'Sin asignar',
                'producto_salida': flujo.producto_salida.codigo if flujo.producto_salida else 'Sin asignar',
                'peso_neto': str(peso_neto),
                'peso_merma': str(peso_merma),
                'tiene_mezcla': tiene_mezcla,
            }},
        )

        RegistroLoteService._sincronizar_mes(
            orden, lote, lote_data, user, operario, maquina, flujo, consumo_total)
        return lote

    @staticmethod
    def _validar_merma(orden, peso_merma):
        if (
            orden
            and getattr(orden, 'peso_neto_requerido', None)
            and peso_merma > Decimal(str(orden.peso_neto_requerido))
        ):
            raise ValidationError(
                f'La merma ({peso_merma} kg) no puede ser mayor a la cantidad requerida '
                f'en la orden ({orden.peso_neto_requerido} kg).'
            )

    @staticmethod
    def _resolver_maquina(orden, lote_data):
        """La máquina puede llegar como objeto (PrimaryKeyRelatedField) o como ID. Sin
        máquina en el payload se usa la asignada a la OP por el Jefe de Área."""
        maquina_ref = lote_data.get('maquina')
        if not maquina_ref:
            return orden.maquina_asignada
        if isinstance(maquina_ref, Maquina):
            return maquina_ref
        try:
            return Maquina.objects.get(id=maquina_ref)
        except Maquina.DoesNotExist:
            raise ValidationError(
                f'La máquina con id={maquina_ref} no existe. Verifique la asignación de la OP.'
            ) from None

    @staticmethod
    def _resolver_flujo(orden, maquina):
        # Si la OP no tiene producto_entrada (creada solo por Jefe de Planta), se asume que
        # el Jefe de Área completará los detalles después; se permite registrar el lote.
        if not orden.producto_entrada_id:
            logger.warning(
                'OP %s sin producto_entrada. El Jefe de Área debe completar los detalles.',
                orden.codigo,
            )
        producto_entrada = orden.producto_entrada
        bodega_entrada = orden.bodega_entrada
        bodega_salida = orden.bodega_salida or bodega_entrada
        # Bodegas intermedias correlacionadas con la máquina
        if maquina:
            bodega_entrada = getattr(maquina, 'bodega_entrada', None) or bodega_entrada
            bodega_salida = getattr(maquina, 'bodega_salida', None) or bodega_salida
        return _Flujo(
            producto_entrada=producto_entrada,
            bodega_entrada=bodega_entrada,
            producto_salida=orden.producto_salida or producto_entrada,
            bodega_salida=bodega_salida,
        )

    @staticmethod
    def _consumir_entrada_simple(orden, flujo, peso_neto, peso_merma, user, tiene_mezcla):
        """Descuenta producto_entrada de bodega_entrada (con mezcla consume ConsumoMezclaService).
        Ambos son opcionales en ciertos flujos (p. ej. empaquetado): sin ellos no hay
        movimiento de consumo."""
        bodega, producto = flujo.bodega_entrada, flujo.producto_entrada
        if not bodega or not producto:
            logger.warning(
                'OP %s sin bodega_entrada o producto_entrada. No se registrará movimiento de consumo.',
                orden.codigo,
            )
            return
        if tiene_mezcla:
            return
        consumo_total = peso_neto + peso_merma
        stock_entrada, _ = safe_get_or_create_stock(StockBodega, bodega, producto, lote=None)
        stock_entrada = StockBodega.objects.select_for_update().get(id=stock_entrada.id)
        if stock_entrada.cantidad < consumo_total:
            raise ValidationError(
                f'Stock insuficiente en {bodega.nombre}. '
                f'Disponible: {stock_entrada.cantidad} kg. Requerido: {consumo_total} kg.'
            )
        stock_entrada.cantidad -= consumo_total
        stock_entrada._justificacion_auditoria = f'Consumo automático OP-{orden.codigo}'
        stock_entrada.save()

        movimientos = [('CONSUMO', peso_neto, f'OP-{orden.codigo}')]
        if peso_merma > 0:
            movimientos.append(('MERMA', peso_merma, f'MERMA-OP-{orden.codigo}'))
        for tipo, cantidad, documento_ref in movimientos:
            MovimientoInventario.objects.create(
                tipo_movimiento=tipo,
                producto=producto,
                bodega_origen=bodega,
                cantidad=cantidad,
                documento_ref=documento_ref,
                usuario=user,
                saldo_resultante=stock_entrada.cantidad,
            )

    @staticmethod
    def _resolver_operario(lote_data, user):
        operario_id = lote_data.get('operario')
        if not operario_id:
            return user
        try:
            return CustomUser.objects.get(id=operario_id)
        except CustomUser.DoesNotExist:
            return user

    @staticmethod
    def _ingresar_salida(orden, flujo, lote, peso_neto, user):
        """Entrada de producto_salida en bodega_salida (si existen ambos)."""
        bodega, producto = flujo.bodega_salida, flujo.producto_salida
        if not bodega or not producto:
            logger.warning(
                'OP %s sin bodega_salida o producto_salida. Lote %s registrado sin actualizar stock.',
                orden.codigo,
                lote.codigo_lote,
            )
            return
        stock_salida, _ = safe_get_or_create_stock(StockBodega, bodega, producto, lote=lote)
        stock_salida = StockBodega.objects.select_for_update().get(id=stock_salida.id)
        stock_salida.cantidad += peso_neto
        stock_salida._justificacion_auditoria = f'Producción lote {lote.codigo_lote}'
        stock_salida.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION',
            producto=producto,
            lote=lote,
            bodega_destino=bodega,
            cantidad=peso_neto,
            documento_ref=f'OP-{orden.codigo}',
            usuario=user,
            saldo_resultante=stock_salida.cantidad,
        )

    @staticmethod
    def _actualizar_estado_orden(orden, completar_orden):
        total_producido = orden.lotes.aggregate(total=Sum('peso_neto_producido'))['total'] or Decimal('0')
        # Sin peso requerido (producción continua) solo se finaliza a pedido explícito
        requerido = orden.peso_neto_requerido
        if completar_orden or (requerido is not None and total_producido >= requerido):
            orden.estado = 'finalizada'
        else:
            orden.estado = 'en_proceso'
        orden.save(update_fields=['estado'])

    @staticmethod
    def _sincronizar_mes(orden, lote, lote_data, user, operario, maquina, flujo, consumo_total):
        """Sincronización transparente con el motor unificado MES (Nivel 3).

        Best-effort: corre en su propio savepoint; un fallo se registra y no revierte el
        lote (sin savepoint, un error de BD aquí dejaba inservible la transacción)."""
        try:
            with transaction.atomic():
                area = RegistroLoteService._area_de_la_orden(orden)
                if not (area and orden.sede):
                    return
                corrida = RegistroLoteService._corrida_de_la_orden(orden, area, maquina, lote_data, user)

                # OperacionProduccion exige máquina y operario. Sin ellos no hay operación MES
                # (ni avance del plan MTS, que se calcula sobre ella), pero el lote sí debe
                # reservarse para su pedido: antes la reserva quedaba en el mismo bloque y se
                # perdía en silencio cuando fallaba la creación de la operación.
                operario_mes = operario if getattr(operario, 'is_authenticated', False) else None
                operacion = None
                if maquina is None or operario_mes is None:
                    logger.warning(
                        'Lote %s registrado sin máquina u operario: no se crea la operación MES '
                        'ni se actualiza el avance del plan.',
                        lote.codigo_lote,
                    )
                else:
                    operacion = RegistroLoteService._crear_operacion_mes(
                        orden, corrida, lote, lote_data, maquina, operario_mes, flujo, consumo_total)

                # Si la orden era bajo pedido (MTO), reservar lote
                if orden.pedido_venta:
                    from inventory.services.reserva_service import ReservaService
                    ReservaService.reservar_lote_para_pedido(
                        lote=lote,
                        pedido=orden.pedido_venta,
                        detalle_pedido=orden.detalle_pedido,
                        cantidad=lote.peso_neto_producido,
                        user=user,
                    )

                # Si la orden era contra stock (MTS), actualizar avance
                if orden.plan_produccion and operacion is not None:
                    from inventory.services.reposicion_service import ReposicionService
                    ReposicionService.actualizar_avance_plan(operacion)

        except Exception as err:
            logger.warning(
                'Error sincronizando lote %s con motor MES: %s',
                lote.codigo_lote,
                err,
                exc_info=True,
            )

    @staticmethod
    def _area_de_la_orden(orden):
        from gestion.models import Area

        if orden.area or not orden.sede:
            return orden.area
        area = Area.objects.filter(sede=orden.sede).first()
        if not area:
            area, _ = Area.objects.get_or_create(sede=orden.sede, defaults={'nombre': 'Área General'})
        return area

    @staticmethod
    def _corrida_de_la_orden(orden, area, maquina, lote_data, user):
        from gestion.models import CorridaProduccion

        modalidad = 'STOCK' if orden.plan_produccion else ('PEDIDO' if orden.pedido_venta else 'CONTINUA')
        corrida, _ = CorridaProduccion.objects.get_or_create(
            orden_produccion=orden,
            estado='en_proceso',
            defaults={
                'codigo': f"CORR-OP-{orden.codigo}",
                'sede': orden.sede,
                'area': area,
                'maquina_principal': maquina,
                'modalidad': modalidad,
                'plan_produccion': orden.plan_produccion,
                'detalle_plan': orden.detalle_plan,
                'pedido_venta': orden.pedido_venta,
                'turno': lote_data.get('turno') or 'General',
                'fecha_jornada': timezone.now().date(),
                'hora_inicio': timezone.now(),
                'supervisor': user if getattr(user, 'is_authenticated', False) else None,
            }
        )
        return corrida

    @staticmethod
    def _crear_operacion_mes(orden, corrida, lote, lote_data, maquina, operario, flujo, consumo_total):
        from gestion.models import ConsumoMaterial, MermaDesperdicio, OperacionProduccion, ProduccionSalida

        operacion = OperacionProduccion.objects.create(
            corrida=corrida,
            numero_secuencia=corrida.operaciones.count() + 1,
            maquina=maquina,
            operario=operario,
            hora_inicio=lote.hora_inicio or timezone.now(),
            hora_fin=lote.hora_final or timezone.now(),
            estado='completada',
            observaciones=f"Registro de lote {lote.codigo_lote} vía OP {orden.codigo}",
        )
        if flujo.producto_entrada and flujo.bodega_entrada:
            ConsumoMaterial.objects.create(
                operacion=operacion,
                producto=flujo.producto_entrada,
                bodega_origen=flujo.bodega_entrada,
                cantidad_consumida=consumo_total,
            )
        if flujo.producto_salida and flujo.bodega_salida:
            ProduccionSalida.objects.create(
                operacion=operacion,
                lote_generado=lote,
                producto=flujo.producto_salida,
                bodega_destino=flujo.bodega_salida,
                cantidad_neta=lote.peso_neto_producido,
                clasificacion_calidad=lote.clasificacion_calidad or 'primera',
                peso_bruto=lote.peso_bruto,
                tara=lote.tara,
                unidades_empaque=lote.unidades_empaque,
                cantidad_metros=lote.cantidad_metros,
            )
        if lote.peso_merma > 0:
            producto_merma = getattr(maquina, 'producto_merma', None)
            MermaDesperdicio.objects.create(
                operacion=operacion,
                peso_merma=lote.peso_merma,
                tipo_merma=lote_data.get('tipo_merma') or 'maquina',
                es_subproducto_vendible=bool(producto_merma),
                producto_subproducto=producto_merma,
                bodega_subproducto=getattr(maquina, 'bodega_merma', None),
            )
        return operacion
