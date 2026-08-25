"""
DespachoEstadoService — determina el estado real de un PedidoVenta según lo
efectivamente despachado (no revertido), en vez de asumir "todo o nada".

SRP: única responsabilidad — leer DetalleHistorialDespacho y decidir estado.
Usado tanto por ProcessDespachoAPIView (al procesar un despacho) como por
DespachoReversionService (al revertir uno), para que ambos caminos calculen
el mismo estado con la misma lógica en vez de reglas divergentes.
"""
from decimal import Decimal

from django.db.models import Sum


class DespachoEstadoService:

    @staticmethod
    def peso_despachado_por_producto(pedido) -> dict:
        """
        Suma, por producto_id, el peso de DetalleHistorialDespacho asignados a
        este pedido que NO están marcados como devolución (es_devolucion=False).
        Una reversión marca es_devolucion=True, así que automáticamente deja de
        contar aquí sin necesitar lógica adicional.
        """
        from inventory.models import DetalleHistorialDespacho

        filas = (
            DetalleHistorialDespacho.objects
            .filter(pedido=pedido, es_devolucion=False)
            .values('producto_id')
            .annotate(total=Sum('peso'))
        )
        return {fila['producto_id']: fila['total'] for fila in filas}

    @staticmethod
    def requerido_por_producto(pedido) -> dict:
        """Suma el peso requerido por producto_id a partir de los detalles del pedido."""
        requerido: dict = {}
        for detalle in pedido.detalles.all():
            requerido[detalle.producto_id] = requerido.get(detalle.producto_id, Decimal('0')) + detalle.peso
        return requerido

    @staticmethod
    def recalcular_estado(pedido) -> str:
        """
        Determina qué estado debería tener el pedido AHORA MISMO según lo
        realmente despachado (no revertido) vs lo requerido en sus detalles.
        No lo guarda — el llamador decide cuándo persistir el cambio.

        - Sin detalles: no hay nada que inferir, se conserva el estado actual
          (evita romper pedidos legacy sin líneas o flujos que no aplican aquí,
          p.ej. 'facturado' no se debe pisar).
        - Si el pedido ya está 'facturado', no se toca — la facturación es un
          estado posterior al despacho que esta lógica no debe revertir.
        - Nada despachado todavía -> 'pendiente'.
        - Todo despachado (cada producto cubre su requerido) -> 'despachado'.
        - Algo despachado pero no todo -> 'despachado_parcial'.
        """
        if pedido.estado == 'facturado':
            return 'facturado'

        despachado = DespachoEstadoService.peso_despachado_por_producto(pedido)
        total_despachado = sum(despachado.values(), Decimal('0'))

        if total_despachado <= 0:
            return 'pendiente'

        requerido = DespachoEstadoService.requerido_por_producto(pedido)
        if not requerido:
            # Sin detalles definidos para comparar (pedido sin líneas, dato
            # legacy): si algo quedó despachado y asignado a este pedido, no
            # hay forma de saber qué falta — se considera completo.
            return 'despachado'

        completo = all(
            despachado.get(producto_id, Decimal('0')) >= cantidad_requerida
            for producto_id, cantidad_requerida in requerido.items()
        )
        return 'despachado' if completo else 'despachado_parcial'
