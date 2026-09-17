import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .catalogo import Producto
from .core import AuditableModelMixin, Sede, SedeResolvableMixin

logger = logging.getLogger(__name__)


class PlanProduccion(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Plan de Producción Agregado / Reposición contra Stock (MTS).
    Define metas de producción por sede y horizonte temporal, controlando
    desviaciones entre lo planificado y lo ejecutado.
    """
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('aprobado', 'Aprobado'),
        ('en_ejecucion', 'En Ejecución'),
        ('cerrado', 'Cerrado'),
        ('cancelado', 'Cancelado'),
    ]

    campos_auditables = [
        'codigo',
        'sede',
        'fecha_inicio',
        'fecha_fin',
        'estado',
        'supervisor',
        'observaciones',
    ]

    codigo = models.CharField(max_length=50, unique=True, db_index=True, verbose_name='Código de Plan')
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        related_name='planes_produccion',
        verbose_name='Sede',
    )
    fecha_inicio = models.DateField(db_index=True, verbose_name='Fecha de Inicio')
    fecha_fin = models.DateField(db_index=True, verbose_name='Fecha de Fin')
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='borrador',
        db_index=True,
        verbose_name='Estado',
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='planes_supervisados',
        verbose_name='Supervisor / Planificador',
    )
    observaciones = models.TextField(blank=True, default='', verbose_name='Observaciones')
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name='Fecha de Creación')
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name='Fecha de Modificación')

    class Meta:
        verbose_name = 'Plan de Producción'
        verbose_name_plural = 'Planes de Producción'
        ordering = ['-fecha_inicio', '-id']
        constraints = [
            models.CheckConstraint(
                check=Q(fecha_fin__gte=models.F('fecha_inicio')),
                name='chk_plan_produccion_fechas_validas',
            )
        ]

    def __str__(self):
        sede_nombre = self.sede.nombre if self.sede else 'Sin Sede'
        return f"{self.codigo} ({sede_nombre}) [{self.get_estado_display()}]"

    def get_audit_sede_id(self):
        return self.sede_id

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin no puede ser anterior a la fecha de inicio.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class DetallePlanProduccion(AuditableModelMixin, models.Model):
    """
    Renglón o meta de producto en un Plan de Producción.
    Mantiene el acumulado ejecutado (primera y segunda calidad) y calcula
    desviaciones respecto a la meta planificada.
    """
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('sobreproducido', 'Sobreproducido'),
    ]

    campos_auditables = [
        'plan',
        'producto_objetivo',
        'cantidad_planificada',
        'cantidad_ejecutada',
        'cantidad_aceptada',
        'cantidad_segunda',
        'estado',
    ]

    plan = models.ForeignKey(
        PlanProduccion,
        on_delete=models.CASCADE,
        related_name='detalles',
        verbose_name='Plan de Producción',
    )
    producto_objetivo = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='detalles_plan_produccion',
        verbose_name='Producto Objetivo',
    )
    cantidad_planificada = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        verbose_name='Cantidad Planificada',
        help_text='Cantidad meta a producir (kg o m)',
    )
    cantidad_ejecutada = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name='Cantidad Ejecutada',
        help_text='Total producido acumulado (primera + segunda)',
    )
    cantidad_aceptada = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name='Cantidad Aceptada',
        help_text='Total conforme de primera calidad',
    )
    cantidad_segunda = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=Decimal('0.0000'),
        verbose_name='Cantidad Segunda',
        help_text='Total de segunda calidad',
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        db_index=True,
        verbose_name='Estado del Detalle',
    )

    class Meta:
        verbose_name = 'Detalle de Plan de Producción'
        verbose_name_plural = 'Detalles de Planes de Producción'
        constraints = [
            models.UniqueConstraint(
                fields=['plan', 'producto_objetivo'],
                name='uniq_detalle_plan_producto',
            ),
            models.CheckConstraint(
                check=Q(cantidad_planificada__gt=0),
                name='chk_detplan_cant_plan_gt_0',
            ),
            models.CheckConstraint(
                check=Q(cantidad_ejecutada__gte=0),
                name='chk_detplan_cant_ejec_gte_0',
            ),
            models.CheckConstraint(
                check=Q(cantidad_aceptada__gte=0),
                name='chk_detplan_cant_acep_gte_0',
            ),
            models.CheckConstraint(
                check=Q(cantidad_segunda__gte=0),
                name='chk_detplan_cant_seg_gte_0',
            ),
        ]

    def __str__(self):
        return f"{self.plan.codigo} - {self.producto_objetivo.codigo}: {self.cantidad_ejecutada}/{self.cantidad_planificada}"

    def get_audit_sede_id(self):
        return self.plan.sede_id if self.plan_id else None

    @property
    def saldo_pendiente(self) -> Decimal:
        """Cantidad restante para cumplir la meta con producto aceptado."""
        return max(Decimal('0.0000'), self.cantidad_planificada - self.cantidad_aceptada)

    @property
    def desviacion_porcentaje(self) -> Decimal:
        """Desviación porcentual de la producción respecto a la meta planificada."""
        if not self.cantidad_planificada or self.cantidad_planificada <= 0:
            return Decimal('0.00')
        desviacion = ((self.cantidad_ejecutada - self.cantidad_planificada) / self.cantidad_planificada) * Decimal('100.0')
        return round(desviacion, 2)

    @property
    def cumplimiento_porcentaje(self) -> Decimal:
        """Porcentaje de cumplimiento de primera calidad frente a la meta."""
        if not self.cantidad_planificada or self.cantidad_planificada <= 0:
            return Decimal('0.00')
        cumplimiento = (self.cantidad_aceptada / self.cantidad_planificada) * Decimal('100.0')
        return round(cumplimiento, 2)

    def clean(self):
        super().clean()
        if self.cantidad_planificada is not None and self.cantidad_planificada <= 0:
            raise ValidationError({'cantidad_planificada': 'La cantidad planificada debe ser estrictamente mayor a 0.'})

        if self.plan_id and self.producto_objetivo_id:
            if self.producto_objetivo.sede_id and self.producto_objetivo.sede_id != self.plan.sede_id:
                raise ValidationError({
                    'producto_objetivo': f"El producto pertenece a la sede {self.producto_objetivo.sede_id}, diferente a la sede del plan {self.plan.sede_id}."
                })

        if self.cantidad_ejecutada is not None:
            suma_calidades = (self.cantidad_aceptada or Decimal('0.0000')) + (self.cantidad_segunda or Decimal('0.0000'))
            if self.cantidad_ejecutada < suma_calidades:
                raise ValidationError({
                    'cantidad_ejecutada': f"La cantidad ejecutada ({self.cantidad_ejecutada}) no puede ser menor a la suma de aceptada ({self.cantidad_aceptada}) y segunda ({self.cantidad_segunda})."
                })

    def actualizar_estado(self):
        """Actualiza el estado según avance."""
        if self.cantidad_ejecutada <= 0:
            self.estado = 'pendiente'
        elif self.cantidad_aceptada >= self.cantidad_planificada * Decimal('1.05'):
            self.estado = 'sobreproducido'
        elif self.cantidad_aceptada >= self.cantidad_planificada:
            self.estado = 'completado'
        else:
            self.estado = 'en_proceso'

    def save(self, *args, **kwargs):
        self.actualizar_estado()
        self.full_clean()
        super().save(*args, **kwargs)
