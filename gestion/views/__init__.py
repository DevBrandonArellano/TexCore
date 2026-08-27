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
    PlantaPulsoDiarioView,
    ProduccionResumenView,
    ProduccionTendenciaView,
    ProduccionPorProductoView,
    ProduccionHistorialProductoView,
    ProduccionPorProductoImprimirView,
)

from .production_maquina_views import (
    MaquinaViewSet,
    ParoMaquinaViewSet,
    LineaProduccionViewSet,
)
from .production_orden_views import (
    OrdenProduccionViewSet,
)
from .production_lote_views import (
    LoteProduccionViewSet,
    RegistrarLoteProduccionView,
    TrazabilidadPorCodigoLoteView,
)
from .production_componente_views import (
    ComponenteMezclaOPViewSet,
    ConsumoLoteDetalleViewSet,
)
from .production_subproceso_views import (
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
    'PlantaPulsoDiarioView',
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
    'TrazabilidadPorCodigoLoteView',
]
