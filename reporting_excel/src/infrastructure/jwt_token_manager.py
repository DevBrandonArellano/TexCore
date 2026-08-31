"""
JWTTokenManager: gestiona ciclo de vida del JWT de servicio.
SRP: única responsabilidad — obtener y renovar el token.
ISO 27001 A.10: token almacenado solo en memoria, nunca en disco.
(Copia idéntica al de scanning_service — servicios independientes, sin paquete compartido)
"""
import logging
import time
from typing import Optional

import httpx
import jwt

logger = logging.getLogger(__name__)
_REFRESH_BUFFER_SECONDS = 30


class JWTTokenManager:
    """SRP: gestiona ciclo de vida del JWT. ISO 27001 A.10: en memoria."""

    def __init__(
        self,
        django_url: str,
        service_name: str,
        service_secret: str,
        public_key: str,
    ) -> None:
        self._django_url = django_url
        self._service_name = service_name
        self._service_secret = service_secret
        self._public_key = public_key
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    async def get_valid_token(self) -> str:
        if self._access_token is None or self._is_expiring(self._access_token):
            self._access_token = await self._fetch_token()
        return self._access_token

    async def _fetch_token(self) -> str:
        # httpx.AsyncClient (no el atajo httpx.post síncrono): esta llamada
        # se dispara desde rutas `async def` de FastAPI — usar I/O bloqueante
        # ahí congela el único event loop del proceso (uvicorn corre sin
        # --workers) y deja el microservicio entero sin atender ninguna otra
        # petición mientras dura el refresh del token.
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._django_url}/api/internal/v1/auth/token/",
                json={
                    "service_name": self._service_name,
                    "service_secret": self._service_secret,
                },
                timeout=10.0,
            )
        if response.status_code == 200:
            data = response.json()
            self._refresh_token = data["refresh_token"]
            return data["access_token"]
        raise RuntimeError(
            f"Error obteniendo token para {self._service_name}: HTTP {response.status_code}"
        )

    def _is_expiring(self, token: str) -> bool:
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                options={"verify_exp": False},
            )
            return payload["exp"] - _REFRESH_BUFFER_SECONDS <= time.time()
        except Exception:
            return True
