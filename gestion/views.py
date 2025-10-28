from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, IsAdminUser
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Inventory, ProcessStep,
    MaterialMovement, Chemical, FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)
from .serializers import (
    SedeSerializer, AreaSerializer, CustomUserSerializer, ProductoSerializer,
    BatchSerializer, InventorySerializer, ProcessStepSerializer,
    MaterialMovementSerializer, ChemicalSerializer, FormulaColorSerializer,
    DetalleFormulaSerializer, ClienteSerializer, OrdenProduccionSerializer,
    LoteProduccionSerializer, PedidoVentaSerializer, DetallePedidoSerializer
)

# Vistas refactorizadas usando Django ORM y ModelViewSet

class SedeViewSet(viewsets.ModelViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAdminUser]

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class MaterialMovementViewSet(viewsets.ModelViewSet):
    queryset = MaterialMovement.objects.all()
    serializer_class = MaterialMovementSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class ChemicalViewSet(viewsets.ModelViewSet):
    queryset = Chemical.objects.all()
    serializer_class = ChemicalSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class FormulaColorViewSet(viewsets.ModelViewSet):
    queryset = FormulaColor.objects.all()
    serializer_class = FormulaColorSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class DetalleFormulaViewSet(viewsets.ModelViewSet):
    queryset = DetalleFormula.objects.all()
    serializer_class = DetalleFormulaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class OrdenProduccionViewSet(viewsets.ModelViewSet):
    queryset = OrdenProduccion.objects.all()
    serializer_class = OrdenProduccionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class LoteProduccionViewSet(viewsets.ModelViewSet):
    queryset = LoteProduccion.objects.all()
    serializer_class = LoteProduccionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class PedidoVentaViewSet(viewsets.ModelViewSet):
    queryset = PedidoVenta.objects.all()
    serializer_class = PedidoVentaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]