import logging
from django.db import models
from django.db.models import Sum, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from gestion.middleware import get_current_user, get_current_ip, get_cascade_justification
import datetime

logger = logging.getLogger(__name__)


class SedeResolvableMixin:
    """
    Protocolo para que cada modelo declare cómo obtener su sede_id para auditoría.
    Implementar get_audit_sede_id() en cada modelo que use AuditableModelMixin.
    Esto reemplaza la función _get_object_sede_id() con su lógica condicional anidada.
    """

    def get_audit_sede_id(self):
        raise NotImplementedError(
            f"{self.__class__.__name__} debe implementar get_audit_sede_id()"
        )


def _get_object_sede_id(obj):
    """
    Obtiene sede_id del objeto para filtrar logs de entidades eliminadas.
    Prioriza el protocolo SedeResolvableMixin si el objeto lo implementa.
    El fallback con hasattr mantiene compatibilidad con modelos no migrados aún.
    """
    if obj is None:
        return None
    # Prioridad 1: protocolo explícito (modelos que implementan SedeResolvableMixin)
    if isinstance(obj, SedeResolvableMixin):
        try:
            return obj.get_audit_sede_id()
        except Exception as e:
            logger.warning(
                "Error en get_audit_sede_id() para %s pk=%s: %s",
                obj.__class__.__name__, getattr(obj, 'pk', 'N/A'), e
            )
            return None
    # Prioridad 2: fallback por atributos comunes (compatibilidad con modelos sin mixin)
    try:
        if obj.__class__.__name__ == 'Sede' and hasattr(obj, 'pk') and obj.pk:
            return obj.pk
        if hasattr(obj, 'sede_id') and obj.sede_id is not None:
            return obj.sede_id
        if hasattr(obj, 'sede') and obj.sede and hasattr(obj.sede, 'pk'):
            return obj.sede.pk
        if hasattr(obj, 'fase') and obj.fase and hasattr(obj.fase, 'formula'):
            f = obj.fase.formula
            return getattr(f, 'sede_id', None) if f else None
        if hasattr(obj, 'bodega') and obj.bodega:
            return getattr(obj.bodega, 'sede_id', None)
        if hasattr(obj, 'orden_produccion') and obj.orden_produccion:
            return getattr(obj.orden_produccion, 'sede_id', None)
        if hasattr(obj, 'pedido_venta') and obj.pedido_venta:
            return getattr(obj.pedido_venta, 'sede_id', None)
        if hasattr(obj, 'formula') and obj.formula:
            return getattr(obj.formula, 'sede_id', None)
        if hasattr(obj, 'bodega_origen') and obj.bodega_origen:
            return getattr(obj.bodega_origen, 'sede_id', None)
        if hasattr(obj, 'bodega_destino') and obj.bodega_destino:
            return getattr(obj.bodega_destino, 'sede_id', None)
        if hasattr(obj, 'area') and obj.area:
            return getattr(obj.area, 'sede_id', None)
        if hasattr(obj, 'producto') and obj.producto:
            return getattr(obj.producto, 'sede_id', None)
        if hasattr(obj, 'lote') and obj.lote and hasattr(obj.lote, 'orden_produccion') and obj.lote.orden_produccion:
            return getattr(obj.lote.orden_produccion, 'sede_id', None)
    except Exception as e:
        logger.warning(
            "Error calculando sede_id (fallback) para %s pk=%s: %s",
            obj.__class__.__name__, getattr(obj, 'pk', 'N/A'), e
        )
    return None


class AuditLog(models.Model):
    ACCION_CHOICES = [
        ('CREATE', 'Creación'),
        ('UPDATE', 'Actualización'),
        ('DELETE', 'Eliminación')
    ]
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Relación polimórfica (Generic)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    # Sede del objeto afectado (denormalizado para filtrar logs de entidades eliminadas)
    object_sede_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    accion = models.CharField(max_length=10, choices=ACCION_CHOICES)
    valor_anterior = models.JSONField(null=True, blank=True)
    valor_nuevo = models.JSONField(null=True, blank=True)
    justificacion = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"

    def __str__(self):
        return f"{self.accion} - {self.content_type} ({self.object_id}) - {self.fecha_hora}"


class AuditableModelMixin(models.Model):
    """
    Mixin para auditar cambios. Guarda estados y emite AuditLogs en save/delete.
    """
    _justificacion_auditoria = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_state = self._get_auditable_data()

    def _get_auditable_data(self):
        data = {}
        campos = getattr(
            self, 'campos_auditables', [
                f.name for f in self._meta.fields if f.name not in (
                    'id', 'fecha_creacion', 'fecha_modificacion')])
        for field in campos:
            try:
                val = getattr(self, field)
                if isinstance(val, models.Model):
                    data[field] = val.pk
                elif isinstance(val, (Decimal, datetime.datetime, datetime.date)):
                    data[field] = str(val)
                else:
                    data[field] = val
            except AttributeError as e:
                logger.warning(
                    "Campo auditable '%s' no encontrado en %s pk=%s: %s",
                    field, self.__class__.__name__, getattr(self, 'pk', 'N/A'), e
                )
        return data

    def clean(self):
        """
        Validaciones de negocio que requieren contexto de auditoría.
        Se llama automáticamente por full_clean() y desde los formularios de Django Admin.
        """
        super().clean()
        is_new = self.pk is None
        requiere_justificacion = getattr(self, 'requiere_justificacion_auditoria', False)

        if not is_new and requiere_justificacion and not self._justificacion_auditoria:
            current_state = self._get_auditable_data()
            changed_auditable = any(
                self._initial_state.get(k) != v
                for k, v in current_state.items()
            )
            if changed_auditable:
                raise ValidationError(
                    "Debe proporcionar una justificación (_justificacion_auditoria) "
                    "para modificar este registro crítico."
                )

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        accion = 'CREATE' if is_new else 'UPDATE'

        # Ejecutar validaciones de clean() antes de guardar
        # (los formularios DRF ya llaman full_clean, pero las operaciones directas de ORM no)
        self.full_clean()

        super().save(*args, **kwargs)
        new_state = self._get_auditable_data()

        if is_new:
            changed = True
            valor_anterior = None
            valor_nuevo = new_state
        else:
            changed = False
            valor_anterior = {}
            valor_nuevo = {}
            for k, v in new_state.items():
                if self._initial_state.get(k) != v:
                    changed = True
                    valor_anterior[k] = self._initial_state.get(k)
                    valor_nuevo[k] = v

        if changed:
            user = get_current_user()
            ip = get_current_ip()
            object_sede_id = _get_object_sede_id(self)
            AuditLog.objects.create(
                usuario=user if user and user.is_authenticated else None,
                ip_address=ip,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.pk,
                object_sede_id=object_sede_id,
                accion=accion,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                justificacion=self._justificacion_auditoria
            )

        self._initial_state = new_state
        self._justificacion_auditoria = None

    def delete(self, *args, **kwargs):
        requiere_justificacion = getattr(self, 'requiere_justificacion_auditoria', False)
        justificacion = self._justificacion_auditoria or get_cascade_justification()
        if requiere_justificacion and not justificacion:
            raise ValidationError(
                "Debe proporcionar una justificación (_justificacion_auditoria) para eliminar este registro crítico.")
        if justificacion and not self._justificacion_auditoria:
            self._justificacion_auditoria = justificacion

        user = get_current_user()
        ip = get_current_ip()
        valor_anterior = self._get_auditable_data()

        ct = ContentType.objects.get_for_model(self)
        pk = self.pk
        justificacion = self._justificacion_auditoria

        object_sede_id = _get_object_sede_id(self)
        super().delete(*args, **kwargs)

        AuditLog.objects.create(
            usuario=user if user and user.is_authenticated else None,
            ip_address=ip,
            content_type=ct,
            object_id=pk,
            object_sede_id=object_sede_id,
            accion='DELETE',
            valor_anterior=valor_anterior,
            valor_nuevo=None,
            justificacion=justificacion
        )


class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=100, default='Ubicación no especificada')
    status = models.CharField(max_length=10, choices=[('activo', 'Activo'), ('inactivo', 'Inactivo')], default='activo')

    def __str__(self):
        return self.nombre


class Area(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='areas')

    class Meta:
        unique_together = ('nombre', 'sede')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'


class CustomUser(AbstractUser):
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    superior = models.ManyToManyField('self', symmetrical=False, related_name='inferiors_set', blank=True)
    bodegas_asignadas = models.ManyToManyField('Bodega', blank=True, related_name='usuarios_asignados')

    def __str__(self):
        return self.username


class Producto(AuditableModelMixin, models.Model):
    campos_auditables = ['codigo', 'descripcion', 'tipo', 'unidad_medida', 'stock_minimo', 'precio_base']
    TIPO_CHOICES = [('hilo', 'Hilo'), ('tela', 'Tela'), ('subproducto', 'Subproducto'),
                    ('quimico', 'Químico'), ('insumo', 'Insumo'), ('materia_prima', 'Materia prima')]
    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos (kg)'),
        ('gr', 'Gramos (gr)'),
        ('lb', 'Libras (lb)'),
        ('l', 'Litros (l)'),
        ('ml', 'Mililitros (ml)'),
        ('gl', 'Galones (gl)'),
        ('metros', 'Metros (m)'),
        ('yardas', 'Yardas (yd)'),
        ('unidades', 'Unidades (u)')
    ]
    codigo = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    unidad_medida = models.CharField(max_length=20, choices=UNIDAD_CHOICES)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    presentacion = models.CharField(max_length=100, blank=True, null=True)
    pais_origen = models.CharField(max_length=100, blank=True, null=True)
    calidad = models.CharField(max_length=100, blank=True, null=True)
    precio_base = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')

    class Meta:
        unique_together = ('codigo', 'sede')

    def __str__(self):
        return f"{self.descripcion} ({self.codigo})"


class Batch(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    code = models.CharField(max_length=100, unique=True)
    initial_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = models.CharField(max_length=50)
    date_received = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Batch {self.code} of {self.producto.descripcion if self.producto else 'N/A'}"


class Proveedor(models.Model):
    nombre = models.CharField(max_length=255)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='proveedores')

    class Meta:
        unique_together = ('nombre', 'sede')

    def __str__(self):
        return self.nombre


class Bodega(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='bodegas')

    class Meta:
        unique_together = ('nombre', 'sede')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'


