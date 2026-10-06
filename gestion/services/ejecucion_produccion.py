import logging
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from gestion.models import (
    Bodega,
    ConsumoMaterial,
    CorridaProduccion,
    CustomUser,
    GenealogiaLote,
    LoteProduccion,
    Maquina,
    MermaDesperdicio,
    OperacionProduccion,
    ProcessStep,
    ProduccionSalida,
    Producto,
)
from gestion.services.evento_etiqueta_service import EventoEtiquetaService
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


def _crear_movimiento_inventario(**kwargs):
    justificacion = kwargs.pop('_justificacion_auditoria', None)
    mov = MovimientoInventario(**kwargs)
    if justificacion:
        mov._justificacion_auditoria = justificacion
    mov.save()
    return mov


def _kg(valor) -> Decimal:
    return Decimal(str(valor)).quantize(Decimal('0.001'))


def _total(items, campo) -> Decimal:
    return sum((_kg(item[campo]) for item in items), Decimal('0'))


def _instancia(valor, modelo):
    """El payload admite la instancia o su ID; un ID inexistente propaga DoesNotExist."""
    return modelo.objects.get(pk=valor) if isinstance(valor, (int, str)) else valor


def _instancia_opcional(valor, modelo):
    return _instancia(valor, modelo) if valor else valor


def _por_pk(valor, modelo, mensaje_no_existe):
    """Como _instancia, pero un ID inexistente es un error de validación con mensaje propio."""
    try:
        return _instancia(valor, modelo)
    except modelo.DoesNotExist:
        raise ValidationError(mensaje_no_existe) from None


@dataclass
class _ContextoOperacion:
    corrida: CorridaProduccion
    operacion: OperacionProduccion
    maquina: Maquina
    operario: CustomUser
    usuario: CustomUser  # quien firma los movimientos: el usuario o, en su defecto, el operario
    justificacion: str

    def documento_ref(self, prefijo: str) -> str:
        return f"{prefijo}-{self.corrida.codigo}-OP-{self.operacion.numero_secuencia}"


