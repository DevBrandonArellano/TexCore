from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Sede, Area, CustomUser, Producto, Batch, ProcessStep,
    FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Bodega
)

# Custom admin for CustomUser to properly show groups and permissions
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    
    # Fields to display in the list view
    list_display = ['username', 'email', 'first_name', 'last_name', 'sede', 'area', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'sede', 'area', 'groups']
    
    # Fieldsets for the detail/edit view
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {
            'fields': ('sede', 'area', 'date_of_birth', 'superior', 'bodegas_asignadas')
        }),
    )
    
    # Fieldsets for adding a new user
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Información Adicional', {
            'fields': ('sede', 'area', 'date_of_birth', 'email', 'first_name', 'last_name', 'bodegas_asignadas')
        }),
    )
    
    # Enable search
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']
    
    # Configure many-to-many fields
    filter_horizontal = ['groups', 'user_permissions', 'superior', 'bodegas_asignadas']

# Inline para asignar usuarios desde la vista de Bodega
class BodegueroInline(admin.TabularInline):
    model = CustomUser.bodegas_asignadas.through
    extra = 1
    verbose_name = "Bodeguero Asignado"
    verbose_name_plural = "Bodegueros Asignados"

class BodegaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'sede']
    search_fields = ['nombre', 'sede__nombre']
    list_filter = ['sede']
    inlines = [BodegueroInline]

# Register models
admin.site.register(Sede)
admin.site.register(Area)
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Bodega, BodegaAdmin)
admin.site.register(Producto)
admin.site.register(Batch)
admin.site.register(ProcessStep)
admin.site.register(FormulaColor)
admin.site.register(DetalleFormula)
admin.site.register(Cliente)
admin.site.register(OrdenProduccion)
admin.site.register(LoteProduccion)
admin.site.register(PedidoVenta)
admin.site.register(DetallePedido)