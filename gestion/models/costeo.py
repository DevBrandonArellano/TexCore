from django.db import models
from django.conf import settings
from decimal import Decimal

from .core import Sede, AuditableModelMixin
from .maquina import Maquina
from .produccion import LoteProduccion

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
