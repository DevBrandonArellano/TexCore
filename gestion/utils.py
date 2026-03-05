import requests
import logging
import os
from django.db import transaction
from django.db.models import Sum, F, DecimalField
from decimal import Decimal

logger = logging.getLogger(__name__)

PRINTING_SERVICE_URL = os.environ.get('PRINTING_SERVICE_URL', 'http://printing:8001')

class PrintingService:
    @staticmethod
    def generate_nota_venta_pdf(data):
        try:
            url = f"{PRINTING_SERVICE_URL}/pdf/nota-venta"
            response = requests.post(url, json=data, timeout=10)
            if response.status_code == 200:
                return response.content
            else:
                logger.error(f"Error generating PDF: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Printing Service Unavailable: {e}")
            return None

    @staticmethod
    def generate_zpl_label(data):
        try:
            url = f"{PRINTING_SERVICE_URL}/zpl/etiqueta"
            response = requests.post(url, json=data, timeout=5)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Error generating ZPL: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Printing Service Unavailable: {e}")
            return None

class PaymentReconciler:
    """
    Utilidad para reconciliar los pagos de clientes contra sus pedidos (FIFO).
    Actualiza el estado 'esta_pagado' basado en el saldo acumulado.
    """
    @staticmethod
    def reconcile_client_orders(cliente):
        # Importaciones locales para evitar dependencias circulares
        from .models import PedidoVenta, PagoCliente

        logger.info(f"Iniciando reconciliación de pagos para cliente: {cliente.nombre_razon_social}")

        # 1. Obtener Total Pagado
        total_pagado = PagoCliente.objects.filter(cliente=cliente).aggregate(
            total=Sum('monto')
        )['total'] or Decimal('0.00')

        # 2. Obtener Todos los Pedidos ordenados por fecha (FIFO - First In First Out)
        # Calculamos el valor total de cada pedido dinámicamente
        
        # Nota: Django no permite fácilmente anotar Sum(F() * F()) directamente en todas las versiones sin ExpressionWrapper
        # Usaremos iteración para mayor seguridad y compatibilidad, o una query más compleja.
        # Para ser robustos:
        pedidos = PedidoVenta.objects.filter(
            cliente=cliente
        ).prefetch_related('detalles').order_by('fecha_pedido', 'id')

        # 3. Iterar y Aplicar Pagos
        saldo_disponible = total_pagado
        pedidos_actualizados = []
        
        with transaction.atomic():
            for pedido in pedidos:
                # Calcular total del pedido
                valor_pedido = sum(d.peso * d.precio_unitario for d in pedido.detalles.all())
                valor_pedido = Decimal(str(valor_pedido)) # Asegurar precisión

                if valor_pedido <= 0:
                    continue # Ignorar pedidos vacíos o gratis

                nuevo_estado = False
                
                # Si tenemos saldo suficiente para cubrir este pedido completo
                if saldo_disponible >= valor_pedido:
                    nuevo_estado = True
                    saldo_disponible -= valor_pedido
                else:
                    # No alcanza para cubrir todo el pedido
                    nuevo_estado = False
                    saldo_disponible = Decimal('0.00') # Se agotó el saldo

                # Solo actualizar si el estado cambió
                if pedido.esta_pagado != nuevo_estado:
                    pedido.esta_pagado = nuevo_estado
                    pedido.save(update_fields=['esta_pagado'])
                    pedidos_actualizados.append(pedido.id)
            
        logger.info(f"Reconciliación completada. {len(pedidos_actualizados)} pedidos actualizados para cliente {cliente.id}. Saldo restante: {saldo_disponible}")
        return saldo_disponible
