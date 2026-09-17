from decimal import Decimal
from rest_framework import serializers
from django.utils import timezone

from gestion.models import (
    CorridaProduccion,
    OperacionProduccion,
    ConsumoMaterial,
    ProduccionSalida,
    MermaDesperdicio,
    GenealogiaLote,
    Sede,
    Area,
    Maquina,
    LineaProduccion,
    ProcessStep,
    Producto,
    Bodega,
    LoteProduccion,
    OrdenProduccion,
    CustomUser,
    PlanProduccion,
    DetallePlanProduccion,
)


class ConsumoMaterialSerializer(serializers.ModelSerializer):
    lote_origen_codigo = serializers.CharField(source='lote_origen.codigo_lote', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    bodega_origen_nombre = serializers.CharField(source='bodega_origen.nombre', read_only=True)

    class Meta:
        model = ConsumoMaterial
        fields = [
            'id',
            'operacion',
            'lote_origen',
            'lote_origen_codigo',
            'producto',
            'producto_codigo',
            'producto_descripcion',
            'producto_unidad',
            'bodega_origen',
            'bodega_origen_nombre',
            'cantidad_consumida',
            'costo_unitario',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class ProduccionSalidaSerializer(serializers.ModelSerializer):
    lote_generado_codigo = serializers.CharField(source='lote_generado.codigo_lote', read_only=True)
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_descripcion = serializers.CharField(source='producto.descripcion', read_only=True)
    producto_unidad = serializers.CharField(source='producto.unidad_medida', read_only=True)
    bodega_destino_nombre = serializers.CharField(source='bodega_destino.nombre', read_only=True)

    class Meta:
        model = ProduccionSalida
        fields = [
            'id',
            'operacion',
            'lote_generado',
            'lote_generado_codigo',
            'producto',
            'producto_codigo',
            'producto_descripcion',
            'producto_unidad',
            'bodega_destino',
            'bodega_destino_nombre',
            'cantidad_neta',
            'clasificacion_calidad',
            'peso_bruto',
            'tara',
            'unidades_empaque',
            'cantidad_metros',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class MermaDesperdicioSerializer(serializers.ModelSerializer):
    tipo_merma_display = serializers.CharField(source='get_tipo_merma_display', read_only=True)
    producto_subproducto_codigo = serializers.CharField(source='producto_subproducto.codigo', read_only=True)
    bodega_subproducto_nombre = serializers.CharField(source='bodega_subproducto.nombre', read_only=True)
    lote_subproducto_codigo = serializers.CharField(source='lote_subproducto.codigo_lote', read_only=True)

    class Meta:
        model = MermaDesperdicio
        fields = [
            'id',
            'operacion',
            'peso_merma',
            'tipo_merma',
            'tipo_merma_display',
            'es_subproducto_vendible',
            'producto_subproducto',
            'producto_subproducto_codigo',
            'bodega_subproducto',
            'bodega_subproducto_nombre',
            'lote_subproducto',
            'lote_subproducto_codigo',
            'fecha_creacion',
        ]
        read_only_fields = ['id', 'fecha_creacion']


class OperacionProduccionSerializer(serializers.ModelSerializer):
    maquina_nombre = serializers.CharField(source='maquina.nombre', read_only=True)
    operario_nombre = serializers.CharField(source='operario.get_full_name', read_only=True)
    proceso_nombre = serializers.CharField(source='proceso.name', read_only=True)
    consumos = ConsumoMaterialSerializer(many=True, read_only=True)
    salidas = ProduccionSalidaSerializer(many=True, read_only=True)
    mermas = MermaDesperdicioSerializer(many=True, read_only=True)

    class Meta:
        model = OperacionProduccion
        fields = [
            'id',
            'corrida',
            'numero_secuencia',
            'maquina',
            'maquina_nombre',
            'proceso',
            'proceso_nombre',
            'operario',
            'operario_nombre',
            'hora_inicio',
            'hora_fin',
            'estado',
            'observaciones',
            'motivo_reversion',
            'consumos',
            'salidas',
            'mermas',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']


class CorridaProduccionSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    area_nombre = serializers.CharField(source='area.nombre', read_only=True)
    linea_nombre = serializers.CharField(source='linea.nombre', read_only=True)
    maquina_principal_nombre = serializers.CharField(source='maquina_principal.nombre', read_only=True)
    supervisor_nombre = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    orden_produccion_codigo = serializers.CharField(source='orden_produccion.codigo', read_only=True)
    plan_produccion_codigo = serializers.CharField(source='plan_produccion.codigo', read_only=True)
    operaciones_count = serializers.IntegerField(source='operaciones.count', read_only=True)

    class Meta:
        model = CorridaProduccion
        fields = [
            'id',
            'codigo',
            'sede',
            'sede_nombre',
            'area',
            'area_nombre',
            'linea',
            'linea_nombre',
            'maquina_principal',
            'maquina_principal_nombre',
            'modalidad',
            'orden_produccion',
            'orden_produccion_codigo',
            'plan_produccion',
            'plan_produccion_codigo',
            'detalle_plan',
            'pedido_venta',
            'turno',
            'fecha_jornada',
            'hora_inicio',
            'hora_fin',
            'estado',
            'supervisor',
            'supervisor_nombre',
            'observaciones',
            'operaciones_count',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']


# ============================================================================
# Serializers de Entrada (Input Validation)
# ============================================================================

class IniciarCorridaInputSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=100, required=False, allow_blank=True)
    sede_id = serializers.IntegerField(required=False)
    area_id = serializers.IntegerField(required=True)
    linea_id = serializers.IntegerField(required=False, allow_null=True)
    maquina_principal_id = serializers.IntegerField(required=False, allow_null=True)
    modalidad = serializers.ChoiceField(
        choices=CorridaProduccion.MODALIDAD_CHOICES,
        default='CONTINUA',
    )
    turno = serializers.CharField(max_length=50, default='Mañana')
    fecha_jornada = serializers.DateField(required=False)
    orden_produccion_id = serializers.IntegerField(required=False, allow_null=True)
    plan_produccion_id = serializers.IntegerField(required=False, allow_null=True)
    detalle_plan_id = serializers.IntegerField(required=False, allow_null=True)
    pedido_venta_id = serializers.IntegerField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)


class ConsumoInputSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(required=True)
    bodega_origen_id = serializers.IntegerField(required=True)
    cantidad_consumida = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    lote_origen_id = serializers.IntegerField(required=False, allow_null=True)
    costo_unitario = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, default=Decimal('0.000'))


class SalidaInputSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(required=True)
    bodega_destino_id = serializers.IntegerField(required=True)
    cantidad_neta = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    lote_generado_id = serializers.IntegerField(required=False, allow_null=True)
    codigo_lote = serializers.CharField(max_length=100, required=False, allow_blank=True)
    clasificacion_calidad = serializers.ChoiceField(
        choices=ProduccionSalida.CALIDAD_CHOICES,
        default='primera',
    )
    peso_bruto = serializers.DecimalField(max_digits=12, decimal_places=3, required=False)
    tara = serializers.DecimalField(max_digits=12, decimal_places=3, required=False, default=Decimal('0.000'))
    unidades_empaque = serializers.IntegerField(required=False, default=1, min_value=1)
    presentacion = serializers.CharField(max_length=100, required=False, default='cono')
    cantidad_metros = serializers.DecimalField(max_digits=12, decimal_places=4, required=False, allow_null=True)


class MermaInputSerializer(serializers.Serializer):
    peso_merma = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal('0.001'))
    tipo_merma = serializers.ChoiceField(
        choices=MermaDesperdicio.TIPO_MERMA_CHOICES,
        default='maquina',
    )
    es_subproducto_vendible = serializers.BooleanField(required=False, default=False)
    producto_subproducto_id = serializers.IntegerField(required=False, allow_null=True)
    bodega_subproducto_id = serializers.IntegerField(required=False, allow_null=True)
    lote_subproducto_id = serializers.IntegerField(required=False, allow_null=True)


class RegistroOperacionInputSerializer(serializers.Serializer):
    maquina_id = serializers.IntegerField(required=False, allow_null=True)
    operario_id = serializers.IntegerField(required=False, allow_null=True)
    proceso_id = serializers.IntegerField(required=False, allow_null=True)
    numero_secuencia = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    hora_inicio = serializers.DateTimeField(required=False)
    hora_fin = serializers.DateTimeField(required=False)
    observaciones = serializers.CharField(required=False, allow_blank=True)
    justificacion = serializers.CharField(required=False, allow_blank=True)
    tolerancia_balance = serializers.DecimalField(
        max_digits=6,
        decimal_places=3,
        required=False,
        default=Decimal('0.050'),
    )
    consumos = ConsumoInputSerializer(many=True, required=True)
    salidas = SalidaInputSerializer(many=True, required=True)
    mermas = MermaInputSerializer(many=True, required=False, default=list)


class RevertirOperacionInputSerializer(serializers.Serializer):
    operacion_id = serializers.IntegerField(required=True)
    justificacion = serializers.CharField(required=True, min_length=5)


class DetallePlanProduccionSerializer(serializers.ModelSerializer):
    producto_objetivo_codigo = serializers.CharField(source='producto_objetivo.codigo', read_only=True)
    producto_objetivo_descripcion = serializers.CharField(source='producto_objetivo.descripcion', read_only=True)
    producto_objetivo_unidad = serializers.CharField(source='producto_objetivo.unidad_medida', read_only=True)
    saldo_pendiente = serializers.DecimalField(max_digits=12, decimal_places=4, read_only=True)
    desviacion_porcentaje = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    cumplimiento_porcentaje = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePlanProduccion
        fields = [
            'id',
            'plan',
            'producto_objetivo',
            'producto_objetivo_codigo',
            'producto_objetivo_descripcion',
            'producto_objetivo_unidad',
            'cantidad_planificada',
            'cantidad_ejecutada',
            'cantidad_aceptada',
            'cantidad_segunda',
            'saldo_pendiente',
            'desviacion_porcentaje',
            'cumplimiento_porcentaje',
            'estado',
        ]
        read_only_fields = [
            'id',
            'cantidad_ejecutada',
            'cantidad_aceptada',
            'cantidad_segunda',
            'saldo_pendiente',
            'desviacion_porcentaje',
            'cumplimiento_porcentaje',
            'estado',
        ]


class PlanProduccionSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    supervisor_nombre = serializers.CharField(source='supervisor.get_full_name', read_only=True)
    detalles = DetallePlanProduccionSerializer(many=True, read_only=True)

    class Meta:
        model = PlanProduccion
        fields = [
            'id',
            'codigo',
            'sede',
            'sede_nombre',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'supervisor',
            'supervisor_nombre',
            'observaciones',
            'detalles',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']


class GenerarOrdenDesdePlanInputSerializer(serializers.Serializer):
    detalle_plan_id = serializers.IntegerField(required=True)
    bodega_salida_id = serializers.IntegerField(required=False, allow_null=True)
    bodega_entrada_id = serializers.IntegerField(required=False, allow_null=True)
    formula_color_id = serializers.IntegerField(required=False, allow_null=True)
    maquina_asignada_id = serializers.IntegerField(required=False, allow_null=True)
    prioridad = serializers.ChoiceField(
        choices=OrdenProduccion.PRIORIDAD_CHOICES,
        default='normal',
        required=False,
    )
    peso_solicitado = serializers.DecimalField(
        max_digits=12,
        decimal_places=4,
        required=False,
        allow_null=True,
    )


class ItemDeficitSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField(required=True)
    deficit = serializers.DecimalField(max_digits=12, decimal_places=4, required=True, min_value=Decimal('0.0001'))


class CrearPlanDesdeAlertasInputSerializer(serializers.Serializer):
    sede_id = serializers.IntegerField(required=True)
    supervisor_id = serializers.IntegerField(required=False, allow_null=True)
    codigo = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fecha_inicio = serializers.DateField(required=False)
    fecha_fin = serializers.DateField(required=False)
    aprobar_inmediatamente = serializers.BooleanField(required=False, default=False)
    items = ItemDeficitSerializer(many=True, required=True)

