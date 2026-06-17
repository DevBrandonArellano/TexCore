from .models import FaseReceta
from gestion.models import MateriaPrimaLote, ConsumoMateriaPrima, CostoLoteProduccion
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.models import Group
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente, PagoCliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Maquina,
    Proveedor, DescargaQuimicoOP, ComponenteMezclaOP, ConsumoLoteDetalle,
    AreaProcessStep, OrdenProduccionSubproceso, EtapaProduccion, TransferenciaInterarea
)
from django.db import transaction
import re
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class MachineEfficiencySerializer(serializers.Serializer):
    maquina_id = serializers.IntegerField()
    maquina_nombre = serializers.CharField()
    capacidad_maxima = serializers.DecimalField(max_digits=10, decimal_places=2)
    produccion_total = serializers.DecimalField(max_digits=12, decimal_places=3)
    eficiencia = serializers.DecimalField(max_digits=5, decimal_places=2)  # Porcentaje


class OperatorDesempenoSerializer(serializers.Serializer):
    operario_id = serializers.IntegerField()
    username = serializers.CharField()
    total_lotes = serializers.IntegerField()
    produccion_total_kg = serializers.DecimalField(max_digits=12, decimal_places=3)
    promedio_kg_por_lote = serializers.DecimalField(max_digits=12, decimal_places=3)
    horas_trabajadas_aprox = serializers.FloatField()
    productividad_kg_hora = serializers.FloatField()


class AreaEfficiencyReportSerializer(serializers.Serializer):
    area_id = serializers.IntegerField()
    area_nombre = serializers.CharField()
    fecha_reporte = serializers.DateField()
    maquinas = MachineEfficiencySerializer(many=True)
    operarios = OperatorDesempenoSerializer(many=True)
    produccion_total_area = serializers.DecimalField(max_digits=15, decimal_places=3)
    eficiencia_promedio_area = serializers.DecimalField(max_digits=5, decimal_places=2)


ALPHANUMERIC_ACCENTS_REGEX = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$')


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
        required=False,
        allow_empty=True
    )
    _justificacion_auditoria = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Bodega
        fields = ['id', 'nombre', 'sede', 'usuarios_asignados', '_justificacion_auditoria']

    def create(self, validated_data):
        usuarios = validated_data.pop('usuarios_asignados', [])
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        bodega = Bodega.objects.create(**validated_data)
        if justificacion:
            bodega._justificacion_auditoria = justificacion
            bodega.save()
        if usuarios:
            bodega.usuarios_asignados.set(usuarios)
        return bodega

    def update(self, instance, validated_data):
        usuarios = validated_data.pop('usuarios_asignados', None)
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        if justificacion:
            instance._justificacion_auditoria = justificacion
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if usuarios is not None:
            instance.usuarios_asignados.set(usuarios)
        return instance


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name')


