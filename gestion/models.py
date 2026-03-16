from django.db import models
from django.db.models import Sum, F, OuterRef, Subquery, DecimalField, Case, When, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.exceptions import ValidationError
from gestion.middleware import get_current_user, get_current_ip
import datetime

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
        campos = getattr(self, 'campos_auditables', [f.name for f in self._meta.fields if f.name not in ('id', 'fecha_creacion', 'fecha_modificacion')])
        for field in campos:
            try:
                val = getattr(self, field)
                if isinstance(val, models.Model):
                    data[field] = val.pk
                elif isinstance(val, (Decimal, datetime.datetime, datetime.date)):
                    data[field] = str(val)
                else:
                    data[field] = val
            except Exception:
                pass
        return data

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        accion = 'CREATE' if is_new else 'UPDATE'
        
        requiere_justificacion = getattr(self, 'requiere_justificacion_auditoria', False)
        if not is_new and requiere_justificacion and not self._justificacion_auditoria:
            # Revisa si realmente cambió algún campo auditable antes de lanzar el error.
            current_state = self._get_auditable_data()
            changed_auditable = False
            for k, v in current_state.items():
                if self._initial_state.get(k) != v:
                    changed_auditable = True
                    break
            
            if changed_auditable:
                raise ValidationError("Debe proporcionar una justificación (_justificacion_auditoria) para modificar este registro crítico.")

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
            
            # Avoid errors during management commands or when not fully initialized
            user_inst = user if user and user.is_authenticated else None
            
            AuditLog.objects.create(
                usuario=user_inst,
                ip_address=ip,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.pk,
                accion=accion,
                valor_anterior=valor_anterior,
                valor_nuevo=valor_nuevo,
                justificacion=self._justificacion_auditoria
            )
            
        self._initial_state = new_state
        self._justificacion_auditoria = None

    def delete(self, *args, **kwargs):
        requiere_justificacion = getattr(self, 'requiere_justificacion_auditoria', False)
        if requiere_justificacion and not self._justificacion_auditoria:
            raise ValidationError("Debe proporcionar una justificación (_justificacion_auditoria) para eliminar este registro crítico.")
            
        user = get_current_user()
        ip = get_current_ip()
        valor_anterior = self._get_auditable_data()
        
        ct = ContentType.objects.get_for_model(self)
        pk = self.pk
        justificacion = self._justificacion_auditoria

        super().delete(*args, **kwargs)

        AuditLog.objects.create(
            usuario=user if user and user.is_authenticated else None,
            ip_address=ip,
            content_type=ct,
            object_id=pk,
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

class Producto(models.Model):
    TIPO_CHOICES = [('hilo', 'Hilo'), ('tela', 'Tela'), ('subproducto', 'Subproducto'), ('quimico', 'Químico'), ('insumo', 'Insumo')]
    UNIDAD_CHOICES = [('kg', 'Kg'), ('metros', 'Metros'), ('unidades', 'Unidades')]
    codigo = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    unidad_medida = models.CharField(max_length=20, choices=UNIDAD_CHOICES)
    stock_minimo = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    presentacion = models.CharField(max_length=100, blank=True, null=True)
    pais_origen = models.CharField(max_length=100, blank=True, null=True)
    calidad = models.CharField(max_length=100, blank=True, null=True)
    precio_base = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='productos')

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
    nombre = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.nombre

class Bodega(models.Model):
    nombre = models.CharField(max_length=100)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, related_name='bodegas')

    def __str__(self):
        return f'{self.nombre} ({self.sede.nombre})'

class Maquina(models.Model):
    ESTADO_CHOICES = [
        ('operativa', 'Operativa'),
        ('mantenimiento', 'Mantenimiento'),
        ('inactiva', 'Inactiva')
    ]
    nombre = models.CharField(max_length=100, unique=True)
    capacidad_maxima = models.DecimalField(max_digits=10, decimal_places=2, help_text="Capacidad máxima de producción por turno (ej. kg)")
    eficiencia_ideal = models.DecimalField(max_digits=3, decimal_places=2, help_text="Eficiencia ideal (0.00 a 1.00)")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='operativa')
    area = models.ForeignKey(Area, on_delete=models.SET_NULL, null=True, blank=True)
    operarios = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='maquinas_asignadas_control')

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

    codigo = models.CharField(max_length=100, unique=True)
    nombre_color = models.CharField(max_length=100, unique=True)
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

    class Meta:
        verbose_name = 'Formula de Color'
        verbose_name_plural = 'Formulas de Color'
        ordering = ['codigo', '-version']

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
        
        iva_multiplier = Case(
            When(detalles__incluye_iva=True, then=Value('1.15')),
            default=Value('1.00'),
            output_field=DecimalField()
        )
        
        pedidos_sq = PedidoVenta.objects.filter(
            cliente=OuterRef('pk')
        ).values('cliente').annotate(
            total=Sum('detalles__total_con_iva', output_field=DecimalField())
        ).values('total')

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
            esta_pagado=False,
            fecha_vencimiento__lt=timezone.now().date()
        ).values('cliente').annotate(
            total_vencido=Sum('detalles__total_con_iva', output_field=DecimalField())
        ).values('total_vencido')

        # Anotación a nivel de base de datos
        return super().get_queryset().annotate(
            saldo_calculado=Coalesce(Subquery(pedidos_sq), Decimal('0.000'), output_field=DecimalField()) - 
                            Coalesce(Subquery(pagos_sq), Decimal('0.000'), output_field=DecimalField()),
            cartera_vencida=Coalesce(Subquery(cartera_vencida_sq), Decimal('0.000'), output_field=DecimalField())
        )

