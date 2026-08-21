from django.db import models
from django.conf import settings

from .core import Sede, AuditableModelMixin
from .catalogo import Producto, Proveedor, Bodega
from .produccion import LoteProduccion

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
