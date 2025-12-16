from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    GroupViewSet,
    SedeViewSet,
    AreaViewSet,
    CustomUserViewSet,
    ProductoViewSet,
    BatchViewSet,
    BodegaViewSet,
    ProcessStepViewSet,
    FormulaColorViewSet,
    DetalleFormulaViewSet,
    ClienteViewSet,
    OrdenProduccionViewSet,
    LoteProduccionViewSet,
    PedidoVentaViewSet,
    DetallePedidoViewSet,
    RegistrarLoteProduccionView,
    # TestErrorView # Import TestErrorView - REMOVED
)
from .profile_views import UserProfileView

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'sedes', SedeViewSet, basename='sede')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'bodegas', BodegaViewSet, basename='bodega')
router.register(r'process-steps', ProcessStepViewSet, basename='processstep')
router.register(r'formula-colors', FormulaColorViewSet, basename='formulacolor')
router.register(r'detalle-formulas', DetalleFormulaViewSet, basename='detalleformula')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'ordenes-produccion', OrdenProduccionViewSet, basename='ordenproduccion')
router.register(r'lotes-produccion', LoteProduccionViewSet, basename='loteproduccion')
router.register(r'pedidos-venta', PedidoVentaViewSet, basename='pedidoventa')
router.register(r'detalles-pedido', DetallePedidoViewSet, basename='detallepedido')


urlpatterns = [
    path('', include(router.urls)),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('ordenes-produccion/<int:orden_id>/registrar-lote/', RegistrarLoteProduccionView.as_view(), name='registrar-lote'),
    # path('test-error/<str:error_type>/', TestErrorView.as_view(), name='test-error'), # Temporary URL for testing error handler - REMOVED
]