class SedeSerializer(serializers.ModelSerializer):
    num_areas = serializers.IntegerField(read_only=True)
    num_users = serializers.IntegerField(read_only=True)
    num_bodegas = serializers.IntegerField(read_only=True)
    num_ordenes = serializers.IntegerField(read_only=True)
    num_pedidos = serializers.IntegerField(read_only=True)

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
    bodega_entrada_nombre = serializers.CharField(source='bodega_entrada.nombre', read_only=True)
    bodega_salida_nombre = serializers.CharField(source='bodega_salida.nombre', read_only=True)

    class Meta:
        model = Maquina
        fields = [
            'id', 'nombre', 'capacidad_maxima', 'eficiencia_ideal',
            'estado', 'area', 'area_nombre', 'operarios', 'operarios_nombres',
            'producto_merma', 'bodega_merma', 'bodega_entrada', 'bodega_entrada_nombre',
            'bodega_salida', 'bodega_salida_nombre',
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
        fields = (
            'id',
            'username',
            'password',
            'first_name',
            'last_name',
            'email',
            'sede',
            'area',
            'date_of_birth',
            'superior',
            'groups')
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

        area = data.get('area', None)
        if area is None and self.instance:
            area = self.instance.area

        # Si se proporciona área pero no sede, inferimos la sede del área
        if area and not sede:
            data['sede'] = area.sede
            sede = area.sede

        # Validar consistencia entre área y sede
        if area and sede and area.sede != sede:
            raise serializers.ValidationError(
                {"area": f"El área '{area.nombre}' no pertenece a la sede '{sede.nombre}'."})

        # If there are no groups assigned yet (e.g., during initial creation steps),
        # we can't validate yet, so we allow it to proceed.
        if not groups:
            return data

        # Check if any of the assigned groups is 'admin_sistemas'
        is_admin_sistemas = any(group.name == 'admin_sistemas' for group in groups)

        # If the user is not an 'admin_sistemas' and no 'sede' is provided, raise an error.
        if not is_admin_sistemas and not sede:
            raise serializers.ValidationError(
                {"sede": "La sede es requerida para todos los roles excepto para el Administrador de Sistemas."})

        return data

    def _ensure_ejecutivo_has_all_bodegas(self, user):
        """Ejecutivos tienen acceso a todo el dashboard de stock: asignar todas las bodegas."""
        if user.groups.filter(name='ejecutivo').exists():
            all_bodegas = list(Bodega.objects.values_list('id', flat=True))
            user.bodegas_asignadas.set(all_bodegas)

    def create(self, validated_data):
        groups_data = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
        if groups_data:
            user.groups.set(groups_data)
        user.save()
        self._ensure_ejecutivo_has_all_bodegas(user)
        return user

    def update(self, instance, validated_data):
        groups_data = validated_data.pop('groups', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if groups_data is not None:
            instance.groups.set(groups_data)
        instance.save()
        self._ensure_ejecutivo_has_all_bodegas(instance)
        return instance


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = '__all__'


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'


class DetalleFormulaSerializer(serializers.ModelSerializer):
    producto_descripcion = serializers.CharField(
        source='producto.descripcion', read_only=True
    )
    producto_codigo = serializers.CharField(
        source='producto.codigo', read_only=True
    )

    class Meta:
        model = DetalleFormula
        fields = [
            'id', 'fase', 'producto', 'producto_descripcion', 'producto_codigo',
            'gramos_por_kilo', 'tipo_calculo', 'concentracion_gr_l', 'porcentaje',
            'orden_adicion', 'notas',
        ]
        extra_kwargs = {
            'fase': {'required': False, 'allow_null': True},
        }

    def validate(self, data):
        tipo_calculo = data.get('tipo_calculo', 'gr_l')

        if tipo_calculo == 'gr_l' and not data.get('concentracion_gr_l'):
            raise serializers.ValidationError({
                'concentracion_gr_l': 'Este campo es requerido cuando el tipo de calculo es gr/L.'
            })
        if tipo_calculo == 'pct' and not data.get('porcentaje'):
            raise serializers.ValidationError({
                'porcentaje': 'Este campo es requerido cuando el tipo de calculo es % de agotamiento.'
            })
        return data


class DetalleFormulaEscrituraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleFormula
        fields = [
            'id', 'producto', 'gramos_por_kilo', 'tipo_calculo',
            'concentracion_gr_l', 'porcentaje', 'orden_adicion', 'notas',
        ]


class FaseRecetaSerializer(serializers.ModelSerializer):
    detalles = DetalleFormulaSerializer(many=True, read_only=True)
    nombre_display = serializers.CharField(
        source='get_nombre_display', read_only=True
    )

    class Meta:
        model = FaseReceta
        fields = ['id', 'nombre', 'nombre_display', 'orden', 'temperatura', 'tiempo', 'observaciones', 'detalles']


class FaseRecetaEscrituraSerializer(serializers.ModelSerializer):
    detalles = DetalleFormulaEscrituraSerializer(many=True, required=False, default=list)

    class Meta:
        model = FaseReceta
        fields = ['id', 'nombre', 'orden', 'temperatura', 'tiempo', 'observaciones', 'detalles']


class FormulaColorSerializer(serializers.ModelSerializer):
    fases = FaseRecetaSerializer(many=True, read_only=True)
    creado_por_nombre = serializers.CharField(
        source='creado_por.username', read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display', read_only=True
    )
    tipo_sustrato_display = serializers.CharField(
        source='get_tipo_sustrato_display', read_only=True
    )

    class Meta:
        model = FormulaColor
        fields = [
            'id', 'codigo', 'nombre_color', 'description', 'tipo_sustrato',
            'tipo_sustrato_display', 'version', 'estado', 'estado_display',
            'creado_por', 'creado_por_nombre', 'fecha_creacion', 'fecha_modificacion',
            'observaciones', 'sede', 'fases',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion', 'creado_por']


class FormulaColorWriteSerializer(serializers.ModelSerializer):
    fases = FaseRecetaEscrituraSerializer(many=True, required=False, default=list)
    _justificacion_auditoria = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = FormulaColor
        fields = [
            'id', 'codigo', 'nombre_color', 'description', 'tipo_sustrato',
            'version', 'estado', 'observaciones', 'sede', 'fases', '_justificacion_auditoria',
        ]

    def validate_fases(self, fases_data):
        productos_vistos = set()
        for i, fase_data in enumerate(fases_data):
            for j, detalle in enumerate(fase_data.get('detalles', [])):
                producto = detalle.get('producto')
                if producto:
                    if producto.id in productos_vistos:
                        raise serializers.ValidationError(
                            f'El insumo "{producto.descripcion}" aparece mas de una vez. '
                            'No se permiten insumos duplicados en la misma formula general.'
                        )
                    productos_vistos.add(producto.id)

                tipo_calculo = detalle.get('tipo_calculo', 'gr_l')
                if tipo_calculo == 'gr_l' and not detalle.get('concentracion_gr_l'):
                    raise serializers.ValidationError(
                        f'El insumo en la posicion {j + 1} de la fase {i + 1} requiere el campo concentracion_gr_l '
                        'cuando tipo_calculo es gr/L.'
                    )
                if tipo_calculo == 'pct' and not detalle.get('porcentaje'):
                    raise serializers.ValidationError(
                        f'El insumo en la posicion {j + 1} de la fase {i + 1} requiere el campo porcentaje '
                        'cuando tipo_calculo es % de agotamiento.'
                    )
        return fases_data

    @transaction.atomic
    def create(self, validated_data):
        fases_data = validated_data.pop('fases', [])
        _ = validated_data.pop('_justificacion_auditoria', None)  # No se requiere para create
        formula = FormulaColor.objects.create(**validated_data)
        for fase_data in fases_data:
            detalles_data = fase_data.pop('detalles', [])
            fase = FaseReceta.objects.create(formula=formula, **fase_data)
            for detalle_data in detalles_data:
                DetalleFormula.objects.create(fase=fase, **detalle_data)
        return formula

    @transaction.atomic
    def update(self, instance, validated_data):
        fases_data = validated_data.pop('fases', None)
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        if justificacion:
            instance._justificacion_auditoria = justificacion

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if fases_data is not None:
            # Recreamos las fases para simplificar la sincronización (Drop and Create)
            from gestion.middleware import set_cascade_justification, clear_cascade_justification
            set_cascade_justification(justificacion)
            try:
                instance.fases.all().delete()
            finally:
                clear_cascade_justification()
            for fase_data in fases_data:
                detalles_data = fase_data.pop('detalles', [])
                fase = FaseReceta.objects.create(formula=instance, **fase_data)
                for detalle_data in detalles_data:
                    DetalleFormula.objects.create(fase=fase, **detalle_data)

        return instance


class DosificacionSerializer(serializers.Serializer):
    """
    Serializer de entrada para el endpoint de calculo de dosificacion.
    """
    kg_tela = serializers.DecimalField(
        max_digits=10, decimal_places=3,
        help_text='Peso de la tela en kilogramos.'
    )
    relacion_bano = serializers.DecimalField(
        max_digits=6, decimal_places=2,
        help_text='Relacion de bano (litros de agua por kg de tela). Ej: 10 para 1:10.'
    )

    def validate_kg_tela(self, value):
        if value <= 0:
            raise serializers.ValidationError('El peso de la tela debe ser mayor a cero.')
        return value

    def validate_relacion_bano(self, value):
        if value <= 0:
            raise serializers.ValidationError('La relacion de bano debe ser mayor a cero.')
        return value


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


class OrdenProduccionEstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrdenProduccion
        fields = ['estado']

    def validate_estado(self, value):
        estado_actual = self.instance.estado if self.instance else None

        # Validar lógica de negocio textilera
        if estado_actual == 'finalizada' and value != 'finalizada':
            raise serializers.ValidationError("No se puede retornar una orden finalizada a estados anteriores.")

        return value


class ComponenteMezclaOPSerializer(serializers.ModelSerializer):
    producto_detail = serializers.SerializerMethodField(read_only=True)
    bodega_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ComponenteMezclaOP
        fields = ['id', 'orden', 'producto', 'producto_detail', 'bodega', 'bodega_detail',
                  'porcentaje', 'cantidad_kg']
        read_only_fields = ['cantidad_kg']

    def get_producto_detail(self, obj):
        return {
            'id': obj.producto.id,
            'codigo': obj.producto.codigo,
            'descripcion': obj.producto.descripcion,
            'tipo': obj.producto.tipo,
        }

    def get_bodega_detail(self, obj):
        return {'id': obj.bodega.id, 'nombre': obj.bodega.nombre}

    def validate_porcentaje(self, value):
        if value <= 0 or value > 100:
            raise serializers.ValidationError(
                'El porcentaje debe ser mayor a 0 y máximo 100.'
            )
        return value

    def validate(self, data):
        # Calcula cantidad_kg automáticamente
        orden = data.get('orden') or (self.instance.orden if self.instance else None)
        if orden and 'porcentaje' in data:
            data['cantidad_kg'] = (
                data['porcentaje'] / Decimal('100') * orden.peso_neto_requerido
            ).quantize(Decimal('0.001'))
        return data


class OrdenProduccionSerializer(serializers.ModelSerializer):
    componentes_mezcla = ComponenteMezclaOPSerializer(many=True, read_only=True)
    producto_entrada_detail = serializers.SerializerMethodField(read_only=True)
    producto_salida_detail = serializers.SerializerMethodField(read_only=True)
    peso_producido = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)

    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'codigo', 'estado', 'prioridad',
            'producto_entrada', 'producto_entrada_detail',
            'producto_salida', 'producto_salida_detail',
            'bodega_entrada', 'bodega_salida',
            'bodega_quimicos', 'formula_color',
            'peso_neto_requerido', 'peso_producido',
            'area', 'sede',
            'maquina_asignada', 'operario_asignado',
            'observaciones', 'inventario_descontado',
            'fecha_inicio_planificada', 'fecha_fin_planificada',
            'componentes_mezcla',
        ]
        read_only_fields = ['peso_producido', 'inventario_descontado']
        extra_kwargs = {
            'producto_entrada': {'required': False, 'allow_null': True},
            'producto_salida': {'required': False, 'allow_null': True},
            'bodega_entrada': {'required': False, 'allow_null': True},
            'bodega_salida': {'required': False, 'allow_null': True},
            'maquina_asignada': {'required': False, 'allow_null': True},
            'operario_asignado': {'required': False, 'allow_null': True},
        }

    def get_producto_entrada_detail(self, obj):
        p = obj.producto_entrada
        if not p:
            return None
        return {'id': p.id, 'codigo': p.codigo, 'descripcion': p.descripcion, 'tipo': p.tipo}

    def get_producto_salida_detail(self, obj):
        p = obj.producto_salida
        if not p:
            return None
        return {'id': p.id, 'codigo': p.codigo, 'descripcion': p.descripcion, 'tipo': p.tipo}

    def validate(self, data):
        # Validación laxa para creación inicial (Jefe de Planta)
        # Solo requiere: codigo, peso_neto_requerido, area
        if self.instance is None:  # Creación
            if not data.get('codigo'):
                raise serializers.ValidationError({'codigo': 'Código es requerido.'})
            if not data.get('peso_neto_requerido'):
                raise serializers.ValidationError({'peso_neto_requerido': 'Peso requerido es obligatorio.'})
            if not data.get('area'):
                raise serializers.ValidationError({'area': 'Área es obligatoria.'})
        else:  # Actualización (Jefe de Área completando detalles)
            componentes = data.get('componentes_mezcla', [])
            if componentes:
                total = sum(c.get('porcentaje', 0) for c in componentes)
                if abs(total - Decimal('100')) > Decimal('0.01'):
                    raise serializers.ValidationError({
                        'componentes_mezcla': f'La suma de porcentajes debe ser 100%. Actual: {total}%'
                    })
        return data


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
                # La validación "si difiere más del 5% del peso requerido"
                # es tricky porque una Orden puede tener N lotes.
                # Asumiremos que el user quiere validar que el Lote no
                # exceda algo absurdo o si la orden es de 1 solo lote.
                # O quizás el requerimiento se refiere a que el Peso Neto
                # del Lote vs Peso Neto Producido reportado anteriormente?
                # Interpretación: "Si el neto difiere más del 5% del peso
                # requerido en la OrdenProduccion".
                # Si la orden es de 100kg, y el lote pesa 10kg, es normal.
                # Probablemente sea: Si es el ÚNICO lote, o validación
                # por lote estándar?
                # Voy a implementar log de advertencia si la diferencia
                # es notable con respecto al promedio/esperado?
                # REQUERIMIENTO: "Si el neto difiere más del 5% del
                # peso requerido...
                # genera alerta logs, pero permite guardar".

                diff = abs(peso_neto_calculado - peso_requerido)
                if diff > (peso_requerido * Decimal('0.05')):
                    logger.warning(
                        f"ALERTA EMPAQUETADO: Lote"
                        f" {data.get('codigo_lote', 'N/A')}"
                        f" peso neto {peso_neto_calculado}"
                        f" difiere >5% de orden {peso_requerido}"
                    )

        return data


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


class RegistrarLoteProduccionSerializer(serializers.Serializer):
    codigo_lote = serializers.CharField(max_length=100, required=False, allow_blank=True)
    peso_neto_producido = serializers.DecimalField(max_digits=10, decimal_places=2)
    maquina = serializers.PrimaryKeyRelatedField(queryset=Maquina.objects.all(), required=False, allow_null=True)
    operario = serializers.IntegerField(required=False, allow_null=True)
    turno = serializers.CharField(max_length=50, required=False, allow_blank=True)
    hora_inicio = serializers.DateTimeField(required=False, allow_null=True)
    hora_final = serializers.DateTimeField(required=False, allow_null=True)
    peso_bruto = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    tara = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    peso_merma = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal('0'))
    tipo_merma = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    unidades_empaque = serializers.IntegerField(required=False, default=1)
    presentacion = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cantidad_metros = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    completar_orden = serializers.BooleanField(required=False, default=False)

    def validate_peso_neto_producido(self, value):
        if value <= 0:
            raise serializers.ValidationError("El peso neto producido debe ser un número positivo.")
        return value

    def validate(self, data):
        if data.get('peso_merma', Decimal('0')) > 0 and not data.get('tipo_merma'):
            raise serializers.ValidationError({
                'tipo_merma': 'tipo_merma es obligatorio cuando peso_merma > 0.'
            })
        return data


