from django.db import models

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, permissions

from inventory.serializers import StockBodegaSerializer
from inventory.models import StockBodega
from inventory.permissions import IsInventoryStaffOrAdmin


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
        # 'bodega__sede' es necesario, no solo 'bodega': Bodega.__str__() lee
        # self.sede.nombre, y StockBodegaSerializer serializa 'bodega' con
        # StringRelatedField (str(bodega)) para las 3465+ filas de este
        # queryset — sin esta relación anidada, cada fila dispara una query
        # extra para su sede (N+1 confirmado: 3466 queries para 3465 filas,
        # auditoría de performance 2026-08-31), la causa real detrás de la
        # latencia alta (p50 700ms, máx ~4.5s) de este endpoint bajo carga.
        queryset = StockBodega.objects.select_related('bodega__sede', 'producto', 'lote').all()
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

        # Ejecutivo ve todas las alertas (reportes gerenciales); bodegueros solo las suyas
        if not (
            user.is_superuser or user.groups.filter(
                name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']
            ).exists()
        ):
            assigned_bodegas = user.bodegas_asignadas.values_list('id', flat=True)
            queryset = queryset.filter(bodega_id__in=assigned_bodegas)

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
