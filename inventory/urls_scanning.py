from django.urls import path
from .views import ValidateLoteAPIView

urlpatterns = [
    path('validate', ValidateLoteAPIView.as_view(), name='validate-lote-scanning'),
]