class EjecucionProduccionService:
    """
    Motor Unificado de Ejecución de Manufactura (MES - Nivel 3).
    Orquesta atómicamente la ejecución de operaciones productivas en máquina:
    - Validación rigurosa de balance de masa (Entradas = Salidas Netas + Mermas).
    - Bloqueo pesimista con SELECT FOR UPDATE sobre saldos de StockBodega.
    - Emisión coherente de movimientos Kardex (CONSUMO, PRODUCCION, MERMA).
    - Construcción automática del Grafo Acíclico Dirigido (DAG) en GenealogiaLote.
    - Reversión atómica con contrasientos y salvaguardas contra consumo posterior.
    """

    @classmethod
    @transaction.atomic
    def registrar_operacion(
        cls,
        corrida: CorridaProduccion,
        operacion_data: dict,
        consumos_data: list,
        salidas_data: list,
        mermas_data: list | None = None,
        user=None,
        justificacion: str | None = None,
        tolerancia_balance: Decimal = Decimal('0.050'),
        validar_balance_masa: bool = True,
    ) -> OperacionProduccion:
        """
        Registra un paso unitario de transformación en máquina dentro de una corrida.
        """
        if mermas_data is None:
            mermas_data = []

        corrida = cls._bloquear_corrida_abierta(corrida)
        # 1. Resolver y validar operador y máquina
        maquina, operario, proceso = cls._resolver_recursos(corrida, operacion_data, user)
        # 2. Secuencia de la operación
        numero_secuencia = cls._siguiente_secuencia(corrida, operacion_data)
        # 3. Validación de Balance de Masa
        total_salidas = cls._validar_balance_masa(
            consumos_data, salidas_data, mermas_data, tolerancia_balance, validar_balance_masa)

        # 4. Crear entidad de OperacionProduccion
        operacion = OperacionProduccion.objects.create(
            corrida=corrida,
            numero_secuencia=numero_secuencia,
            maquina=maquina,
            proceso=proceso,
            operario=operario,
            hora_inicio=operacion_data.get('hora_inicio') or timezone.now(),
            hora_fin=operacion_data.get('hora_fin') or timezone.now(),
            estado=operacion_data.get('estado', 'completada'),
            observaciones=operacion_data.get('observaciones', ''),
        )
        ctx = _ContextoOperacion(
            corrida=corrida,
            operacion=operacion,
            maquina=maquina,
            operario=operario,
            usuario=user or operario,
            justificacion=justificacion or f"Operación #{numero_secuencia} en Corrida {corrida.codigo}",
        )

        # 5. Consumos de material, 6. salidas de producción y 7. mermas y subproductos
        consumos_creados = [cls._consumir_material(ctx, c_data) for c_data in consumos_data]
        salidas_creadas = [cls._registrar_salida(ctx, s_data) for s_data in salidas_data]
        for m_data in mermas_data:
            cls._registrar_merma(ctx, m_data, consumos_creados)

        # 8. Construcción del Grafo DAG en GenealogiaLote
        cls._construir_genealogia(operacion, consumos_creados, salidas_creadas, total_salidas)
        # 9. Actualización condicional del estado de OrdenProduccion si aplica
        cls._actualizar_estado_orden(corrida)

        # 10. Actualización de avance en Plan de Producción (MTS) si aplica
        from inventory.services.reposicion_service import ReposicionService
        ReposicionService.actualizar_avance_plan(operacion)

        # 11. Reserva inmutable para Pedido Comercial (MTO) si aplica
        cls._reservar_para_pedido(ctx, salidas_creadas)

        logger.info(
            'Operación #%s registrada exitosamente en Corrida %s. Consumos=%s, Salidas=%s, Mermas=%s',
            operacion.numero_secuencia,
            corrida.codigo,
            len(consumos_creados),
            len(salidas_creadas),
            len(mermas_data),
        )
        return operacion

    @staticmethod
    def _bloquear_corrida_abierta(corrida):
        if not corrida or not corrida.pk:
            raise ValidationError("Se requiere una corrida de producción válida.")
        # Lock pesimista sobre la corrida para serializar operaciones concurrentes
        corrida = CorridaProduccion.objects.select_for_update().get(pk=corrida.pk)
        if corrida.estado in ('finalizada', 'anulada'):
            raise ValidationError(
                f"No se pueden registrar operaciones en una corrida con estado '{corrida.estado}'."
            )
        return corrida

    @staticmethod
    def _resolver_recursos(corrida, operacion_data, user):
        """(maquina, operario, proceso); cada uno puede llegar como instancia o como ID."""
        maquina = operacion_data.get('maquina') or corrida.maquina_principal
        if not maquina:
            raise ValidationError("Se requiere una máquina para la operación de producción.")
        maquina = _por_pk(maquina, Maquina, f"La máquina con ID {maquina} no existe.")

        operario = operacion_data.get('operario') or user
        if not operario:
            raise ValidationError("Se requiere un operario responsable para la operación.")
        operario = _por_pk(operario, CustomUser, f"El usuario operario con ID {operario} no existe.")

        proceso = operacion_data.get('proceso')
        if proceso:
            proceso = _por_pk(proceso, ProcessStep, f"El proceso con ID {proceso} no existe.")
        return maquina, operario, proceso

    @staticmethod
    def _siguiente_secuencia(corrida, operacion_data):
        numero_secuencia = operacion_data.get('numero_secuencia')
        if numero_secuencia:
            return numero_secuencia
        max_sec = corrida.operaciones.aggregate(models.Max('numero_secuencia'))['numero_secuencia__max'] or 0
        return max_sec + 1

    @staticmethod
    def _validar_balance_masa(consumos_data, salidas_data, mermas_data, tolerancia_balance, validar):
        """Entradas = Salidas netas + Mermas, dentro de la tolerancia. Devuelve el total de salidas."""
        total_entradas = _total(consumos_data, 'cantidad_consumida')
        total_salidas = _total(salidas_data, 'cantidad_neta')
        total_mermas = _total(mermas_data, 'peso_merma')
        total_salidas_mermas = total_salidas + total_mermas

        if validar and consumos_data and (salidas_data or mermas_data):
            diferencia = abs(total_entradas - total_salidas_mermas)
            if diferencia > tolerancia_balance:
                raise ValidationError(
                    f"Desbalance de masa detectado: Entradas={total_entradas} kg != "
                    f"Salidas={total_salidas} kg + Mermas={total_mermas} kg (Total={total_salidas_mermas} kg). "
                    f"Diferencia de {diferencia} kg excede la tolerancia permitida ({tolerancia_balance} kg)."
                )
        return total_salidas

    @staticmethod
    def _consumir_material(ctx, c_data):
        producto = _instancia(c_data.get('producto') or c_data.get('producto_id'), Producto)
        bodega = _instancia(c_data.get('bodega_origen') or c_data.get('bodega_origen_id'), Bodega)
        cantidad_consumo = _kg(c_data['cantidad_consumida'])
        costo_unit = _kg(c_data.get('costo_unitario', 0))
        lote_origen = _instancia_opcional(c_data.get('lote_origen') or c_data.get('lote_origen_id'), LoteProduccion)

        # Lock pesimista sobre el stock de origen
        stock_row = StockBodega.objects.select_for_update().filter(
            bodega=bodega,
            producto=producto,
            lote=lote_origen,
        ).first()
        lote_desc = f" (Lote: {lote_origen.codigo_lote})" if lote_origen else ""
        if not stock_row:
            raise ValidationError(
                f"No existe stock registrado para el producto {producto.codigo} "
                f"en la bodega {bodega.nombre}{lote_desc}."
            )
        if stock_row.cantidad < cantidad_consumo:
            raise ValidationError(
                f"Stock insuficiente en {bodega.nombre} para {producto.codigo}{lote_desc}. "
                f"Disponible: {stock_row.cantidad} kg, Requerido: {cantidad_consumo} kg."
            )

        stock_row.cantidad -= cantidad_consumo
        stock_row._justificacion_auditoria = ctx.justificacion
        stock_row.save()

        _crear_movimiento_inventario(
            tipo_movimiento='CONSUMO',
            producto=producto,
            lote=lote_origen,
            bodega_origen=bodega,
            cantidad=cantidad_consumo,
            saldo_resultante=stock_row.cantidad,
            usuario=ctx.usuario,
            documento_ref=ctx.documento_ref('CORRIDA'),
            _justificacion_auditoria=ctx.justificacion,
        )
        return ConsumoMaterial.objects.create(
            operacion=ctx.operacion,
            lote_origen=lote_origen,
            producto=producto,
            bodega_origen=bodega,
            cantidad_consumida=cantidad_consumo,
            costo_unitario=costo_unit,
        )

    @classmethod
    def _registrar_salida(cls, ctx, s_data):
        producto_salida = _instancia(s_data.get('producto') or s_data.get('producto_id'), Producto)
        bodega_destino = _instancia(s_data.get('bodega_destino') or s_data.get('bodega_destino_id'), Bodega)
        cantidad_neta = _kg(s_data['cantidad_neta'])
        datos_lote = {
            'clasificacion_calidad': s_data.get('clasificacion_calidad', 'primera'),
            'peso_bruto': _kg(s_data.get('peso_bruto', cantidad_neta)),
            'tara': _kg(s_data.get('tara', 0)),
            'unidades_empaque': int(s_data.get('unidades_empaque', 1)),
            'cantidad_metros': (
                Decimal(str(s_data['cantidad_metros'])).quantize(Decimal('0.0001'))
                if s_data.get('cantidad_metros') is not None
                else None
            ),
        }

        lote_generado = _instancia_opcional(
            s_data.get('lote_generado') or s_data.get('lote_generado_id'), LoteProduccion)
        if not lote_generado:
            lote_generado = cls._crear_lote_generado(
                ctx, s_data, producto_salida, cantidad_neta, datos_lote)

        # Entrada a StockBodega de destino con safe_get_or_create_stock
        stock_salida, _ = safe_get_or_create_stock(
            StockBodega,
            bodega=bodega_destino,
            producto=producto_salida,
            lote=lote_generado,
        )
        stock_salida = StockBodega.objects.select_for_update().get(pk=stock_salida.pk)
        stock_salida.cantidad += cantidad_neta
        stock_salida._justificacion_auditoria = ctx.justificacion
        stock_salida.save()

        _crear_movimiento_inventario(
            tipo_movimiento='PRODUCCION',
            producto=producto_salida,
            lote=lote_generado,
            bodega_destino=bodega_destino,
            cantidad=cantidad_neta,
            saldo_resultante=stock_salida.cantidad,
            usuario=ctx.usuario,
            documento_ref=ctx.documento_ref('CORRIDA'),
            _justificacion_auditoria=ctx.justificacion,
        )
        return ProduccionSalida.objects.create(
            operacion=ctx.operacion,
            lote_generado=lote_generado,
            producto=producto_salida,
            bodega_destino=bodega_destino,
            cantidad_neta=cantidad_neta,
            **datos_lote,
        )

    @staticmethod
    def _crear_lote_generado(ctx, s_data, producto_salida, cantidad_neta, datos_lote):
        corrida = ctx.corrida
        codigo_lote = s_data.get('codigo_lote')
        if not codigo_lote:
            if corrida.orden_produccion:
                codigo_lote = corrida.orden_produccion.generate_next_lote_codigo()
            else:
                correlativo = LoteProduccion.objects.filter(
                    codigo_lote__startswith=f"{corrida.codigo}-L"
                ).count() + 1
                codigo_lote = f"{corrida.codigo}-L{correlativo}"

        lote_generado = LoteProduccion.objects.create(
            orden_produccion=corrida.orden_produccion,
            producto=producto_salida,
            codigo_lote=codigo_lote,
            peso_neto_producido=cantidad_neta,
            operario=ctx.operario,
            maquina=ctx.maquina,
            turno=corrida.turno,
            hora_inicio=ctx.operacion.hora_inicio,
            hora_final=ctx.operacion.hora_fin or timezone.now(),
            presentacion=s_data.get('presentacion', 'cono'),
            **datos_lote,
        )
        # Snapshot inicial del código de barras
        EventoEtiquetaService.registrar_original(lote_generado, ctx.usuario)
        return lote_generado

    @staticmethod
    def _registrar_merma(ctx, m_data, consumos_creados):
        peso_merma = _kg(m_data['peso_merma'])
        if peso_merma <= Decimal('0.000'):
            return

        es_subproducto = bool(m_data.get('es_subproducto_vendible', False))
        prod_sub = m_data.get('producto_subproducto') or m_data.get('producto_subproducto_id')
        bod_sub = m_data.get('bodega_subproducto') or m_data.get('bodega_subproducto_id')
        lote_sub = m_data.get('lote_subproducto') or m_data.get('lote_subproducto_id')

        if es_subproducto:
            prod_sub = _instancia_opcional(prod_sub, Producto)
            bod_sub = _instancia_opcional(bod_sub, Bodega)
            lote_sub = _instancia_opcional(lote_sub, LoteProduccion)
            if not prod_sub or not bod_sub:
                raise ValidationError(
                    "Para mermas vendibles debe especificar 'producto_subproducto' y 'bodega_subproducto'."
                )

            stock_sub, _ = safe_get_or_create_stock(
                StockBodega,
                bodega=bod_sub,
                producto=prod_sub,
                lote=lote_sub,
            )
            stock_sub = StockBodega.objects.select_for_update().get(pk=stock_sub.pk)
            stock_sub.cantidad += peso_merma
            stock_sub._justificacion_auditoria = ctx.justificacion
            stock_sub.save()

            _crear_movimiento_inventario(
                tipo_movimiento='PRODUCCION',
                producto=prod_sub,
                lote=lote_sub,
                bodega_destino=bod_sub,
                cantidad=peso_merma,
                saldo_resultante=stock_sub.cantidad,
                usuario=ctx.usuario,
                documento_ref=ctx.documento_ref('SUBPRODUCTO-CORRIDA'),
                _justificacion_auditoria=ctx.justificacion,
            )
        elif consumos_creados:
            # Merma estándar: reflejar salida en Kardex desde el primer insumo consumido
            c_ref = consumos_creados[0]
            _crear_movimiento_inventario(
                tipo_movimiento='MERMA',
                producto=c_ref.producto,
                lote=c_ref.lote_origen,
                bodega_origen=c_ref.bodega_origen,
                cantidad=peso_merma,
                saldo_resultante=Decimal('0.000'),
                usuario=ctx.usuario,
                documento_ref=ctx.documento_ref('MERMA-CORRIDA'),
                _justificacion_auditoria=ctx.justificacion,
            )

        MermaDesperdicio.objects.create(
            operacion=ctx.operacion,
            peso_merma=peso_merma,
            tipo_merma=m_data.get('tipo_merma', 'maquina'),
            es_subproducto_vendible=es_subproducto,
            producto_subproducto=prod_sub,
            bodega_subproducto=bod_sub,
            lote_subproducto=lote_sub,
        )

    @staticmethod
    def _construir_genealogia(operacion, consumos_creados, salidas_creadas, total_salidas):
        """Arista lote_padre → lote_hijo por cada par consumo/salida con lote, repartiendo el
        consumo en proporción a la cantidad neta de cada salida."""
        for salida in salidas_creadas:
            for consumo in consumos_creados:
                if not (consumo.lote_origen and salida.lote_generado):
                    continue
                if consumo.lote_origen_id == salida.lote_generado_id:
                    continue  # Prevenir ciclo reflexivo

                # total_salidas > 0: el modelo exige cantidad_neta > 0 en cada salida.
                proporcion = salida.cantidad_neta / total_salidas
                cant_usada = max((consumo.cantidad_consumida * proporcion).quantize(Decimal('0.001')), Decimal('0.001'))

                GenealogiaLote.objects.create(
                    lote_padre=consumo.lote_origen,
                    lote_hijo=salida.lote_generado,
                    operacion=operacion,
                    cantidad_padre_usada=cant_usada,
                )

    @staticmethod
    def _actualizar_estado_orden(corrida):
        op = corrida.orden_produccion
        if not op:
            return
        total_producido = op.lotes.aggregate(total=models.Sum('peso_neto_producido'))['total'] or Decimal('0.00')
        if op.peso_neto_requerido and total_producido >= op.peso_neto_requerido:
            op.estado = 'finalizada'
        else:
            op.estado = 'en_proceso'
        op.save(update_fields=['estado'])

    @staticmethod
    def _reservar_para_pedido(ctx, salidas_creadas):
        orden = ctx.corrida.orden_produccion
        pedido_mto = ctx.corrida.pedido_venta or (orden.pedido_venta if orden else None)
        if not pedido_mto:
            return
        from inventory.services.reserva_service import ReservaService
        for salida in salidas_creadas:
            if salida.lote_generado and salida.clasificacion_calidad == 'primera':
                ReservaService.reservar_lote_para_pedido(
                    lote=salida.lote_generado,
                    pedido=pedido_mto,
                    detalle_pedido=orden.detalle_pedido if orden else None,
                    cantidad=salida.cantidad_neta,
                    user=ctx.usuario,
                )

    @classmethod
    @transaction.atomic
    def revertir_operacion(cls, operacion: OperacionProduccion, user, justificacion: str) -> OperacionProduccion:
        """
        Revierte atómicamente una operación de producción:
        - Verifica que los lotes producidos no hayan sido ya consumidos o despachados.
        - Genera contrasientos de inventario (AJUSTE/DEVOLUCION) restaurando saldos.
        - Elimina las aristas de genealogía asociadas a esta operación.
        - Marca la operación con estado 'revertida' y guarda el motivo de auditoría.
        """
        if not operacion or not operacion.pk:
            raise ValidationError("Se requiere una operación válida para revertir.")

        operacion = OperacionProduccion.objects.select_for_update().get(pk=operacion.pk)
        if operacion.estado == 'revertida':
            raise ValidationError("Esta operación ya ha sido revertida.")

        if not justificacion or not str(justificacion).strip():
            raise ValidationError("Se requiere una justificación explícita para revertir la operación.")

        justificacion = justificacion.strip()
        reversion_ref = f"REVERSION-OP-{operacion.id}"

        # 1. Validar que ninguna salida haya sido utilizada en operaciones posteriores
        for salida in operacion.salidas.select_related('lote_generado', 'producto', 'bodega_destino'):
            lote = salida.lote_generado

            # Verificar si el lote ya tiene descendientes en GenealogiaLote
            if GenealogiaLote.objects.filter(lote_padre=lote).exists():
                raise ValidationError(
                    f"No se puede revertir la operación: el lote producido {lote.codigo_lote} "
                    f"ya fue transformado en operaciones productivas posteriores."
                )

            # Verificar saldo disponible en la bodega de destino
            stock = StockBodega.objects.select_for_update().filter(
                bodega=salida.bodega_destino,
                producto=salida.producto,
                lote=lote,
            ).first()

            if not stock or stock.cantidad < salida.cantidad_neta:
                saldo_disp = stock.cantidad if stock else Decimal('0.000')
                raise ValidationError(
                    f"No se puede revertir la operación: el stock del lote {lote.codigo_lote} "
                    f"en {salida.bodega_destino.nombre} ({saldo_disp} kg) es menor a la "
                    f"cantidad producida originalmente ({salida.cantidad_neta} kg). "
                    f"Parte del lote ya fue transferida o despachada."
                )

        # 1.5. Liberar reservas MTO de los lotes generados si aplica (antes de restar saldo)
        from inventory.services.reserva_service import ReservaService
        for salida in operacion.salidas.select_related('lote_generado').all():
            if salida.lote_generado and salida.lote_generado.pedido_venta_reserva:
                ReservaService.liberar_reserva_lote(
                    lote=salida.lote_generado,
                    user=user,
                    justificacion=justificacion,
                )

        # 2. Descontar las salidas netas de StockBodega y emitir AJUSTE
        for salida in operacion.salidas.select_related('lote_generado', 'producto', 'bodega_destino'):
            stock = StockBodega.objects.select_for_update().get(
                bodega=salida.bodega_destino,
                producto=salida.producto,
                lote=salida.lote_generado,
            )
            stock.cantidad -= salida.cantidad_neta
            stock._justificacion_auditoria = f"Reversión de Op #{operacion.numero_secuencia}: {justificacion}"
            stock.save()

            _crear_movimiento_inventario(
                tipo_movimiento='AJUSTE',
                producto=salida.producto,
                lote=salida.lote_generado,
                bodega_origen=salida.bodega_destino,
                cantidad=salida.cantidad_neta,
                saldo_resultante=stock.cantidad,
                usuario=user,
                documento_ref=reversion_ref,
                _justificacion_auditoria=f"Reversión de Op #{operacion.numero_secuencia}: {justificacion}",
            )

        # 3. Restaurar consumos en StockBodega de origen y emitir DEVOLUCION
        for consumo in operacion.consumos.select_related('lote_origen', 'producto', 'bodega_origen'):
            # safe_get_or_create_stock ya devuelve la fila bloqueada (select_for_update).
            stock_origen, _ = safe_get_or_create_stock(
                StockBodega,
                bodega=consumo.bodega_origen,
                producto=consumo.producto,
                lote=consumo.lote_origen,
            )
            stock_origen.cantidad += consumo.cantidad_consumida
            stock_origen._justificacion_auditoria = f"Reversión de Op #{operacion.numero_secuencia}: {justificacion}"
            stock_origen.save()

            _crear_movimiento_inventario(
                tipo_movimiento='DEVOLUCION',
                producto=consumo.producto,
                lote=consumo.lote_origen,
                bodega_destino=consumo.bodega_origen,
                cantidad=consumo.cantidad_consumida,
                saldo_resultante=stock_origen.cantidad,
                usuario=user,
                documento_ref=reversion_ref,
                _justificacion_auditoria=f"Reversión de Op #{operacion.numero_secuencia}: {justificacion}",
            )

        # 4. Revertir subproductos vendibles si existían
        for merma in operacion.mermas.filter(es_subproducto_vendible=True):
            stock = StockBodega.objects.select_for_update().filter(
                bodega=merma.bodega_subproducto,
                producto=merma.producto_subproducto,
                lote=merma.lote_subproducto,
            ).first()

            if stock and stock.cantidad >= merma.peso_merma:
                stock.cantidad -= merma.peso_merma
                stock._justificacion_auditoria = (
                    f"Reversión Subproducto Op #{operacion.numero_secuencia}: {justificacion}")
                stock.save()

                _crear_movimiento_inventario(
                    tipo_movimiento='AJUSTE',
                    producto=merma.producto_subproducto,
                    lote=merma.lote_subproducto,
                    bodega_origen=merma.bodega_subproducto,
                    cantidad=merma.peso_merma,
                    saldo_resultante=stock.cantidad,
                    usuario=user,
                    documento_ref=reversion_ref,
                    _justificacion_auditoria=f"Reversión Subproducto Op #{operacion.numero_secuencia}: {justificacion}",
                )

        # 5. Eliminar aristas de genealogía vinculadas a la operación revertida
        operacion.genealogias.all().delete()

        # 6. Actualizar estado de la operación
        operacion.estado = 'revertida'
        operacion.motivo_reversion = justificacion
        operacion.save(update_fields=['estado', 'motivo_reversion'])

        # 7. Revertir avance en Plan de Producción (MTS) si aplica
        from inventory.services.reposicion_service import ReposicionService
        ReposicionService.revertir_avance_plan(operacion)

        logger.info(
            'Operación #%s en Corrida %s fue revertida exitosamente. Motivo: %s',
            operacion.numero_secuencia,
            operacion.corrida.codigo,
            justificacion,
        )
        return operacion
