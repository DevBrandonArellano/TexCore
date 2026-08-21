from rest_framework import serializers


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
