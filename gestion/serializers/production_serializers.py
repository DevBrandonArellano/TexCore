import logging
from decimal import Decimal

from rest_framework import serializers

from gestion.models import (
    Maquina, ParoMaquina, LineaProduccion, OrdenProduccion, ComponenteMezclaOP,
    TransformacionProducto, LoteProduccion, DescargaQuimicoOP, ConsumoLoteDetalle,
    CostoLoteProduccion, AreaProcessStep, OrdenProduccionSubproceso, EtapaProduccion,
    TransferenciaInterarea, ProcessStep,
)

from ._common import ALPHANUMERIC_ACCENTS_REGEX

logger = logging.getLogger(__name__)


class MaquinaSerializer(serializers.ModelSerializer):
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    operarios_nombres = serializers.SerializerMethodField()
    bodega_entrada_nombre = serializers.CharField(source='bodega_entrada.nombre', read_only=True)
    bodega_salida_nombre = serializers.CharField(source='bodega_salida.nombre', read_only=True)
    producto_merma_detail = serializers.SerializerMethodField()
    bodega_merma_detail = serializers.SerializerMethodField()

    class Meta:
        model = Maquina
        fields = [
            'id', 'nombre', 'capacidad_maxima', 'eficiencia_ideal',
            'estado', 'area', 'area_nombre', 'operarios', 'operarios_nombres',
            'producto_merma', 'producto_merma_detail', 'bodega_merma', 'bodega_merma_detail',
            'bodega_entrada', 'bodega_entrada_nombre',
            'bodega_salida', 'bodega_salida_nombre',
        ]
        extra_kwargs = {
            'operarios': {'required': False}
        }

    def get_operarios_nombres(self, obj):
        return [u.username for u in obj.operarios.all()]

    def get_producto_merma_detail(self, obj):
        if not obj.producto_merma:
            return None
        return {
            'id': obj.producto_merma.id,
            'codigo': obj.producto_merma.codigo,
            'descripcion': obj.producto_merma.descripcion,
            'tipo': obj.producto_merma.tipo,
        }

    def get_bodega_merma_detail(self, obj):
        if not obj.bodega_merma:
            return None
        return {
            'id': obj.bodega_merma.id,
            'nombre': obj.bodega_merma.nombre,
        }


class ParoMaquinaSerializer(serializers.ModelSerializer):
    """Downtime de máquina con reason code (Seis Grandes Pérdidas — OEE for Operators).
    Revalida fin > inicio aquí (además de ParoMaquina.clean()) para que la API
    devuelva 400 con el detalle del campo en vez de un 500 si el modelo lo rechaza."""
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    duracion_minutos = serializers.FloatField(read_only=True)

    class Meta:
        model = ParoMaquina
        fields = [
            'id', 'maquina', 'maquina_nombre', 'inicio', 'fin', 'categoria',
            'categoria_display', 'planificado', 'descripcion', 'turno',
            'usuario', 'duracion_minutos',
        ]
        extra_kwargs = {
            'usuario': {'required': False},
        }

    def validate(self, attrs):
        fin = attrs.get('fin', getattr(self.instance, 'fin', None))
        inicio = attrs.get('inicio', getattr(self.instance, 'inicio', None))
        if fin is not None and inicio is not None and fin <= inicio:
            raise serializers.ValidationError(
                {'fin': 'La fecha de fin debe ser posterior a la fecha de inicio.'})
        return attrs


