"""URLs de la API interna. Namespace: internal_api."""
from django.urls import path

from internal_api.views.auth_views import ServiceTokenRefreshView, ServiceTokenView
from internal_api.views.scanning_views import ValidateLoteView
from internal_api.views.pdf_produccion_views import (
    BalanceMasasPdfView,
    ReporteAvancePdfView,
)
from internal_api.views.reporting_views import (
    AgingView,
    DeudoresGerencialView,
    DeudoresVendedorView,
    KardexView,
    LotesProduccionView,
    OrdenesProduccionView,
    PlantaPulsoDiarioView,
    ProductosView,
    ResumenMovimientosView,
    RotacionView,
    StockActualView,
    StockCeroView,
    TendenciaProduccionView,
    TopClientesGerencialView,
    TopClientesVendedorView,
    UsuariosView,
    ValorizacionView,
    VentasGerencialView,
    VentasVendedorView,
)

app_name = "internal_api"

urlpatterns = [
    # ── Autenticación ──────────────────────────────────────────────────────
    path("auth/token/", ServiceTokenView.as_view(), name="service_token"),
    path("auth/refresh/", ServiceTokenRefreshView.as_view(), name="service_token_refresh"),

    # ── Scanning ───────────────────────────────────────────────────────────
    path("lotes/<str:codigo_barras>/validate/", ValidateLoteView.as_view(), name="validate_lote"),

    # ── Reporting — Inventario ─────────────────────────────────────────────
    path("reports/kardex/", KardexView.as_view(), name="reports_kardex"),
    path("reports/productos/", ProductosView.as_view(), name="reports_productos"),
    path("reports/usuarios/", UsuariosView.as_view(), name="reports_usuarios"),
    path("reports/stock-actual/", StockActualView.as_view(), name="reports_stock_actual"),
    path("reports/valorizacion/", ValorizacionView.as_view(), name="reports_valorizacion"),
    path("reports/aging/", AgingView.as_view(), name="reports_aging"),
    path("reports/rotacion/", RotacionView.as_view(), name="reports_rotacion"),
    path("reports/stock-cero/", StockCeroView.as_view(), name="reports_stock_cero"),
    path("reports/resumen-movimientos/", ResumenMovimientosView.as_view(), name="reports_resumen_movimientos"),

    # ── Reporting — Vendedores ──────────────────────────────────────────────
    path("vendedores/<int:vendedor_id>/ventas/", VentasVendedorView.as_view(), name="vendedores_ventas"),
    path("vendedores/<int:vendedor_id>/top-clientes/", TopClientesVendedorView.as_view(), name="vendedores_top_clientes"),
    path("vendedores/<int:vendedor_id>/deudores/", DeudoresVendedorView.as_view(), name="vendedores_deudores"),

    # ── Reporting — Gerencial ───────────────────────────────────────────────
    path("gerencial/ventas/", VentasGerencialView.as_view(), name="gerencial_ventas"),
    path("gerencial/top-clientes/", TopClientesGerencialView.as_view(), name="gerencial_top_clientes"),
    path("gerencial/deudores/", DeudoresGerencialView.as_view(), name="gerencial_deudores"),

    # ── Reporting — Producción ──────────────────────────────────────────────
    path("produccion/ordenes/", OrdenesProduccionView.as_view(), name="produccion_ordenes"),
    path("produccion/lotes/", LotesProduccionView.as_view(), name="produccion_lotes"),
    path("produccion/tendencia/", TendenciaProduccionView.as_view(), name="produccion_tendencia"),

    # ── PDF de producción (proxy al printing_service) ───────────────────
    path(
        "reports/produccion/reporte-avance/",
        ReporteAvancePdfView.as_view(),
        name="reports_produccion_reporte_avance",
    ),
    path(
        "reports/produccion/reporte-balance/",
        BalanceMasasPdfView.as_view(),
        name="reports_produccion_reporte_balance",
    ),

    # ── Pulso Diario Planta ─────────────────────────────────────────────────
    path("planta/pulso-diario/", PlantaPulsoDiarioView.as_view(), name="planta_pulso_diario"),
]
