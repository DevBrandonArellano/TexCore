from django.contrib import admin
from .models import StockBodega, MovimientoInventario, HistorialDespacho, DetalleHistorialDespacho

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

class DetalleHistorialDespachoInline(admin.TabularInline):
    model = DetalleHistorialDespacho
    extra = 0
    readonly_fields = ('lote', 'producto', 'peso', 'es_devolucion')
    can_delete = False

@admin.register(HistorialDespacho)
class HistorialDespachoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha_despacho', 'usuario', 'total_bultos', 'total_peso', 'pedidos_ids')
    list_filter = ('fecha_despacho', 'usuario')
    search_fields = ('pedidos_ids', 'observaciones', 'usuario__username')
    readonly_fields = ('fecha_despacho', 'usuario', 'pedidos_ids', 'total_bultos', 'total_peso')
    inlines = [DetalleHistorialDespachoInline]
    date_hierarchy = 'fecha_despacho'
    
    def has_add_permission(self, request):
        # No permitir crear despachos manualmente desde el admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar despachos desde el admin
        return False

@admin.register(DetalleHistorialDespacho)
class DetalleHistorialDespachoAdmin(admin.ModelAdmin):
    list_display = ('historial', 'lote', 'producto', 'peso', 'es_devolucion')
    list_filter = ('es_devolucion', 'historial__fecha_despacho')
    search_fields = ('lote__codigo_lote', 'producto__descripcion')
    readonly_fields = ('historial', 'lote', 'producto', 'peso', 'es_devolucion')
    
    def has_add_permission(self, request):
        # No permitir crear detalles manualmente desde el admin
        return False
    
    def has_delete_permission(self, request, obj=None):
        # No permitir eliminar detalles desde el admin
        return False