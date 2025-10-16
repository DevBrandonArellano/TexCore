from django.urls import path
from .views import SedeAPIView, AreaAPIView, CustomUserAPIView

urlpatterns = [
    path('sedes/', SedeAPIView.as_view(), name='sede-list'),
    path('sedes/<int:pk>/', SedeAPIView.as_view(), name='sede-detail'),
    path('areas/', AreaAPIView.as_view(), name='area-list'),
    path('areas/<int:pk>/', AreaAPIView.as_view(), name='area-detail'),
    path('users/', CustomUserAPIView.as_view(), name='user-list'),
    path('users/<int:pk>/', CustomUserAPIView.as_view(), name='user-detail'),
]