class Cliente(AuditableModelMixin, models.Model):
    campos_auditables = ['limite_credito', 'plazo_credito_dias', 'nivel_precio', 'is_active']
    requiere_justificacion_auditoria = True
    NIVEL_PRECIO_CHOICES = [('mayorista', 'Mayorista'), ('normal', 'Normal')]
    ruc_cedula = models.CharField(max_length=20, unique=True)
    nombre_razon_social = models.CharField(max_length=255)
    direccion_envio = models.CharField(max_length=500)
    nivel_precio = models.CharField(max_length=20, choices=NIVEL_PRECIO_CHOICES)
    tiene_beneficio = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    limite_credito = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    plazo_credito_dias = models.IntegerField(default=0, help_text="Días de crédito (0=Contado)")
    vendedor_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_asignados')
    sede = models.ForeignKey(Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes')

    objects = ClienteManager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(limite_credito__gte=0),
                name='gestion_cliente_limite_credito_positivo'
            )
        ]

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

    def __str__(self):
        return f"Pago {self.id} - {self.cliente.nombre_razon_social} - ${self.monto}"

class OrdenProduccion(models.Model):
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('en_proceso', 'En Proceso'), ('finalizada', 'Finalizada')]
    codigo = models.CharField(max_length=100, unique=True)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    formula_color = models.ForeignKey(FormulaColor, on_delete=models.CASCADE, null=True, blank=True)
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name='ordenes_produccion', null=True, blank=True)
    area = models.ForeignKey('Area', on_delete=models.PROTECT, related_name='ordenes_produccion', null=True, blank=True)
    peso_neto_requerido = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', db_index=True)
    inventario_descontado = models.BooleanField(default=False)
    
    # Planificación y Asignación
    fecha_inicio_planificada = models.DateField(null=True, blank=True)
    fecha_fin_planificada = models.DateField(null=True, blank=True)
    maquina_asignada = models.ForeignKey('Maquina', on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_asignadas')
    operario_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='ordenes_asignadas')
    observaciones = models.CharField(max_length=500, blank=True, null=True)
    
    fecha_creacion = models.DateField(auto_now_add=True)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True, db_index=True)

    def __str__(self):
        return f"OP-{self.codigo} para {self.producto.descripcion if self.producto else 'N/A'}"

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

class LoteProduccion(models.Model):
    orden_produccion = models.ForeignKey(OrdenProduccion, on_delete=models.CASCADE, related_name='lotes', null=True, blank=True)
    codigo_lote = models.CharField(max_length=100, unique=True)
    peso_neto_producido = models.DecimalField(max_digits=12, decimal_places=3)
    operario = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    maquina = models.ForeignKey(Maquina, on_delete=models.SET_NULL, null=True, related_name='lotes_producidos')
    turno = models.CharField(max_length=50)
    hora_inicio = models.DateTimeField()
    hora_final = models.DateTimeField()
    
    # Nuevos campos para Empaquetado
    peso_bruto = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    tara = models.DecimalField(max_digits=12, decimal_places=3, default=0.000)
    unidades_empaque = models.IntegerField(default=1) # Ej: 12 rollos por caja, o 1 cono por funda
    presentacion = models.CharField(max_length=100, blank=True, null=True) # Ej: Caja, Funda, Cono
    cantidad_metros = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Metros reenrollados para telas")

    def clean(self):
        from django.core.exceptions import ValidationError
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
                pass # Otros tipos de presentación

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

    def __str__(self):
        return self.codigo_lote

class PedidoVenta(models.Model):
    ESTADO_CHOICES = [('pendiente', 'Pendiente'), ('despachado', 'Despachado'), ('facturado', 'Facturado')]
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, null=True, blank=True)
    guia_remision = models.CharField(max_length=100)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_despacho = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    esta_pagado = models.BooleanField(default=False)
    sede = models.ForeignKey(Sede, on_delete=models.CASCADE, null=True, blank=True)
    vendedor_asignado = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos_creados')

    class Meta:
        indexes = [
            models.Index(
                fields=['vendedor_asignado', 'fecha_pedido'],
                include=['cliente', 'estado'],
                name='idx_pedido_vendedor_fecha_incl'
            )
        ]

    def __str__(self):
        return f"Pedido {self.id} para {self.cliente.nombre_razon_social if self.cliente else 'N/A'}"

class DetallePedido(models.Model):
    pedido_venta = models.ForeignKey(PedidoVenta, on_delete=models.CASCADE, related_name='detalles', null=True, blank=True)
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