class LineaProduccionSerializer(serializers.ModelSerializer):
    """Serializer de Células de Manufactura Flexibles.

    'compartida' es informativo para el Jefe de Área (recurso repartido entre
    líneas activas); la capacidad y las colas de trabajo se agregan por ÁREA,
    no por línea (evita duplicidad fantasma de capacidad)."""
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    maquinas = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Maquina.objects.all(), required=False)
    maquinas_detail = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = LineaProduccion
        fields = ['id', 'nombre', 'descripcion', 'estado', 'area', 'area_nombre',
                  'maquinas', 'maquinas_detail', 'fecha_creacion', 'fecha_modificacion']
        read_only_fields = ['fecha_creacion', 'fecha_modificacion']

    def get_maquinas_detail(self, obj):
        # 'compartida' = la máquina pertenece a MÁS DE UNA línea ACTIVA.
        # num_lineas_activas viene anotado por el Prefetch del ViewSet; el
        # fallback cubre usos del serializer fuera de ese queryset.
        detalle = []
        for m in obj.maquinas.all():
            num_activas = getattr(m, 'num_lineas_activas', None)
            if num_activas is None:
                num_activas = m.lineas_produccion.filter(estado='activa').count()
            detalle.append({
                'id': m.id, 'nombre': m.nombre, 'estado': m.estado,
                'compartida': num_activas > 1,
            })
        return detalle

    def validate_nombre(self, value):
        if not ALPHANUMERIC_ACCENTS_REGEX.match(value or ''):
            raise serializers.ValidationError('Solo letras, números y espacios (Ñ y acentos permitidos).')
        return value

    def validate(self, data):
        # Resolver valores efectivos en PATCH parcial
        area = data.get('area') or (self.instance.area if self.instance else None)
        maquinas = data.get('maquinas')
        if maquinas is None and self.instance:
            maquinas = list(self.instance.maquinas.all())

        # Regla 1: toda máquina de la línea debe pertenecer a su misma área.
        # Que una máquina ya esté en OTRA línea no es error: es el recurso
        # compartido de la célula flexible.
        if area and maquinas:
            ajenas = [m.nombre for m in maquinas if m.area_id != area.id]
            if ajenas:
                raise serializers.ValidationError(
                    {'maquinas': f"Estas máquinas no pertenecen al área '{area.nombre}': {', '.join(ajenas)}."})

        # Regla 2: un jefe_area (no admin) solo gestiona líneas de SU área
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if (user and not user.is_superuser
                and user.groups.filter(name='jefe_area').exists()
                and not user.groups.filter(name__in=['admin_sistemas', 'jefe_planta']).exists()):
            if area and area != user.area:
                raise serializers.ValidationError(
                    {'area': 'Solo puedes gestionar líneas de tu propia área.'})
        return data


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
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)

    class Meta:
        model = OrdenProduccion
        fields = [
            'id', 'codigo', 'estado', 'prioridad',
            'producto_entrada', 'producto_entrada_detail',
            'producto_salida', 'producto_salida_detail',
            'bodega_entrada', 'bodega_salida',
            'bodega_quimicos', 'formula_color',
            'peso_neto_requerido', 'peso_producido',
            'area', 'area_nombre', 'sede',
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


class TransformacionProductoSerializer(serializers.ModelSerializer):
    """Lectura/escritura de una transformación máquina a máquina.

    ``producto_entrada`` y ``merma`` son de solo lectura: los deriva/calcula el
    servicio (continuidad de cadena) y el modelo (merma), no el cliente.
    """
    producto_entrada_detail = serializers.SerializerMethodField(read_only=True)
    producto_salida_detail = serializers.SerializerMethodField(read_only=True)
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    operario_nombre = serializers.CharField(source='operario.username', read_only=True)

    class Meta:
        model = TransformacionProducto
        fields = [
            'id', 'orden_produccion', 'etapa', 'numero_secuencia',
            'producto_entrada', 'producto_entrada_detail',
            'producto_salida', 'producto_salida_detail',
            'maquina', 'maquina_nombre', 'operario', 'operario_nombre',
            'peso_entrada', 'peso_salida', 'merma',
            'cantidad_entrada', 'cantidad_salida',
            'fecha_inicio', 'fecha_fin', 'estado', 'observaciones',
            'fecha_creacion',
        ]
        read_only_fields = [
            'numero_secuencia', 'producto_entrada', 'merma',
            'orden_produccion', 'fecha_creacion',
        ]

    def get_producto_entrada_detail(self, obj):
        p = obj.producto_entrada
        return {'id': p.id, 'codigo': p.codigo, 'descripcion': p.descripcion} if p else None

    def get_producto_salida_detail(self, obj):
        p = obj.producto_salida
        return {'id': p.id, 'codigo': p.codigo, 'descripcion': p.descripcion} if p else None


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


class RegistrarLoteProduccionSerializer(serializers.Serializer):
    codigo_lote = serializers.CharField(max_length=100, required=False, allow_blank=True)
    peso_neto_producido = serializers.DecimalField(max_digits=10, decimal_places=2)
    maquina = serializers.PrimaryKeyRelatedField(queryset=Maquina.objects.all(), required=False, allow_null=True)
    operario = serializers.IntegerField(required=False, allow_null=True)
    turno = serializers.CharField(max_length=50, required=False, allow_blank=True)
    # NOT NULL en el modelo (LoteProduccion.hora_inicio/hora_final): antes eran
    # opcionales aquí y el INSERT fallaba con IntegrityError, que el view
    # reportaba (incorrectamente) como "código de lote duplicado".
    hora_inicio = serializers.DateTimeField()
    hora_final = serializers.DateTimeField()
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
        choices=['maquina', 'material', 'setup', 'corte', 'otro'], required=False, allow_blank=True, allow_null=True
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
    # orden_area_origen/orden_area_destino quedan como PrimaryKeyRelatedField
    # (auto-generados por ModelSerializer, escribibles) para que el create()
    # del ViewSet pueda persistirlos — son NOT NULL en el modelo. El detalle
    # anidado se expone aparte para no perder la representación completa en
    # las respuestas de lectura.
    orden_area_origen_detail = OrdenProduccionSerializer(source='orden_area_origen', read_only=True)
    orden_area_destino_detail = OrdenProduccionSerializer(source='orden_area_destino', read_only=True)

    class Meta:
        model = TransferenciaInterarea
        fields = [
            'id', 'orden_area_origen', 'orden_area_origen_detail', 'orden_area_origen_codigo',
            'orden_area_destino', 'orden_area_destino_detail', 'orden_area_destino_codigo',
            'bodega_origen', 'bodega_origen_nombre',
            'bodega_destino', 'bodega_destino_nombre',
            'cantidad_transferida', 'fecha_transferencia',
            'usuario_responsable', 'usuario_responsable_nombre',
            'observaciones'
        ]
        read_only_fields = ['usuario_responsable', 'fecha_transferencia']
