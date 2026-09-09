from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

from .core import Area, CustomUser, SedeResolvableMixin, AuditableModelMixin


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


class ParoMaquina(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """
    Registro de downtime de máquina, con reason code = las Seis Grandes Pérdidas
    (OEE for Operators — Productivity Press). Alimenta el cálculo de Disponibilidad
    del OEE (OeeService): tiempo detenido no planificado / (run_time + downtime).

    - Disponibilidad: AVERIA, SETUP.
    - Rendimiento: MICROPARO, VELOCIDAD_REDUCIDA.
    - Calidad: RECHAZO_ARRANQUE, DEFECTO_PROCESO.
    - No penaliza Disponibilidad: MANTENIMIENTO_PLANIFICADO, OTRO (si planificado=True).
    """
    CATEGORIA_CHOICES = [
        ('AVERIA', 'Avería / Falla de Equipo'),
        ('SETUP', 'Setup y Ajustes'),
        ('MICROPARO', 'Paro Menor / Microparo'),
        ('VELOCIDAD_REDUCIDA', 'Velocidad Reducida'),
        ('RECHAZO_ARRANQUE', 'Rechazo de Arranque'),
        ('DEFECTO_PROCESO', 'Defecto de Proceso'),
        ('FALTA_MATERIAL', 'Falta de Material'),
        ('MANTENIMIENTO_PLANIFICADO', 'Mantenimiento Planificado'),
        ('OTRO', 'Otro'),
    ]

    maquina = models.ForeignKey(Maquina, on_delete=models.CASCADE, related_name='paros')
    inicio = models.DateTimeField()
    fin = models.DateTimeField(null=True, blank=True, help_text="Vacío = paro en curso")
    categoria = models.CharField(max_length=30, choices=CATEGORIA_CHOICES)
    planificado = models.BooleanField(
        default=False,
        help_text="Los paros planificados (mantenimiento programado) no penalizan Disponibilidad")
    descripcion = models.TextField(blank=True)
    turno = models.CharField(max_length=50, blank=True)
    usuario = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='paros_maquina')

    class Meta:
        ordering = ['-inicio']
        indexes = [
            models.Index(fields=['maquina', 'inicio']),
            models.Index(fields=['inicio']),
        ]

    def get_audit_sede_id(self):
        if self.maquina and self.maquina.area:
            return self.maquina.area.sede_id
        return None

    def clean(self):
        super().clean()
        if self.fin is not None and self.inicio is not None and self.fin <= self.inicio:
            raise ValidationError({'fin': 'La fecha de fin debe ser posterior a la fecha de inicio.'})

    @property
    def duracion_minutos(self):
        if self.fin is None:
            return None
        return (self.fin - self.inicio).total_seconds() / 60

    def __str__(self):
        return f"{self.maquina.nombre} — {self.get_categoria_display()} ({self.inicio:%Y-%m-%d %H:%M})"


class LineaProduccion(models.Model):
    """Célula de Manufactura Flexible: agrupación organizativa de máquinas
    dentro de un área (ISA-95: agrupador de flujo / work-center grouping).

    CONTROL DE CAPACIDAD (TOC): la línea NO asigna carga. Las colas de
    trabajo y las Órdenes de Producción se calculan estrictamente a nivel
    de ÁREA. Una máquina puede pertenecer a varias líneas activas (recurso
    compartido, para no dejar ociosa una máquina rápida frente al cuello de
    botella); por eso sumar capacidades "por línea" duplicaría capacidad
    fantasma — cualquier lógica APS debe agregarse por Área.

    Validación máquina∈área: vive en el serializer (el M2M no es validable
    en Model.clean durante el create)."""
    ESTADO_CHOICES = [('activa', 'Activa'), ('inactiva', 'Inactiva')]

    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='lineas_produccion')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activa')
    maquinas = models.ManyToManyField(Maquina, blank=True, related_name='lineas_produccion')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('nombre', 'area')
        ordering = ['area', 'nombre']
        verbose_name = 'Línea de Producción'
        verbose_name_plural = 'Líneas de Producción'

    def __str__(self):
        return f"{self.nombre} ({self.area.nombre})"


class ProcessStep(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
