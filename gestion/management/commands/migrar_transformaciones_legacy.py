import logging
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from gestion.models import (
    Area,
    AuditLog,
    CorridaProduccion,
    ConsumoMaterial,
    LoteProduccion,
    MermaDesperdicio,
    OperacionProduccion,
    OrdenProduccion,
    ProduccionSalida,
    TransformacionProducto,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Migra los registros históricos de TransformacionProducto hacia el "
        "nuevo modelo unificado de ejecución MES (CorridaProduccion y OperacionProduccion)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la migración sin escribir cambios en la base de datos.',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Número de transformaciones a procesar por bloque (por defecto 100).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']

        self.stdout.write(self.style.NOTICE(
            f"Iniciando migración histórica de Transformaciones MES (dry-run={dry_run}, batch-size={batch_size})..."
        ))

        total_transf = TransformacionProducto.objects.count()
        if total_transf == 0:
            self.stdout.write(self.style.SUCCESS("No hay registros históricos de TransformacionProducto para migrar."))
            return

        self.stdout.write(f"Total de transformaciones a evaluar: {total_transf}")

        migrados = 0
        omitidos = 0
        errores = 0

        qs = TransformacionProducto.objects.select_related(
            'orden_produccion',
            'orden_produccion__sede',
            'orden_produccion__area',
            'orden_produccion__bodega_entrada',
            'orden_produccion__bodega_salida',
            'orden_produccion__plan_produccion',
            'orden_produccion__pedido_venta',
            'producto_entrada',
            'producto_salida',
            'maquina',
            'maquina__area',
            'maquina__bodega_entrada',
            'maquina__bodega_salida',
            'maquina__producto_merma',
            'maquina__bodega_merma',
            'operario',
        ).order_by('orden_produccion_id', 'numero_secuencia')

        with transaction.atomic():
            for transf in qs:
                try:
                    op = transf.orden_produccion
                    if not op or not op.sede:
                        self.stdout.write(self.style.WARNING(
                            f"Transformación #{transf.id} omitida: sin orden de producción o sin sede."
                        ))
                        omitidos += 1
                        continue

                    ref_obs = f"Migrado de TransformacionProducto #{transf.id}"

                    # Verificar idempotencia
                    if OperacionProduccion.objects.filter(observaciones__contains=ref_obs).exists():
                        omitidos += 1
                        continue

                    if dry_run:
                        migrados += 1
                        continue

                    # Determinar área y sede
                    sede = op.sede
                    area = op.area or (transf.maquina.area if transf.maquina else None)
                    if not area:
                        area = Area.objects.filter(sede=sede).first()
                        if not area:
                            area, _ = Area.objects.get_or_create(sede=sede, defaults={'nombre': 'Área General'})

                    modalidad = 'STOCK' if op.plan_produccion else ('PEDIDO' if op.pedido_venta else 'CONTINUA')

                    corrida_codigo = f"CORR-LEGACY-OP-{op.codigo}"
                    corrida, _ = CorridaProduccion.objects.get_or_create(
                        codigo=corrida_codigo,
                        defaults={
                            'sede': sede,
                            'area': area,
                            'linea': None,
                            'maquina_principal': transf.maquina,
                            'modalidad': modalidad,
                            'orden_produccion': op,
                            'plan_produccion': op.plan_produccion,
                            'detalle_plan': op.detalle_plan,
                            'pedido_venta': op.pedido_venta,
                            'turno': 'General',
                            'fecha_jornada': transf.fecha_inicio.date() if transf.fecha_inicio else timezone.now().date(),
                            'hora_inicio': transf.fecha_inicio or timezone.now(),
                            'hora_fin': transf.fecha_fin,
                            'estado': 'finalizada' if op.estado == 'finalizada' else 'en_proceso',
                            'supervisor': transf.operario,
                            'observaciones': f"Corrida histórica generada desde OP {op.codigo}",
                        }
                    )

                    # Crear u obtener OperacionProduccion
                    obs_completa = f"{transf.observaciones or ''} [{ref_obs}]".strip()
                    operacion, op_created = OperacionProduccion.objects.get_or_create(
                        corrida=corrida,
                        numero_secuencia=transf.numero_secuencia,
                        defaults={
                            'maquina': transf.maquina,
                            'operario': transf.operario,
                            'hora_inicio': transf.fecha_inicio or timezone.now(),
                            'hora_fin': transf.fecha_fin or timezone.now(),
                            'estado': transf.estado or 'completada',
                            'observaciones': obs_completa,
                        }
                    )

                    if not op_created and operacion.salidas.exists():
                        omitidos += 1
                        continue

                    # Bodegas de entrada y salida
                    bodega_in = op.bodega_entrada or getattr(transf.maquina, 'bodega_entrada', None)
                    bodega_out = op.bodega_salida or getattr(transf.maquina, 'bodega_salida', None)

                    if transf.producto_entrada and bodega_in and not operacion.consumos.exists():
                        ConsumoMaterial.objects.create(
                            operacion=operacion,
                            producto=transf.producto_entrada,
                            bodega_origen=bodega_in,
                            cantidad_consumida=transf.peso_entrada,
                        )

                    if transf.producto_salida and bodega_out and not operacion.salidas.exists():
                        lote_generado = op.lotes.filter(producto=transf.producto_salida).first()
                        if not lote_generado:
                            lote_codigo = f"LOTE-LEGACY-OP-{op.codigo}-{transf.numero_secuencia}"
                            lote_generado, _ = LoteProduccion.objects.get_or_create(
                                codigo_lote=lote_codigo,
                                defaults={
                                    'orden_produccion': op,
                                    'producto': transf.producto_salida,
                                    'peso_neto_producido': transf.peso_salida,
                                    'peso_merma': transf.merma or Decimal('0.000'),
                                    'maquina': transf.maquina,
                                    'operario': transf.operario,
                                    'turno': 'General',
                                    'hora_inicio': transf.fecha_inicio or timezone.now(),
                                    'hora_final': transf.fecha_fin or timezone.now(),
                                }
                            )

                        ProduccionSalida.objects.create(
                            operacion=operacion,
                            lote_generado=lote_generado,
                            producto=transf.producto_salida,
                            bodega_destino=bodega_out,
                            cantidad_neta=transf.peso_salida,
                            clasificacion_calidad='primera',
                        )

                    if transf.merma and transf.merma > Decimal('0.000') and not operacion.mermas.exists():
                        MermaDesperdicio.objects.create(
                            operacion=operacion,
                            peso_merma=transf.merma,
                            tipo_merma='maquina',
                            es_subproducto_vendible=bool(transf.maquina and getattr(transf.maquina, 'producto_merma', None)),
                            producto_subproducto=getattr(transf.maquina, 'producto_merma', None) if transf.maquina else None,
                            bodega_subproducto=getattr(transf.maquina, 'bodega_merma', None) if transf.maquina else None,
                        )

                    # Registrar en AuditLog
                    AuditLog.objects.create(
                        usuario=transf.operario,
                        ip_address='127.0.0.1',
                        content_type=ContentType.objects.get_for_model(transf),
                        object_id=transf.pk,
                        object_sede_id=sede.pk,
                        accion='CREATE',
                        valor_anterior={},
                        valor_nuevo={
                            'corrida_id': corrida.id,
                            'operacion_id': operacion.id,
                            'op_codigo': op.codigo,
                            'peso_entrada': str(transf.peso_entrada),
                            'peso_salida': str(transf.peso_salida),
                        },
                        justificacion="Migración de datos histórica hacia Nivel 3 MES",
                    )

                    migrados += 1
                except Exception as ex:
                    errores += 1
                    self.stdout.write(self.style.ERROR(
                        f"Error migrando TransformacionProducto #{transf.id}: {ex}"
                    ))
                    logger.exception(f"Error migrando TransformacionProducto #{transf.id}")

            if dry_run:
                self.stdout.write(self.style.WARNING("Simulación completada. Realizando rollback."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f"Proceso concluido: {migrados} migrados, {omitidos} omitidos/existentes, {errores} errores."
        ))
