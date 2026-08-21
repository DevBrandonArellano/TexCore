from django.db import models
from django.conf import settings

from .core import Sede, AuditableModelMixin
from .catalogo import Producto


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
