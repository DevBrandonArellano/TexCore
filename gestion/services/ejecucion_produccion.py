import logging
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
        mermas_data: list = None,
        user=None,
        justificacion: str = None,
        tolerancia_balance: Decimal = Decimal('0.050'),
        validar_balance_masa: bool = True,
    ) -> OperacionProduccion:
        """
        Registra un paso unitario de transformación en máquina dentro de una corrida.
        """
        if mermas_data is None:
            mermas_data = []

        if not corrida or not corrida.pk:
            raise ValidationError("Se requiere una corrida de producción válida.")

        # Lock pesimista sobre la corrida para serializar operaciones concurrentes
        corrida = CorridaProduccion.objects.select_for_update().get(pk=corrida.pk)
        if corrida.estado in ('finalizada', 'anulada'):
            raise ValidationError(
                f"No se pueden registrar operaciones en una corrida con estado '{corrida.estado}'."
            )

        # 1. Resolver y validar operador y máquina
        maquina = operacion_data.get('maquina') or corrida.maquina_principal
        if not maquina:
            raise ValidationError("Se requiere una máquina para la operación de producción.")
        if isinstance(maquina, (int, str)):
            try:
                maquina = Maquina.objects.get(pk=maquina)
            except Maquina.DoesNotExist:
                raise ValidationError(f"La máquina con ID {maquina} no existe.")

        operario = operacion_data.get('operario') or user
        if not operario:
            raise ValidationError("Se requiere un operario responsable para la operación.")
        if isinstance(operario, (int, str)):
            try:
                operario = CustomUser.objects.get(pk=operario)
            except CustomUser.DoesNotExist:
                raise ValidationError(f"El usuario operario con ID {operario} no existe.")

        proceso = operacion_data.get('proceso')
        if proceso and isinstance(proceso, (int, str)):
            try:
                proceso = ProcessStep.objects.get(pk=proceso)
            except ProcessStep.DoesNotExist:
                raise ValidationError(f"El proceso con ID {proceso} no existe.")

        hora_inicio = operacion_data.get('hora_inicio') or timezone.now()
        hora_fin = operacion_data.get('hora_fin') or timezone.now()
        estado_op = operacion_data.get('estado', 'completada')
        observaciones = operacion_data.get('observaciones', '')

        # 2. Secuencia de la operación
        numero_secuencia = operacion_data.get('numero_secuencia')
        if not numero_secuencia:
            max_sec = corrida.operaciones.aggregate(models.Max('numero_secuencia'))['numero_secuencia__max'] or 0
            numero_secuencia = max_sec + 1

        # 3. Validación de Balance de Masa
        total_entradas = sum(
            Decimal(str(c['cantidad_consumida'])).quantize(Decimal('0.001'))
            for c in consumos_data
        )
        total_salidas = sum(
            Decimal(str(s['cantidad_neta'])).quantize(Decimal('0.001'))
            for s in salidas_data
        )
        total_mermas = sum(
            Decimal(str(m['peso_merma'])).quantize(Decimal('0.001'))
            for m in mermas_data
        )
        total_salidas_mermas = total_salidas + total_mermas

        if validar_balance_masa and consumos_data and (salidas_data or mermas_data):
            diferencia = abs(total_entradas - total_salidas_mermas)
            if diferencia > tolerancia_balance:
                raise ValidationError(
                    f"Desbalance de masa detectado: Entradas={total_entradas} kg != "
                    f"Salidas={total_salidas} kg + Mermas={total_mermas} kg (Total={total_salidas_mermas} kg). "
                    f"Diferencia de {diferencia} kg excede la tolerancia permitida ({tolerancia_balance} kg)."
                )

        # 4. Crear entidad de OperacionProduccion
        operacion = OperacionProduccion.objects.create(
            corrida=corrida,
            numero_secuencia=numero_secuencia,
            maquina=maquina,
            proceso=proceso,
            operario=operario,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            estado=estado_op,
            observaciones=observaciones,
        )

        audit_justificacion = justificacion or f"Operación #{numero_secuencia} en Corrida {corrida.codigo}"

        # 5. Procesar Consumos de Material
        consumos_creados = []
        for c_data in consumos_data:
            producto = c_data.get('producto') or c_data.get('producto_id')
            if isinstance(producto, (int, str)):
                producto = Producto.objects.get(pk=producto)

            bodega = c_data.get('bodega_origen') or c_data.get('bodega_origen_id')
            if isinstance(bodega, (int, str)):
                bodega = Bodega.objects.get(pk=bodega)

            cantidad_consumo = Decimal(str(c_data['cantidad_consumida'])).quantize(Decimal('0.001'))
            costo_unit = Decimal(str(c_data.get('costo_unitario', 0))).quantize(Decimal('0.001'))

            lote_origen = c_data.get('lote_origen') or c_data.get('lote_origen_id')
            if lote_origen and isinstance(lote_origen, (int, str)):
                lote_origen = LoteProduccion.objects.get(pk=lote_origen)

            # Lock pesimista sobre el stock de origen
            stock_qs = StockBodega.objects.select_for_update().filter(
                bodega=bodega,
                producto=producto,
                lote=lote_origen,
            )
            stock_row = stock_qs.first()

            if not stock_row:
                lote_desc = f" (Lote: {lote_origen.codigo_lote})" if lote_origen else ""
                raise ValidationError(
                    f"No existe stock registrado para el producto {producto.codigo} "
                    f"en la bodega {bodega.nombre}{lote_desc}."
                )

            if stock_row.cantidad < cantidad_consumo:
                lote_desc = f" (Lote: {lote_origen.codigo_lote})" if lote_origen else ""
                raise ValidationError(
                    f"Stock insuficiente en {bodega.nombre} para {producto.codigo}{lote_desc}. "
                    f"Disponible: {stock_row.cantidad} kg, Requerido: {cantidad_consumo} kg."
                )

            stock_row.cantidad -= cantidad_consumo
            stock_row._justificacion_auditoria = audit_justificacion
            stock_row.save()

            _crear_movimiento_inventario(
                tipo_movimiento='CONSUMO',
                producto=producto,
                lote=lote_origen,
                bodega_origen=bodega,
                cantidad=cantidad_consumo,
                saldo_resultante=stock_row.cantidad,
                usuario=user or operario,
                documento_ref=f"CORRIDA-{corrida.codigo}-OP-{operacion.numero_secuencia}",
                _justificacion_auditoria=audit_justificacion,
            )

            consumo_obj = ConsumoMaterial.objects.create(
                operacion=operacion,
                lote_origen=lote_origen,
                producto=producto,
                bodega_origen=bodega,
                cantidad_consumida=cantidad_consumo,
                costo_unitario=costo_unit,
            )
            consumos_creados.append(consumo_obj)

        # 6. Procesar Salidas de Producción
        salidas_creadas = []
        for s_data in salidas_data:
            producto_salida = s_data.get('producto') or s_data.get('producto_id')
            if isinstance(producto_salida, (int, str)):
                producto_salida = Producto.objects.get(pk=producto_salida)

            bodega_destino = s_data.get('bodega_destino') or s_data.get('bodega_destino_id')
            if isinstance(bodega_destino, (int, str)):
                bodega_destino = Bodega.objects.get(pk=bodega_destino)

            cantidad_neta = Decimal(str(s_data['cantidad_neta'])).quantize(Decimal('0.001'))
            calidad = s_data.get('clasificacion_calidad', 'primera')
            peso_bruto = Decimal(str(s_data.get('peso_bruto', cantidad_neta))).quantize(Decimal('0.001'))
            tara = Decimal(str(s_data.get('tara', 0))).quantize(Decimal('0.001'))
            unidades_empaque = int(s_data.get('unidades_empaque', 1))
            presentacion = s_data.get('presentacion', 'cono')
            cantidad_metros = (
                Decimal(str(s_data['cantidad_metros'])).quantize(Decimal('0.0001'))
                if s_data.get('cantidad_metros') is not None
                else None
            )

            # Resolver o instanciar lote generado
            lote_generado = s_data.get('lote_generado') or s_data.get('lote_generado_id')
            if lote_generado and isinstance(lote_generado, (int, str)):
                lote_generado = LoteProduccion.objects.get(pk=lote_generado)

            if not lote_generado:
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
                    clasificacion_calidad=calidad,
                    operario=operario,
                    maquina=maquina,
                    turno=corrida.turno,
                    hora_inicio=operacion.hora_inicio,
                    hora_final=operacion.hora_fin or timezone.now(),
                    peso_bruto=peso_bruto,
                    tara=tara,
                    unidades_empaque=unidades_empaque,
                    presentacion=presentacion,
                    cantidad_metros=cantidad_metros,
                )
                # Snapshot inicial del código de barras
                EventoEtiquetaService.registrar_original(lote_generado, user or operario)

            # Entrada a StockBodega de destino con safe_get_or_create_stock
            stock_salida, _ = safe_get_or_create_stock(
                StockBodega,
                bodega=bodega_destino,
                producto=producto_salida,
                lote=lote_generado,
            )
            stock_salida = StockBodega.objects.select_for_update().get(pk=stock_salida.pk)
            stock_salida.cantidad += cantidad_neta
            stock_salida._justificacion_auditoria = audit_justificacion
            stock_salida.save()

            _crear_movimiento_inventario(
                tipo_movimiento='PRODUCCION',
                producto=producto_salida,
                lote=lote_generado,
                bodega_destino=bodega_destino,
                cantidad=cantidad_neta,
                saldo_resultante=stock_salida.cantidad,
                usuario=user or operario,
                documento_ref=f"CORRIDA-{corrida.codigo}-OP-{operacion.numero_secuencia}",
                _justificacion_auditoria=audit_justificacion,
            )

            salida_obj = ProduccionSalida.objects.create(
                operacion=operacion,
                lote_generado=lote_generado,
                producto=producto_salida,
                bodega_destino=bodega_destino,
                cantidad_neta=cantidad_neta,
                clasificacion_calidad=calidad,
                peso_bruto=peso_bruto,
                tara=tara,
                unidades_empaque=unidades_empaque,
                cantidad_metros=cantidad_metros,
            )
            salidas_creadas.append(salida_obj)

        # 7. Procesar Mermas y Subproductos
        for m_data in mermas_data:
            peso_merma = Decimal(str(m_data['peso_merma'])).quantize(Decimal('0.001'))
            if peso_merma <= Decimal('0.000'):
                continue

            tipo_merma = m_data.get('tipo_merma', 'maquina')
            es_subproducto = bool(m_data.get('es_subproducto_vendible', False))
            prod_sub = m_data.get('producto_subproducto') or m_data.get('producto_subproducto_id')
            bod_sub = m_data.get('bodega_subproducto') or m_data.get('bodega_subproducto_id')
            lote_sub = m_data.get('lote_subproducto') or m_data.get('lote_subproducto_id')

            if es_subproducto:
                if prod_sub and isinstance(prod_sub, (int, str)):
                    prod_sub = Producto.objects.get(pk=prod_sub)
                if bod_sub and isinstance(bod_sub, (int, str)):
                    bod_sub = Bodega.objects.get(pk=bod_sub)
                if lote_sub and isinstance(lote_sub, (int, str)):
                    lote_sub = LoteProduccion.objects.get(pk=lote_sub)

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
                stock_sub._justificacion_auditoria = audit_justificacion
                stock_sub.save()

                _crear_movimiento_inventario(
                    tipo_movimiento='PRODUCCION',
                    producto=prod_sub,
                    lote=lote_sub,
                    bodega_destino=bod_sub,
                    cantidad=peso_merma,
                    saldo_resultante=stock_sub.cantidad,
                    usuario=user or operario,
                    documento_ref=f"SUBPRODUCTO-CORRIDA-{corrida.codigo}-OP-{operacion.numero_secuencia}",
                    _justificacion_auditoria=audit_justificacion,
                )
            else:
                # Merma estándar: reflejar salida en Kardex desde el primer insumo consumido
                if consumos_creados:
                    c_ref = consumos_creados[0]
                    _crear_movimiento_inventario(
                        tipo_movimiento='MERMA',
                        producto=c_ref.producto,
                        lote=c_ref.lote_origen,
                        bodega_origen=c_ref.bodega_origen,
                        cantidad=peso_merma,
                        saldo_resultante=Decimal('0.000'),
                        usuario=user or operario,
                        documento_ref=f"MERMA-CORRIDA-{corrida.codigo}-OP-{operacion.numero_secuencia}",
                        _justificacion_auditoria=audit_justificacion,
                    )

            MermaDesperdicio.objects.create(
                operacion=operacion,
                peso_merma=peso_merma,
                tipo_merma=tipo_merma,
                es_subproducto_vendible=es_subproducto,
                producto_subproducto=prod_sub,
                bodega_subproducto=bod_sub,
                lote_subproducto=lote_sub,
            )

        # 8. Construcción del Grafo DAG en GenealogiaLote
        for salida in salidas_creadas:
            for consumo in consumos_creados:
                if consumo.lote_origen and salida.lote_generado:
                    if consumo.lote_origen_id == salida.lote_generado_id:
                        continue  # Prevenir ciclo reflexivo

                    if total_salidas > Decimal('0.000'):
                        proporcion = salida.cantidad_neta / total_salidas
                        cant_usada = (consumo.cantidad_consumida * proporcion).quantize(Decimal('0.001'))
                    else:
                        cant_usada = consumo.cantidad_consumida

                    if cant_usada <= Decimal('0.000'):
                        cant_usada = Decimal('0.001')

                    GenealogiaLote.objects.create(
                        lote_padre=consumo.lote_origen,
                        lote_hijo=salida.lote_generado,
                        operacion=operacion,
                        cantidad_padre_usada=cant_usada,
                    )

        # 9. Actualización condicional del estado de OrdenProduccion si aplica
        if corrida.orden_produccion:
            op = corrida.orden_produccion
            total_producido = op.lotes.aggregate(
                total=models.Sum('peso_neto_producido')
            )['total'] or Decimal('0.00')

            if op.peso_neto_requerido and total_producido >= op.peso_neto_requerido:
                op.estado = 'finalizada'
            else:
                op.estado = 'en_proceso'
            op.save(update_fields=['estado'])

        # 10. Actualización de avance en Plan de Producción (MTS) si aplica
        from inventory.services.reposicion_service import ReposicionService
        ReposicionService.actualizar_avance_plan(operacion)

        # 11. Reserva inmutable para Pedido Comercial (MTO) si aplica
        pedido_mto = corrida.pedido_venta or (
            corrida.orden_produccion.pedido_venta if corrida.orden_produccion else None
        )
        if pedido_mto:
            from inventory.services.reserva_service import ReservaService
            for salida in salidas_creadas:
                if salida.lote_generado and salida.clasificacion_calidad == 'primera':
                    ReservaService.reservar_lote_para_pedido(
                        lote=salida.lote_generado,
                        pedido=pedido_mto,
                        detalle_pedido=corrida.orden_produccion.detalle_pedido if corrida.orden_produccion else None,
                        cantidad=salida.cantidad_neta,
                        user=user or operario,
                    )

        logger.info(
            f"Operación #{operacion.numero_secuencia} registrada exitosamente en Corrida {corrida.codigo}. "
            f"Consumos={len(consumos_creados)}, Salidas={len(salidas_creadas)}, Mermas={len(mermas_data)}"
        )
        return operacion

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
            stock, _ = safe_get_or_create_stock(
                StockBodega,
                bodega=consumo.bodega_origen,
                producto=consumo.producto,
                lote=consumo.lote_origen,
            )
            stock = StockBodega.objects.select_for_update().get(pk=stock.pk)
            stock.cantidad += consumo.cantidad_consumida
            stock._justificacion_auditoria = f"Reversión de Op #{operacion.numero_secuencia}: {justificacion}"
            stock.save()

            _crear_movimiento_inventario(
                tipo_movimiento='DEVOLUCION',
                producto=consumo.producto,
                lote=consumo.lote_origen,
                bodega_destino=consumo.bodega_origen,
                cantidad=consumo.cantidad_consumida,
                saldo_resultante=stock.cantidad,
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
                stock._justificacion_auditoria = f"Reversión Subproducto Op #{operacion.numero_secuencia}: {justificacion}"
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
            f"Operación #{operacion.numero_secuencia} en Corrida {operacion.corrida.codigo} "
            f"fue revertida exitosamente. Motivo: {justificacion}"
        )
        return operacion