class ConsumoInputSerializer(serializers.Serializer):
    lote_origen_id = serializers.IntegerField()
    cantidad_kg = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    genera_nuevo_lote = serializers.BooleanField(default=True)
    bodega_id = serializers.IntegerField()
    producto_id = serializers.IntegerField()


class RegistrarLoteSerializer(serializers.Serializer):
    codigo_lote = serializers.CharField(required=False, allow_blank=True)
    peso_neto_producido = serializers.DecimalField(
        max_digits=12, decimal_places=3, min_value=Decimal('0.001')
    )
    peso_merma = serializers.DecimalField(
        max_digits=12, decimal_places=3, default=Decimal('0'), min_value=Decimal('0')
    )
    tipo_merma = serializers.ChoiceField(
        choices=['maquina', 'material', 'setup', 'corte', 'otro'], required=False, allow_blank=True
    )
    clasificacion_calidad = serializers.ChoiceField(
        choices=['primera', 'segunda', 'saldo'], default='primera'
    )
    maquina = serializers.IntegerField(required=False, allow_null=True)
    operario = serializers.IntegerField(required=False, allow_null=True)
    turno = serializers.CharField(required=False, default='', allow_blank=True)
    hora_inicio = serializers.DateTimeField(required=False, allow_null=True)
    hora_final = serializers.DateTimeField(required=False, allow_null=True)
    unidades_empaque = serializers.IntegerField(default=1, min_value=1)
    presentacion = serializers.CharField(default='cono')
    consumos = ConsumoInputSerializer(many=True, required=False)
    completar_orden = serializers.BooleanField(default=False)

    def validate(self, data):
        if data.get('peso_merma', Decimal('0')) > 0 and not data.get('tipo_merma'):
            raise serializers.ValidationError({
                'tipo_merma': 'tipo_merma es obligatorio cuando peso_merma > 0.'
            })
        return data


