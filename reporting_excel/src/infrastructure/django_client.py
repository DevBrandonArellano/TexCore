"""
DjangoReportRepository: implementa IReportRepository via Django Internal API.
Patrón Adapter: mapea SP queries a endpoints REST.
ISO 27001 A.9: sin credenciales de BD en el servicio.
"""
import logging
import re
from typing import Optional, Tuple

import httpx
import pandas as pd

from .jwt_token_manager import JWTTokenManager

logger = logging.getLogger(__name__)

# Mapeo: nombre_sp → (endpoint_path, [param_names_en_orden])
# Orden de parámetros DEBE coincidir con el orden en las llamadas EXEC.
_SP_MAPPING: dict[str, tuple[str, list[str]]] = {
    "sp_GetKardexBodega": (
        "/api/internal/v1/reports/kardex/",
        ["bodega_id", "producto_id", "fecha_desde", "fecha_hasta", "proveedor_id", "lote_codigo"],
    ),
    "sp_GetProductosCatalogo": ("/api/internal/v1/reports/productos/", []),
    "sp_GetUsuariosSistema": ("/api/internal/v1/reports/usuarios/", []),
    "sp_GetStockActualBodega": (
        # NOTA: sin "sede_id" — el SQL de exports.py hardcodea @SedeID=NULL
        # como literal (no placeholder ?), así que solo 2 valores viajan
        # realmente en la tupla de params. Un tercer nombre aquí desalinea
        # el zip() posicional de execute_sp() y hace que producto_id se
        # envíe mal etiquetado como sede_id (que StockActualView ni lee).
        "/api/internal/v1/reports/stock-actual/",
        ["bodega_id", "producto_id"],
    ),
    "sp_GetValorizacionInventario": (
        "/api/internal/v1/reports/valorizacion/",
        ["bodega_id", "sede_id"],
    ),
    "sp_GetInventarioAging": (
        # NOTA: mismo caso que sp_GetStockActualBodega — @SedeID=NULL es
        # literal en el SQL de exports.py, no un placeholder ?.
        "/api/internal/v1/reports/aging/",
        ["bodega_id", "dias_minimos"],
    ),
    "sp_GetRotacionInventario": (
        "/api/internal/v1/reports/rotacion/",
        ["bodega_id", "fecha_desde", "fecha_hasta", "sede_id"],
    ),
    "sp_GetStockCeroBodega": (
        "/api/internal/v1/reports/stock-cero/",
        ["bodega_id", "sede_id"],
    ),
    "sp_GetResumenMovimientos": (
        "/api/internal/v1/reports/resumen-movimientos/",
        ["bodega_id", "fecha_desde", "fecha_hasta", "sede_id"],
    ),
    "sp_GetVentasPorVendedor": (
        "/api/internal/v1/vendedores/{vendedor_id}/ventas/",
        ["vendedor_id", "fecha_desde", "fecha_hasta"],
    ),
    "sp_GetTopClientesPorVendedor": (
        "/api/internal/v1/vendedores/{vendedor_id}/top-clientes/",
        ["vendedor_id", "fecha_desde", "fecha_hasta"],
    ),
    "sp_GetDeudoresPorVendedor": (
        "/api/internal/v1/vendedores/{vendedor_id}/deudores/",
        ["vendedor_id"],
    ),
    "sp_GetVentasGerencial": (
        "/api/internal/v1/gerencial/ventas/",
        ["fecha_desde", "fecha_hasta", "sede_id"],
    ),
    "sp_GetTopClientesGerencial": (
        "/api/internal/v1/gerencial/top-clientes/",
        ["fecha_desde", "fecha_hasta", "sede_id"],
    ),
    "sp_GetDeudoresGerencial": ("/api/internal/v1/gerencial/deudores/", ["sede_id"]),
    "sp_GetOrdenesProduccionGerencial": (
        "/api/internal/v1/produccion/ordenes/",
        ["fecha_desde", "fecha_hasta", "sede_id"],
    ),
    "sp_GetLotesProduccionGerencial": (
        "/api/internal/v1/produccion/lotes/",
        ["fecha_desde", "fecha_hasta", "sede_id"],
    ),
    "sp_GetTendenciaProduccionGerencial": (
        "/api/internal/v1/produccion/tendencia/",
        ["fecha_desde", "fecha_hasta", "sede_id"],
    ),
}


class DjangoReportRepository:
    """Adapter que implementa IReportRepository via Django Internal API."""

    def __init__(self, token_manager: JWTTokenManager, base_url: str) -> None:
        self._token_manager = token_manager
        self._base_url = base_url.rstrip("/")

    async def _headers(self) -> dict:
        return {"Authorization": f"Bearer {await self._token_manager.get_valid_token()}"}

    @staticmethod
    def _extract_sp_name(sp_query: str) -> str:
        """Extrae 'sp_GetKardexBodega' de 'EXEC sp_GetKardexBodega @BodegaID=?, ...'"""
        match = re.search(r"(sp_\w+)", sp_query, re.IGNORECASE)
        if not match:
            raise ValueError(f"No se encontró nombre de SP en: {sp_query[:60]}")
        return match.group(1)

    async def execute_sp(self, sp_query: str, params: Optional[Tuple]) -> pd.DataFrame:
        """
        Ejecuta un SP (mapeado a endpoint REST) y retorna el resultado como DataFrame.
        Implementa el mismo contrato que SqlRepository.execute_sp().
        """
        sp_name = self._extract_sp_name(sp_query)
        mapping = _SP_MAPPING.get(sp_name)
        if not mapping:
            raise ValueError(
                f"SP no mapeado: '{sp_name}'. Agregar a _SP_MAPPING en django_client.py."
            )

        endpoint_template, param_names = mapping

        # Construir path params y query params desde la lista ordenada
        path_params: dict = {}
        query_params: dict = {}
        if params and param_names:
            for name, value in zip(param_names, params):
                if value is None:
                    continue
                if f"{{{name}}}" in endpoint_template:
                    path_params[name] = value
                else:
                    query_params[name] = str(value)

        endpoint = endpoint_template.format(**path_params)
        url = f"{self._base_url}{endpoint}"

        try:
            # httpx.AsyncClient — no el atajo httpx.get síncrono. Esta llamada
            # se dispara desde rutas `async def` de FastAPI; bloquear el event
            # loop aquí congela TODO el microservicio (un solo worker uvicorn,
            # sin threads) mientras dura la consulta contra Django/SQL Server.
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url, params=query_params, headers=await self._headers()
                )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP %d en %s",
                exc.response.status_code,
                url,
                extra={"sd": {"severity": 3, "sp": sp_name, "status": exc.response.status_code}},
            )
            raise

        data = response.json()
        logger.info(
            "Reporte obtenido",
            extra={"sd": {"severity": 6, "sp": sp_name, "rows": len(data)}},
        )
        return pd.DataFrame(data) if data else pd.DataFrame()