class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operativa', 'Operativa'),
        ('mantenimiento', 'Mantenimiento'),
        ('inactiva', 'Inactiva')
    ]
    nombre = models.CharField(max_length=100)
    capacidad_maxima = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Capacidad máxima de producción por turno (ej. kg)")
    eficiencia_ideal = models.DecimalField(max_digits=3, decimal_places=2, help_text="Eficiencia ideal (0.00 a 1.00)")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='operativa')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    operarios = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='maquinas_asignadas_control')
    producto_merma = models.ForeignKey(
        'Producto', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maquinas_generadoras',
        verbose_name='Producto de Merma'
    )
    bodega_merma = models.ForeignKey(
        'Bodega', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maquinas_merma',
        verbose_name='Bodega de Merma'
    )
    bodega_entrada = models.ForeignKey(
        'Bodega', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maquinas_entrada',
        verbose_name='Bodega de Entrada'
    )
    bodega_salida = models.ForeignKey(
        'Bodega', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='maquinas_salida',
        verbose_name='Bodega de Salida'
    )

    class Meta:
        unique_together = ('nombre', 'area')

    def __str__(self):
        return f"{self.nombre} - {self.get_estado_display()}"


class ProcessStep(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class FormulaColor(AuditableModelMixin, models.Model):
    campos_auditables = ['codigo', 'nombre_color', 'tipo_sustrato', 'estado', 'observaciones']
    requiere_justificacion_auditoria = True
    TIPO_SUSTRATO_CHOICES = [
        ('algodon', 'Algodon'),
        ('poliester', 'Poliester'),
        ('nylon', 'Nylon'),
        ('mixto', 'Mixto'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('en_pruebas', 'En Pruebas'),
        ('aprobada', 'Aprobada'),
    ]

    codigo = models.CharField(max_length=100)
    nombre_color = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    tipo_sustrato = models.CharField(
        max_length=20, choices=TIPO_SUSTRATO_CHOICES, default='algodon',
        help_text='Tipo de fibra o sustrato al que aplica esta formula'
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text='Numero de version. Se incrementa al duplicar la formula'
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='en_pruebas', db_index=True,
        help_text='Estado de aprobacion de la formula'
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='formulas_creadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    observaciones = models.CharField(
        max_length=500, blank=True, null=True,
        help_text='Observaciones generales sobre la formula'
    )
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='formulas_color')

    class Meta:
        verbose_name = 'Formula de Color'
        verbose_name_plural = 'Formulas de Color'
        ordering = ['codigo', '-version']
        unique_together = [('codigo', 'sede'), ('nombre_color', 'sede')]

    def __str__(self):
        return f"{self.nombre_color} v{self.version} ({self.get_estado_display()})"


class FaseReceta(models.Model):
    TIPO_FASE_CHOICES = [
        ('pre_tratamiento', 'Pre-Tratamiento / Blanqueo'),
        ('tintura', 'Tintura Principal'),
        ('lavado', 'Lavado / Jabonado'),
        ('suavizado', 'Suavizado / Acabado Final'),
        ('auxiliares', 'Baño de Auxiliares Extras'),
    ]
    formula = models.ForeignKey(
        FormulaColor, on_delete=models.CASCADE,
        related_name='fases'
    )
    nombre = models.CharField(max_length=50, choices=TIPO_FASE_CHOICES)
    orden = models.PositiveIntegerField(
        help_text="Orden de ejecución del baño dentro del proceso de tintura"
    )
    temperatura = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Temperatura objetivo en °C para esta fase (Curva térmica)"
    )
    tiempo = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Tiempo de retención en minutos del baño"
    )
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['orden']
        unique_together = ('formula', 'orden')

    def __str__(self):
        return f"{self.formula.codigo} - {self.get_nombre_display()}"


class DetalleFormula(AuditableModelMixin, models.Model):
    campos_auditables = ['producto', 'tipo_calculo', 'concentracion_gr_l', 'porcentaje', 'orden_adicion']
    requiere_justificacion_auditoria = True
    TIPO_CALCULO_CHOICES = [
        ('gr_l', 'Concentracion (gr/L)'),
        ('pct', 'Agotamiento (%)'),
    ]

    fase = models.ForeignKey(
        FaseReceta, on_delete=models.CASCADE,
        null=True, blank=True, related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        limit_choices_to={'tipo': 'quimico'}
    )
    # Campo legacy mantenido por compatibilidad. Se usa como fallback cuando
    # tipo_calculo no ha sido definido en registros anteriores.
    gramos_por_kilo = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    tipo_calculo = models.CharField(
        max_length=10, choices=TIPO_CALCULO_CHOICES, default='gr_l',
        help_text='Metodo de calculo de dosificacion para este insumo'
    )
    concentracion_gr_l = models.DecimalField(
        max_digits=10, decimal_places=3, null=True, blank=True,
        help_text='Concentracion en gr/L del insumo en el bano de tintura'
    )
    porcentaje = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True,
        help_text='Porcentaje del insumo sobre el peso de la tela (agotamiento)'
    )
    orden_adicion = models.PositiveSmallIntegerField(
        default=1,
        help_text='Orden de adicion del insumo al bano (1 = primero)'
    )
    notas = models.TextField(
        blank=True, null=True,
        help_text='Observaciones tecnicas del insumo en esta formula'
    )

    class Meta:
        unique_together = ('fase', 'producto')
        ordering = ['orden_adicion']
        verbose_name = 'Detalle de Formula'
        verbose_name_plural = 'Detalles de Formula'

    def __str__(self):
        producto_desc = self.producto.descripcion if self.producto else 'N/A'
        fase_nombre = self.fase.get_nombre_display() if self.fase else 'N/A'
        formula_nombre = self.fase.formula.nombre_color if self.fase and self.fase.formula else 'N/A'
        return f"{producto_desc} en Fase: {fase_nombre} ({formula_nombre})"


