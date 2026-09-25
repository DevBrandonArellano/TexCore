from rest_framework import serializers
from django.db import transaction

from ._common import ConservarOmitidosEnPutMixin
from gestion.models import (
    ProcessStep, DetalleFormula, FaseReceta, FormulaColor, ProcesoTintoreria, VersionFormula,
)


class ProcessStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessStep
        fields = ['id', 'name', 'description']


class ProcesoTintoreriaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = ProcesoTintoreria
        fields = ['id', 'codigo', 'nombre', 'tipo', 'tipo_display', 'descripcion', 'activo', 'sede']

    def validate(self, attrs):
        # La sede suele llegar por SedeAutoAssignMixin en perform_create, fuera del alcance
        # del UniqueTogetherValidator de DRF: se valida aquí contra la sede efectiva.
        request = self.context.get('request')
        sede = attrs.get('sede') or getattr(getattr(request, 'user', None), 'sede', None)
        codigo = attrs.get('codigo')
        if ProcesoTintoreria.objects.filter(codigo=codigo, sede=sede).exists():
            raise serializers.ValidationError({'codigo': f'Ya existe un proceso con codigo "{codigo}" en esta sede.'})
        return attrs


class DetalleFormulaSerializer(ConservarOmitidosEnPutMixin, serializers.ModelSerializer):
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
    proceso_codigo = serializers.CharField(source='proceso.codigo', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.nombre', read_only=True)

    class Meta:
        model = FaseReceta
        fields = [
            'id', 'proceso', 'proceso_codigo', 'proceso_nombre',
            'ciclo', 'orden', 'temperatura', 'tiempo', 'observaciones', 'detalles',
        ]


class FaseRecetaEscrituraSerializer(serializers.ModelSerializer):
    """La fase se indica por `proceso` (id del catálogo ProcesoTintoreria de la sede de la
    fórmula; FormulaColorWriteSerializer valida la sede)."""
    detalles = DetalleFormulaEscrituraSerializer(many=True, required=False, default=list)
    proceso = serializers.PrimaryKeyRelatedField(queryset=ProcesoTintoreria.objects.all())

    class Meta:
        model = FaseReceta
        fields = ['id', 'proceso', 'ciclo', 'orden', 'temperatura', 'tiempo', 'observaciones', 'detalles']


class VersionFormulaResumenSerializer(serializers.ModelSerializer):
    creada_por_nombre = serializers.CharField(source='creada_por.username', read_only=True, default=None)

    class Meta:
        model = VersionFormula
        fields = ['id', 'numero', 'es_oficial', 'motivo', 'observaciones', 'fecha', 'creada_por', 'creada_por_nombre']
        read_only_fields = fields


class VersionFormulaSerializer(VersionFormulaResumenSerializer):
    class Meta(VersionFormulaResumenSerializer.Meta):
        fields = VersionFormulaResumenSerializer.Meta.fields + ['snapshot']
        read_only_fields = fields


class CrearVersionSerializer(serializers.Serializer):
    """Entrada de POST /formula-colors/{id}/versiones/ (spec 2026-09-24 D7): congela
    la receta viva como un ensayo nuevo, sin marcarlo oficial."""
    observaciones = serializers.CharField(min_length=10)


class CrearVarianteSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=100)
    nombre_color = serializers.CharField(max_length=100)


class DerivarFormulaSerializer(serializers.Serializer):
    """Entrada de POST /formula-colors/{id}/derivar/ (spec 2026-09-24 §5.7, D9)."""
    codigo = serializers.CharField(max_length=100)
    nombre_color = serializers.CharField(max_length=100)
    tipo_sustrato = serializers.ChoiceField(choices=FormulaColor.TIPO_SUSTRATO_CHOICES, required=False)
    version_origen = serializers.IntegerField(min_value=1)
    motivo_derivacion = serializers.CharField(required=False, allow_blank=True, default='')
    es_laboratorio = serializers.BooleanField(required=False, default=False)