class DescargaQuimicoOPSerializer(serializers.ModelSerializer):
    """
    Serializer read-only para registrar detalles de descarga de químicos por OP.
    Patrón: Entidad de Dominio auditada con trazabilidad.
    """
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    bodega_nombre = serializers.CharField(source='bodega.nombre', read_only=True)
    descargado_por_nombre = serializers.CharField(source='descargado_por.username', read_only=True)

    class Meta:
        model = DescargaQuimicoOP
        fields = [
            'id', 'orden_produccion', 'producto', 'producto_codigo', 'producto_descripcion',
            'fase', 'bodega', 'bodega_nombre', 'tipo_calculo',
            'cantidad_calculada_kg', 'cantidad_real_kg', 'estado',
            'fecha_descarga', 'descargado_por', 'descargado_por_nombre', 'justificacion'
        ]
        read_only_fields = [
            'id', 'fecha_descarga', 'descargado_por', 'descargado_por_nombre',
            'producto_codigo', 'producto_descripcion', 'bodega_nombre'
        ]


class StockQuimicoSerializer(serializers.Serializer):
    """
    Serializer para endpoint stock-quimicos: lista de químicos disponibles con alerta.
    Patrón: Proxy que enriquece datos de StockBodega con información de alerta.
    """
    producto_id = serializers.IntegerField()
    producto_codigo = serializers.CharField()
    producto_descripcion = serializers.CharField()
    cantidad = serializers.DecimalField(max_digits=12, decimal_places=3)
    stock_minimo = serializers.DecimalField(max_digits=12, decimal_places=3)
    alerta = serializers.BooleanField()
    bodega_nombre = serializers.CharField()


