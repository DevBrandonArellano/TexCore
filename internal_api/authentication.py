"""
JWTServiceAuthentication: valida JWT RS256 de microservicios.
ISO 27001 A.9.4 — Control de acceso a sistemas y aplicaciones.
DIP: depende de settings (abstracción), no de archivos físicos.
"""
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

logger = logging.getLogger(__name__)


@dataclass
class ServicePrincipal:
    """Identidad de un microservicio autenticado. Inmutable post-creación.

    `sede_id`/`is_admin` son claims OPCIONALES firmados: cuando el llamador
    autorizado (p. ej. el proxy Django que conoce al usuario humano) los
    incluye, permiten a las vistas imponer aislamiento por sede como defensa
    en profundidad. Ausentes en tokens servicio-a-servicio clásicos.
    """

    service_name: str
    scopes: List[str] = field(default_factory=list)
    is_authenticated: bool = True
    sede_id: Optional[int] = None
    is_admin: bool = False

    def __str__(self) -> str:
        return f"Service:{self.service_name}"


class JWTServiceAuthentication(BaseAuthentication):
    """
    DRF Authentication backend para JWT de servicio (RS256).
    Retorna None si no hay header Bearer (otros backends pueden seguir).
    Lanza AuthenticationFailed si el token es inválido o expirado.
    """

    def authenticate(self, request: Request) -> Optional[Tuple[ServicePrincipal, str]]:
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ", 1)[1].strip()
        return self._validate_token(token)

    def _validate_token(self, token: str) -> Tuple[ServicePrincipal, str]:
        try:
            payload = jwt.decode(
                token,
                settings.INTERNAL_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                options={
                    "verify_exp": True,
                    "require": ["sub", "scope", "jti", "type"],
                },
            )
        except jwt.ExpiredSignatureError:
            logger.warning(
                "JWT de servicio expirado",
                extra={"sd": {"severity": 4, "action": "jwt_expired"}},
            )
            raise AuthenticationFailed("Token de servicio expirado.")
        except jwt.InvalidTokenError as exc:
            logger.warning(
                "JWT de servicio inválido: %s", exc,
                extra={"sd": {"severity": 4, "action": "jwt_invalid"}},
            )
            raise AuthenticationFailed(f"Token de servicio inválido: {exc}")

        if payload.get("type") != "service_access":
            raise AuthenticationFailed("Tipo de token incorrecto. Se requiere service_access.")

        principal = ServicePrincipal(
            service_name=payload["sub"],
            scopes=payload.get("scope", []),
            sede_id=payload.get("sede_id"),
            is_admin=bool(payload.get("is_admin", False)),
        )
        logger.info(
            "Servicio autenticado: %s", principal.service_name,
            extra={"sd": {"severity": 6, "service": principal.service_name}},
        )
        return principal, token

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="texcore-internal"'

    @staticmethod
    def generate_token(
        service_name: str,
        scopes: List[str],
        expires_in: int = 300,
        sede_id: Optional[int] = None,
        is_admin: bool = False,
    ) -> str:
        """
        Genera un JWT RS256 firmado para autenticación entre servicios.
        ISO 27001 A.9.4: tokens de corta duración (default 5 min).

        `sede_id`/`is_admin` son claims opcionales: cuando el llamador conoce al
        usuario humano final, los firma para que las vistas internas puedan
        imponer aislamiento por sede (defensa en profundidad). Se omiten del
        payload si no se proveen, preservando la compatibilidad con tokens
        servicio-a-servicio existentes.
        """
        now = int(time.time())
        payload = {
            "iss": "texcore",
            "sub": service_name,
            "type": "service_access",
            "scope": scopes,
            "iat": now,
            "exp": now + expires_in,
            "jti": str(uuid.uuid4()),
        }
        if sede_id is not None:
            payload["sede_id"] = sede_id
        if is_admin:
            payload["is_admin"] = True
        return jwt.encode(
            payload,
            settings.INTERNAL_JWT_PRIVATE_KEY,
            algorithm="RS256"
        )
