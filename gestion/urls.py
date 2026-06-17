from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.reporting_proxy import ReportingProxyView
from .views import (
    GroupViewSet,
    SedeViewSet,
    AreaViewSet,
    CustomUserViewSet,
    ChemicalViewSet,
    ProductoViewSet,
    BatchViewSet,
    BodegaViewSet,
    ProcessStepViewSet,
    FormulaColorViewSet,
    DetalleFormulaViewSet,
    ClienteViewSet,
    OrdenProduccionViewSet,
    LoteProduccionViewSet,
    PedidoVentaViewSet,
    DetallePedidoViewSet,
    PagoClienteViewSet,
    MaquinaViewSet,
    RegistrarLoteProduccionView,
    KPIAreaView,
    ProveedorViewSet,
    KpiEjecutivoView,
    ProduccionResumenView,
    ProduccionTendenciaView,
    FrontendLogView,
    ComponenteMezclaOPViewSet,
    ConsumoLoteDetalleViewSet,
    AreaProcessStepViewSet,
    OrdenProduccionSubprocesoViewSet,
    EtapaProduccionViewSet,
    TransferenciaInterareaViewSet,
)
from .views.materia_prima_views import MateriaPrimaLoteViewSet, TraceabilityViewSet

from .profile_views import UserProfileView

router = DefaultRouter()
router.register(r'groups', GroupViewSet, basename='group')
router.register(r'sedes', SedeViewSet, basename='sede')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'users', CustomUserViewSet, basename='user')
router.register(r'chemicals', ChemicalViewSet, basename='chemical')
# Alias legacy para compatibilidad con clientes que aún consumen /quimicos/
router.register(r'quimicos', ChemicalViewSet, basename='chemical-legacy')
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'bodegas', BodegaViewSet, basename='bodega')
router.register(r'process-steps', ProcessStepViewSet, basename='processstep')
router.register(r'formula-colors', FormulaColorViewSet, basename='formulacolor')
router.register(r'detalle-formulas', DetalleFormulaViewSet, basename='detalleformula')
router.register(r'clientes', ClienteViewSet, basename='cliente')
router.register(r'ordenes-produccion', OrdenProduccionViewSet, basename='ordenproduccion')
router.register(r'lotes-produccion', LoteProduccionViewSet, basename='loteproduccion')
router.register(r'pedidos-venta', PedidoVentaViewSet, basename='pedidoventa')
router.register(r'detalles-pedido', DetallePedidoViewSet, basename='detallepedido')
router.register(r'pagos-cliente', PagoClienteViewSet, basename='pagocliente')
router.register(r'maquinas', MaquinaViewSet, basename='maquina')
router.register(r'proveedores', ProveedorViewSet, basename='proveedor')
router.register(r'componentes-mezcla', ComponenteMezclaOPViewSet, basename='componente-mezcla')
router.register(r'consumo-lote-detalle', ConsumoLoteDetalleViewSet, basename='consumo-lote-detalle')
router.register(r'materia-prima', MateriaPrimaLoteViewSet, basename='materia-prima')
router.register(r'trazabilidad', TraceabilityViewSet, basename='trazabilidad')
router.register(r'area-process-steps', AreaProcessStepViewSet, basename='area-process-step')
router.register(
    r'ordenes-produccion-subprocesos',
    OrdenProduccionSubprocesoViewSet,
    basename='orden-produccion-subproceso')
router.register(r'etapas-produccion', EtapaProduccionViewSet, basename='etapa-produccion')
router.register(r'transferencias-interarea', TransferenciaInterareaViewSet, basename='transferencia-interarea')


urlpatterns = [
    path('', include(router.urls)),
    path('reporting/<path:report_path>', ReportingProxyView.as_view(), name='reporting-proxy-fallback'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('ordenes-produccion/<int:orden_id>/registrar-lote/',
         RegistrarLoteProduccionView.as_view(), name='registrar-lote'),
    path('kpi-area/', KPIAreaView.as_view(), name='kpi-area'),
    # --- Vistas Ejecutivas (CU-EJ-01, CU-EJ-02, CU-EJ-03) ---
    path('kpi-ejecutivo/', KpiEjecutivoView.as_view(), name='kpi-ejecutivo'),
    path('produccion/resumen/', ProduccionResumenView.as_view(), name='produccion-resumen'),
    path('produccion/tendencia/', ProduccionTendenciaView.as_view(), name='produccion-tendencia'),
    path('logs/', FrontendLogView.as_view(), name='frontend-logs'),
]