class ClienteManager(models.Manager):
    def get_queryset(self):
        # Subconsulta para el total de pedidos
        from .models import PedidoVenta, PagoCliente

        pedidos_sq = PedidoVenta.objects.filter(cliente=OuterRef('pk'),
                                                anulado=False,).values('cliente').annotate(
            total=Sum('detalles__total_con_iva', output_field=DecimalField())
            - Sum('valor_retencion', output_field=DecimalField())).values('total')

        # Subconsulta para el total de pagos
        pagos_sq = PagoCliente.objects.filter(
            cliente=OuterRef('pk')
        ).values('cliente').annotate(
            total=Sum('monto', output_field=DecimalField())
        ).values('total')

        # Subconsulta para Cartera Vencida (deuda vencida ayer o antes)
        from django.utils import timezone

        cartera_vencida_sq = PedidoVenta.objects.filter(
            cliente=OuterRef('pk'),
            anulado=False, esta_pagado=False, fecha_vencimiento__lt=timezone.now().date()).values('cliente').annotate(
            total_vencido=Sum('detalles__total_con_iva', output_field=DecimalField())
            - Sum('valor_retencion', output_field=DecimalField())).values('total_vencido')

        # Anotación a nivel de base de datos
        return super().get_queryset().annotate(
            saldo_calculado=Coalesce(Subquery(pedidos_sq), Decimal('0.000'), output_field=DecimalField())
            - Coalesce(Subquery(pagos_sq), Decimal('0.000'), output_field=DecimalField()),
            cartera_vencida=Coalesce(Subquery(cartera_vencida_sq), Decimal('0.000'), output_field=DecimalField())
        )


class Cliente(AuditableModelMixin, models.Model):
    campos_auditables = ['limite_credito', 'plazo_credito_dias', 'nivel_precio', 'is_active']
    requiere_justificacion_auditoria = True
    NIVEL_PRECIO_CHOICES = [('mayorista', 'Mayorista'), ('normal', 'Normal')]
    ruc_cedula = models.CharField(max_length=20)
    nombre_razon_social = models.CharField(max_length=255)
    direccion_envio = models.CharField(max_length=500)
    nivel_precio = models.CharField(max_length=20, choices=NIVEL_PRECIO_CHOICES)
    tiene_beneficio = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    limite_credito = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    plazo_credito_dias = models.IntegerField(default=0, help_text="Días de crédito (0=Contado)")
    vendedor_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clientes_asignados')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')

    objects = ClienteManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(limite_credito__gte=0),
                name='gestion_cliente_limite_credito_positivo'
            )
        ]
        unique_together = ('ruc_cedula', 'sede')

    def __str__(self):
        return self.nombre_razon_social


class PagoCliente(models.Model):
    METODO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('cheque', 'Cheque'),
        ('otro', 'Otro')
    ]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pagos')
    fecha = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=12, decimal_places=3)
    metodo_pago = models.CharField(max_length=20, choices=METODO_CHOICES, default='transferencia')
    comprobante = models.CharField(max_length=100, blank=True, null=True)
    notas = models.CharField(max_length=500, blank=True, null=True)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True)
    # P1-002: marca explícita de anticipo — permite que el monto exceda la
    # deuda actual; el excedente queda como saldo a favor del cliente
    es_anticipo = models.BooleanField(
        default=False,
        help_text='Pago por adelantado: el excedente sobre la deuda queda como saldo a favor'
    )

    def __str__(self):
        return f"Pago {self.id} - {self.cliente.nombre_razon_social} - ${self.monto}"


class OrdenProduccion(AuditableModelMixin, models.Model):
    campos_auditables = [
        'codigo',
        'producto_entrada',
        'producto_salida',
        'peso_neto_requerido',
        'estado',
        'maquina_asignada',
        'operario_asignado',
        'prioridad',
        'bodega_entrada',
        'bodega_salida']
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('en_proceso', 'En Proceso'), ('finalizada', 'Finalizada')]
    PRIORIDAD_CHOICES = [('baja', 'Baja'), ('normal', 'Normal'), ('alta', 'Alta'), ('urgente', 'Urgente')]

    codigo = models.CharField(max_length=100)
    producto_entrada = models.ForeignKey(
        'Producto', on_delete=models.PROTECT, db_index=True,
        related_name='ordenes_como_entrada',
        null=True, blank=True,
        verbose_name='Producto de Entrada'
    )
    producto_salida = models.ForeignKey(
        'Producto', on_delete=models.PROTECT, db_index=True,
        related_name='ordenes_como_salida',
        null=True, blank=True,
        verbose_name='Producto de Salida'
    )
    formula_color = models.ForeignKey(FormulaColor, on_delete=models.CASCADE, null=True, blank=True)
    bodega_entrada = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        related_name='ordenes_entrada',
        null=True, blank=True,
        verbose_name='Bodega de Entrada (MP)'
    )
    bodega_salida = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        related_name='ordenes_salida',
        null=True, blank=True,
        verbose_name='Bodega de Salida (PT)'
    )
    area = models.ForeignKey('Area', on_delete=models.PROTECT, related_name='ordenes_produccion', null=True, blank=True)
    peso_neto_requerido = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='normal', db_index=True)
    inventario_descontado = models.BooleanField(default=False)

    # Planificación y Asignación
    fecha_inicio_planificada = models.DateField(null=True, blank=True)
    fecha_fin_planificada = models.DateField(null=True, blank=True)
    maquina_asignada = models.ForeignKey(
        'Maquina',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_asignadas')
    operario_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ordenes_asignadas')
    observaciones = models.CharField(max_length=500, blank=True, null=True)

    # Gestión de químicos - bodega de uso diario en tintorería
    bodega_quimicos = models.ForeignKey(Bodega, on_delete=models.SET_NULL, null=True,
                                        blank=True, related_name='ordenes_quimicos')

    fecha_creacion = models.DateField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True, db_index=True)

    def __str__(self):
        return f"OP-{self.codigo} para {self.producto_entrada.descripcion if self.producto_entrada else 'N/A'}"

    def generate_next_lote_codigo(self):
        """
        Genera el siguiente código de lote secuencial para esta orden.
        Ejemplo: OP-101-L1, OP-101-L2, etc.
        """
        count = self.lotes.count() + 1
        return f"{self.codigo}-L{count}"

    @property
    def peso_producido(self):
        from django.db.models import Sum
        return self.lotes.aggregate(Sum('peso_neto_producido'))['peso_neto_producido__sum'] or 0

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_neto_requerido__gt=0),
                name='gestion_ordenproduccion_peso_neto_positivo',
            )
        ]
        unique_together = ('codigo', 'sede')


