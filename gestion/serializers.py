from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import Group
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente, PagoCliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Maquina
)
from django.db import models, transaction
import re
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

ALPHANUMERIC_ACCENTS_REGEX = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$')

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

class MaquinaSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    operarios_nombres = serializers.SerializerMethodField()

    class Meta:
        model = Maquina
        fields = [
            'id', 'nombre', 'capacidad_maxima', 'eficiencia_ideal', 
            'estado', 'area', 'area_nombre', 'operarios', 'operarios_nombres'
        ]
        extra_kwargs = {
            'operarios': {'required': False}
        }

    def get_operarios_nombres(self, obj):
        return [u.username for u in obj.operarios.all()]

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
                    "precio_unitario": f"El precio unitario (${precio_unitario}) no puede ser menor al costo base del producto (${producto.precio_base})."
                })
        return data

class PedidoVentaResumenSerializer(serializers.ModelSerializer):
    """
    Serializer minimalista para mostrar el historial de pedidos dentro del cliente.
    """
    total = serializers.SerializerMethodField()

    vendedor_nombre = serializers.ReadOnlyField(source='vendedor_asignado.username')
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = PedidoVenta
        fields = ['id', 'fecha_pedido', 'esta_pagado', 'total', 'guia_remision', 'estado', 'vendedor_nombre', 'cliente', 'sede', 'detalles']

    def get_total(self, obj):
        from django.db.models import Sum, F
        total = obj.detalles.aggregate(
            total=Sum(F('peso') * F('precio_unitario'), output_field=models.DecimalField())
        )['total'] or 0
        return total

class PagoClienteSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_razon_social')
    
    class Meta:
        model = PagoCliente
        fields = ['id', 'cliente', 'cliente_nombre', 'fecha', 'monto', 'metodo_pago', 'comprobante', 'notas', 'sede']

class ClienteSerializer(serializers.ModelSerializer):
    ultima_compra = serializers.SerializerMethodField()
    saldo_pendiente = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    pedidos = PedidoVentaResumenSerializer(source='pedidoventa_set', many=True, read_only=True)
    pagos = PagoClienteSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = [
            'id', 'ruc_cedula', 'nombre_razon_social', 'direccion_envio', 
            'nivel_precio', 'tiene_beneficio', 'limite_credito', 
            'saldo_pendiente', 'ultima_compra', 'pedidos', 'pagos', 'vendedor_asignado'
        ]
        extra_kwargs = {
            'vendedor_asignado': {'read_only': True}
        }

    def validate_tiene_beneficio(self, value):
        user = self.context['request'].user
        # Check if the field is actually being changed
        if self.instance and self.instance.tiene_beneficio != value:
            is_authorized = user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'vendedor']).exists()
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
            "fecha": last_order.fecha_pedido,
            "id_pedido": last_order.id,
            "items": items
        }

class OrdenProduccionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.descripcion', read_only=True)
    formula_color_nombre = serializers.CharField(source='formula_color.nombre_color', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    maquina_asignada_nombre = serializers.CharField(source='maquina_asignada.nombre', read_only=True)
    operario_asignado_nombre = serializers.CharField(source='operario_asignado.username', read_only=True)

    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'codigo', 'producto', 'formula_color', 'peso_neto_requerido',
            'estado', 'fecha_creacion', 'sede', 'area', 'area_nombre', 'producto_nombre',
            'formula_color_nombre', 'sede_nombre', 'fecha_inicio_planificada',
            'fecha_fin_planificada', 'maquina_asignada', 'maquina_asignada_nombre',
            'operario_asignado', 'operario_asignado_nombre',
            'observaciones'
        ]

