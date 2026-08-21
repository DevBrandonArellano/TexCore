import logging

from rest_framework import serializers

from decimal import Decimal

from django.db import transaction

from gestion.models import Cliente, PagoCliente, PedidoVenta, DetallePedido

logger = logging.getLogger(__name__)


def _fecha_pedido_to_iso_utc(val):
    """Convierte fecha_pedido a ISO UTC con Z para que el frontend muestre la hora local correcta."""
    if val is None:
        return None
    try:
        from django.utils import timezone
        from datetime import datetime, date
        if isinstance(val, date) and not isinstance(val, datetime):
            dt = datetime.combine(val, datetime.min.time())
        else:
            dt = val
        if hasattr(dt, 'astimezone'):
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
    except Exception:
        pass
    return val.isoformat() if hasattr(val, 'isoformat') else str(val)


class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)

    class Meta:
        model = DetallePedido
        fields = '__all__'

    def validate(self, data):
        producto = data.get('producto')
        precio_unitario = data.get('precio_unitario')

        if producto and precio_unitario is not None:
            if precio_unitario < producto.precio_base:
                raise serializers.ValidationError({
                    "precio_unitario": (
                        f"El precio unitario (${precio_unitario:.3f}) no puede"
                        f" ser menor al costo base del producto"
                        f" (${producto.precio_base:.3f})."
                    )
                })
        return data


class PedidoVentaResumenSerializer(serializers.ModelSerializer):
    """
    Serializer minimalista para mostrar el historial de pedidos dentro del cliente.
    """
    total = serializers.SerializerMethodField()
    fecha_pedido = serializers.SerializerMethodField()
    vendedor_nombre = serializers.ReadOnlyField(source='vendedor_asignado.username')
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = PedidoVenta
        fields = [
            'id',
            'fecha_pedido',
            'esta_pagado',
            'total',
            'guia_remision',
            'estado',
            'vendedor_nombre',
            'cliente',
            'sede',
            'valor_retencion',
            'detalles']

    def get_fecha_pedido(self, obj):
        return _fecha_pedido_to_iso_utc(obj.fecha_pedido)

    def get_total(self, obj):
        # Optimización: sumamos desde el prefetch local para evitar aggregate() (query extra N+1)
        # Esto asume que 'detalles' ya fue prefecheado.
        total = 0
        for d in obj.detalles.all():
            subt = Decimal(str(d.peso)) * Decimal(str(d.precio_unitario))
            total += subt * Decimal('1.15') if d.incluye_iva else subt

        retencion = obj.valor_retencion or 0
        return total - retencion


class PagoClienteSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_razon_social')

    class Meta:
        model = PagoCliente
        fields = [
            'id',
            'cliente',
            'cliente_nombre',
            'fecha',
            'monto',
            'metodo_pago',
            'comprobante',
            'notas',
            'sede',
            'es_anticipo']


class ClienteListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados masivos (Admin/Vendedor Dashboard)"""
    saldo_pendiente = serializers.DecimalField(
        source='saldo_calculado',
        max_digits=12,
        decimal_places=3,
        read_only=True)
    cartera_vencida = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    saldo_a_favor = serializers.SerializerMethodField()
    ultima_compra = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = [
            'id',
            'ruc_cedula',
            'nombre_razon_social',
            'direccion_envio',
            'nivel_precio',
            'tiene_beneficio',
            'limite_credito',
            'plazo_credito_dias',
            'saldo_pendiente',
            'cartera_vencida',
            'saldo_a_favor',
            'ultima_compra',
            'sede',
            'vendedor_asignado',
            'is_active']
        read_only_fields = ['vendedor_asignado']

    def get_saldo_a_favor(self, obj):
        """P1-002: anticipo disponible = saldo_calculado negativo invertido."""
        saldo = getattr(obj, 'saldo_calculado', None) or Decimal('0.000')
        return -saldo if saldo < 0 else Decimal('0.000')

    def get_ultima_compra(self, obj):
        last_order = obj.pedidoventa_set.order_by('-fecha_pedido').first()

        if not last_order:
            return None

        detalles = last_order.detalles.all()
        items = [
            {
                "producto": d.producto.descripcion,
                "cantidad": d.cantidad,
                "piezas": d.piezas,
                "peso": d.peso
            }
            for d in detalles
        ]

        return {
            "fecha": _fecha_pedido_to_iso_utc(last_order.fecha_pedido),
            "id_pedido": last_order.id,
            "items": items
        }


class ClienteSerializer(serializers.ModelSerializer):
    ultima_compra = serializers.SerializerMethodField()
    saldo_pendiente = serializers.DecimalField(
        source='saldo_calculado',
        max_digits=12,
        decimal_places=3,
        read_only=True)
    cartera_vencida = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    pedidos = PedidoVentaResumenSerializer(source='pedidoventa_set', many=True, read_only=True)
    pagos = PagoClienteSerializer(many=True, read_only=True)

    _justificacion_auditoria = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Cliente
        fields = [
            'id', 'ruc_cedula', 'nombre_razon_social', 'direccion_envio',
            'nivel_precio', 'tiene_beneficio', 'limite_credito', 'plazo_credito_dias',
            'saldo_pendiente', 'cartera_vencida', 'ultima_compra', 'pedidos', 'pagos',
            'sede', 'vendedor_asignado', 'is_active', '_justificacion_auditoria'
        ]
        extra_kwargs = {
            'vendedor_asignado': {'read_only': True}
        }

    def create(self, validated_data):
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        instance = super().create(validated_data)
        if justificacion:
            instance._justificacion_auditoria = justificacion
            instance.save()  # Volver a guardar para que se registre la auditoría si es necesario
        return instance

    def update(self, instance, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        justificacion = validated_data.pop('_justificacion_auditoria', None)
        if justificacion:
            instance._justificacion_auditoria = justificacion
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

    def validate_tiene_beneficio(self, value):
        user = self.context['request'].user
        # Check if the field is actually being changed
        if self.instance and self.instance.tiene_beneficio != value:
            is_authorized = user.is_superuser or user.groups.filter(
                name__in=['admin_sistemas', 'admin_sede', 'vendedor']).exists()
            if not is_authorized:
                raise serializers.ValidationError("No tienes permiso para modificar los beneficios de un cliente.")
        return value

    def get_ultima_compra(self, obj):
        last_order = obj.pedidoventa_set.order_by('-fecha_pedido').first()

        if not last_order:
            return None

        detalles = last_order.detalles.all()
        items = [
            {
                "producto": d.producto.descripcion,
                "cantidad": d.cantidad,
                "piezas": d.piezas,
                "peso": d.peso
            }
            for d in detalles
        ]

        return {
            "fecha": _fecha_pedido_to_iso_utc(last_order.fecha_pedido),
            "id_pedido": last_order.id,
            "items": items
        }


class PedidoVentaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_razon_social')
    vendedor_nombre = serializers.ReadOnlyField(source='vendedor_asignado.username')
    sede_nombre = serializers.ReadOnlyField(source='sede.nombre')
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    fecha_pedido = serializers.SerializerMethodField()
    porcentaje_pagado = serializers.SerializerMethodField()

    anulado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = PedidoVenta
        fields = [
            'id', 'cliente', 'cliente_nombre', 'vendedor_nombre', 'guia_remision', 'fecha_pedido',
            'fecha_despacho', 'fecha_vencimiento', 'estado', 'esta_pagado', 'monto_pagado',
            'porcentaje_pagado', 'sede', 'sede_nombre',
            'valor_retencion', 'detalles',
            'anulado', 'motivo_anulacion', 'anulado_por', 'anulado_por_nombre', 'fecha_anulacion',
        ]
        read_only_fields = ['anulado', 'motivo_anulacion', 'anulado_por', 'anulado_por_nombre', 'fecha_anulacion',
                            'monto_pagado', 'porcentaje_pagado']

    def get_porcentaje_pagado(self, obj):
        """P1-003: % del valor del pedido cubierto por la reconciliación FIFO."""
        total = sum(d.total_con_iva for d in obj.detalles.all()) - (obj.valor_retencion or Decimal('0.000'))
        if total <= 0:
            return Decimal('0.00')
        return (Decimal(str(obj.monto_pagado)) / Decimal(str(total)) * 100).quantize(Decimal('0.01'))

    def get_anulado_por_nombre(self, obj):
        if obj.anulado_por:
            return obj.anulado_por.get_full_name() or obj.anulado_por.username
        return None

    def get_fecha_pedido(self, obj):
        return _fecha_pedido_to_iso_utc(obj.fecha_pedido)

    def validate(self, data):
        # Allow initial_data access for nested validation
        cliente = data.get('cliente')
        esta_pagado = data.get('esta_pagado', False)

        # Sede is mandatory but usually derived from user
        user = self.context['request'].user
        if not data.get('sede') and hasattr(user, 'sede'):
            data['sede'] = user.sede

        if cliente and not esta_pagado:
            detalles_data = self.initial_data.get('detalles', [])
            nuevo_total = Decimal('0.000')
            for d in detalles_data:
                peso = Decimal(str(d.get('peso', 0)))
                precio = Decimal(str(d.get('precio_unitario', 0)))
                incluye_iva = d.get('incluye_iva', True)
                mult = Decimal('1.15') if incluye_iva else Decimal('1.00')
                nuevo_total += (peso * precio * mult)

            # Re-fetch via custom manager so saldo_calculado annotation
            # is present
            from gestion.models import Cliente as ClienteModel
            cliente_annotated = ClienteModel.objects.get(pk=cliente.pk)
            saldo_actual = cliente_annotated.saldo_calculado

            if (saldo_actual + nuevo_total) > cliente.limite_credito:
                raise serializers.ValidationError({
                    "cliente": (
                        f"El cliente ha excedido su límite de crédito."
                        f" Límite: ${cliente.limite_credito:.3f},"
                        f" Saldo proyectado:"
                        f" ${(saldo_actual + nuevo_total):.3f}"
                    )
                })

            # ISO 27001 - Validación de Cartera Vencida (bloqueo estricto)
            import datetime
            cartera_vencida = PedidoVenta.objects.filter(
                cliente=cliente,
                esta_pagado=False,
                fecha_vencimiento__lt=datetime.date.today()
            ).exists()

            if cartera_vencida:
                raise serializers.ValidationError({
                    "cliente": (
                        "OPERACIÓN DENEGADA: El cliente mantiene deuda con"
                        " plazo vencido. Regularice el pago antes de emitir"
                        " nuevos pedidos."
                    )
                })

            # ISO 27001 - Validación de Contado
            if cliente.plazo_credito_dias == 0 and not esta_pagado:
                pedidos_impagos = PedidoVenta.objects.filter(cliente=cliente, esta_pagado=False).exists()
                if pedidos_impagos:
                    raise serializers.ValidationError({
                        "esta_pagado": (
                            "POLÍTICA DE CRÉDITO: Los clientes de 'Contado'"
                            " ya tienen un pedido pendiente de pago. Deben"
                            " cancelar la factura anterior antes de generar"
                            " un nuevo pedido."
                        )
                    })

        return data

    @transaction.atomic
    def create(self, validated_data):
        detalles_data = self.initial_data.get('detalles', [])

        cliente = validated_data.get('cliente')
        # Calcular fecha vencimiento
        import datetime
        plazo = cliente.plazo_credito_dias if cliente else 0
        validated_data['fecha_vencimiento'] = datetime.date.today() + datetime.timedelta(days=plazo)

        if 'valor_retencion' not in validated_data:
            validated_data['valor_retencion'] = self.initial_data.get('valor_retencion', 0)

        pedido = PedidoVenta.objects.create(**validated_data)

        for detalle_data in detalles_data:
            # We need to manually validate and save details because they are nested
            # Note: in a production app, we should use a proper nested serializer implementation
            # but for this specific logic, this is efficient.
            DetallePedido.objects.create(
                pedido_venta=pedido,
                producto_id=detalle_data.get('producto'),
                lote_id=detalle_data.get('lote'),
                cantidad=detalle_data.get('cantidad', 0),
                piezas=detalle_data.get('piezas', 0),
                peso=detalle_data.get('peso', 0),
                precio_unitario=detalle_data.get('precio_unitario', 0),
                incluye_iva=detalle_data.get('incluye_iva', True)
            )

        return pedido


class AnulacionPedidoSerializer(serializers.Serializer):
    motivo_anulacion = serializers.CharField(required=True, min_length=10)

    def validate_motivo_anulacion(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("El motivo debe tener al menos 10 caracteres.")
        return value.strip()


class ModificacionPedidoSerializer(serializers.Serializer):
    guia_remision = serializers.CharField(required=False, allow_blank=True)
    fecha_despacho = serializers.DateField(required=False, allow_null=True)
    valor_retencion = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, min_value=0)
    esta_pagado = serializers.BooleanField(required=False)
    motivo = serializers.CharField(required=True, min_length=10)

    def validate_motivo(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("El motivo debe tener al menos 10 caracteres.")
        return value.strip()
