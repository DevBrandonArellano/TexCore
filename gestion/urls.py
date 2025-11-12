from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GroupViewSet,
    SedeViewSet,
    AreaViewSet,
    CustomUserViewSet,
    ProductoViewSet,
    BatchViewSet,
    InventoryViewSet,
    ProcessStepViewSet,
    MaterialMovementViewSet,
    ChemicalViewSet,
    FormulaColorViewSet,
    DetalleFormulaViewSet,
    ClienteViewSet,
    OrdenProduccionViewSet,
    LoteProduccionViewSet,
    PedidoVentaViewSet,
    DetallePedidoViewSet,
)

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'sedes', SedeViewSet, basename='sede')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'productos', ProductoViewSet, basename='producto') # Changed from materials
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'process-steps', ProcessStepViewSet, basename='processstep')
router.register(r'material-movements', MaterialMovementViewSet, basename='materialmovement')
router.register(r'chemicals', ChemicalViewSet, basename='chemical')
router.register(r'formula-colors', FormulaColorViewSet, basename='formulacolor')
router.register(r'detalle-formulas', DetalleFormulaViewSet, basename='detalleformula')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'ordenes-produccion', OrdenProduccionViewSet, basename='ordenproduccion')
router.register(r'lotes-produccion', LoteProduccionViewSet, basename='loteproduccion')
router.register(r'pedidos-venta', PedidoVentaViewSet, basename='pedidoventa')
router.register(r'detalles-pedido', DetallePedidoViewSet, basename='detallepedido')


urlpatterns = [
    path('', include(router.urls)),
]