class DescargaQuimicoOP(models.Model):
    # Artefacto RUP: Entidad de Dominio - Registro de descarga química
    # Caso de Uso: CU-DescargaQuimicaAutomatica
    # Patrón: Entity + Audit Trail (inmutable post-creación)
    ESTADO_CHOICES = [
        ('aplicada', 'Aplicada'),
        ('revertida', 'Revertida'),
    ]
    TIPO_CALCULO_CHOICES = [
        ('gr_l', 'Concentración (gr/L)'),
        ('pct', 'Agotamiento (%)'),
    ]

    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='descargas_quimicos')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    fase = models.ForeignKey(FaseReceta, on_delete=models.SET_NULL, null=True, blank=True)
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT)
    tipo_calculo = models.CharField(max_length=10, choices=TIPO_CALCULO_CHOICES, default='gr_l')
    cantidad_calculada_kg = models.DecimalField(max_digits=12, decimal_places=6)
    cantidad_real_kg = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='aplicada')
    fecha_descarga = models.DateTimeField(auto_now_add=True)
    descargado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    justificacion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Descarga Química OP'
        verbose_name_plural = 'Descargas Químicas OP'
        ordering = ['-fecha_descarga']
        indexes = [
            models.Index(fields=['orden_produccion', 'estado']),
            models.Index(fields=['bodega', 'fecha_descarga']),
        ]

    def __str__(self):
        return (
            f"Descarga {self.producto.descripcion} "
            f"({self.cantidad_calculada_kg}kg) - OP {self.orden_produccion.codigo}"
        )


