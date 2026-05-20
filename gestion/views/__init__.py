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
    MaquinaViewSet,
    OrdenProduccionViewSet,
    LoteProduccionViewSet,
    RegistrarLoteProduccionView,
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
    'AreaViewSet',
    'BatchViewSet',
    'BodegaViewSet',
    'ChemicalViewSet',
    'ClienteViewSet',
    'CustomUserViewSet',
    'DetalleFormulaViewSet',
    'DetallePedidoViewSet',
    'FormulaColorViewSet',
    'FrontendLogView',
    'GroupViewSet',
    'KPIAreaView',
    'KpiEjecutivoView',
    'LoteProduccionViewSet',
    'MaquinaViewSet',
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
]
