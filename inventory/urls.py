from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TransferenciaStockAPIView, KardexBodegaAPIView, AlertasStockAPIView, 
    MovimientoInventarioViewSet, StockBodegaViewSet,
    ValidateLoteAPIView, ProcessDespachoAPIView
)
from .transform_view import TransformacionAPIView

router = DefaultRouter()
router.register(r'movimientos', MovimientoInventarioViewSet, basename='movimiento')
router.register(r'stock', StockBodegaViewSet, basename='stock')

urlpatterns = [
    path('', include(router.urls)),
    path('transferencias/', TransferenciaStockAPIView.as_view(), name='realizar-transferencia'),
    path('transformaciones/', TransformacionAPIView.as_view(), name='realizar-transformacion'),
    path('bodegas/<int:bodega_id>/kardex/', KardexBodegaAPIView.as_view(), name='reporte-kardex'),
    path('alertas-stock/', AlertasStockAPIView.as_view(), name='alertas-stock'),
    path('process-despacho/', ProcessDespachoAPIView.as_view(), name='process-despacho'),
]