class LoteProduccionSerializer(serializers.ModelSerializer):
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    operario_nombre = serializers.CharField(source='operario.username', read_only=True)
    
    class Meta:
        model = LoteProduccion
        fields = '__all__'

    def validate(self, data):
        # 1. Validación de Peso Neto (Empaquetado)
        peso_bruto = data.get('peso_bruto')
        tara = data.get('tara')
        
        # Si se ingresan datos de empaquetado, validar consistencia
        if peso_bruto is not None and tara is not None:
             # Nota: Los campos Decimal vienen como Decimal o float dependiendo del parser.
             # Convertir a Decimal por seguridad.
             p_bruto = Decimal(str(peso_bruto))
             p_tara = Decimal(str(tara))
             
             if p_tara >= p_bruto:
                 raise serializers.ValidationError({"tara": "La tara no puede ser mayor o igual al peso bruto."})
                 
             peso_neto_calculado = p_bruto - p_tara
             
             # Verificar desviación si tenemos contexto de OrdenProduccion
             # Si se está creando (self.instance es None) o actualizando.
             # Si LoteProduccion tiene 'orden_produccion', podemos validar contra eso.
             orden = data.get('orden_produccion')
             if not orden and self.instance: 
                 orden = self.instance.orden_produccion
                 
             if orden:
                 peso_requerido = orden.peso_neto_requerido
                 # Supongamos que este Lote es PARTE de la orden.
                 # La validación "si difiere más del 5% del peso requerido" es tricky porque una Orden puede tener N lotes.
                 # Asumiremos que el user quiere validar que el Lote no exceda algo absurdo o si la orden es de 1 solo lote.
                 # O quizás el requerimiento se refiere a que el Peso Neto del Lote vs Peso Neto Producido reportado anteriormente?
                 # Interpretación: "Si el neto difiere más del 5% del peso requerido en la OrdenProduccion". 
                 # Si la orden es de 100kg, y el lote pesa 10kg, es normal.
                 # Probablemente sea: Si es el ÚNICO lote, o validación por lote estándar?
                 # Voy a implementar log de advertencia si la diferencia es notable con respecto al promedio/esperado?
                 # REQUERIMIENTO: "Si el neto difiere más del 5% del peso requerido... genera alerta logs, pero permite guardar".
                 
                 diff = abs(peso_neto_calculado - peso_requerido)
                 if diff > (peso_requerido * Decimal('0.05')):
                      logger.warning(f"ALERTA EMPAQUETADO: Lote {data.get('codigo_lote', 'N/A')} peso neto {peso_neto_calculado} difiere >5% de orden {peso_requerido}")

        return data

class PedidoVentaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre_razon_social')
    vendedor_nombre = serializers.ReadOnlyField(source='vendedor_asignado.username')
    sede_nombre = serializers.ReadOnlyField(source='sede.nombre')
    detalles = DetallePedidoSerializer(many=True, read_only=True)

    class Meta:
        model = PedidoVenta
        fields = [
            'id', 'cliente', 'cliente_nombre', 'vendedor_nombre', 'guia_remision', 'fecha_pedido', 
            'fecha_despacho', 'estado', 'esta_pagado', 'sede', 'sede_nombre', 'detalles'
        ]

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

    @transaction.atomic
    def create(self, validated_data):
        detalles_data = self.initial_data.get('detalles', [])
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
                precio_unitario=detalle_data.get('precio_unitario', 0)
            )
        
        return pedido

        return data

class RegistrarLoteProduccionSerializer(serializers.Serializer):
    codigo_lote = serializers.CharField(max_length=100)
    peso_neto_producido = serializers.DecimalField(max_digits=10, decimal_places=2)
    maquina = serializers.PrimaryKeyRelatedField(queryset=Maquina.objects.all(), required=False, allow_null=True)
    turno = serializers.CharField(max_length=50, required=False, allow_blank=True)
    hora_inicio = serializers.DateTimeField(required=False)
    hora_final = serializers.DateTimeField(required=False)
    peso_bruto = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    tara = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    unidades_empaque = serializers.IntegerField(required=False, default=1)
    presentacion = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate_peso_neto_producido(self, value):
        if value <= 0:
            raise serializers.ValidationError("El peso neto producido debe ser un número positivo.")
        return value
