from rest_framework import serializers
from django.contrib.auth.models import Group
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, Inventory, ProcessStep,
    MaterialMovement, Chemical, FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)
...
class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'

class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'
import re

ALPHANUMERIC_ACCENTS_REGEX = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$')

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'

    def validate_nombre(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

class CustomUserSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=Group.objects.all(), required=False)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'sede', 'area', 'date_of_birth', 'superior', 'groups')
        extra_kwargs = {'password': {'write_only': True}, 'superior': {'read_only': True}}

    def validate_email(self, value):
        if value is None:
            return value
        value = value.strip()
        return value

    def validate_first_name(self, value):
        if value and not ALPHANUMERIC_ACCENTS_REGEX.match(value):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_last_name(self, value):
        if value and not ALPHANUMERIC_ACCENTS_REGEX.match(value):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def create(self, validated_data):
        groups_data = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
        if groups_data:
            user.groups.set(groups_data)
        user.save()
        return user

    def update(self, instance, validated_data):
        groups_data = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
        if groups_data is not None:
            user.groups.set(groups_data)
        user.save()
        return user

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = '__all__'

class MaterialMovementSerializer(serializers.ModelSerializer):
    productId = serializers.SerializerMethodField()
    productName = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    areaId = serializers.SerializerMethodField()
    areaName = serializers.SerializerMethodField()
    sedeId = serializers.SerializerMethodField()
    sedeName = serializers.SerializerMethodField()
    operarioId = serializers.SerializerMethodField()
    operarioName = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    class Meta:
        model = MaterialMovement
        fields = [
            'id', 'producto', 'quantity', 'movement_type', 'responsible_user',
            'from_sede', 'from_area', 'to_sede', 'to_area', 'notes', 'timestamp',
            'status', 'productId', 'productName', 'type', 'unit', 'areaId', 'areaName',
            'sedeId', 'sedeName', 'operarioId', 'operarioName', 'date'
        ]
        read_only_fields = [
            'status', 'productId', 'productName', 'type', 'unit', 'areaId', 'areaName',
            'sedeId', 'sedeName', 'operarioId', 'operarioName', 'date', 'timestamp'
        ]

    def get_productId(self, obj):
        return obj.producto.id if obj.producto else None

    def get_productName(self, obj):
        return obj.producto.descripcion if obj.producto else None

    def get_type(self, obj):
        return 'ingreso' if obj.movement_type == 'in' else 'egreso'

    def get_unit(self, obj):
        return obj.producto.unidad_medida if obj.producto else None

    def get_areaId(self, obj):
        if obj.movement_type == 'in':
            return obj.to_area.id if obj.to_area else None
        return obj.from_area.id if obj.from_area else None

    def get_areaName(self, obj):
        if obj.movement_type == 'in':
            return obj.to_area.nombre if obj.to_area else None
        return obj.from_area.nombre if obj.from_area else None

    def get_sedeId(self, obj):
        if obj.movement_type == 'in':
            return obj.to_sede.id if obj.to_sede else None
        return obj.from_sede.id if obj.from_sede else None

    def get_sedeName(self, obj):
        if obj.movement_type == 'in':
            return obj.to_sede.nombre if obj.to_sede else None
        return obj.from_sede.nombre if obj.from_sede else None
    
    def get_operarioId(self, obj):
        return obj.responsible_user.id if obj.responsible_user else None

    def get_operarioName(self, obj):
        return obj.responsible_user.username if obj.responsible_user else None

    def get_date(self, obj):
        return obj.timestamp


class ChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemical
        fields = '__all__'

class FormulaColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormulaColor
        fields = '__all__'

class DetalleFormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleFormula
        fields = '__all__'

class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = '__all__'

class OrdenProduccionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.descripcion', read_only=True)
    formula_color_nombre = serializers.CharField(source='formula_color.nombre_color', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)

    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'codigo', 'producto', 'formula_color', 'peso_neto_requerido',
            'estado', 'fecha_creacion', 'sede', 'producto_nombre',
            'formula_color_nombre', 'sede_nombre'
        ]

class LoteProduccionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoteProduccion
        fields = '__all__'

class PedidoVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedidoVenta
        fields = '__all__'

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = '__all__'