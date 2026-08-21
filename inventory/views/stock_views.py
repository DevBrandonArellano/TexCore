import logging

from django.db import models

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions

from inventory.serializers import StockBodegaSerializer
from inventory.models import StockBodega
from inventory.permissions import IsInventoryStaffOrAdmin

logger = logging.getLogger('inventory.views')


class StockBodegaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para ver el stock actual en todas las bodegas.
    """
    serializer_class = StockBodegaSerializer
    permission_classes = [IsInventoryStaffOrAdmin]
    # Este endpoint alimenta dashboards (admin/bodeguero/ejecutivo) que esperan
    # el universo completo de stock para agregar por bodega; paginar aquí corta
    # bodegas y genera gráficos/informes incompletos.
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = StockBodega.objects.select_related('bodega', 'producto', 'lote').all()
        sede_id = self.request.query_params.get('sede_id', None)
        if sede_id:
            queryset = queryset.filter(bodega__sede_id=sede_id)

        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists():
            return queryset

        # Bodegueros: solo stock de bodegas asignadas
        assigned_bodegas = user.bodegas_asignadas.values_list('id', flat=True)
        return queryset.filter(bodega_id__in=assigned_bodegas)


class AlertasStockAPIView(APIView):
    """
    API para listar todos los productos cuyo stock en alguna bodega
    está por debajo del mínimo definido.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = StockBodega.objects.filter(
            cantidad__lt=models.F('producto__stock_minimo')
        ).select_related('producto', 'bodega').order_by('bodega__nombre', 'producto__descripcion')
        sede_id = request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(bodega__sede_id=sede_id)

        # Ejecutivo ve todas las alertas (reportes gerenciales); bodegueros solo las suyas
        if not (
            user.is_superuser or user.groups.filter(
                name__in=[
                    'admin_sistemas',
                    'admin_sede',
                'ejecutivo']).exists()):
            assigned_bodegas = user.bodegas_asignadas.values_list('id', flat=True)
            queryset = queryset.filter(bodega_id__in=assigned_bodegas)

        alertas = queryset

        resultado = [
            {
                "bodega": item.bodega.nombre,
                "producto": item.producto.descripcion,
                "producto_codigo": item.producto.codigo,
                "stock_actual": item.cantidad,
                "stock_minimo": item.producto.stock_minimo,
                "faltante": item.producto.stock_minimo - item.cantidad
            }
            for item in alertas if item.producto.stock_minimo > 0
        ]
        return Response(resultado, status=status.HTTP_200_OK)