class ConsumoLoteDetalleSerializer(serializers.ModelSerializer):
    lote_origen_codigo = serializers.CharField(source='lote_origen.codigo_lote', read_only=True)

    class Meta:
        model = ConsumoLoteDetalle
        fields = ['id', 'lote_produccion', 'lote_origen', 'lote_origen_codigo',
                  'cantidad_consumida', 'genera_nuevo_lote']
        read_only_fields = ['id', 'lote_produccion', 'lote_origen', 'lote_origen_codigo']


# ============================================================================
# F0-001 / F0-002: Trazabilidad de Materia Prima y Costeo (Sprint 6)
# ============================================================================


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


class CostoLoteProduccionSerializer(serializers.ModelSerializer):
    lote_codigo = serializers.ReadOnlyField(source='lote_produccion.codigo_lote')

    class Meta:
        model = CostoLoteProduccion
        fields = [
            'id', 'lote_produccion', 'lote_codigo',
            'costo_materia_prima', 'costo_quimicos', 'costo_operario',
            'costo_maquina', 'otros_costos', 'total_costo',
            'precio_venta_esperado', 'margen_bruto', 'margen_bruto_pct',
            'calculado_en', 'recalculado_en',
        ]
        read_only_fields = fields


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ['id', 'name', 'description']


class AreaProcessStepSerializer(serializers.ModelSerializer):
    proceso_nombre = serializers.CharField(source='proceso.name', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)

    class Meta:
        model = AreaProcessStep
        fields = [
            'id', 'area', 'area_nombre', 'proceso', 'proceso_nombre',
            'orden', 'tipo_flujo', 'es_bloqueante'
        ]


