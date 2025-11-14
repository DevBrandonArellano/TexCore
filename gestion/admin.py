from django.contrib import admin
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Inventory, ProcessStep,
    MaterialMovement, Chemical, FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)

admin.site.register(Sede)
admin.site.register(Area)
admin.site.register(CustomUser)
admin.site.register(Producto)
admin.site.register(Batch)
admin.site.register(Inventory)
admin.site.register(ProcessStep)
admin.site.register(MaterialMovement)
admin.site.register(Chemical)
admin.site.register(FormulaColor)
admin.site.register(DetalleFormula)
admin.site.register(Cliente)
admin.site.register(OrdenProduccion)
admin.site.register(LoteProduccion)
admin.site.register(PedidoVenta)
admin.site.register(DetallePedido)