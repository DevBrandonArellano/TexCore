from rest_framework import serializers
from django.db import transaction

from gestion.models import Batch, ProcessStep, DetalleFormula, FaseReceta, FormulaColor


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = '__all__'


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ['id', 'name', 'description']


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