class OrdenProduccionSubprocesoSerializer(serializers.ModelSerializer):
    proceso_nombre = serializers.CharField(source='area_proceso.proceso.name', read_only=True)
    area_nombre = serializers.CharField(source='area_proceso.area.nombre', read_only=True)
    usuario_responsable_nombre = serializers.CharField(source='usuario_responsable.get_full_name', read_only=True)
    duracion_minutos = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OrdenProduccionSubproceso
        fields = [
            'id', 'orden_produccion', 'area_proceso', 'proceso_nombre', 'area_nombre',
            'estado', 'fecha_inicio_planificada', 'fecha_inicio_real', 'fecha_fin_real',
            'usuario_responsable', 'usuario_responsable_nombre', 'observaciones',
            'motivo_rechazo', 'fecha_creacion', 'fecha_modificacion', 'duracion_minutos'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion', 'duracion_minutos']

    def get_duracion_minutos(self, obj):
        return obj.duracion_minutos


class EtapaProduccionSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    bodega_entrada_nombre = serializers.CharField(source='bodega_entrada.nombre', read_only=True)
    bodega_salida_nombre = serializers.CharField(source='bodega_salida.nombre', read_only=True)

    class Meta:
        model = EtapaProduccion
        fields = [
            'id', 'area', 'area_nombre', 'nombre', 'orden',
            'maquina', 'maquina_nombre',
            'bodega_entrada', 'bodega_entrada_nombre',
            'bodega_salida', 'bodega_salida_nombre',
            'tiempo_procesamiento_minutos',
            'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']


class TransferenciaInterareaSerializer(serializers.ModelSerializer):
    orden_area_origen_codigo = serializers.CharField(source='orden_area_origen.codigo', read_only=True)
    orden_area_destino_codigo = serializers.CharField(source='orden_area_destino.codigo', read_only=True)
    bodega_origen_nombre = serializers.CharField(source='bodega_origen.nombre', read_only=True)
    bodega_destino_nombre = serializers.CharField(source='bodega_destino.nombre', read_only=True)
    usuario_responsable_nombre = serializers.CharField(source='usuario_responsable.get_full_name', read_only=True)
    orden_area_origen = OrdenProduccionSerializer(read_only=True)
    orden_area_destino = OrdenProduccionSerializer(read_only=True)

    class Meta:
        model = TransferenciaInterarea
        fields = [
            'id', 'orden_area_origen', 'orden_area_origen_codigo',
            'orden_area_destino', 'orden_area_destino_codigo',
            'bodega_origen', 'bodega_origen_nombre',
            'bodega_destino', 'bodega_destino_nombre',
            'cantidad_transferida', 'fecha_transferencia',
            'usuario_responsable', 'usuario_responsable_nombre',
            'observaciones', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion', 'usuario_responsable', 'fecha_transferencia']
