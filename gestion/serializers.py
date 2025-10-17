from rest_framework import serializers
from .models import Sede, Area, CustomUser, Material, Batch, Inventory, ProcessStep, MaterialMovement, Chemical, Formula, FormulaChemical
import re

ALPHANUMERIC_ACCENTS_REGEX = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$')

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'

    def validate_nombre(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'

    def validate_nombre(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}, 'superior': {'read_only': True}}

    def validate_email(self, value):
        # DRF EmailField already validates; ensure string and strip
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

    def validate_date_of_birth(self, value):
        from datetime import date
        if value is None:
            return value
        today = date.today()
        # compute age
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age > 80:
            raise serializers.ValidationError('La edad no puede ser mayor a 80 años.')
        if value > today:
            raise serializers.ValidationError('La fecha de nacimiento no puede ser futura.')
        return value

    def validate(self, attrs):
        request_method = getattr(getattr(self.context, 'request', None), 'method', None)
        # Creation: require sede and area
        if request_method == 'POST':
            if attrs.get('sede') is None:
                raise serializers.ValidationError({'sede': 'Este campo es obligatorio.'})
            if attrs.get('area') is None:
                raise serializers.ValidationError({'area': 'Este campo es obligatorio.'})
        # Update: if provided, cannot be null
        if request_method in ('PUT', 'PATCH'):
            if 'sede' in attrs and attrs.get('sede') is None:
                raise serializers.ValidationError({'sede': 'No puede ser nulo.'})
            if 'area' in attrs and attrs.get('area') is None:
                raise serializers.ValidationError({'area': 'No puede ser nulo.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=['password'])
        return user

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'

    def validate_name(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_unit_of_measure(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'

    def validate_code(self, value):
        if not re.match(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 -]+$', value or ''):
            raise serializers.ValidationError('Solo letras, números, espacios y guiones (Ñ y acentos permitidos).')
        return value

    def validate_unit_of_measure(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate(self, attrs):
        for field in ('initial_quantity', 'current_quantity'):
            v = attrs.get(field)
            if v is not None and v < 0:
                raise serializers.ValidationError({field: 'Debe ser un número mayor o igual a 0.'})
        return attrs

class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = '__all__'

    def validate_quantity(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Debe ser un número mayor o igual a 0.')
        return value

class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = '__all__'

    def validate_name(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_description(self, value):
        # Allow punctuation basic but prevent dangerous characters; relax as needed
        if value and not re.match(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ,.()-]*$', value):
            raise serializers.ValidationError('Descripción contiene caracteres no permitidos.')
        return value

class MaterialMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialMovement
        fields = '__all__'

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Cantidad debe ser un número mayor a 0.')
        return value

    def validate_movement_type(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

class ChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemical
        fields = '__all__'

    def validate_code(self, value):
        if not re.match(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 -]+$', value or ''):
            raise serializers.ValidationError('Solo letras, números, espacios y guiones (Ñ y acentos permitidos).')
        return value

    def validate_name(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_unit_of_measure(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_current_stock(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('Debe ser un número mayor o igual a 0.')
        return value

class FormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Formula
        fields = '__all__'

    def validate_name(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_description(self, value):
        if value and not re.match(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ,.()-]*$', value):
            raise serializers.ValidationError('Descripción contiene caracteres no permitidos.')
        return value

class FormulaChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormulaChemical
        fields = '__all__'

    def validate_unit_of_measure(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate_quantity(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Cantidad debe ser un número mayor a 0.')
        return value
