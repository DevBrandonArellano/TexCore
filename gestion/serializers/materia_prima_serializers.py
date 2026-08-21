from rest_framework import serializers

from gestion.models import MateriaPrimaLote, ConsumoMateriaPrima, Proveedor, Producto, Bodega


class MateriaPrimaLoteSerializer(serializers.ModelSerializer):
    cantidad_disponible = serializers.SerializerMethodField()
    proveedor_nombre = serializers.ReadOnlyField(source='proveedor.nombre')
    producto_descripcion = serializers.ReadOnlyField(source='producto.descripcion')
    bodega_nombre = serializers.ReadOnlyField(source='bodega_recepcion.nombre')

    class Meta:
        model = MateriaPrimaLote
        fields = [
            'id', 'producto', 'producto_descripcion', 'proveedor', 'proveedor_nombre',
            'lote_proveedor', 'fecha_recepcion', 'cantidad_kg', 'costo_unitario',
            'certificado_calidad', 'numero_documento_entrada',
            'bodega_recepcion', 'bodega_nombre',
            'cantidad_consumida', 'cantidad_disponible', 'completamente_consumida',
            'sede', 'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'cantidad_consumida', 'completamente_consumida', 'sede']

    def get_cantidad_disponible(self, obj):
        return float(obj.cantidad_disponible)


class RegistrarMateriaPrimaSerializer(serializers.Serializer):
    """Entrada del endpoint registrar_entrada — la creación real la hace el servicio."""
    proveedor = serializers.PrimaryKeyRelatedField(queryset=Proveedor.objects.all())
    producto = serializers.PrimaryKeyRelatedField(queryset=Producto.objects.all())
    lote_proveedor = serializers.CharField(max_length=100)
    cantidad_kg = serializers.DecimalField(max_digits=12, decimal_places=3)
    costo_unitario = serializers.DecimalField(max_digits=12, decimal_places=3)
    bodega_recepcion = serializers.PrimaryKeyRelatedField(queryset=Bodega.objects.all())
    fecha_recepcion = serializers.DateField()
    numero_documento_entrada = serializers.CharField(required=False, allow_blank=True, max_length=100)


class ConsumoMateriaPrimaSerializer(serializers.ModelSerializer):
    materia_prima_lote_codigo = serializers.ReadOnlyField(source='materia_prima_lote.lote_proveedor')
    proveedor_nombre = serializers.ReadOnlyField(source='materia_prima_lote.proveedor.nombre')

    class Meta:
        model = ConsumoMateriaPrima
        fields = [
            'id', 'lote_produccion', 'materia_prima_lote', 'materia_prima_lote_codigo',
            'proveedor_nombre', 'cantidad_kg', 'porcentaje_utilizado', 'fecha_consumo', 'usuario',
        ]
        read_only_fields = fields  # inmutable desde API (ISO 27001 A.12.4)
