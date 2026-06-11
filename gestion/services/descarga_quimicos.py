"""
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-DescargaQuimicaAutomatica
Patrón: Service Layer + Template Method + Strategy (tipo_calculo)
SOLID: SRP — este módulo solo gestiona ciclo de vida de descarga química
"""

import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from gestion.models import DescargaQuimicoOP, Producto, Bodega
from gestion.services_formula import DosificacionCalculator
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger('gestion.services.descarga_quimicos')


class DescargaQuimicosService:
    """
    Servicio de descarga automática de químicos al crear/modificar/eliminar órdenes de producción.
    Reutiliza DosificacionCalculator para cálculos y safe_get_or_create_stock para acceso thread-safe.
    """

    @staticmethod
    @transaction.atomic
    def descargar_para_op(orden, usuario) -> list:
        """
        SRP: solo ejecuta descarga inicial. Cálculo delegado a DosificacionCalculator.

        Args:
            orden: Instancia de OrdenProduccion con formula_color y bodega_quimicos
            usuario: Usuario que solicita la descarga

        Returns:
            Lista de DescargaQuimicoOP creados

        Raises:
            ValidationError si bodega_quimicos no está configurada
        """
        if not orden.bodega_quimicos:
            raise ValidationError("Bodega de químicos no configurada en la orden.")
        if not orden.formula_color:
            raise ValidationError("Fórmula de color no asignada a la orden.")

        # Cálculo de dosificación usando DosificacionCalculator (reutilización de patrón Strategy)
        try:
            resultado = DosificacionCalculator(orden.formula_color).calcular(
                kg_tela=orden.peso_neto_requerido,
                relacion_bano=Decimal('10')  # configurable por sed/fórmula en versión futura
            )
        except Exception as e:
            logger.error(f"Error calculando dosificación para OP {orden.codigo}: {str(e)}")
            raise ValidationError(f"Error calculando dosificación: {str(e)}")

        registros = []

        for insumo in resultado.insumos:
            try:
                # Thread-safe get-or-create con savepoint
                stock, _ = safe_get_or_create_stock(
                    StockBodega,
                    bodega=orden.bodega_quimicos,
                    producto=insumo.producto_id, # Se pasa el ID al campo ForeignKey
                    lote=None
                )

                # Descuento del stock (3 decimales — precisión estándar del sistema, P1-008)
                cantidad_descontar = insumo.cantidad_kg.quantize(Decimal('0.001'))

                # P0-006: validar disponibilidad ANTES de descontar — el stock
                # jamás debe quedar negativo. transaction.atomic revierte los
                # insumos ya descontados de esta misma descarga.
                if stock.cantidad < cantidad_descontar:
                    raise ValidationError(
                        f"Stock insuficiente de {insumo.producto_descripcion} en bodega "
                        f"'{orden.bodega_quimicos.nombre}': disponible {stock.cantidad} kg, "
                        f"requerido {cantidad_descontar} kg."
                    )

                stock.cantidad -= cantidad_descontar
                stock._justificacion_auditoria = f"Descarga automática OP-{orden.codigo}"
                stock.save()

                # Registro de movimiento de inventario.
                # estado_movimiento='completado' explícito: la descarga de
                # químicos es consumo inmediato en la OP, sin bodega de
                # tránsito (el protocolo 3-fase aplica a TRANSFERENCIAS vía
                # TransicionBodegaService).
                MovimientoInventario.objects.create(
                    tipo_movimiento='CONSUMO',
                    producto_id=insumo.producto_id,
                    bodega_origen=orden.bodega_quimicos,
                    bodega_destino=None,
                    cantidad=cantidad_descontar,
                    usuario=usuario,
                    documento_ref=f'OP-{orden.codigo}',
                    estado_movimiento='completado',
                    saldo_resultante=stock.cantidad
                )

                # Registro de descarga química (auditoría)
                registro = DescargaQuimicoOP.objects.create(
                    orden_produccion=orden,
                    producto_id=insumo.producto_id,
                    fase=insumo.fase_id if hasattr(insumo, 'fase_id') else None,
                    bodega=orden.bodega_quimicos,
                    tipo_calculo=insumo.tipo_calculo,
                    cantidad_calculada_kg=insumo.cantidad_kg,
                    estado='aplicada',
                    descargado_por=usuario
                )
                registros.append(registro)

                # Verificar alertas de stock bajo
                DescargaQuimicosService._verificar_alertas(
                    bodega=orden.bodega_quimicos,
                    producto_id=insumo.producto_id,
                    saldo=stock.cantidad
                )

            except ValidationError:
                # Errores de negocio (ej. stock insuficiente) suben sin re-envolver
                raise
            except Exception as e:
                logger.error(f"Error descargando {insumo.producto_descripcion} en OP {orden.codigo}: {str(e)}")
                raise ValidationError(f"Error descargando {insumo.producto_descripcion}: {str(e)}")

        # Marcar orden como con inventario descontado
        orden.inventario_descontado = True
        orden.save(update_fields=['inventario_descontado'])

        logger.info(f"Descarga exitosa OP-{orden.codigo}: {len(registros)} químicos descargados")
        return registros

    @staticmethod
    @transaction.atomic
    def revertir_descarga_op(orden, usuario, justificacion: str):
        """
        Template Method: paso de reversión dentro de ajustar_descarga_op.
        Se usa al eliminar una OP o para ajuste de modificación.

        Args:
            orden: Instancia de OrdenProduccion
            usuario: Usuario que solicita la reversión
            justificacion: Razón de la reversión (obligatoria)
        """
        if not justificacion:
            raise ValidationError("Justificación obligatoria para revertir descarga de químicos.")

        descargas = orden.descargas_quimicos.filter(estado='aplicada').select_related('producto', 'bodega')

        for descarga in descargas:
            try:
                # Recuperar stock de forma thread-safe
                stock, _ = safe_get_or_create_stock(
                    StockBodega,
                    bodega=descarga.bodega,
                    producto=descarga.producto_id,
                    lote=None
                )

                # Devolución al stock (3 decimales — precisión estándar del sistema, P1-008)
                cantidad_revertir = descarga.cantidad_calculada_kg.quantize(Decimal('0.001'))
                stock.cantidad += cantidad_revertir
                stock._justificacion_auditoria = justificacion
                stock.save()

                # Registro de movimiento de devolución
                MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto_id=descarga.producto_id,
                    bodega_origen=None,
                    bodega_destino=descarga.bodega,
                    cantidad=cantidad_revertir,
                    usuario=usuario,
                    documento_ref=f'REVERT-OP-{orden.codigo}',
                    saldo_resultante=stock.cantidad
                )

                # Marcar descarga como revertida
                descarga.estado = 'revertida'
                descarga.justificacion = justificacion
                descarga.save(update_fields=['estado', 'justificacion'])

            except Exception as e:
                logger.error(f"Error revirtiendo descarga {descarga.id} de OP {orden.codigo}: {str(e)}")
                raise ValidationError(f"Error revirtiendo {descarga.producto.descripcion}: {str(e)}")

        # Marcar orden como sin inventario descontado
        orden.inventario_descontado = False
        orden.save(update_fields=['inventario_descontado'])

        logger.info(f"Reversión exitosa OP-{orden.codigo}: {descargas.count()} químicos revertidos")

    @staticmethod
    @transaction.atomic
    def ajustar_descarga_op(orden, usuario, justificacion: str):
        """
        Template Method: secuencia fija revertir → descargar.
        Se usa al modificar peso o fórmula de una OP que ya tiene descarga.

        Args:
            orden: Instancia de OrdenProduccion
            usuario: Usuario que solicita el ajuste
            justificacion: Razón del ajuste (obligatoria)
        """
        if not justificacion:
            raise ValidationError("Justificación obligatoria para ajustar descarga de químicos.")

        # Paso 1: Revertir descargas existentes
        DescargaQuimicosService.revertir_descarga_op(orden, usuario, justificacion)

        # Paso 2: Realizar nueva descarga con valores actualizados
        DescargaQuimicosService.descargar_para_op(orden, usuario)

        logger.info(f"Ajuste exitoso OP-{orden.codigo}: reversión + nueva descarga")

    @staticmethod
    def _verificar_alertas(bodega: Bodega, producto_id: int, saldo: Decimal):
        """
        Verifica si el stock ha caído por debajo del mínimo.
        Emite warning en logs y puede extenderse para crear AlertaStock.

        Args:
            bodega: Instancia de Bodega
            producto_id: ID del producto
            saldo: Saldo resultante después de descarga
        """
        try:
            producto = Producto.objects.get(pk=producto_id)
            if saldo < producto.stock_minimo:
                alerta_msg = f"[ALERTA STOCK] {producto.descripcion} en bodega '{bodega.nombre}': {saldo}kg (mínimo: {producto.stock_minimo}kg)"
                logger.warning(alerta_msg)
                # Extensión futura: crear instancia de AlertaStock si existe
        except Producto.DoesNotExist:
            logger.error(f"Producto {producto_id} no encontrado al verificar alertas")
