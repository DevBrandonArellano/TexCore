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
        fields = ['id', 'numero', 'es_oficial', 'motivo', 'fecha', 'creada_por', 'creada_por_nombre']
        read_only_fields = fields


class VersionFormulaSerializer(VersionFormulaResumenSerializer):
    class Meta(VersionFormulaResumenSerializer.Meta):
        fields = VersionFormulaResumenSerializer.Meta.fields + ['snapshot']
        read_only_fields = fields


class AprobarFormulaSerializer(serializers.Serializer):
    motivo = serializers.CharField(min_length=10)


class CrearVarianteSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=100)
    nombre_color = serializers.CharField(max_length=100)


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

    class Meta:
        model = FormulaColor
        fields = [
            'id', 'codigo', 'nombre_color', 'description', 'tipo_sustrato',
            'tipo_sustrato_display', 'version', 'version_oficial', 'estado', 'estado_display',
            'creado_por', 'creado_por_nombre', 'fecha_creacion', 'fecha_modificacion',
            'observaciones', 'sede', 'fases',
        ]
        read_only_fields = ['fecha_creacion', 'fecha_modificacion', 'creado_por']

    def get_version_oficial(self, obj):
        # FormulaColorViewSet.get_queryset lo anota con un Subquery (sin N+1); el
        # fallback cubre instancias recién creadas o actualizadas.
        if hasattr(obj, 'numero_version_oficial'):
            return obj.numero_version_oficial
        return obj.versiones.filter(es_oficial=True).values_list('numero', flat=True).first()


class FormulaColorWriteSerializer(ConservarOmitidosEnPutMixin, serializers.ModelSerializer):
    fases = FaseRecetaEscrituraSerializer(many=True, required=False, default=list)
    _justificacion_auditoria = serializers.CharField(write_only=True, required=False)
    # Regla 3: editar una fórmula aprobada exige motivo y crea una versión nueva.
    motivo = serializers.CharField(write_only=True, required=False, min_length=10)

    class Meta:
        model = FormulaColor
        fields = [
            'id', 'codigo', 'nombre_color', 'description', 'tipo_sustrato',
            'version', 'estado', 'observaciones', 'sede', 'fases', '_justificacion_auditoria', 'motivo',
        ]
        # `version` refleja el número de la versión oficial y lo mantiene VersionadoFormulaService.
        read_only_fields = ['version']

    def to_representation(self, instance):
        # La respuesta de create/update es la representación de lectura completa
        # (fases con proceso, version_oficial...), igual que en list/retrieve.
        return FormulaColorSerializer(instance, context=self.context).data

    def validate_estado(self, value):
        # Solo /aprobar/ aprueba (crea la versión oficial); el estado no se cambia por PUT/POST.
        actual = self.instance.estado if self.instance else 'en_pruebas'
        if value != actual:
            raise serializers.ValidationError(
                'El estado no se modifica directamente: use la acción "aprobar" '
                '(POST /formula-colors/{id}/aprobar/).')
        return value

    def validate(self, attrs):
        if self.instance and self.instance.estado == 'aprobada' and not attrs.get('motivo'):
            raise serializers.ValidationError({
                'motivo': 'Modificar una formula aprobada exige un motivo: se creara una version nueva.'})
        return attrs

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
        motivo = validated_data.pop('motivo', None)
        justificacion = validated_data.pop('_justificacion_auditoria', None) or motivo
        if justificacion:
            instance._justificacion_auditoria = justificacion

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        try:
            instance.save()
        except DjangoValidationError as e:
            raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)

        if fases_data is not None:
            # Recreamos las fases para simplificar la sincronización (Drop and Create)
            from gestion.middleware import set_cascade_justification, clear_cascade_justification
            set_cascade_justification(justificacion)
            try:
                instance.fases.all().delete()
            finally:
                clear_cascade_justification()
            self._crear_fases(instance, fases_data)

        if instance.estado == 'aprobada':
            from gestion.services.versionado_formula import VersionadoFormulaService
            try:
                version = VersionadoFormulaService.versionar(instance, motivo, self.context['request'].user)
            except DjangoValidationError as e:
                raise DRFValidationError(e.message_dict if hasattr(e, 'message_dict') else e.messages)
            instance.refresh_from_db()
            # La instancia viene anotada por get_queryset con la oficial previa
            instance.numero_version_oficial = version.numero

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
