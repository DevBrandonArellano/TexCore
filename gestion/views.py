from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, IsAdminUser, AllowAny
from .permissions import IsSystemAdmin
from django.contrib.auth.models import Group
from .models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido
)
from .serializers import (
    GroupSerializer, SedeSerializer, AreaSerializer, CustomUserSerializer, ProductoSerializer,
    BatchSerializer, BodegaSerializer, ProcessStepSerializer,
    FormulaColorSerializer,
    DetalleFormulaSerializer, ClienteSerializer, OrdenProduccionSerializer,
    LoteProduccionSerializer, PedidoVentaSerializer, DetallePedidoSerializer
)

# Vistas refactorizadas usando Django ORM y ModelViewSet

class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

class SedeViewSet(viewsets.ModelViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer
    permission_classes = [IsSystemAdmin]

class AreaViewSet(viewsets.ModelViewSet):
    queryset = Area.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [IsSystemAdmin]

class CustomUserViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    permission_classes = [IsSystemAdmin]

    def get_queryset(self):
        queryset = CustomUser.objects.select_related('sede', 'area').prefetch_related('groups').all()
        sede_id = self.request.query_params.get('sede', None)
        if sede_id is not None:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

class ChemicalViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.filter(tipo='quimico')
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class BodegaViewSet(viewsets.ModelViewSet):
    serializer_class = BodegaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede']).exists():
            return Bodega.objects.all()
        # For bodegueros and others, filter by assigned warehouses
        return Bodega.objects.filter(id__in=user.bodegas_asignadas.values_list('id', flat=True))

class ProcessStepViewSet(viewsets.ModelViewSet):
    queryset = ProcessStep.objects.all()
    serializer_class = ProcessStepSerializer
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

    def get_queryset(self):
        user = self.request.user
        queryset = Cliente.objects.prefetch_related(
            'pedidoventa_set',
            'pedidoventa_set__detalles',
            'pedidoventa_set__detalles__producto'
        )
        
        # If user is a salesman, only show their assigned clients
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(vendedor_asignado=user)
            
        return queryset.all()

class OrdenProduccionViewSet(viewsets.ModelViewSet):
    serializer_class = OrdenProduccionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        return OrdenProduccion.objects.select_related(
            'producto', 'formula_color', 'sede'
        ).all()

class LoteProduccionViewSet(viewsets.ModelViewSet):
    queryset = LoteProduccion.objects.all()
    serializer_class = LoteProduccionSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

class PedidoVentaViewSet(viewsets.ModelViewSet):
    serializer_class = PedidoVentaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    def get_queryset(self):
        user = self.request.user
        queryset = PedidoVenta.objects.select_related('cliente', 'sede').order_by('-fecha_pedido')
        
        # Filtering: Salesmen only see their own clients' orders
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
             queryset = queryset.filter(cliente__vendedor_asignado=user)
             
        # Optional: Skip older orders to avoid memory overload (e.g., last 100)
        limit = self.request.query_params.get('limit', 100)
        return queryset[:int(limit)]

from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from inventory.models import StockBodega, MovimientoInventario
# ... (existing imports)
from .serializers import (
    # ... (existing serializers)
    RegistrarLoteProduccionSerializer
)

# ... (existing viewsets)

class RegistrarLoteProduccionView(APIView):
    """
    API View to register a production lot and handle all related inventory movements.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, orden_id, *args, **kwargs):
        orden = get_object_or_404(OrdenProduccion, id=orden_id)

        if orden.estado != 'en_proceso':
            return Response({"error": "Solo se pueden registrar lotes en órdenes que están 'en proceso'."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RegistrarLoteProduccionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        lote_data = serializer.validated_data
        peso_neto_producido = lote_data['peso_neto_producido']
        
        # --- 1. Consume Input Product ---
        # Assumption: The main input product is stored in the same warehouse as the production order.
        producto_a_consumir = orden.producto
        bodega_origen = orden.bodega

        try:
            # Find stock for the input product, locking the row for the transaction.
            stock_input = StockBodega.objects.select_for_update().get(
                bodega=bodega_origen, producto=producto_a_consumir, lote=None
            )
            if stock_input.cantidad < peso_neto_producido:
                raise serializers.ValidationError(f"Stock insuficiente de '{producto_a_consumir.descripcion}'. Necesario: {peso_neto_producido}, Disponible: {stock_input.cantidad}")

            # Update stock and create movement record
            stock_input.cantidad -= peso_neto_producido
            stock_input.save()
            
            MovimientoInventario.objects.create(
                tipo_movimiento='CONSUMO',
                producto=producto_a_consumir,
                bodega_origen=bodega_origen,
                cantidad=peso_neto_producido,
                usuario=request.user,
                documento_ref=f'OP-{orden.codigo}'
            )
        except StockBodega.DoesNotExist:
            raise serializers.ValidationError(f"No hay stock de '{producto_a_consumir.descripcion}' en la bodega '{bodega_origen.nombre}'.")

        # --- 2. Consume Chemicals if Formula exists ---
        if orden.formula_color:
            for detalle in orden.formula_color.detalleformula_set.all():
                quimico = detalle.producto
                cantidad_requerida = (peso_neto_producido * detalle.gramos_por_kilo) / Decimal('1000.0')

                try:
                    stock_quimico = StockBodega.objects.select_for_update().get(bodega=bodega_origen, producto=quimico, lote=None)
                    if stock_quimico.cantidad < cantidad_requerida:
                        raise serializers.ValidationError(f"Stock insuficiente del químico '{quimico.descripcion}'. Necesario: {cantidad_requerida:.4f}, Disponible: {stock_quimico.cantidad}")

                    stock_quimico.cantidad -= cantidad_requerida
                    stock_quimico.save()

                    MovimientoInventario.objects.create(
                        tipo_movimiento='CONSUMO',
                        producto=quimico,
                        bodega_origen=bodega_origen,
                        cantidad=cantidad_requerida,
                        usuario=request.user,
                        documento_ref=f'OP-{orden.codigo}'
                    )
                except StockBodega.DoesNotExist:
                    raise serializers.ValidationError(f"No hay stock del químico '{quimico.descripcion}' en la bodega '{bodega_origen.nombre}'.")

        # --- 3. Create the Production Lot ---
        # Assumption: Output product is the same as input product (e.g. Hilo Crudo -> Hilo Tinturado)
        # A more complex system might have a different output product defined on the order.
        producto_final = orden.producto
        
        lote = LoteProduccion.objects.create(
            orden_produccion=orden,
            operario=request.user,
            **lote_data
        )

        # --- 4. Add the new lot to inventory ---
        # Assumption: The produced lot goes to the same warehouse where production happened.
        bodega_destino = orden.bodega
        stock_output, created = StockBodega.objects.get_or_create(
            bodega=bodega_destino,
            producto=producto_final,
            lote=lote,
            defaults={'cantidad': 0}
        )
        stock_output.cantidad += peso_neto_producido
        stock_output.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION',
            producto=producto_final,
            lote=lote,
            bodega_destino=bodega_destino,
            cantidad=peso_neto_producido,
            usuario=request.user,
            documento_ref=f'OP-{orden.codigo}'
        )

        return Response(LoteProduccionSerializer(lote).data, status=status.HTTP_201_CREATED)

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
