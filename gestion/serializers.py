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
    usuarios_asignados = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=CustomUser.objects.all(),
        required=False
    )

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

class PedidoVentaResumenSerializer(serializers.ModelSerializer):
    """
    Serializer minimalista para mostrar el historial de pedidos dentro del cliente.
    """
    total = serializers.SerializerMethodField()

    class Meta:
        model = PedidoVenta
        fields = ['id', 'fecha_pedido', 'esta_pagado', 'total', 'guia_remision', 'estado']

    def get_total(self, obj):
        from django.db.models import Sum, F
        total = obj.detalles.aggregate(
            total=Sum(F('peso') * F('precio_unitario'), output_field=models.DecimalField())
        )['total'] or 0
        return total

class ClienteSerializer(serializers.ModelSerializer):
    ultima_compra = serializers.SerializerMethodField()
    saldo_pendiente = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    pedidos = PedidoVentaResumenSerializer(source='pedidoventa_set', many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = [
            'id', 'ruc_cedula', 'nombre_razon_social', 'direccion_envio', 
            'nivel_precio', 'tiene_beneficio', 'limite_credito', 
            'saldo_pendiente', 'ultima_compra', 'pedidos'
        ]

    def validate_tiene_beneficio(self, value):
        user = self.context['request'].user
        # Check if the field is actually being changed
        if self.instance and self.instance.tiene_beneficio != value:
            is_authorized = user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'vendedor']).exists()
            if not is_authorized:
                raise serializers.ValidationError("No tienes permiso para modificar los beneficios de un cliente.")
        return value

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

    def validate(self, data):
        cliente = data.get('cliente')
        esta_pagado = data.get('esta_pagado', False)
        
        # We only care about validation if it's a new or existing unpaid order
        if cliente and not esta_pagado:
            # Calculate the total of the order being created/updated
            # This depends on whether we are doing nested creation or not.
            # Assuming for now standard creation. Often total is sent or calculated from details.
            # Since this is a check *before* creation, if details are nested, we use them.
            
            detalles_data = self.initial_data.get('detalles', [])
            nuevo_total = 0
            for d in detalles_data:
                peso = float(d.get('peso', 0))
                precio = float(d.get('precio_unitario', 0))
                nuevo_total += (peso * precio)
            
            from decimal import Decimal
            nuevo_total_dec = Decimal(str(nuevo_total))
            
            if (cliente.saldo_pendiente + nuevo_total_dec) > cliente.limite_credito:
                raise serializers.ValidationError({
                    "cliente": f"El cliente ha excedido su límite de crédito. Límite: ${cliente.limite_credito}, Saldo proyectado: ${cliente.saldo_pendiente + nuevo_total_dec}"
                })
        
        return data

class DetallePedidoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetallePedido
        fields = '__all__'

    def validate(self, data):
        producto = data.get('producto')
        precio_unitario = data.get('precio_unitario')
        
        if producto and precio_unitario is not None:
            if precio_unitario < producto.precio_base:
                raise serializers.ValidationError({
                    "precio_unitario": f"El precio unitario (${precio_unitario}) no puede ser menor al costo base del producto (${producto.precio_base})."
                })
        return data



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
