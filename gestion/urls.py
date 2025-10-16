from django.urls import path
from .views import SedeAPIView, AreaAPIView, CustomUserAPIView, MaterialAPIView, BatchAPIView, InventoryAPIView, ProcessStepAPIView, MaterialMovementAPIView, ChemicalAPIView

urlpatterns = [
    path('sedes/', SedeAPIView.as_view(), name='sede-list'),
    path('sedes/<int:pk>/', SedeAPIView.as_view(), name='sede-detail'),
    path('areas/', AreaAPIView.as_view(), name='area-list'),
    path('areas/<int:pk>/', AreaAPIView.as_view(), name='area-detail'),
    path('users/', CustomUserAPIView.as_view(), name='user-list'),
    path('users/<int:pk>/', CustomUserAPIView.as_view(), name='user-detail'),
    path('materials/', MaterialAPIView.as_view(), name='material-list'),
    path('materials/<int:pk>/', MaterialAPIView.as_view(), name='material-detail'),
    path('batches/', BatchAPIView.as_view(), name='batch-list'),
    path('batches/<int:pk>/', BatchAPIView.as_view(), name='batch-detail'),
    path('inventory/', InventoryAPIView.as_view(), name='inventory-list'),
    path('inventory/<int:pk>/', InventoryAPIView.as_view(), name='inventory-detail'),
    path('process-steps/', ProcessStepAPIView.as_view(), name='processstep-list'),
    path('process-steps/<int:pk>/', ProcessStepAPIView.as_view(), name='processstep-detail'),
    path('material-movements/', MaterialMovementAPIView.as_view(), name='materialmovement-list'),
    path('material-movements/<int:pk>/', MaterialMovementAPIView.as_view(), name='materialmovement-detail'),
    path('chemicals/', ChemicalAPIView.as_view(), name='chemical-list'),
    path('chemicals/<int:pk>/', ChemicalAPIView.as_view(), name='chemical-detail'),
]
