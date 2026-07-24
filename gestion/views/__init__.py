from .catalog_views import (
    ChemicalViewSet,
    ProductoViewSet,
    ProveedorViewSet,
)

from .core_views import (
    GroupViewSet,
    SedeViewSet,
    AreaViewSet,
    CustomUserViewSet,
)

from .formula_views import (
    BatchViewSet,
    ProcessStepViewSet,
    FormulaColorViewSet,
    DetalleFormulaViewSet,
)

from .inventory_views import (
    BodegaViewSet,
)

from .kpi_views import (
    KPIAreaView,
    KpiEjecutivoView,
    ProduccionResumenView,
    ProduccionTendenciaView,
)

from .production_views import (
    LineaProduccionViewSet,
    MaquinaViewSet,
    ParoMaquinaViewSet,
    OrdenProduccionViewSet,
    LoteProduccionViewSet,
    RegistrarLoteProduccionView,
    ComponenteMezclaOPViewSet,
    ConsumoLoteDetalleViewSet,
    AreaProcessStepViewSet,
    OrdenProduccionSubprocesoViewSet,
    EtapaProduccionViewSet,
    TransferenciaInterareaViewSet,
)

from .sales_views import (
    ClienteViewSet,
    PagoClienteViewSet,
    PedidoVentaViewSet,
    DetallePedidoViewSet,
)

from .system_views import (
    FrontendLogView,
)

__all__ = [
    'AreaProcessStepViewSet',
    'AreaViewSet',
    'BatchViewSet',
    'BodegaViewSet',
    'ChemicalViewSet',
    'ClienteViewSet',
    'ComponenteMezclaOPViewSet',
    'ConsumoLoteDetalleViewSet',
    'CustomUserViewSet',
    'DetalleFormulaViewSet',
    'DetallePedidoViewSet',
    'EtapaProduccionViewSet',
    'FormulaColorViewSet',
    'FrontendLogView',
    'GroupViewSet',
    'KPIAreaView',
    'KpiEjecutivoView',
    'LineaProduccionViewSet',
    'LoteProduccionViewSet',
    'MaquinaViewSet',
    'ParoMaquinaViewSet',
    'OrdenProduccionSubprocesoViewSet',
    'OrdenProduccionViewSet',
    'PagoClienteViewSet',
    'PedidoVentaViewSet',
    'ProcessStepViewSet',
    'ProduccionResumenView',
    'ProduccionTendenciaView',
    'ProductoViewSet',
    'ProveedorViewSet',
    'RegistrarLoteProduccionView',
    'SedeViewSet',
    'TransferenciaInterareaViewSet',
]
