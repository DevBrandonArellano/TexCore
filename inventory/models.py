from django.db import models
from django.conf import settings
from gestion.models import Bodega, Producto, LoteProduccion

class StockBodega(models.Model):
    """
    Representa el stock actual (saldo) de un producto específico en una bodega.
    Esta tabla se actualiza mediante las operaciones en MovimientoInventario.
    """
    bodega = models.ForeignKey(Bodega, on_delete=models.CASCADE, related_name="stock_items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="stock_items")
    lote = models.ForeignKey(LoteProduccion, on_delete=models.CASCADE, null=True, blank=True, related_name="stock_items")
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Stock en Bodega"
        verbose_name_plural = "Stock en Bodegas"
        constraints = [
            models.UniqueConstraint(
                fields=['bodega', 'producto'],
                condition=models.Q(lote__isnull=True),
                name='inventory_stockbodega_unique_without_lote'
            ),
            models.UniqueConstraint(
                fields=['bodega', 'producto', 'lote'],
                condition=models.Q(lote__isnull=False),
                name='inventory_stockbodega_unique_with_lote'
            )
        ]

    def __str__(self):
        lote_code = f" (Lote: {self.lote.codigo_lote})" if self.lote else ""
        return f"{self.cantidad} x {self.producto.descripcion} en {self.bodega.nombre}{lote_code}"

class MovimientoInventario(models.Model):
    """
    Registra cada transacción de inventario. Es la fuente de verdad para la trazabilidad (Kardex).
    """
    TIPO_MOVIMIENTO_CHOICES = [
        ('COMPRA', 'Compra de Material'),
        ('PRODUCCION', 'Entrada por Producción'),
        ('TRANSFERENCIA', 'Transferencia entre Bodegas'),
        ('AJUSTE', 'Ajuste de Inventario'),
        ('VENTA', 'Salida por Venta'),
        ('DEVOLUCION', 'Devolución de Cliente'),
        ('CONSUMO', 'Consumo para Producción'),
    ]

    fecha = models.DateTimeField(auto_now_add=True, db_index=True)
    tipo_movimiento = models.CharField(max_length=20, choices=TIPO_MOVIMIENTO_CHOICES, db_index=True)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, db_index=True)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Origen y Destino del movimiento
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name='movimientos_salida', null=True, blank=True, db_index=True)
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name='movimientos_entrada', null=True, blank=True, db_index=True)
    
    cantidad = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Referencia a otros documentos (Orden de Compra, Venta, etc.)
    documento_ref = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Usuario responsable de la transacción
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    # Campo denormalizado para facilitar el cálculo del Kardex
    saldo_resultante = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Campos de auditoría
    editado = models.BooleanField(default=False, help_text="Indica si este movimiento ha sido editado")
    fecha_ultima_edicion = models.DateTimeField(null=True, blank=True, help_text="Fecha de la última edición")

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"

    def __str__(self):
        return f"{self.get_tipo_movimiento_display()} de {self.producto.descripcion} ({self.cantidad}) - {self.fecha.strftime('%Y-%m-%d')}"



class AuditoriaMovimiento(models.Model):
    """
    Registra cada modificación realizada a un MovimientoInventario.
    Permite trazabilidad completa de cambios para control y auditoría.
    """
    movimiento = models.ForeignKey(
        MovimientoInventario, 
        on_delete=models.CASCADE, 
        related_name='auditorias'
    )
    fecha_modificacion = models.DateTimeField(auto_now_add=True, db_index=True)
    usuario_modificador = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True
    )
    
    # Campos modificados
    campo_modificado = models.CharField(max_length=50, help_text="Nombre del campo que fue modificado")
    valor_anterior = models.TextField(help_text="Valor antes de la modificación")
    valor_nuevo = models.TextField(help_text="Valor después de la modificación")
    razon_cambio = models.TextField(blank=True, help_text="Justificación del cambio")
    
    class Meta:
        ordering = ['-fecha_modificacion']
        verbose_name = "Auditoría de Movimiento"
        verbose_name_plural = "Auditorías de Movimientos"
        indexes = [
            models.Index(fields=['movimiento', '-fecha_modificacion']),
        ]

    def __str__(self):
        usuario = self.usuario_modificador.get_full_name() if self.usuario_modificador else "Sistema"
        return f"{self.campo_modificado} modificado por {usuario} - {self.fecha_modificacion.strftime('%Y-%m-%d %H:%M')}"

