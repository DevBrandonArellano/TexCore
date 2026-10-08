from django.db import models
from django.db.models import Count, Q, Sum
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.views._common import parse_int_param
from inventory.models import StockBodega
from inventory.pagination import PaginacionAcotada
from inventory.permissions import IsInventoryStaffOrAdmin, bodegas_visibles
from inventory.serializers import StockBodegaSerializer


def stock_con_existencias(user, params):
    """Filas de stock con existencias que el usuario puede ver, acotadas por los filtros
    de la petición (sede_id, bodega_id, producto_id, lote_id, search). Base común del
    listado paginado y del resumen por bodega."""
    # Sin existencias no se lista: cada lote vendido deja su fila en cero y, con años de
    # operación, son decenas de miles de filas vacías (prueba de carga 2026-10-06).
    queryset = StockBodega.objects.exclude(cantidad=0, stock_comprometido=0)
    for param, campo in (
        ('sede_id', 'bodega__sede_id'),
        ('bodega_id', 'bodega_id'),
        ('producto_id', 'producto_id'),
        ('lote_id', 'lote_id'),
    ):
        valor = parse_int_param(params.get(param), param)
        if valor is not None:
            queryset = queryset.filter(**{campo: valor})
    texto = (params.get('search') or '').strip()
    if texto:
        queryset = queryset.filter(
            Q(producto__codigo__icontains=texto)
            | Q(producto__descripcion__icontains=texto)
            | Q(lote__codigo_lote__icontains=texto)
            | Q(bodega__nombre__icontains=texto)
        )

    visibles = bodegas_visibles(user)
    if visibles is None:
        return queryset
    return queryset.filter(bodega_id__in=visibles.values('id'))


class StockBodegaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API para ver el stock actual en todas las bodegas.
    """
    serializer_class = StockBodegaSerializer
    permission_classes = [IsInventoryStaffOrAdmin]
    # Paginado como kárdex y materia prima: sin tope, el administrador recibía 28 799
    # filas (8 MB) por petición y los workers se quedaban sin memoria (prueba de carga
    # 2026-10-06). Los dashboards que suman el universo completo usan /stock/resumen/.
    pagination_class = PaginacionAcotada

    def get_queryset(self):
        # 'bodega__sede', no solo 'bodega': Bodega.__str__() lee self.sede.nombre y el
        # serializer usa StringRelatedField; sin la relación anidada cada fila dispara
        # una consulta por su sede (N+1, auditoría de performance 2026-08-31).
        return (
            stock_con_existencias(self.request.user, self.request.query_params)
            .select_related('bodega__sede', 'producto', 'lote')
            .order_by('bodega__nombre', 'producto__descripcion', 'lote_id', 'id')
        )


class StockResumenAPIView(APIView):
    """
    Totales de stock por bodega, calculados en la base: alimenta los gráficos y KPI de
    los dashboards sin traer las filas por lote. Acepta los mismos filtros que el listado.
    """
    permission_classes = [IsInventoryStaffOrAdmin]

    def get(self, request, *args, **kwargs):
        queryset = stock_con_existencias(request.user, request.query_params)
        por_bodega = [
            {
                'bodega_id': fila['bodega_id'],
                'bodega': fila['bodega__nombre'],
                'cantidad': fila['cantidad'],
                'filas': fila['filas'],
            }
            for fila in queryset.values('bodega_id', 'bodega__nombre')
            .annotate(cantidad=Sum('cantidad'), filas=Count('id'))
            .order_by('-cantidad', 'bodega__nombre')
        ]
        totales = queryset.aggregate(
            total_cantidad=Sum('cantidad'),
            productos=Count('producto_id', distinct=True),
        )
        return Response({
            'total_cantidad': totales['total_cantidad'] or 0,
            'productos': totales['productos'],
            'bodegas': len(por_bodega),
            'por_bodega': por_bodega,
        })


class AlertasStockAPIView(APIView):
    """
    API para listar todos los productos cuyo stock acumulado en alguna bodega
    está por debajo del mínimo definido.
    Agrupa las existencias de todos los lotes por (bodega, producto) para
    evitar falsas alertas cuando múltiples lotes suman una cantidad superior
    al stock mínimo.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = StockBodega.objects.all()

        sede_id = request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(bodega__sede_id=sede_id)

        visibles = bodegas_visibles(user)
        if visibles is not None:
            queryset = queryset.filter(bodega_id__in=visibles.values('id'))

        # Agrupación por bodega y producto sumando todos los lotes
        alertas = (
            queryset
            .values(
                'bodega__nombre',
                'producto__codigo',
                'producto__descripcion',
                'producto__stock_minimo',
            )
            .annotate(stock_actual=models.Sum('cantidad'))
            .filter(
                producto__stock_minimo__gt=0,
                stock_actual__lt=models.F('producto__stock_minimo'),
            )
            .order_by('bodega__nombre', 'producto__descripcion')
        )

        resultado = [
            {
                "bodega": item['bodega__nombre'],
                "producto": item['producto__descripcion'],
                "producto_codigo": item['producto__codigo'],
                "stock_actual": item['stock_actual'],
                "stock_minimo": item['producto__stock_minimo'],
                "faltante": item['producto__stock_minimo'] - item['stock_actual'],
            }
            for item in alertas
        ]
        return Response(resultado, status=status.HTTP_200_OK)
