from decimal import Decimal
from django.db.models import Sum, Q, Count
from gestion.models import Cliente, PedidoVenta, PagoCliente


class ExecutiveKPIService:
    def __init__(self, sede_id=None):
        self.sede_id = sede_id

    def obtener_kpis(self):
        clientes = Cliente.objects.all()
        if self.sede_id:
            clientes = clientes.filter(sede_id=self.sede_id)

        cartera_total = Decimal('0')
        cartera_vencida = Decimal('0')
        pedidos_pendientes = 0
        clientes_activos = clientes.filter(is_active=True).count()

        for cliente in clientes:
            saldo = cliente.saldo_pendiente
            if isinstance(saldo, str):
                saldo = Decimal(saldo)
            cartera_total += saldo

            if cliente.cartera_vencida:
                vencida = cliente.cartera_vencida
                if isinstance(vencida, str):
                    vencida = Decimal(vencida)
                cartera_vencida += vencida

        pedidos_pendientes = PedidoVenta.objects.filter(
            estado='pendiente',
            anulado=False
        )
        if self.sede_id:
            pedidos_pendientes = pedidos_pendientes.filter(
                sede_id=self.sede_id
            )
        pedidos_pendientes = pedidos_pendientes.count()

        return {
            'cartera_total': cartera_total,
            'cartera_vencida': cartera_vencida,
            'pedidos_pendientes': pedidos_pendientes,
            'clientes_activos': clientes_activos
        }
