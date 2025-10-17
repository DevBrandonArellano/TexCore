from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SedeViewSet,
    AreaViewSet,
    CustomUserViewSet,
    MaterialViewSet,
    BatchViewSet,
    InventoryViewSet,
    ProcessStepViewSet,
    MaterialMovementViewSet,
    ChemicalViewSet,
)

router = DefaultRouter()
router.register(r'sedes', SedeViewSet, basename='sede')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'materials', MaterialViewSet, basename='material')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'inventory', InventoryViewSet, basename='inventory')
router.register(r'process-steps', ProcessStepViewSet, basename='processstep')
router.register(r'material-movements', MaterialMovementViewSet, basename='materialmovement')
router.register(r'chemicals', ChemicalViewSet, basename='chemical')

urlpatterns = [
    path('', include(router.urls)),
]
