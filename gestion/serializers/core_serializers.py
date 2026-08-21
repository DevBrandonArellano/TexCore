import logging

from django.contrib.auth.models import Group
from rest_framework import serializers

from gestion.models import Sede, Area, CustomUser, Bodega

from ._common import ALPHANUMERIC_ACCENTS_REGEX

logger = logging.getLogger(__name__)


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
