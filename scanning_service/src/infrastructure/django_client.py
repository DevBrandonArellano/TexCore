"""
DjangoApiClient: implementa ILoteRepository via Django Internal API.
Patrón Adapter: traduce HTTP response a domain models.
Circuit Breaker: 3 errores consecutivos → RuntimeError con mensaje claro.
ISO 27001 A.12.4: logs estructurados por cada llamada HTTP.
"""
import logging
from decimal import Decimal
from typing import Optional

import httpx

from ..domain.models import Bodega, LoteProduccion, OrdenProduccion, Producto, StockBodega
from .jwt_token_manager import JWTTokenManager

logger = logging.getLogger(__name__)

_CIRCUIT_THRESHOLD = 3


class DjangoApiClient:
    """
    Adapter que implementa ILoteRepository haciendo UNA llamada HTTP a Django.
    Distribuye los datos entre get_lote_by_codigo y get_stock_activo_por_lote
    mediante un caché interno de corta duración (por request).
    """

    def __init__(self, token_manager: JWTTokenManager, base_url: str) -> None:
        self._token_manager = token_manager
        self._base_url = base_url.rstrip("/")
        self._stock_cache: dict[int, Optional[StockBodega]] = {}
        self._error_count: int = 0

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token_manager.get_valid_token()}"}

    def get_lote_by_codigo(self, codigo: str) -> Optional[LoteProduccion]:
        url = f"{self._base_url}/api/internal/v1/lotes/{codigo}/validate/"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=5.0)
            self._error_count = 0  # reset en éxito
        except httpx.TimeoutException:
            self._error_count += 1
            logger.error(
                "Timeout en Django API [%d/%d]",
                self._error_count,
                _CIRCUIT_THRESHOLD,
                extra={"sd": {"severity": 3, "url": url, "errors": self._error_count}},
            )
            if self._error_count >= _CIRCUIT_THRESHOLD:
                raise RuntimeError(
                    "Django Internal API no responde (circuit breaker activo)."
                )
            raise

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            self._error_count += 1
            logger.error(
                "Error HTTP %d en Django API",
                response.status_code,
                extra={"sd": {"severity": 3, "status": response.status_code}},
            )
            raise RuntimeError(f"Django Internal API respondió {response.status_code}")

        data = response.json()
        lote_id = data["lote_id"]

        # Poblar cache de stock para la siguiente llamada (protocolo 2-pasos)
        if data.get("peso_kg") is not None:
            self._stock_cache[lote_id] = StockBodega(
                id=data["stock_id"],
                cantidad=Decimal(str(data["peso_kg"])),
                bodega=Bodega(
                    id=data["bodega"]["id"],
                    nombre=data["bodega"]["nombre"],
                ),
            )
        else:
            self._stock_cache[lote_id] = None

        logger.info(
            "Lote obtenido desde Django API",
            extra={"sd": {"severity": 6, "lote_id": lote_id}},
        )
        return LoteProduccion(
            id=lote_id,
            codigo_lote=data["codigo_lote"],
            orden_produccion=OrdenProduccion(
                id=data["orden_produccion_id"],
                estado=data["estado"],
                producto=Producto(
                    id=data["producto"]["id"],
                    descripcion=data["producto"]["descripcion"],
                ),
            ),
        )

    def get_stock_activo_por_lote(self, lote_id: int) -> Optional[StockBodega]:
        """Retorna StockBodega desde caché poblado por get_lote_by_codigo."""
        return self._stock_cache.pop(lote_id, None)
