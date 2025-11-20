from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransferenciaStockAPIView, KardexBodegaAPIView, AlertasStockAPIView, MovimientoInventarioViewSet

router = DefaultRouter()
router.register(r'movimientos', MovimientoInventarioViewSet, basename='movimiento')

urlpatterns = [
    path('', include(router.urls)),
    path('transferencias/', TransferenciaStockAPIView.as_view(), name='realizar-transferencia'),
    path('bodegas/<int:bodega_id>/kardex/', KardexBodegaAPIView.as_view(), name='reporte-kardex'),
    path('alertas-stock/', AlertasStockAPIView.as_view(), name='alertas-stock'),
]
