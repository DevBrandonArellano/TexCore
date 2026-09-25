from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models

from .core import Sede, AuditableModelMixin, SedeResolvableMixin
from .catalogo import Producto


class FormulaColor(SedeResolvableMixin, AuditableModelMixin, models.Model):
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

    def get_audit_sede_id(self):
        return self.sede_id


class ProcesoTintoreria(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """Catálogo por sede de procesos de tintorería (DESCRUDE, LAVADO REDUCTIVO...).
    No reutiliza ProcessStep: aquél es el catálogo global de pasos de producción por
    área (spec 2026-09-24, decisión D5)."""
    TIPO_CHOICES = [
        ('pre_tratamiento', 'Pre-Tratamiento'),
        ('colorante', 'Colorante'),
        ('auxiliar', 'Auxiliar'),
        ('lavado', 'Lavado'),
        ('acabado', 'Acabado'),
    ]

    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    sede = models.ForeignKey(
        Sede, on_delete=models.SET_NULL, null=True, blank=True, related_name='procesos_tintoreria'
    )

    class Meta:
        verbose_name = 'Proceso de Tintoreria'
        verbose_name_plural = 'Procesos de Tintoreria'
        ordering = ['codigo']
        unique_together = ('codigo', 'sede')

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def get_audit_sede_id(self):
        return self.sede_id

    @classmethod
    def obtener_legacy(cls, nombre_fase, sede):
        """Proceso de la sede equivalente a un valor del antiguo enum de fases; lo crea
        si la sede aún no lo tiene (p. ej. sedes creadas después de la migración 0014)."""
        codigo, nombre, tipo = FASES_LEGACY[nombre_fase]
        proceso, _ = cls.objects.get_or_create(
            codigo=codigo, sede=sede, defaults={'nombre': nombre, 'tipo': tipo})
        return proceso


# Enum de fases previo al catálogo ProcesoTintoreria (hasta la migración 0014).
# valor legacy -> (codigo del proceso, nombre, tipo). La API ya no lo acepta; queda para
# obtener_legacy(), que usan los comandos de siembra y las factories de pruebas.
FASES_LEGACY = {
    'pre_tratamiento': ('PRE_TRATAMIENTO', 'Pre-Tratamiento / Blanqueo', 'pre_tratamiento'),
    'tintura': ('TINTURA', 'Tintura Principal', 'colorante'),
    'lavado': ('LAVADO', 'Lavado / Jabonado', 'lavado'),
    'suavizado': ('SUAVIZADO', 'Suavizado / Acabado Final', 'acabado'),
    'auxiliares': ('AUXILIARES', 'Baño de Auxiliares Extras', 'auxiliar'),
}


class FaseReceta(models.Model):
    formula = models.ForeignKey(
        FormulaColor, on_delete=models.CASCADE,
        related_name='fases'
    )
    proceso = models.ForeignKey(
        ProcesoTintoreria, on_delete=models.PROTECT,
        related_name='fases'
    )
    ciclo = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Número de ciclo del proceso en la hoja de tintura"
    )
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
        return f"{self.formula.codigo} - {self.proceso.nombre}"


class VersionFormula(SedeResolvableMixin, AuditableModelMixin, models.Model):
    """Versión inmutable de una receta (spec 2026-09-24 §5.5, decisión D1): la receta
    completa se congela como JSON. Solo `es_oficial` puede cambiar después de creada
    (al oficializar otra versión); el resto de campos y el borrado se rechazan."""
    CAMPOS_INMUTABLES = ('formula', 'numero', 'snapshot', 'motivo')
    campos_auditables = ['formula', 'numero', 'snapshot', 'motivo', 'es_oficial']

    formula = models.ForeignKey(FormulaColor, on_delete=models.CASCADE, related_name='versiones')
    numero = models.PositiveIntegerField()
    snapshot = models.JSONField()
    motivo = models.TextField(validators=[MinLengthValidator(10, 'El motivo debe tener al menos 10 caracteres.')])
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='versiones_formula_creadas'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    es_oficial = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Version de Formula'
        verbose_name_plural = 'Versiones de Formula'
        ordering = ['formula', '-numero']
        unique_together = ('formula', 'numero')
        constraints = [
            models.UniqueConstraint(
                fields=['formula'], condition=models.Q(es_oficial=True),
                name='gestion_versionformula_una_oficial_por_formula',
            ),
        ]

    def __str__(self):
        oficial = ' (oficial)' if self.es_oficial else ''
        return f"{self.formula.codigo} v{self.numero}{oficial}"

    def get_audit_sede_id(self):
        return self.formula.sede_id if self.formula_id else None

    def clean(self):
        super().clean()
        if self.pk is not None:
            actual = self._get_auditable_data()
            if any(self._initial_state.get(c) != actual.get(c) for c in self.CAMPOS_INMUTABLES):
                raise ValidationError('Una versión de fórmula es inmutable: solo puede cambiar su marca de oficial.')

    def delete(self, *args, **kwargs):
        raise ValidationError('Una versión de fórmula es inmutable y no se puede eliminar.')


class DetalleFormula(SedeResolvableMixin, AuditableModelMixin, models.Model):
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
        fase_nombre = self.fase.proceso.nombre if self.fase else 'N/A'
        formula_nombre = self.fase.formula.nombre_color if self.fase and self.fase.formula else 'N/A'
        return f"{producto_desc} en Fase: {fase_nombre} ({formula_nombre})"

    def get_audit_sede_id(self):
        if self.fase and self.fase.formula:
            return self.fase.formula.sede_id
        return None
