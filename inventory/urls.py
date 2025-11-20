from django.urls import path
from .views import TransferenciaStockAPIView, KardexBodegaAPIView, AlertasStockAPIView

urlpatterns = [
    path('transferencias/', TransferenciaStockAPIView.as_view(), name='realizar-transferencia'),
    path('bodegas/<int:bodega_id>/kardex/', KardexBodegaAPIView.as_view(), name='reporte-kardex'),
    path('alertas-stock/', AlertasStockAPIView.as_view(), name='alertas-stock'),
]
