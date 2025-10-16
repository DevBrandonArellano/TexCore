from rest_framework import serializers
from .models import Sede, Area, CustomUser, Material, Batch, Inventory, ProcessStep, MaterialMovement, Chemical, Formula, FormulaChemical

class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = '__all__'

class AreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Area
        fields = '__all__'

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'password', 'first_name', 'last_name', 'email', 'sede', 'area', 'date_of_birth', 'superior')
        extra_kwargs = {'password': {'write_only': True}, 'superior': {'read_only': True}}

class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
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
    class Meta:
        model = MaterialMovement
        fields = '__all__'

class ChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chemical
        fields = '__all__'

class FormulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Formula
        fields = '__all__'

class FormulaChemicalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FormulaChemical
        fields = '__all__'
