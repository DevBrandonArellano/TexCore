from django.urls import include, path
from rest_framework.routers import DefaultRouter

from inventory.reporting_proxy import ReportingProxyView

from .profile_views import UserProfileView
from .views import (
    AreaViewSet,
    BodegaViewSet,
    ChemicalViewSet,
    ClienteViewSet,
    ComponenteMezclaOPViewSet,
    ConsumoLoteDetalleViewSet,
    CorridaProduccionViewSet,
    CustomUserViewSet,
    EtapaProduccionViewSet,
    FormulaColorViewSet,
    FrontendLogView,
    GroupViewSet,
    KPIAreaView,
    KpiEjecutivoView,
    LineaProduccionViewSet,
    LoteProduccionViewSet,
    MaquinaViewSet,
    OperacionProduccionViewSet,
    OrdenProduccionViewSet,
    PagoClienteViewSet,
    ParoMaquinaViewSet,
    PedidoVentaViewSet,
    PlanProduccionViewSet,
    PlantaPulsoDiarioView,
    ProcesoTintoreriaViewSet,
    ProcessStepViewSet,
    ProduccionHistorialProductoView,
    ProduccionPorProductoImprimirView,
    ProduccionPorProductoView,
    ProduccionResumenView,
    ProduccionTendenciaView,
    ProductoViewSet,
    ProveedorViewSet,
    RegistrarLoteProduccionView,
    SedeViewSet,
    TransferenciaInterareaViewSet,
    TrazabilidadPorCodigoLoteView,
)
from .views.materia_prima_views import MateriaPrimaLoteViewSet, TraceabilityViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'sedes', SedeViewSet, basename='sede')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'chemicals', ChemicalViewSet, basename='chemical')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'bodegas', BodegaViewSet, basename='bodega')
router.register(r'process-steps', ProcessStepViewSet, basename='processstep')
router.register(r'formula-colors', FormulaColorViewSet, basename='formulacolor')
router.register(r'procesos-tintoreria', ProcesoTintoreriaViewSet, basename='procesotintoreria')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'ordenes-produccion', OrdenProduccionViewSet, basename='ordenproduccion')
router.register(r'lotes-produccion', LoteProduccionViewSet, basename='loteproduccion')
router.register(r'pedidos-venta', PedidoVentaViewSet, basename='pedidoventa')
router.register(r'pagos-cliente', PagoClienteViewSet, basename='pagocliente')
router.register(r'maquinas', MaquinaViewSet, basename='maquina')
router.register(r'paros-maquina', ParoMaquinaViewSet, basename='paromaquina')
router.register(r'lineas-produccion', LineaProduccionViewSet, basename='linea-produccion')
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'componentes-mezcla', ComponenteMezclaOPViewSet, basename='componente-mezcla')
router.register(r'consumo-lote-detalle', ConsumoLoteDetalleViewSet, basename='consumo-lote-detalle')
router.register(r'materia-prima', MateriaPrimaLoteViewSet, basename='materia-prima')
router.register(r'trazabilidad', TraceabilityViewSet, basename='trazabilidad')
router.register(r'etapas-produccion', EtapaProduccionViewSet, basename='etapa-produccion')
router.register(r'transferencias-interarea', TransferenciaInterareaViewSet, basename='transferencia-interarea')
router.register(r'corridas-produccion', CorridaProduccionViewSet, basename='corridaproduccion')
router.register(r'operaciones-produccion', OperacionProduccionViewSet, basename='operacionproduccion')
router.register(r'planes-produccion', PlanProduccionViewSet, basename='planproduccion')


urlpatterns = [
    path('', include(router.urls)),
    path('reporting/<path:report_path>', ReportingProxyView.as_view(), name='reporting-proxy-fallback'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('ordenes-produccion/<int:orden_id>/registrar-lote/',
         RegistrarLoteProduccionView.as_view(), name='registrar-lote'),
    path('trazabilidad-lote/<str:codigo_lote>/',
         TrazabilidadPorCodigoLoteView.as_view(), name='trazabilidad-por-codigo-lote'),
    path('kpi-area/', KPIAreaView.as_view(), name='kpi-area'),
    path('produccion/pulso-diario/', PlantaPulsoDiarioView.as_view(), name='planta-pulso-diario'),
    # --- Vistas Ejecutivas (CU-EJ-01, CU-EJ-02, CU-EJ-03) ---
    path('kpi-ejecutivo/', KpiEjecutivoView.as_view(), name='kpi-ejecutivo'),
    path('produccion/resumen/', ProduccionResumenView.as_view(), name='produccion-resumen'),
    path('produccion/tendencia/', ProduccionTendenciaView.as_view(), name='produccion-tendencia'),
    # --- CU-EJ-08/09: Producción por Producto (drill-down ejecutivo) ---
    path('produccion/por-producto/', ProduccionPorProductoView.as_view(), name='produccion-por-producto'),
    path('produccion/por-producto/imprimir/', ProduccionPorProductoImprimirView.as_view(),
         name='produccion-por-producto-imprimir'),
    path('produccion/historial-producto/', ProduccionHistorialProductoView.as_view(),
         name='produccion-historial-producto'),
    path('logs/', FrontendLogView.as_view(), name='frontend-logs'),
]
