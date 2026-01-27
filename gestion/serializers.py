from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import Group
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)
class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Custom claims
        token['username'] = user.username
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['email'] = user.email

        token['sede'] = user.sede_id
        token['area'] = user.area_id

        # ADD GROUP IDS
        token['groups'] = list(user.groups.values_list('id', flat=True))

        # Optional: permissions
        token['permissions'] = list(
            user.user_permissions.values_list('codename', flat=True)
        )

        return token

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'

class BodegaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bodega
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
        extra_kwargs = {
            'password': {'write_only': True}, 
            'superior': {'read_only': True},
            'email': {'required': False, 'allow_blank': True}
        }

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

    def validate(self, data):
        # On updates, 'groups' might not be in the payload. We get them from the instance.
        # On creates, 'groups' will be in data or None.
        groups = data.get('groups', None)
        if groups is None and self.instance:
            groups = self.instance.groups.all()
        
        sede = data.get('sede', None)
        # If sede is not being updated, get it from the instance
        if sede is None and self.instance:
            sede = self.instance.sede

        # If there are no groups assigned yet (e.g., during initial creation steps),
        # we can't validate yet, so we allow it to proceed.
        if not groups:
            return data

        # Check if any of the assigned groups is 'admin_sistemas'
        is_admin_sistemas = any(group.name == 'admin_sistemas' for group in groups)

        # If the user is not an 'admin_sistemas' and no 'sede' is provided, raise an error.
        if not is_admin_sistemas and not sede:
            raise serializers.ValidationError({"sede": "La sede es requerida para todos los roles excepto para el Administrador de Sistemas."})

        return data

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

class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
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
    ultima_compra = serializers.SerializerMethodField()

    class Meta:
        model = Cliente
        fields = '__all__'

    def get_ultima_compra(self, obj):
        # Obtener el último pedido.
        # Gracias al prefetch_related en la vista, esto debería ser eficiente si se hace con cuidado,
        # pero para garantizar orden, usaremos la consulta normal (que Django cacheará si es posible)
        # o filtraremos en memoria si ya está prefetched.
        # Dado que 'pedidoventa_set' devuelve un manager, podemos re-consultar o ordenar en Python.
        
        # Opcion mas segura y simple: Query normal (optimizado por prefetch si se accede correctamente)
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
            "fecha": last_order.fecha_pedido,
            "id_pedido": last_order.id,
            "items": items
        }

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



class RegistrarLoteProduccionSerializer(serializers.Serializer):

    codigo_lote = serializers.CharField(max_length=100)

    peso_neto_producido = serializers.DecimalField(max_digits=10, decimal_places=2)

    maquina = serializers.CharField(max_length=100, required=False, allow_blank=True)

    turno = serializers.CharField(max_length=50, required=False, allow_blank=True)

    hora_inicio = serializers.DateTimeField(required=False)

    hora_final = serializers.DateTimeField(required=False)



    def validate_peso_neto_producido(self, value):

        if value <= 0:

            raise serializers.ValidationError("El peso neto producido debe ser un número positivo.")

        return value