class AreaProcessStep(models.Model):
    """
    Define los subprocesos de un área con su orden y tipo de flujo.
    Permite configurar qué ProcessSteps ejecuta cada área y en qué orden/paralelismo.
    """
    FLUJO_CHOICES = [
        ('secuencial', 'Secuencial'),
        ('paralelo', 'Paralelo'),
    ]

    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='subprocesos')
    proceso = models.ForeignKey(ProcessStep, on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(help_text="Orden de ejecución (menor número = primero)")
    tipo_flujo = models.CharField(max_length=20, choices=FLUJO_CHOICES, default='secuencial')
    es_bloqueante = models.BooleanField(default=True,
                                        help_text="Si es True, los siguientes procesos esperan a que se complete")

    class Meta:
        unique_together = ('area', 'proceso')
        ordering = ['orden']

    def __str__(self):
        return f"{self.area.nombre} → {self.proceso.name} (Orden: {self.orden})"


class OrdenProduccionSubproceso(models.Model):
    """
    Rastrea el progreso de cada subproceso en una orden de producción.
    Permite al jefe de área monitorear y controlar cada fase.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completado', 'Completado'),
        ('pausado', 'Pausado'),
        ('rechazado', 'Rechazado'),
    ]

    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='subprocesos')
    area_proceso = models.ForeignKey(AreaProcessStep, on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)

    # Tiempos
    fecha_inicio_planificada = models.DateTimeField(null=True, blank=True)
    fecha_inicio_real = models.DateTimeField(null=True, blank=True)
    fecha_fin_real = models.DateTimeField(null=True, blank=True)

    # Responsable
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subprocesos_responsable'
    )

    # Observaciones y validación
    observaciones = models.TextField(blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True, help_text="Si fue rechazado, incluir el motivo")

    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('orden_produccion', 'area_proceso')
        ordering = ['area_proceso__orden']
        indexes = [
            models.Index(fields=['orden_produccion', 'estado']),
            models.Index(fields=['usuario_responsable', 'estado']),
        ]

    def __str__(self):
        return f"OP-{self.orden_produccion.codigo} → {self.area_proceso.proceso.name} ({self.get_estado_display()})"

    @property
    def duracion_minutos(self):
        """Retorna la duración en minutos si el subproceso está completado."""
        if self.fecha_inicio_real and self.fecha_fin_real:
            delta = self.fecha_fin_real - self.fecha_inicio_real
            return int(delta.total_seconds() / 60)
        return None


class LoteProduccion(models.Model):
    CALIDAD_CHOICES = [
        ('primera', 'Primera Calidad'),
        ('segunda', 'Segunda Calidad'),
        ('saldo', 'Saldo / Retazo'),
    ]
    TIPO_MERMA_CHOICES = [
        ('maquina', 'Falla Técnica / Máquina'),
        ('material', 'Calidad de Hilo / Material'),
        ('setup', 'Arranque / Setup'),
        ('corte', 'Corte / Empalme'),
        ('otro', 'Otro'),
    ]

    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE,
                                         related_name='lotes', null=True, blank=True)
    codigo_lote = models.CharField(max_length=100)
    peso_neto_producido = models.DecimalField(max_digits=12, decimal_places=3)
    operario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    maquina = models.ForeignKey(Maquina, on_delete=models.SET_NULL, null=True, related_name='lotes_producidos')
    turno = models.CharField(max_length=50)
    hora_inicio = models.DateTimeField()
    hora_final = models.DateTimeField()

    # Mermas y Calidad
    peso_merma = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    tipo_merma = models.CharField(max_length=50, choices=TIPO_MERMA_CHOICES, blank=True, null=True)
    clasificacion_calidad = models.CharField(max_length=50, choices=CALIDAD_CHOICES, default='primera')

    # Nuevos campos para Empaquetado
    peso_bruto = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    tara = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    unidades_empaque = models.IntegerField(default=1)  # Ej: 12 rollos por caja, o 1 cono por funda
    presentacion = models.CharField(max_length=100, blank=True, null=True)  # Ej: Caja, Funda, Cono
    cantidad_metros = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Metros reenrollados para telas")

    # F0-001: trazabilidad de materia prima — qué lotes de MP del proveedor
    # alimentaron este lote producido (through inmutable con cantidad y usuario)
    materias_primas = models.ManyToManyField(
        'MateriaPrimaLote',
        through='ConsumoMateriaPrima',
        related_name='lotes_produccion',
        blank=True,
    )

    def clean(self):
        # Regla de negocio estricta: 1 baño = 15 fundas, 1 funda = 15 conos
        if self.presentacion:
            pres = self.presentacion.lower().strip()
            # Si dicen que es Baño, pero intentan poner menos de las unidades correspondientes,
            # forzamos o validamos la equivalencia.
            if pres == 'baño':
                self.unidades_empaque = 225  # Equivalencia total en conos
            elif pres == 'funda':
                self.unidades_empaque = 15   # Equivalencia en conos
            elif pres == 'cono':
                self.unidades_empaque = 1    # Unidad mínima
            else:
                pass  # Otros tipos de presentación

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(peso_neto_producido__gte=0),
                name='gestion_loteproduccion_peso_neto_positivo'
            ),
            models.CheckConstraint(
                condition=models.Q(peso_bruto__gte=0),
                name='gestion_loteproduccion_peso_bruto_positivo'
            ),
            models.CheckConstraint(
                condition=models.Q(tara__gte=0),
                name='gestion_loteproduccion_tara_positiva'
            )
        ]
        unique_together = ('codigo_lote', 'orden_produccion')

    def __str__(self):
        return self.codigo_lote


class ComponenteMezclaOP(AuditableModelMixin, models.Model):
    """
    Receta de mezcla para una OP. Definida por Jefe de Área.
    COBIT DSS06: sum(porcentaje) == 100 validado en serializer y service.
    ISO 27001 A.12.4: auditoría automática vía AuditableModelMixin.
    """
    campos_auditables = ['porcentaje', 'cantidad_kg', 'producto', 'bodega']

    orden = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='componentes_mezcla',
        verbose_name='Orden de Producción'
    )
    producto = models.ForeignKey(
        'Producto', on_delete=models.PROTECT,
        verbose_name='Producto Componente'
    )
    bodega = models.ForeignKey(
        'Bodega', on_delete=models.PROTECT,
        verbose_name='Bodega Origen del Componente'
    )
    porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Porcentaje (%)'
    )
    cantidad_kg = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Cantidad calculada (kg)'
    )

    class Meta:
        verbose_name = 'Componente de Mezcla'
        unique_together = [('orden', 'producto')]
        constraints = [
            models.CheckConstraint(
                check=models.Q(porcentaje__gt=0) & models.Q(porcentaje__lte=100),
                name='componente_porcentaje_rango'
            )
        ]

    def __str__(self):
        return f'{self.orden.codigo} — {self.producto.codigo} ({self.porcentaje}%)'


class ConsumoLoteDetalle(AuditableModelMixin, models.Model):
    """
    Registro inmutable del consumo real de lotes de entrada al producir un lote.
    ISO 27001 A.12.4: NO permite UPDATE. Solo DELETE vía endpoint rechazar/ con justificación.
    """
    campos_auditables = ['cantidad_consumida']

    lote_produccion = models.ForeignKey(
        LoteProduccion, on_delete=models.CASCADE,
        related_name='consumos_detalle',
        verbose_name='Lote Producido (output)'
    )
    lote_origen = models.ForeignKey(
        LoteProduccion, on_delete=models.PROTECT,
        related_name='usos_como_input',
        verbose_name='Lote de Origen (input)'
    )
    cantidad_consumida = models.DecimalField(
        max_digits=12, decimal_places=3,
        verbose_name='Cantidad Consumida (kg)'
    )
    genera_nuevo_lote = models.BooleanField(
        default=True,
        verbose_name='¿Genera nuevo código de lote?'
    )

    class Meta:
        verbose_name = 'Detalle de Consumo de Lote'
        constraints = [
            models.CheckConstraint(
                check=models.Q(cantidad_consumida__gt=0),
                name='consumo_cantidad_positiva'
            )
        ]

    def __str__(self):
        return (f'{self.lote_produccion.codigo_lote} ← '
                f'{self.lote_origen.codigo_lote} ({self.cantidad_consumida} kg)')


class PedidoVenta(AuditableModelMixin, models.Model):
    campos_auditables = ['cliente', 'guia_remision', 'estado', 'esta_pagado', 'valor_retencion', 'anulado']
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('despachado', 'Despachado'), ('facturado', 'Facturado')]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    guia_remision = models.CharField(max_length=100)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_despacho = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    esta_pagado = models.BooleanField(default=False)
    # P1-003: monto aplicado vía reconciliación FIFO — visibiliza pagos
    # parciales que el booleano esta_pagado no puede representar
    monto_pagado = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    valor_retencion = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True)
    vendedor_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pedidos_creados')

    # Anulación
    anulado = models.BooleanField(default=False, db_index=True)
    motivo_anulacion = models.TextField(blank=True, null=True)
    anulado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pedidos_anulados'
    )
    fecha_anulacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        pass

    def __str__(self):
        return f"Pedido {self.id} para {self.cliente.nombre_razon_social if self.cliente else 'N/A'}"


class DetallePedido(models.Model):
    pedido_venta = models.ForeignKey(
        PedidoVenta,
        on_delete=models.CASCADE,
        related_name='detalles',
        null=True,
        blank=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.IntegerField()
    piezas = models.IntegerField()
    peso = models.DecimalField(max_digits=12, decimal_places=3)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=3)
    incluye_iva = models.BooleanField(default=True)

    # Nuevos campos desnormalizados (Fase 4)
    subtotal = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    total_con_iva = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=0),
                name='gestion_detallepedido_cantidad_positiva'
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name='gestion_detallepedido_precio_unitario_positivo'
            )
        ]

    def save(self, *args, **kwargs):
        from decimal import Decimal
        subt = Decimal(str(self.peso)) * Decimal(str(self.precio_unitario))
        self.subtotal = subt
        self.total_con_iva = subt * Decimal('1.15') if self.incluye_iva else subt
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Detalle {self.id} para Pedido {self.pedido_venta.id if self.pedido_venta else 'N/A'}"

# ============================================================================
# F0-001: Trazabilidad de Materia Prima (Sprint 6 — 10-Jun-2026)
# Caso de uso: cliente reclama defecto -> "Lote X vino de Proveedor Y,
# certificado Z". Cadena: Proveedor -> MateriaPrimaLote -> ConsumoMateriaPrima
# -> LoteProduccion -> Despacho.
# ============================================================================


class MateriaPrimaLote(AuditableModelMixin, models.Model):
    campos_auditables = ['producto', 'proveedor', 'lote_proveedor', 'cantidad_kg', 'costo_unitario']
    requiere_justificacion_auditoria = True

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='materias_primas')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='lotes_suministrados')
    lote_proveedor = models.CharField(max_length=100, db_index=True)
    fecha_recepcion = models.DateField(db_index=True)
    cantidad_kg = models.DecimalField(max_digits=12, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=3)

    # Documentacion y auditoria
    certificado_calidad = models.FileField(upload_to='certificados/%Y/%m/', null=True, blank=True)
    numero_documento_entrada = models.CharField(max_length=100, blank=True)
    bodega_recepcion = models.ForeignKey(
        Bodega,
        on_delete=models.SET_NULL,
        null=True,
        related_name='materias_primas_recibidas')

    # Control de uso
    cantidad_consumida = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    completamente_consumida = models.BooleanField(default=False)

    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='materias_primas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('proveedor', 'lote_proveedor', 'fecha_recepcion')
        verbose_name = 'Materia Prima Lote'
        verbose_name_plural = 'Materias Primas Lotes'
        indexes = [
            models.Index(fields=['producto', 'proveedor', '-fecha_recepcion'], name='idx_mp_prod_prov_fecha'),
            models.Index(fields=['sede', 'completamente_consumida'], name='idx_mp_sede_consumida'),
        ]

    def __str__(self):
        return f'{self.lote_proveedor} ({self.producto.codigo}) - {self.proveedor.nombre}'

    @property
    def cantidad_disponible(self):
        return self.cantidad_kg - self.cantidad_consumida


class ConsumoMateriaPrima(models.Model):
    """Through-table: LoteProduccion <-> MateriaPrimaLote (inmutable post-registro)"""
    lote_produccion = models.ForeignKey(LoteProduccion, on_delete=models.CASCADE, related_name='consumos_materia_prima')
    materia_prima_lote = models.ForeignKey(MateriaPrimaLote, on_delete=models.PROTECT, related_name='consumos')
    cantidad_kg = models.DecimalField(max_digits=12, decimal_places=3)
    porcentaje_utilizado = models.DecimalField(max_digits=5, decimal_places=2, null=True)

    fecha_consumo = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('lote_produccion', 'materia_prima_lote')
        verbose_name = 'Consumo Materia Prima'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad_kg__gt=0),
                name='gestion_consumomp_cantidad_positiva'
            )
        ]

    def __str__(self):
        return f'{self.lote_produccion.codigo_lote} <- {self.materia_prima_lote.lote_proveedor} ({self.cantidad_kg}kg)'

# ============================================================================
# F0-002: Costeo de Produccion por Lote (Sprint 6 — 10-Jun-2026)
# Costo total = MP + quimicos + operario + maquina. El vendedor ve el margen
# real antes de fijar precio.
# ============================================================================


class TarifaOperario(models.Model):
    """Tarifa vigente de un operario; vigente_hasta NULL = sin fecha de fin."""
    TIPO_CONTRATO_CHOICES = [
        ('tiempo', 'Por Tiempo'),
        ('pieza', 'Por Pieza'),
    ]

    operario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tarifas')
    tipo_contrato = models.CharField(max_length=20, choices=TIPO_CONTRATO_CHOICES, default='tiempo')
    tarifa_hora = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    tarifa_pieza = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('operario', 'vigente_desde', 'sede')
        verbose_name = 'Tarifa de Operario'

    def __str__(self):
        return (
            f'{self.operario.get_full_name() or self.operario.username} - '
            f'{self.tarifa_hora or self.tarifa_pieza} ({self.tipo_contrato})'
        )


class CostoHoraMaquina(models.Model):
    """Costo operativo por hora de maquina (amortizacion + energia + mantto)."""
    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, related_name='costos_hora')
    costo_hora = models.DecimalField(max_digits=8, decimal_places=2)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('maquina', 'vigente_desde')
        verbose_name = 'Costo Hora Maquina'

    def __str__(self):
        return f'{self.maquina.nombre} - {self.costo_hora}/h'


class CostoLoteProduccion(AuditableModelMixin, models.Model):
    campos_auditables = ['costo_materia_prima', 'costo_quimicos', 'costo_operario', 'costo_maquina', 'total_costo']

    lote_produccion = models.OneToOneField(LoteProduccion, on_delete=models.CASCADE, related_name='costo')

    # Desglose de costos
    costo_materia_prima = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    costo_quimicos = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    costo_operario = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    costo_maquina = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    otros_costos = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    total_costo = models.DecimalField(max_digits=12, decimal_places=3, default=0)

    # Informacion de venta
    precio_venta_esperado = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    margen_bruto = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    margen_bruto_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    calculado_en = models.DateTimeField(auto_now_add=True)
    recalculado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Costo Lote Produccion'
        ordering = ['-calculado_en']

    def __str__(self):
        return f'Costo {self.lote_produccion.codigo_lote}: {self.total_costo}'

    def calcular_margen(self, precio_venta=None):
        if precio_venta is not None:
            self.precio_venta_esperado = precio_venta

        if self.precio_venta_esperado:
            self.margen_bruto = self.precio_venta_esperado - self.total_costo
            if self.precio_venta_esperado > 0:
                self.margen_bruto_pct = (self.margen_bruto / self.precio_venta_esperado * 100).quantize(Decimal('0.01'))
            self.save(update_fields=['precio_venta_esperado', 'margen_bruto', 'margen_bruto_pct'])


class EtapaProduccion(models.Model):
    """
    Define las etapas secuenciales de producción dentro de un área.
    Cada etapa es ejecutada por una máquina específica y tiene:
    - Bodega de entrada (donde obtiene material)
    - Bodega de salida (donde deja resultado)

    Ejemplo Área Tintura:
    - Etapa 1: Teñido (Máquina Tintura 1) → Bodega Tintura → Bodega Sec Tintura
    - Etapa 2: Secado (Máquina Secadora) → Bodega Sec Tintura → Bodega Final Tintura
    """
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='etapas_produccion')
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(help_text="Orden secuencial de ejecución (1, 2, 3...)")
    maquina = models.ForeignKey(Maquina, on_delete=models.PROTECT)

    bodega_entrada = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='etapas_entrada',
        help_text="Bodega de donde toma el material"
    )
    bodega_salida = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='etapas_salida',
        help_text="Bodega donde deposita el resultado"
    )

    tiempo_procesamiento_minutos = models.IntegerField(
        null=True, blank=True,
        help_text="Tiempo promedio estimado para esta etapa"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('area', 'orden')
        ordering = ['area', 'orden']
        verbose_name = 'Etapa de Producción'
        verbose_name_plural = 'Etapas de Producción'

    def __str__(self):
        return f"{self.area.nombre} → Etapa {self.orden}: {self.nombre}"


class TransferenciaInterarea(models.Model):
    """
    Registra la transferencia de producto de una área a la siguiente.
    Cuando un área termina su producción, transfiere el producto a la bodega
    inicial de la siguiente área.

    Vincula dos órdenes de producción (una por cada área).
    """
    orden_area_origen = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='transferencias_salida',
        help_text="Orden de producción que generó el producto"
    )
    orden_area_destino = models.ForeignKey(
        OrdenProduccion, on_delete=models.CASCADE,
        related_name='transferencias_entrada',
        help_text="Orden de producción que recibe el producto"
    )

    bodega_origen = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='transferencias_origen',
        help_text="Bodega final del área origen"
    )
    bodega_destino = models.ForeignKey(
        Bodega, on_delete=models.PROTECT,
        related_name='transferencias_destino',
        help_text="Bodega inicial del área destino (= MP para el área destino)"
    )

    cantidad_transferida = models.DecimalField(max_digits=12, decimal_places=3)
    fecha_transferencia = models.DateTimeField(auto_now_add=True)

    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )

    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-fecha_transferencia']
        indexes = [
            models.Index(fields=['orden_area_origen', 'orden_area_destino']),
            models.Index(fields=['fecha_transferencia']),
        ]
        verbose_name = 'Transferencia Interárea'
        verbose_name_plural = 'Transferencias Interárea'

    def __str__(self):
        return (
            f"Transferencia: OP-{self.orden_area_origen.codigo} "
            f"→ OP-{self.orden_area_destino.codigo} ({self.cantidad_transferida}kg)"
        )
