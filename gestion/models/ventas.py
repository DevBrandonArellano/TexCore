from django.db import models
from django.db.models import Sum, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from django.conf import settings
from decimal import Decimal

from .core import Sede, AuditableModelMixin, SedeResolvableMixin
from .catalogo import Producto
from .produccion import LoteProduccion


class ClienteManager(models.Manager):
    def get_queryset(self):
        # Subconsulta para el total de pedidos
        from .ventas import PedidoVenta, PagoCliente

        pedidos_sq = PedidoVenta.objects.filter(cliente=OuterRef('pk'),
                                                anulado=False,).values('cliente').annotate(
            total=Sum('detalles__total_con_iva', output_field=DecimalField())
            - Sum('valor_retencion', output_field=DecimalField())).values('total')

        # Subconsulta para el total de pagos
        pagos_sq = PagoCliente.objects.filter(
            cliente=OuterRef('pk')
        ).values('cliente').annotate(
            total=Sum('monto', output_field=DecimalField())
        ).values('total')

        # Subconsulta para Cartera Vencida (deuda vencida ayer o antes)
        from django.utils import timezone

        cartera_vencida_sq = PedidoVenta.objects.filter(
            cliente=OuterRef('pk'),
            anulado=False, esta_pagado=False, fecha_vencimiento__lt=timezone.now().date()).values('cliente').annotate(
            total_vencido=Sum('detalles__total_con_iva', output_field=DecimalField())
            - Sum('valor_retencion', output_field=DecimalField())).values('total_vencido')

        # Anotación a nivel de base de datos
        return super().get_queryset().annotate(
            saldo_calculado=Coalesce(Subquery(pedidos_sq), Decimal('0.000'), output_field=DecimalField())
            - Coalesce(Subquery(pagos_sq), Decimal('0.000'), output_field=DecimalField()),
            cartera_vencida=Coalesce(Subquery(cartera_vencida_sq), Decimal('0.000'), output_field=DecimalField())
        )


class Cliente(SedeResolvableMixin, AuditableModelMixin, models.Model):
    campos_auditables = ['limite_credito', 'plazo_credito_dias', 'nivel_precio', 'is_active']
    requiere_justificacion_auditoria = True
    NIVEL_PRECIO_CHOICES = [('mayorista', 'Mayorista'), ('normal', 'Normal')]
    ruc_cedula = models.CharField(max_length=20)
    nombre_razon_social = models.CharField(max_length=255)
    direccion_envio = models.CharField(max_length=500)
    nivel_precio = models.CharField(max_length=20, choices=NIVEL_PRECIO_CHOICES)
    tiene_beneficio = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    limite_credito = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    plazo_credito_dias = models.IntegerField(default=0, help_text="Días de crédito (0=Contado)")
    vendedor_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clientes_asignados')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')

    objects = ClienteManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(limite_credito__gte=0),
                name='gestion_cliente_limite_credito_positivo'
            )
        ]
        unique_together = ('ruc_cedula', 'sede')

    def __str__(self):
        return self.nombre_razon_social

    def get_audit_sede_id(self):
        return self.sede_id


class PagoCliente(models.Model):
    METODO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('otro', 'Otro')
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pagos')
    fecha = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=12, decimal_places=3)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES, default='transferencia')
    comprobante = models.CharField(max_length=100, blank=True, null=True)
    notas = models.CharField(max_length=500, blank=True, null=True)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    # P1-002: marca explícita de anticipo — permite que el monto exceda la
    # deuda actual; el excedente queda como saldo a favor del cliente
    es_anticipo = models.BooleanField(
        default=False,
        help_text='Pago por adelantado: el excedente sobre la deuda queda como saldo a favor'
    )

    def __str__(self):
        return f"Pago {self.id} - {self.cliente.nombre_razon_social} - ${self.monto}"


class PedidoVenta(SedeResolvableMixin, AuditableModelMixin, models.Model):
    campos_auditables = ['cliente', 'guia_remision', 'estado', 'esta_pagado', 'valor_retencion', 'anulado']
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('despachado_parcial', 'Despachado Parcialmente'),
        ('despachado', 'Despachado'),
        ('facturado', 'Facturado'),
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    guia_remision = models.CharField(max_length=100)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_despacho = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    esta_pagado = models.BooleanField(default=False)
    # P1-003: monto aplicado vía reconciliación FIFO — visibiliza pagos
    # parciales que el booleano esta_pagado no puede representar
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    valor_retencion = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True)
    vendedor_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_creados')

    # Anulación
    anulado = models.BooleanField(default=False, db_index=True)
    motivo_anulacion = models.TextField(blank=True, null=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_anulados'
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        pass

    def __str__(self):
        return f"Pedido {self.id} para {self.cliente.nombre_razon_social if self.cliente else 'N/A'}"

    def get_audit_sede_id(self):
        return self.sede_id


class DetallePedido(models.Model):
    pedido_venta = models.ForeignKey(
        PedidoVenta,
        on_delete=models.CASCADE,
        related_name='detalles',
        null=True,
        blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.IntegerField()
    piezas = models.IntegerField()
    peso = models.DecimalField(max_digits=12, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=3)
    incluye_iva = models.BooleanField(default=True)

    # Nuevos campos desnormalizados (Fase 4)
    subtotal = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    total_con_iva = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=0),
                name='gestion_detallepedido_cantidad_positiva'
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name='gestion_detallepedido_precio_unitario_positivo'
            )
        ]

    def save(self, *args, **kwargs):
        from decimal import Decimal
        subt = Decimal(str(self.peso)) * Decimal(str(self.precio_unitario))
        self.subtotal = subt
        self.total_con_iva = subt * Decimal('1.15') if self.incluye_iva else subt
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Detalle {self.id} para Pedido {self.pedido_venta.id if self.pedido_venta else 'N/A'}"
