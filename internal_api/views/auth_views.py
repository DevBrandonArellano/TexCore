"""
Endpoints de autenticación servicio-a-servicio.
SRP: solo emite y renueva JWT de servicio.
ISO 27001 A.9.4: autenticación de servicios con secretos hasheados.
"""
import ipaddress
import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils import timezone as dj_timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from internal_api.models import ServiceCredential
from internal_api.serializers import (
    ServiceTokenRefreshRequestSerializer,
    ServiceTokenRequestSerializer,
)

logger = logging.getLogger(__name__)


class ServiceAuthThrottle(AnonRateThrottle):
    """Un microservicio renueva su token cada `INTERNAL_JWT_ACCESS_TTL_SECONDS`
    (minutos, no segundos) — 10/min es holgado para uso legítimo y corta
    fuerza bruta contra `service_secret`. Cache por-proceso (LocMemCache, sin
    CACHES configurado): con gunicorn multi-worker el límite real es
    10 * BACKEND_WORKERS/min hasta que haya un cache compartido (Redis)."""

    rate = "10/minute"


def _is_internal_request(remote_addr: str) -> bool:
    """True si `remote_addr` es una IP privada/loopback (RFC 1918 o ::1/127.0.0.1).

    Defensa en profundidad: el bloqueo de nginx en `/api/internal/` es la
    barrera principal contra tráfico externo; esta función protege además el
    camino directo `backend:8000` que nginx nunca toca (llamado real de los
    microservicios, y cualquier contenedor comprometido en la red). No
    reemplaza el bloqueo de nginx — si nginx reenvía una petición externa por
    error de configuración, `REMOTE_ADDR` que Django ve es la IP de nginx
    (también privada), así que esta función no la detectaría en ese caso.
    """
    try:
        ip_obj = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return ip_obj.is_private or ip_obj.is_loopback


def _generate_token_pair(credential: ServiceCredential) -> dict:
    """Genera par access+refresh JWT RS256. Lógica extraída para reutilización."""
    now = datetime.now(timezone.utc)
    access_payload = {
        "iss": "texcore",
        "sub": credential.name,
        "scope": credential.allowed_scopes,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=settings.INTERNAL_JWT_ACCESS_TTL_SECONDS),
        "type": "service_access",
    }
    refresh_payload = {
        "iss": "texcore",
        "sub": credential.name,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=settings.INTERNAL_JWT_REFRESH_TTL_SECONDS),
        "type": "service_refresh",
    }
    return {
        "access_token": jwt.encode(
            access_payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256"
        ),
        "refresh_token": jwt.encode(
            refresh_payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256"
        ),
        "expires_in": settings.INTERNAL_JWT_ACCESS_TTL_SECONDS,
    }


class ServiceTokenView(APIView):
    """POST /api/internal/v1/auth/token/ — emite JWT para un microservicio."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ServiceAuthThrottle]

    def post(self, request):
        remote_addr = request.META.get("REMOTE_ADDR", "")
        if not _is_internal_request(remote_addr):
            logger.critical(
                "Intento de acceso a auth/token desde IP no privada: %s",
                remote_addr,
                extra={"sd": {"severity": 2, "remote_addr": remote_addr}},
            )
            return Response({"detail": "Acceso no autorizado."}, status=403)

        serializer = ServiceTokenRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        service_name = serializer.validated_data["service_name"]
        service_secret = serializer.validated_data["service_secret"]

        try:
            credential = ServiceCredential.objects.get(name=service_name)
        except ServiceCredential.DoesNotExist:
            logger.warning(
                "Intento de autenticación con servicio inexistente: %s",
                service_name,
                extra={"sd": {"severity": 4, "service": service_name}},
            )
            return Response({"detail": "Credenciales inválidas."}, status=401)

        if not credential.is_active:
            logger.warning(
                "Intento de autenticación con servicio inactivo: %s",
                service_name,
                extra={"sd": {"severity": 4, "service": service_name}},
            )
            return Response({"detail": "Servicio deshabilitado."}, status=403)

        if not check_password(service_secret, credential.secret_hash):
            logger.warning(
                "Secreto incorrecto para servicio: %s",
                service_name,
                extra={"sd": {"severity": 4, "service": service_name}},
            )
            return Response({"detail": "Credenciales inválidas."}, status=401)

        credential.last_used_at = dj_timezone.now()
        credential.save(update_fields=["last_used_at"])

        logger.info(
            "Token emitido para servicio: %s",
            service_name,
            extra={"sd": {"severity": 6, "service": service_name}},
        )
        return Response(_generate_token_pair(credential), status=200)


class ServiceTokenRefreshView(APIView):
    """POST /api/internal/v1/auth/refresh/ — renueva access token con refresh token."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ServiceAuthThrottle]

    def post(self, request):
        remote_addr = request.META.get("REMOTE_ADDR", "")
        if not _is_internal_request(remote_addr):
            logger.critical(
                "Intento de acceso a auth/refresh desde IP no privada: %s",
                remote_addr,
                extra={"sd": {"severity": 2, "remote_addr": remote_addr}},
            )
            return Response({"detail": "Acceso no autorizado."}, status=403)

        serializer = ServiceTokenRefreshRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        refresh_token = serializer.validated_data["refresh_token"]
        try:
            payload = jwt.decode(
                refresh_token,
                settings.INTERNAL_JWT_PUBLIC_KEY,
                algorithms=["RS256"],
                options={"verify_exp": True},
            )
        except jwt.ExpiredSignatureError:
            return Response({"detail": "Refresh token expirado."}, status=401)
        except jwt.InvalidTokenError as exc:
            return Response({"detail": f"Token inválido: {exc}"}, status=401)

        if payload.get("type") != "service_refresh":
            return Response({"detail": "Tipo de token incorrecto."}, status=401)

        try:
            credential = ServiceCredential.objects.get(
                name=payload["sub"], is_active=True
            )
        except ServiceCredential.DoesNotExist:
            return Response(
                {"detail": "Servicio no encontrado o inactivo."}, status=403
            )

        return Response(_generate_token_pair(credential), status=200)