class FormulaColorSerializer(serializers.ModelSerializer):
    fases = FaseRecetaSerializer(many=True, read_only=True)
    # Número de la versión oficial vigente; None si la fórmula nunca se aprobó.
    version_oficial = serializers.SerializerMethodField()
    creado_por_nombre = serializers.CharField(
        source='creado_por.username', read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display', read_only=True
    )
    tipo_sustrato_display = serializers.CharField(
        source='get_tipo_sustrato_display', read_only=True
    )
    # Derivación (spec 2026-09-24 §5.7): de dónde nació esta fórmula, si aplica.
    formula_origen_codigo = serializers.CharField(source='formula_origen.codigo', read_only=True, default=None)
    version_origen_numero = serializers.IntegerField(source='version_origen.numero', read_only=True, default=None)

    class Meta:
        model = FormulaColor
        fields = [
            'id', 'codigo', 'nombre_color', 'description', 'tipo_sustrato',
            'tipo_sustrato_display', 'version', 'version_oficial', 'estado', 'estado_display',
            'creado_por', 'creado_por_nombre', 'fecha_creacion', 'fecha_modificacion',
            'observaciones', 'sede', 'fases',
            'formula_origen', 'formula_origen_codigo', 'version_origen', 'version_origen_numero',
            'motivo_derivacion', 'es_laboratorio',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion', 'creado_por']

    def get_version_oficial(self, obj):
        # FormulaColorViewSet.get_queryset lo anota con un Subquery (sin N+1); el
        # fallback cubre instancias recién creadas o actualizadas.
        if hasattr(obj, 'numero_version_oficial'):
            return obj.numero_version_oficial
        return obj.versiones.filter(es_oficial=True).values_list('numero', flat=True).first()


class FormulaColorWriteSerializer(ConservarOmitidosEnPutMixin, serializers.ModelSerializer):
    """Edita la receta viva de la fórmula. Desde D7 esto ya NO crea versiones por sí
    solo: para congelar el estado actual como un ensayo hay que llamar aparte a
    POST /formula-colors/{id}/versiones/ (acción `crear_version`, con `observaciones`)."""
    fases = FaseRecetaEscrituraSerializer(many=True, required=False, default=list)
    _justificacion_auditoria = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = FormulaColor
        fields = [
            'id', 'codigo', 'nombre_color', 'description', 'tipo_sustrato',
            'version', 'estado', 'observaciones', 'sede', 'fases', '_justificacion_auditoria',
            'es_laboratorio',
        ]
        # `version` refleja el número de la versión oficial y lo mantiene VersionadoFormulaService.
        read_only_fields = ['version']

    def to_representation(self, instance):
        # La respuesta de create/update es la representación de lectura completa
        # (fases con proceso, version_oficial...), igual que en list/retrieve.
        return FormulaColorSerializer(instance, context=self.context).data

    def validate_estado(self, value):
        # El estado lo cambia VersionadoFormulaService.marcar_oficial(), no un PUT/POST directo.
        actual = self.instance.estado if self.instance else 'en_pruebas'
        if value != actual:
            raise serializers.ValidationError(
                'El estado no se modifica directamente: se fija al marcar una versión oficial '
                '(POST /formula-colors/{id}/versiones/{n}/marcar-oficial/).')
        return value

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

    @staticmethod
    def _crear_fases(formula, fases_data):
        for fase_data in fases_data:
            detalles_data = fase_data.pop('detalles', [])
            proceso = fase_data.pop('proceso')
            if proceso.sede_id != formula.sede_id:
                raise serializers.ValidationError(
                    {'fases': f'El proceso "{proceso.codigo}" no pertenece a la sede de la formula.'})
            fase = FaseReceta.objects.create(formula=formula, proceso=proceso, **fase_data)
            for detalle_data in detalles_data:
                DetalleFormula.objects.create(fase=fase, **detalle_data)

    @transaction.atomic
    def create(self, validated_data):
        fases_data = validated_data.pop('fases', [])
        _ = validated_data.pop('_justificacion_auditoria', None)  # No se requiere para create
        validated_data.pop('motivo', None)
        formula = FormulaColor.objects.create(**validated_data)
        self._crear_fases(formula, fases_data)
        return formula

    @transaction.atomic
    def update(self, instance, validated_data):
        from django.core.exceptions import ValidationError as DjangoValidationError
        from rest_framework.exceptions import ValidationError as DRFValidationError

        fases_data = validated_data.pop('fases', None)
        justificacion = validated_data.pop('_justificacion_auditoria', None)
        if justificacion:
            instance._justificacion_auditoria = justificacion

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        try:
            instance.save()
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

        if fases_data is not None:
            # Recreamos las fases para simplificar la sincronización (Drop and Create).
            # Esto edita la receta VIVA (D1): las versiones ya congeladas son JSON
            # independiente y no se ven afectadas (regla 1, D7 — ver crear_version()).
            from gestion.middleware import set_cascade_justification, clear_cascade_justification
            set_cascade_justification(justificacion)
            try:
                instance.fases.all().delete()
            finally:
                clear_cascade_justification()
            self._crear_fases(instance, fases_data)

        return instance


class DosificacionSerializer(serializers.Serializer):
    """
    Serializer de entrada para el endpoint de calculo de dosificacion.

    Spec 2026-09-24 (D3): los litros son el dato canonico que fija el ingeniero
    tintorero; la relacion de bano se deriva (litros / peso), no se recibe.
    """
    peso = serializers.DecimalField(
        max_digits=10, decimal_places=3,
        help_text='Peso de la tela en kilogramos.'
    )
    litros = serializers.DecimalField(
        max_digits=10, decimal_places=2,
        help_text='Litros de bano fijados por el ingeniero tintorero.'
    )

    def validate_peso(self, value):
        if value <= 0:
            raise serializers.ValidationError('El peso debe ser mayor a cero.')
        return value

    def validate_litros(self, value):
        if value <= 0:
            raise serializers.ValidationError('Los litros de bano deben ser mayores a cero.')
        return value
