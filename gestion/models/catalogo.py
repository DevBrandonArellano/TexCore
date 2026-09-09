from django.db import models

from .core import Sede, AuditableModelMixin, SedeResolvableMixin


class Producto(SedeResolvableMixin, AuditableModelMixin, models.Model):
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

    def get_audit_sede_id(self):
        return self.sede_id


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
