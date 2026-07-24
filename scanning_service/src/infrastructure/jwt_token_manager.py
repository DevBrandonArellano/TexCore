"""
JWTTokenManager: gestiona ciclo de vida del JWT de servicio.
SRP: única responsabilidad — obtener y renovar el token.
ISO 27001 A.10: token almacenado solo en memoria, nunca en disco.
"""
import logging
import time
from typing import Optional

import httpx
import jwt

logger = logging.getLogger(__name__)

_REFRESH_BUFFER_SECONDS = 30


class JWTTokenManager:
    """
    Obtiene y renueva automáticamente el JWT RS256 del servicio.
    Thread-safe para uso en un único proceso Uvicorn worker.
    """

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

    def get_valid_token(self) -> str:
        """Retorna access token válido. Refresca si expira en los próximos 30s."""
        if self._access_token is None or self._is_expiring(self._access_token):
            logger.info(
                "Renovando token de servicio %s",
                self._service_name,
                extra={"sd": {"severity": 5, "service": self._service_name}},
            )
            self._access_token = self._fetch_token()
        return self._access_token

    def _fetch_token(self) -> str:
        """Solicita nuevo access token a Django Internal API."""
        response = httpx.post(
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
            logger.info(
                "Token obtenido correctamente para %s",
                self._service_name,
                extra={"sd": {"severity": 5, "service": self._service_name}},
            )
            return data["access_token"]
        raise RuntimeError(
            f"Error obteniendo token para {self._service_name}: HTTP {response.status_code}"
        )

    def _is_expiring(self, token: str) -> bool:
        """True si el token expira en los próximos REFRESH_BUFFER_SECONDS."""
        try:
            payload = jwt.decode(
                token,
                self._public_key,
                algorithms=["RS256"],
                options={"verify_exp": False},
            )
            return payload["exp"] - _REFRESH_BUFFER_SECONDS <= time.time()
        except Exception:
            return True  # Ante cualquier duda, refrescar
