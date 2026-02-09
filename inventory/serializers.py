from rest_framework import serializers
from .models import MovimientoInventario, StockBodega, AuditoriaMovimiento
from gestion.models import Bodega, Producto, LoteProduccion


class StockBodegaSerializer(serializers.ModelSerializer):
    """
    Serializer para ver el stock actual en las bodegas.
    """
    bodega = serializers.StringRelatedField()
    producto = serializers.StringRelatedField()
    lote = serializers.StringRelatedField()

    class Meta:
        model = StockBodega
        fields = ['id', 'bodega', 'producto', 'lote', 'cantidad']

class MovimientoInventarioSerializer(serializers.ModelSerializer):
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    lote = serializers.PrimaryKeyRelatedField(queryset=LoteProduccion.objects.all(), required=False, allow_null=True)
    bodega_origen = serializers.PrimaryKeyRelatedField(queryset=Bodega.objects.all(), required=False, allow_null=True)
    bodega_destino = serializers.PrimaryKeyRelatedField(queryset=Bodega.objects.all(), required=False, allow_null=True)
    usuario = serializers.StringRelatedField(read_only=True)
    saldo_resultante = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True) # Este campo es calculado, no de entrada

    class Meta:
        model = MovimientoInventario
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['producto'] = str(instance.producto)
        representation['lote'] = str(instance.lote) if instance.lote else None
        representation['bodega_origen'] = str(instance.bodega_origen) if instance.bodega_origen else None
        representation['bodega_destino'] = str(instance.bodega_destino) if instance.bodega_destino else None
        return representation

class TransferenciaSerializer(serializers.Serializer):
    """
    Serializer para validar los datos de entrada de una transferencia entre bodegas.
    """
    producto_id = serializers.PrimaryKeyRelatedField(
        queryset=Producto.objects.all(), source='producto'
    )
    bodega_origen_id = serializers.PrimaryKeyRelatedField(
        queryset=Bodega.objects.all(), source='bodega_origen'
    )
    bodega_destino_id = serializers.PrimaryKeyRelatedField(
        queryset=Bodega.objects.all(), source='bodega_destino'
    )
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0.01)
    lote_id = serializers.PrimaryKeyRelatedField(
        queryset=LoteProduccion.objects.all(), source='lote', required=False, allow_null=True
    )
    documento_ref = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """
        Valida que la bodega de origen y destino no sean la misma.
        """
        if data['bodega_origen'] == data['bodega_destino']:
            raise serializers.ValidationError("La bodega de origen y destino no pueden ser la misma.")
        return data

class KardexSerializer(serializers.ModelSerializer):
    """
    Serializer para presentar los datos del historial de un producto en formato Kardex.
    """
    tipo_movimiento = serializers.CharField(source='get_tipo_movimiento_display')
    entrada = serializers.SerializerMethodField()
    salida = serializers.SerializerMethodField()
    bodega_actual_id = None # Campo para almacenar el contexto de la bodega

    class Meta:
        model = MovimientoInventario
        fields = ['fecha', 'tipo_movimiento', 'documento_ref', 'entrada', 'salida']

    def get_entrada(self, obj):
        if obj.bodega_destino_id == self.bodega_actual_id:
            return obj.cantidad
        return ""

    def get_salida(self, obj):
        if obj.bodega_origen_id == self.bodega_actual_id:
            return obj.cantidad
        return ""


class AuditoriaMovimientoSerializer(serializers.ModelSerializer):
    """
    Serializer para el historial de auditoría de movimientos.
    """
    usuario_modificador_nombre = serializers.SerializerMethodField()
    
    class Meta:
        model = AuditoriaMovimiento
        fields = [
            'id', 'fecha_modificacion', 'usuario_modificador', 
            'usuario_modificador_nombre', 'campo_modificado', 
            'valor_anterior', 'valor_nuevo', 'razon_cambio'
        ]
    
    def get_usuario_modificador_nombre(self, obj):
        if obj.usuario_modificador:
            return obj.usuario_modificador.get_full_name() or obj.usuario_modificador.username
        return "Sistema"


class MovimientoInventarioUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para actualizar movimientos de inventario.
    Solo permite editar cantidad y documento_ref.
    """
    razon_cambio = serializers.CharField(write_only=True, required=True, min_length=10)
    
    class Meta:
        model = MovimientoInventario
        fields = ['cantidad', 'documento_ref', 'razon_cambio']
    
    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value
    
    def validate_razon_cambio(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Debe proporcionar una razón detallada del cambio (mínimo 10 caracteres)"
            )
        return value.strip()
