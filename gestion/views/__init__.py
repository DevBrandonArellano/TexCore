from .catalog_views import (
    ChemicalViewSet,
    ProductoViewSet,
    ProveedorViewSet,
)
from .configuracion_empaque_views import ConfiguracionEmpaqueView
from .core_views import (
    AreaViewSet,
    CustomUserViewSet,
    GroupViewSet,
    SedeViewSet,
)
from .formula_views import (
    FormulaColorViewSet,
    ProcesoTintoreriaViewSet,
    ProcessStepViewSet,
)
from .inventory_views import (
    BodegaViewSet,
)
from .kpi_views import (
    KPIAreaView,
    KpiEjecutivoView,
    PlantaPulsoDiarioView,
    ProduccionHistorialProductoView,
    ProduccionPorProductoImprimirView,
    ProduccionPorProductoView,
    ProduccionResumenView,
    ProduccionTendenciaView,
)
from .mes_views import (
    CorridaProduccionViewSet,
    OperacionProduccionViewSet,
    PlanProduccionViewSet,
)
from .production_componente_views import (
    ComponenteMezclaOPViewSet,
    ConsumoLoteDetalleViewSet,
)
from .production_lote_views import (
    LoteProduccionViewSet,
    RegistrarLoteProduccionView,
    TrazabilidadPorCodigoLoteView,
)
from .production_maquina_views import (
    LineaProduccionViewSet,
    MaquinaViewSet,
    ParoMaquinaViewSet,
)
from .production_orden_views import (
    OrdenProduccionViewSet,
)
from .production_subproceso_views import (
    EtapaProduccionViewSet,
    TransferenciaInterareaViewSet,
)
from .sales_views import (
    ClienteViewSet,
    PagoClienteViewSet,
    PedidoVentaViewSet,
)
from .system_views import (
    FrontendLogView,
)

__all__ = [
    'AreaViewSet',
    'BodegaViewSet',
    'ChemicalViewSet',
    'ClienteViewSet',
    'ComponenteMezclaOPViewSet',
    'ConfiguracionEmpaqueView',
    'ConsumoLoteDetalleViewSet',
    'CorridaProduccionViewSet',
    'CustomUserViewSet',
    'EtapaProduccionViewSet',
    'FormulaColorViewSet',
    'FrontendLogView',
    'GroupViewSet',
    'KPIAreaView',
    'KpiEjecutivoView',
    'LineaProduccionViewSet',
    'LoteProduccionViewSet',
    'MaquinaViewSet',
    'OperacionProduccionViewSet',
    'OrdenProduccionViewSet',
    'PagoClienteViewSet',
    'ParoMaquinaViewSet',
    'PedidoVentaViewSet',
    'PlanProduccionViewSet',
    'PlantaPulsoDiarioView',
    'ProcesoTintoreriaViewSet',
    'ProcessStepViewSet',
    'ProduccionHistorialProductoView',
    'ProduccionPorProductoImprimirView',
    'ProduccionPorProductoView',
    'ProduccionResumenView',
    'ProduccionTendenciaView',
    'ProductoViewSet',
    'ProveedorViewSet',
    'RegistrarLoteProduccionView',
    'SedeViewSet',
    'TransferenciaInterareaViewSet',
    'TrazabilidadPorCodigoLoteView',
]
