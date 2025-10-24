from rest_framework import viewsets, status
from rest_framework.response import Response
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

class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer

class CustomUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

class InventoryViewSet(viewsets.ModelViewSet):
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer

class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer

class MaterialMovementViewSet(viewsets.ModelViewSet):
    queryset = MaterialMovement.objects.all()
    serializer_class = MaterialMovementSerializer

class ChemicalViewSet(viewsets.ModelViewSet):
    queryset = Chemical.objects.all()
    serializer_class = ChemicalSerializer

class FormulaColorViewSet(viewsets.ModelViewSet):
    queryset = FormulaColor.objects.all()
    serializer_class = FormulaColorSerializer

class DetalleFormulaViewSet(viewsets.ModelViewSet):
    queryset = DetalleFormula.objects.all()
    serializer_class = DetalleFormulaSerializer

class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

class OrdenProduccionViewSet(viewsets.ModelViewSet):
    queryset = OrdenProduccion.objects.all()
    serializer_class = OrdenProduccionSerializer

class LoteProduccionViewSet(viewsets.ModelViewSet):
    queryset = LoteProduccion.objects.all()
    serializer_class = LoteProduccionSerializer

class PedidoVentaViewSet(viewsets.ModelViewSet):
    queryset = PedidoVenta.objects.all()
    serializer_class = PedidoVentaSerializer

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer