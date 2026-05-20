import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from rest_framework.exceptions import ValidationError
from gestion.models import OrdenProduccion, LoteProduccion, Maquina, Producto
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger('gestion.services')

class RegistroLoteService:
    @staticmethod
    @transaction.atomic
    def registrar_lote(orden: OrdenProduccion, lote_data: dict, user, completar_orden: bool = False) -> LoteProduccion:
        peso_neto_producido = Decimal(str(lote_data['peso_neto_producido'])).quantize(Decimal('0.01'))
        peso_merma = Decimal(str(lote_data.get('peso_merma', '0.00'))).quantize(Decimal('0.01'))
        
        lote_data['peso_neto_producido'] = peso_neto_producido
        if 'peso_merma' in lote_data:
            lote_data['peso_merma'] = peso_merma

        consumo_total_requerido = peso_neto_producido + peso_merma
        
        # --- Validate Order has necessary components ---
        if not orden.producto or not orden.bodega:
            logger.warning("Orden sin producto o bodega", extra={"sd": {"entity": "LoteProduccion", "field": "orden", "reason": "La orden de producción no tiene un producto o bodega asignada"}})
            raise ValidationError({"detail": "La orden de producción no tiene un producto o bodega asignada."})

        # --- 1. Generate/Validate Batch Code ---
        if not lote_data.get('codigo_lote'):
            lote_data['codigo_lote'] = orden.generate_next_lote_codigo()
        
        maquina_instance = lote_data.get('maquina')
        if maquina_instance and not isinstance(maquina_instance, Maquina):
            try:
                maquina_instance = Maquina.objects.get(pk=maquina_instance)
                lote_data['maquina'] = maquina_instance
            except Maquina.DoesNotExist:
                raise ValidationError({"detail": "La máquina especificada no existe."})
        
        # --- 2. Consume Raw Material (Standard Production + Merma) ---
        producto_a_consumir = orden.producto
        bodega_origen = orden.bodega

        if producto_a_consumir and bodega_origen:
            try:
                stock_input = StockBodega.objects.select_for_update().get(
                    bodega=bodega_origen, producto=producto_a_consumir, lote__isnull=True
                )
                if stock_input.cantidad >= consumo_total_requerido:
                    stock_input.cantidad -= consumo_total_requerido
                    stock_input._justificacion_auditoria = f"Consumo (y merma) automático para OP-{orden.codigo}"
                    stock_input.save()
                    
                    # Movimiento de consumo principal
                    MovimientoInventario.objects.create(
                        tipo_movimiento='CONSUMO', producto=producto_a_consumir, bodega_origen=bodega_origen,
                        cantidad=peso_neto_producido, usuario=user, documento_ref=f'OP-{orden.codigo}'
                    )
                    
                    # Movimiento de merma si aplica
                    if peso_merma > 0:
                        MovimientoInventario.objects.create(
                            tipo_movimiento='MERMA', producto=producto_a_consumir, bodega_origen=bodega_origen,
                            cantidad=peso_merma, usuario=user, documento_ref=f'MERMA-OP-{orden.codigo}'
                        )
                else:
                    logger.warning(
                        "Stock insuficiente en bodega",
                        extra={'sd': {
                            'entity': 'LoteProduccion',
                            'producto': producto_a_consumir.codigo,
                            'bodega': bodega_origen.nombre,
                            'disponible': str(stock_input.cantidad),
                            'requerido': str(consumo_total_requerido),
                        }}
                    )
            except StockBodega.DoesNotExist:
                logger.error(
                    "No existe stock para producto base",
                    extra={'sd': {
                        'entity': 'LoteProduccion',
                        'producto': producto_a_consumir.codigo,
                        'bodega': bodega_origen.nombre,
                    }}
                )

        # --- 3. Consume Specific Packaging Supplies (Insumos) ---
        presentacion = lote_data.get('presentacion', '').lower()
        insumo_skus = ['INS-ETQ-01'] # Default label
        
        if 'caja' in presentacion:
            insumo_skus.append('INS-CJ-01')
        elif 'funda' in presentacion:
            insumo_skus.append('INS-FD-01')
        
        for sku in insumo_skus:
            try:
                prod_insumo = Producto.objects.get(codigo=sku)
                stock_insumo = StockBodega.objects.select_for_update().get(bodega=bodega_origen, producto=prod_insumo)
                if stock_insumo.cantidad >= 1:
                    stock_insumo.cantidad -= 1
                    stock_insumo._justificacion_auditoria = f"Uso de insumo {sku} para lote {lote_data['codigo_lote']}"
                    stock_insumo.save()
                    MovimientoInventario.objects.create(
                        tipo_movimiento='CONSUMO',
                        producto=prod_insumo,
                        bodega_origen=bodega_origen,
                        cantidad=1,
                        usuario=user,
                        documento_ref=f'INSUMO-LOTE-{lote_data["codigo_lote"]}'
                    )
            except (Producto.DoesNotExist, StockBodega.DoesNotExist):
                continue

        # --- 4. Create the Production Lot ---
        lote = LoteProduccion.objects.create(
            orden_produccion=orden,
            operario=user,
            **lote_data
        )

        # --- 5. Add the new lot to inventory ---
        producto_final = orden.producto
        bodega_destino = orden.bodega
        stock_output, created = safe_get_or_create_stock(
            StockBodega,
            bodega=bodega_destino, 
            producto=producto_final, 
            lote=lote
        )
        stock_output.cantidad += peso_neto_producido
        stock_output._justificacion_auditoria = f"Entrada por producción lote {lote.codigo_lote}"
        stock_output.save()
        
        MovimientoInventario.objects.create(
             tipo_movimiento='PRODUCCION', producto=producto_final, lote=lote,
             bodega_destino=bodega_destino, cantidad=peso_neto_producido,
             usuario=user, documento_ref=f'OP-{orden.codigo}'
        )

        # --- 6. Update Order Status ---
        total_producido = orden.lotes.aggregate(Sum('peso_neto_producido'))['peso_neto_producido__sum'] or 0
        
        if completar_orden or total_producido >= orden.peso_neto_requerido:
            orden.estado = 'finalizada'
            orden.fecha_fin_planificada = timezone.now().date()
        else:
            orden.estado = 'en_proceso'
            
        orden.save()

        logger.info(
            "Lote de producción registrado",
            extra={'sd': {
                'entity': 'LoteProduccion',
                'action': 'CREATE',
                'lote_codigo': lote.codigo_lote,
                'orden_codigo': orden.codigo,
                'peso_neto': str(peso_neto_producido),
                'peso_merma': str(peso_merma),
                'user': user.username if user else 'system'
            }}
        )

        return lote
