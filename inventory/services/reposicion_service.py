import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from gestion.models import (
    Bodega,
    DetallePlanProduccion,
    OperacionProduccion,
    OrdenProduccion,
    PlanProduccion,
    Producto,
    Sede,
)
from inventory.models import StockBodega

logger = logging.getLogger('inventory.reposicion')


class ReposicionService:
    """
    Servicio de Reposición y Planificación Contra Stock (Make-to-Stock / MTS).
    Conecta las alertas de stock mínimo con Planes de Producción y Órdenes de Producción,
    monitoreando la desviación en tiempo real a través de las operaciones del motor MES.
    """

    @classmethod
    @transaction.atomic
    def generar_orden_desde_plan(
        cls,
        detalle_plan: DetallePlanProduccion,
        user=None,
        bodega_salida: Optional[Bodega] = None,
        bodega_entrada: Optional[Bodega] = None,
        formula_color=None,
        prioridad: str = 'normal',
        maquina_asignada=None,
        peso_solicitado: Optional[Decimal] = None,
    ) -> OrdenProduccion:
        """
        Genera una OrdenProduccion de reposición ligada a un DetallePlanProduccion.
        El plan debe estar en estado 'aprobado' o 'en_ejecucion'.
        """
        if not detalle_plan or not detalle_plan.pk:
            raise ValidationError("Se requiere un detalle de plan válido.")

        plan = detalle_plan.plan
        if plan.estado not in ['aprobado', 'en_ejecucion']:
            raise ValidationError(
                f"No se puede generar órdenes para un plan en estado '{plan.get_estado_display()}'. "
                "El plan debe estar 'Aprobado' o 'En Ejecución'."
            )

        saldo_pendiente = detalle_plan.saldo_pendiente
        if saldo_pendiente <= Decimal('0.0000'):
            raise ValidationError(
                f"El producto {detalle_plan.producto_objetivo.codigo} ya ha cumplido la meta planificada."
            )

        peso_requerido = peso_solicitado if peso_solicitado is not None else saldo_pendiente
        if peso_requerido <= Decimal('0.0000'):
            raise ValidationError("El peso requerido debe ser mayor a 0.")

        # Resolver bodega de salida por defecto si no se especificó
        if not bodega_salida:
            bodega_salida = Bodega.objects.filter(
                sede=plan.sede,
                activa=True,
            ).order_by('id').first()

        # Generar código secuencial para la OP ligada al plan
        correlativo = OrdenProduccion.objects.filter(
            plan_produccion=plan,
        ).count() + 1
        codigo_op = f"MTS-{plan.codigo}-{detalle_plan.producto_objetivo.codigo}-{correlativo}"
        if len(codigo_op) > 100:
            codigo_op = codigo_op[:100]

        op = OrdenProduccion.objects.create(
            codigo=codigo_op,
            producto_salida=detalle_plan.producto_objetivo,
            peso_neto_requerido=Decimal(str(peso_requerido)).quantize(Decimal('0.01')),
            bodega_salida=bodega_salida,
            bodega_entrada=bodega_entrada,
            formula_color=formula_color,
            prioridad=prioridad,
            maquina_asignada=maquina_asignada,
            operario_asignado=user,
            sede=plan.sede,
            plan_produccion=plan,
            detalle_plan=detalle_plan,
            estado='pendiente',
            observaciones=f"Reposición MTS generada desde Plan {plan.codigo}",
        )

        # Transicionar plan a 'en_ejecucion' si estaba 'aprobado'
        if plan.estado == 'aprobado':
            plan.estado = 'en_ejecucion'
            plan.save(update_fields=['estado', 'fecha_modificacion'])

        # Transicionar detalle a 'en_proceso' si estaba 'pendiente'
        if detalle_plan.estado == 'pendiente':
            detalle_plan.estado = 'en_proceso'
            detalle_plan.save(update_fields=['estado'])

        logger.info(
            f"Orden de Producción MTS {op.codigo} generada exitosamente para plan {plan.codigo} "
            f"(Producto: {detalle_plan.producto_objetivo.codigo}, Requerido: {op.peso_neto_requerido}kg)"
        )
        return op

    @classmethod
    @transaction.atomic
    def actualizar_avance_plan(cls, operacion: OperacionProduccion) -> None:
        """
        Actualiza el avance cuantitativo y cualitativo en DetallePlanProduccion
        a partir de los lotes y cantidades reportadas en una OperacionProduccion.
        Usa bloqueo pesimista select_for_update() para evitar condiciones de carrera.
        """
        if not operacion or not operacion.pk:
            return

        corrida = operacion.corrida
        plan = corrida.plan_produccion or (
            corrida.orden_produccion.plan_produccion if corrida.orden_produccion else None
        )
        detalle_directo = corrida.detalle_plan or (
            corrida.orden_produccion.detalle_plan if corrida.orden_produccion else None
        )

        if not plan and not detalle_directo:
            return

        for salida in operacion.salidas.select_related('producto').all():
            target_dp = None
            if detalle_directo and detalle_directo.producto_objetivo_id == salida.producto_id:
                target_dp = detalle_directo
            elif plan:
                target_dp = plan.detalles.filter(producto_objetivo_id=salida.producto_id).first()

            if not target_dp:
                continue

            dp_locked = DetallePlanProduccion.objects.select_for_update().get(pk=target_dp.pk)
            dp_locked.cantidad_ejecutada += salida.cantidad_neta

            if salida.clasificacion_calidad == 'primera':
                dp_locked.cantidad_aceptada += salida.cantidad_neta
            elif salida.clasificacion_calidad == 'segunda':
                dp_locked.cantidad_segunda += salida.cantidad_neta

            dp_locked.actualizar_estado()
            dp_locked.save()

            parent_plan = dp_locked.plan
            # Transicionar plan si estaba aprobado
            if parent_plan.estado == 'aprobado':
                parent_plan.estado = 'en_ejecucion'
                parent_plan.save(update_fields=['estado', 'fecha_modificacion'])

            # Verificar si todos los detalles del plan están completados o sobreproducidos
            todos_detalles = parent_plan.detalles.all()
            if todos_detalles.exists() and all(d.estado in ['completado', 'sobreproducido'] for d in todos_detalles):
                parent_plan.estado = 'cerrado'
                parent_plan.save(update_fields=['estado', 'fecha_modificacion'])
                logger.info(f"Plan de Producción {parent_plan.codigo} cerrado automáticamente al cumplir todas las metas.")

    @classmethod
    @transaction.atomic
    def revertir_avance_plan(cls, operacion: OperacionProduccion) -> None:
        """
        Revierte el avance registrado en DetallePlanProduccion cuando una operación MES es revertida.
        """
        if not operacion or not operacion.pk:
            return

        corrida = operacion.corrida
        plan = corrida.plan_produccion or (
            corrida.orden_produccion.plan_produccion if corrida.orden_produccion else None
        )
        detalle_directo = corrida.detalle_plan or (
            corrida.orden_produccion.detalle_plan if corrida.orden_produccion else None
        )

        if not plan and not detalle_directo:
            return

        for salida in operacion.salidas.select_related('producto').all():
            target_dp = None
            if detalle_directo and detalle_directo.producto_objetivo_id == salida.producto_id:
                target_dp = detalle_directo
            elif plan:
                target_dp = plan.detalles.filter(producto_objetivo_id=salida.producto_id).first()

            if not target_dp:
                continue

            dp_locked = DetallePlanProduccion.objects.select_for_update().get(pk=target_dp.pk)
            dp_locked.cantidad_ejecutada = max(Decimal('0.0000'), dp_locked.cantidad_ejecutada - salida.cantidad_neta)

            if salida.clasificacion_calidad == 'primera':
                dp_locked.cantidad_aceptada = max(Decimal('0.0000'), dp_locked.cantidad_aceptada - salida.cantidad_neta)
            elif salida.clasificacion_calidad == 'segunda':
                dp_locked.cantidad_segunda = max(Decimal('0.0000'), dp_locked.cantidad_segunda - salida.cantidad_neta)

            dp_locked.actualizar_estado()
            dp_locked.save()

            parent_plan = dp_locked.plan
            if parent_plan.estado == 'cerrado':
                parent_plan.estado = 'en_ejecucion'
                parent_plan.save(update_fields=['estado', 'fecha_modificacion'])

    @classmethod
    def analizar_necesidades_reposicion(cls, sede_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Calcula las necesidades de reposición agrupadas por producto sumando todos
        los lotes disponibles en la sede, comparando contra el stock mínimo definido.
        """
        queryset = StockBodega.objects.all()
        if sede_id:
            queryset = queryset.filter(bodega__sede_id=sede_id)

        agrupado = (
            queryset
            .values(
                'producto_id',
                'producto__codigo',
                'producto__descripcion',
                'producto__tipo',
                'producto__unidad_medida',
                'producto__stock_minimo',
                'bodega__sede_id',
                'bodega__sede__nombre',
            )
            .annotate(stock_actual=models.Sum('cantidad'))
            .filter(
                producto__stock_minimo__gt=0,
                stock_actual__lt=models.F('producto__stock_minimo'),
            )
            .order_by('bodega__sede__nombre', 'producto__descripcion')
        )

        resultado = []
        for item in agrupado:
            stock_act = item['stock_actual'] or Decimal('0.0000')
            stock_min = item['producto__stock_minimo'] or Decimal('0.0000')
            deficit = stock_min - stock_act
            resultado.append({
                'sede_id': item['bodega__sede_id'],
                'sede_nombre': item['bodega__sede__nombre'],
                'producto_id': item['producto_id'],
                'producto_codigo': item['producto__codigo'],
                'producto_descripcion': item['producto__descripcion'],
                'tipo': item['producto__tipo'],
                'unidad_medida': item['producto__unidad_medida'],
                'stock_actual': stock_act,
                'stock_minimo': stock_min,
                'deficit': deficit,
            })
        return resultado

    @classmethod
    @transaction.atomic
    def crear_plan_desde_alertas(
        cls,
        sede: Sede,
        productos_deficit: List[Dict[str, Any]],
        supervisor=None,
        codigo: Optional[str] = None,
        fecha_inicio=None,
        fecha_fin=None,
        aprobar_inmediatamente: bool = False,
    ) -> PlanProduccion:
        """
        Crea un PlanProduccion con sus respectivos DetallePlanProduccion a partir
        de los déficits de inventario detectados.
        """
        if not productos_deficit:
            raise ValidationError("No se proporcionaron productos con déficit para generar el plan.")

        today = timezone.localdate()
        fecha_inicio = fecha_inicio or today
        fecha_fin = fecha_fin or (today + timezone.timedelta(days=7))

        if not codigo:
            correlativo = PlanProduccion.objects.filter(sede=sede).count() + 1
            codigo = f"PLAN-{sede.id}-{today.strftime('%Y%m')}-{correlativo:03d}"

        plan = PlanProduccion.objects.create(
            codigo=codigo,
            sede=sede,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado='aprobado' if aprobar_inmediatamente else 'borrador',
            supervisor=supervisor,
            observaciones=f"Plan de reposición generado a partir de alertas de stock mínimo ({len(productos_deficit)} items)",
        )

        for item in productos_deficit:
            prod_id = item.get('producto_id')
            prod = Producto.objects.get(pk=prod_id)
            deficit = Decimal(str(item.get('deficit', item.get('cantidad_planificada', 0))))
            if deficit <= Decimal('0.0000'):
                continue

            DetallePlanProduccion.objects.create(
                plan=plan,
                producto_objetivo=prod,
                cantidad_planificada=deficit.quantize(Decimal('0.0001')),
                cantidad_ejecutada=Decimal('0.0000'),
                cantidad_aceptada=Decimal('0.0000'),
                cantidad_segunda=Decimal('0.0000'),
                estado='pendiente',
            )

        logger.info(f"Plan de producción {plan.codigo} creado exitosamente con {plan.detalles.count()} renglones.")
        return plan
