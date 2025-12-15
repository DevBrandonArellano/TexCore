from django.contrib import admin
from .models import StockBodega, MovimientoInventario

@admin.register(StockBodega)
class StockBodegaAdmin(admin.ModelAdmin):
    list_display = ('producto', 'bodega', 'lote', 'cantidad')
    list_filter = ('bodega',)
    search_fields = ('producto__descripcion', 'producto__codigo', 'lote__codigo_lote')

@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'tipo_movimiento', 'producto', 'cantidad', 'bodega_origen', 'bodega_destino', 'usuario')
    list_filter = ('tipo_movimiento', 'bodega_origen', 'bodega_destino')
    search_fields = ('producto__descripcion', 'producto__codigo', 'documento_ref')
    raw_id_fields = ('producto', 'lote', 'bodega_origen', 'bodega_destino', 'usuario')