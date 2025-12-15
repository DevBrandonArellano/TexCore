from rest_framework import serializers
from .models import MovimientoInventario, StockBodega
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
    producto = serializers.StringRelatedField()
    lote = serializers.StringRelatedField()
    bodega_origen = serializers.StringRelatedField()
    bodega_destino = serializers.StringRelatedField()
    usuario = serializers.StringRelatedField()

    class Meta:
        model = MovimientoInventario
        fields = '__all__'

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
