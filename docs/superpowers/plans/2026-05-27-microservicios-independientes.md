# Microservicios Independientes — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar el acceso directo a BD de `scanning_service` y `reporting_excel`; reemplazarlo por JWT RS256 → Django Internal API `/api/internal/v1/`.

**Architecture:** Django es el único propietario de `texcore_db`. Los microservicios se autentican con JWT Service Tokens RS256 y consumen endpoints REST internos. `printing_service` ya es independiente — sin cambios.

**Tech Stack:** PyJWT + cryptography (RS256), httpx (HTTP client), Django REST Framework, pytest, factory-boy.

---

## Task 1: Generar claves RSA + agregar dependencia `cryptography`

**Files:**
- Modify: `requirements.txt`
- Modify: `.env` (o documentar en docker-compose.yml)

- [ ] **Step 1: Agregar `cryptography` a requirements.txt**

```text
# Al final de requirements.txt, después de PyJWT==2.10.1:
cryptography==42.0.8
```

- [ ] **Step 2: Generar par de claves RSA 2048-bit**

Ejecutar en terminal (fuera de Docker):
```bash
openssl genrsa -out internal_jwt_private.pem 2048
openssl rsa -in internal_jwt_private.pem -pubout -out internal_jwt_public.pem
```

- [ ] **Step 3: Verificar claves generadas**

```bash
openssl rsa -in internal_jwt_private.pem -check
# Expected: RSA key ok
```

- [ ] **Step 4: Copiar contenido de claves al .env**

Agregar en `.env` (una línea cada una, con `\n` como saltos):
```env
INTERNAL_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----"
INTERNAL_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----"
SCANNING_SERVICE_SECRET=scanning-dev-secret-change-in-prod
REPORTING_SERVICE_SECRET=reporting-dev-secret-change-in-prod
```

---

## Task 2: Django — App `internal_api` (scaffold + modelo)

**Files:**
- Create: `internal_api/__init__.py`
- Create: `internal_api/apps.py`
- Create: `internal_api/models.py`
- Modify: `TexCore/settings.py`

- [ ] **Step 1: Escribir test del modelo ServiceCredential (TDD — falla primero)**

Crear `internal_api/tests/__init__.py` (vacío) y `internal_api/tests/test_models.py`:

```python
"""Tests TDD para ServiceCredential. EP + STT."""
from django.test import TestCase
from django.contrib.auth.hashers import check_password
from internal_api.models import ServiceCredential


class TestServiceCredentialCreacion(TestCase):
    """EP: creación normal de una credencial de servicio."""

    def test_service_credential_dado_datos_validos_cuando_crea_entonces_almacena_hash(self):
        cred = ServiceCredential.objects.create(
            name="scanning_service",
            secret_hash=ServiceCredential.hash_secret("mi-secreto"),
            allowed_scopes=["lotes:read"],
        )
        self.assertEqual(cred.name, "scanning_service")
        self.assertTrue(check_password("mi-secreto", cred.secret_hash))

    def test_service_credential_dado_secreto_incorrecto_cuando_verifica_entonces_retorna_false(self):
        cred = ServiceCredential.objects.create(
            name="reporting_excel",
            secret_hash=ServiceCredential.hash_secret("correcto"),
            allowed_scopes=["reports:read"],
        )
        self.assertFalse(check_password("incorrecto", cred.secret_hash))


class TestServiceCredentialEstado(TestCase):
    """STT: transición activo → inactivo revoca acceso."""

    def test_service_credential_dado_activo_cuando_desactiva_entonces_is_active_false(self):
        cred = ServiceCredential.objects.create(
            name="svc_test",
            secret_hash=ServiceCredential.hash_secret("secret"),
            allowed_scopes=[],
            is_active=True,
        )
        cred.is_active = False
        cred.save()
        cred.refresh_from_db()
        self.assertFalse(cred.is_active)
```

- [ ] **Step 2: Ejecutar test — debe fallar con ImportError**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_models -v 2
# Expected: ImportError: No module named 'internal_api'
```

- [ ] **Step 3: Crear estructura de la app**

```python
# internal_api/__init__.py
# (vacío)
```

```python
# internal_api/apps.py
from django.apps import AppConfig

class InternalApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "internal_api"
    verbose_name = "Internal API (Service-to-Service)"
```

- [ ] **Step 4: Crear modelo ServiceCredential**

```python
# internal_api/models.py
"""
ServiceCredential: identidad de un microservicio autorizado.
ISO 27001 A.9.2 — Gestión de información de autenticación secreta.
SRP: única responsabilidad — almacenar y verificar credenciales de servicio.
"""
from django.contrib.auth.hashers import make_password
from django.db import models


class ServiceCredential(models.Model):
    """Representa la identidad de un microservicio que consume la API interna."""

    name = models.CharField(max_length=100, unique=True, help_text="Nombre único del servicio (ej: scanning_service)")
    secret_hash = models.CharField(max_length=255, help_text="Hash bcrypt del secret del servicio")
    is_active = models.BooleanField(default=True, help_text="Si False, el servicio no puede autenticarse")
    allowed_scopes = models.JSONField(default=list, help_text='Ej: ["lotes:read", "reports:read"]')
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "internal_service_credential"
        verbose_name = "Service Credential"
        verbose_name_plural = "Service Credentials"

    def __str__(self) -> str:
        status = "activo" if self.is_active else "inactivo"
        return f"{self.name} ({status})"

    @staticmethod
    def hash_secret(plain_secret: str) -> str:
        """Genera hash seguro del secret usando el hasher de Django (PBKDF2/bcrypt)."""
        return make_password(plain_secret)
```

- [ ] **Step 5: Registrar app en settings.py y agregar config JWT**

En `TexCore/settings.py`, en `INSTALLED_APPS` después de `'inventory.apps.InventoryConfig'`:
```python
    'internal_api.apps.InternalApiConfig',
```

Al final de `TexCore/settings.py`, después del bloque Celery:
```python
# ---------------------------------------------------------------------------
# Internal API — JWT Service Tokens (RS256 asimétrico)
# ISO 27001 A.10: clave privada solo en Django, pública distribuida a servicios
# ---------------------------------------------------------------------------
import textwrap

def _load_rsa_key(env_var: str) -> str:
    """Carga clave RSA desde env var, reemplazando \\n literales por saltos reales."""
    raw = os.environ.get(env_var, "")
    return raw.replace("\\n", "\n")

INTERNAL_JWT_PRIVATE_KEY: str = _load_rsa_key("INTERNAL_JWT_PRIVATE_KEY")
INTERNAL_JWT_PUBLIC_KEY: str = _load_rsa_key("INTERNAL_JWT_PUBLIC_KEY")
INTERNAL_JWT_ACCESS_TTL_SECONDS: int = 900    # 15 minutos
INTERNAL_JWT_REFRESH_TTL_SECONDS: int = 86400 # 24 horas
```

- [ ] **Step 6: Crear y ejecutar migración**

```bash
docker exec texcore-backend-1 python manage.py makemigrations internal_api
docker exec texcore-backend-1 python manage.py migrate internal_api
# Expected: Applying internal_api.0001_initial... OK
```

- [ ] **Step 7: Ejecutar tests — deben pasar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_models -v 2
# Expected: Ran 3 tests in X.XXXs — OK
```

---

## Task 3: Django — JWT Authentication + Permissions

**Files:**
- Create: `internal_api/authentication.py`
- Create: `internal_api/permissions.py`

- [ ] **Step 1: Escribir tests de autenticación (TDD)**

Crear `internal_api/tests/test_authentication.py`:

```python
"""Tests para JWTServiceAuthentication. EP + BVA."""
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.test import RequestFactory, TestCase
from rest_framework.exceptions import AuthenticationFailed

from internal_api.authentication import JWTServiceAuthentication, ServicePrincipal


def _make_token(sub="scanning_service", scope=None, exp_delta=900, token_type="service_access"):
    """Helper: genera token RS256 válido para tests."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore",
        "sub": sub,
        "scope": scope or ["lotes:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=exp_delta),
        "type": token_type,
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class TestJWTServiceAuthentication(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.auth = JWTServiceAuthentication()

    # EP: token válido → retorna ServicePrincipal
    def test_auth_dado_token_valido_cuando_autentica_entonces_retorna_principal(self):
        token = _make_token()
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        principal, _ = result
        self.assertEqual(principal.service_name, "scanning_service")
        self.assertIn("lotes:read", principal.scopes)

    # EP: sin header Authorization → retorna None (no es error, solo no aplica)
    def test_auth_dado_sin_header_cuando_autentica_entonces_retorna_none(self):
        request = self.factory.get("/")
        result = self.auth.authenticate(request)
        self.assertIsNone(result)

    # BVA: token expirado → AuthenticationFailed
    def test_auth_dado_token_expirado_cuando_autentica_entonces_lanza_error(self):
        token = _make_token(exp_delta=-1)
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)

    # EP: tipo de token incorrecto → AuthenticationFailed
    def test_auth_dado_tipo_refresh_cuando_autentica_entonces_lanza_error(self):
        token = _make_token(token_type="service_refresh")
        request = self.factory.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate(request)
```

- [ ] **Step 2: Ejecutar test — debe fallar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_authentication -v 2
# Expected: ImportError: cannot import name 'JWTServiceAuthentication'
```

- [ ] **Step 3: Implementar authentication.py**

```python
# internal_api/authentication.py
"""
JWTServiceAuthentication: valida JWT RS256 de microservicios.
ISO 27001 A.9.4 — Control de acceso a sistemas y aplicaciones.
DIP: depende de settings (abstracción), no de archivos físicos.
"""
import logging
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
    """Identidad de un microservicio autenticado. Inmutable post-creación."""
    service_name: str
    scopes: List[str] = field(default_factory=list)
    is_authenticated: bool = True

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
                options={"verify_exp": True, "require": ["sub", "scope", "jti", "type"]},
            )
        except jwt.ExpiredSignatureError:
            logger.warning("JWT de servicio expirado")
            raise AuthenticationFailed("Token de servicio expirado.")
        except jwt.InvalidTokenError as exc:
            logger.warning("JWT de servicio inválido: %s", exc)
            raise AuthenticationFailed(f"Token de servicio inválido: {exc}")

        if payload.get("type") != "service_access":
            raise AuthenticationFailed("Tipo de token incorrecto. Se requiere service_access.")

        principal = ServicePrincipal(
            service_name=payload["sub"],
            scopes=payload.get("scope", []),
        )
        logger.info(
            "Servicio autenticado",
            extra={"sd": {"service": principal.service_name, "scopes": str(principal.scopes)}},
        )
        return principal, token

    def authenticate_header(self, request: Request) -> str:
        return 'Bearer realm="texcore-internal"'
```

- [ ] **Step 4: Implementar permissions.py**

```python
# internal_api/permissions.py
"""
Permisos para la API interna.
ISP: una clase por responsabilidad de permiso.
COBIT DSS06: control de acceso basado en scopes.
"""
import logging
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class IsInternalService(BasePermission):
    """Permite acceso solo si el request fue autenticado como ServicePrincipal."""

    message = "Acceso restringido a servicios internos autenticados."

    def has_permission(self, request, view) -> bool:
        from internal_api.authentication import ServicePrincipal
        return isinstance(getattr(request, "user", None), ServicePrincipal)


class HasScope(BasePermission):
    """
    Verifica que el ServicePrincipal tiene el scope requerido.
    Uso: permission_classes = [IsInternalService, HasScope('lotes:read')]
    """

    def __init__(self, required_scope: str) -> None:
        self.required_scope = required_scope

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "user", None)
        scopes = getattr(principal, "scopes", [])
        allowed = self.required_scope in scopes
        if not allowed:
            logger.warning(
                "Scope insuficiente",
                extra={"sd": {
                    "service": getattr(principal, "service_name", "unknown"),
                    "required": self.required_scope,
                    "has": str(scopes),
                }},
            )
        return allowed
```

- [ ] **Step 5: Ejecutar tests — deben pasar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_authentication -v 2
# Expected: Ran 4 tests in X.XXXs — OK
```

---

## Task 4: Django — AuditLogger RFC 5424

**Files:**
- Create: `internal_api/audit.py`

- [ ] **Step 1: Crear AuditLogger**

```python
# internal_api/audit.py
"""
AuditLogger: registra accesos de servicios internos.
ISO 27001 A.12.4 — Registro de eventos.
RFC 5424: niveles de severidad en logs estructurados.
SRP: única responsabilidad — registrar eventos de audit.
"""
import logging
import time
from typing import Optional

logger = logging.getLogger("internal_api.audit")


class AuditLogger:
    """
    Registra en log estructurado (RFC 5424 INFO=6) cada acceso
    a la API interna con identidad de servicio, recurso y duración.
    """

    @staticmethod
    def log(
        service: str,
        action: str,
        resource: str,
        status_code: int = 200,
        duration_ms: Optional[int] = None,
        extra: Optional[dict] = None,
    ) -> None:
        """
        Emite log RFC 5424 severity 6 (INFO) para trazabilidad de acceso.
        ISO 27001 A.12.4: quién accedió, a qué recurso, cuándo, resultado.
        """
        sd = {
            "service": service,
            "action": action,
            "resource": resource,
            "status_code": status_code,
        }
        if duration_ms is not None:
            sd["duration_ms"] = duration_ms
        if extra:
            sd.update(extra)

        severity = logging.INFO if status_code < 400 else (
            logging.WARNING if status_code < 500 else logging.ERROR
        )
        logger.log(
            severity,
            f"[AUDIT] {service} → {action} on {resource} [{status_code}]",
            extra={"sd": sd},
        )
```

---

## Task 5: Django — Endpoints auth/token + auth/refresh (TDD)

**Files:**
- Create: `internal_api/serializers.py`
- Create: `internal_api/views/__init__.py`
- Create: `internal_api/views/auth_views.py`
- Create: `internal_api/urls.py`
- Modify: `TexCore/urls.py`
- Create: `internal_api/tests/test_auth_views.py`

- [ ] **Step 1: Escribir tests (TDD)**

```python
# internal_api/tests/test_auth_views.py
"""Tests para endpoints de autenticación de servicios. EP + STT."""
import jwt
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from internal_api.models import ServiceCredential


def _create_credential(name="scanning_service", secret="test-secret", scopes=None, active=True):
    return ServiceCredential.objects.create(
        name=name,
        secret_hash=ServiceCredential.hash_secret(secret),
        allowed_scopes=scopes or ["lotes:read"],
        is_active=active,
    )


class TestServiceTokenView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/internal/v1/auth/token/"

    # EP: credenciales válidas → 200 + tokens
    def test_token_dado_credenciales_validas_cuando_solicita_entonces_retorna_200(self):
        _create_credential()
        resp = self.client.post(self.url, {"service_name": "scanning_service", "service_secret": "test-secret"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access_token", resp.data)
        self.assertIn("refresh_token", resp.data)
        self.assertEqual(resp.data["expires_in"], 900)

    # EP: payload del access_token contiene sub y scope correctos
    def test_token_dado_credenciales_validas_cuando_decodifica_entonces_payload_correcto(self):
        _create_credential()
        resp = self.client.post(self.url, {"service_name": "scanning_service", "service_secret": "test-secret"}, format="json")
        payload = jwt.decode(resp.data["access_token"], settings.INTERNAL_JWT_PUBLIC_KEY, algorithms=["RS256"])
        self.assertEqual(payload["sub"], "scanning_service")
        self.assertEqual(payload["type"], "service_access")
        self.assertIn("lotes:read", payload["scope"])

    # EP: secreto incorrecto → 401
    def test_token_dado_secreto_incorrecto_cuando_solicita_entonces_retorna_401(self):
        _create_credential()
        resp = self.client.post(self.url, {"service_name": "scanning_service", "service_secret": "wrong"}, format="json")
        self.assertEqual(resp.status_code, 401)

    # STT: servicio inactivo → 403
    def test_token_dado_servicio_inactivo_cuando_solicita_entonces_retorna_403(self):
        _create_credential(active=False)
        resp = self.client.post(self.url, {"service_name": "scanning_service", "service_secret": "test-secret"}, format="json")
        self.assertEqual(resp.status_code, 403)

    # EP: servicio inexistente → 401
    def test_token_dado_servicio_inexistente_cuando_solicita_entonces_retorna_401(self):
        resp = self.client.post(self.url, {"service_name": "no_existe", "service_secret": "x"}, format="json")
        self.assertEqual(resp.status_code, 401)
```

- [ ] **Step 2: Ejecutar test — debe fallar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_auth_views -v 2
# Expected: 404 Not Found (URL no registrada aún)
```

- [ ] **Step 3: Crear serializers.py**

```python
# internal_api/serializers.py
"""Serializers para la API interna. ISP: un serializer por caso de uso."""
from rest_framework import serializers


class ServiceTokenRequestSerializer(serializers.Serializer):
    service_name = serializers.CharField(max_length=100)
    service_secret = serializers.CharField(max_length=500)


class ServiceTokenRefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()
```

- [ ] **Step 4: Crear views/auth_views.py**

```python
# internal_api/views/__init__.py
# (vacío)
```

```python
# internal_api/views/auth_views.py
"""
Endpoints de autenticación servicio-a-servicio.
SRP: solo emite y renueva JWT de servicio.
ISO 27001 A.9.4: autenticación de servicios con secretos hasheados.
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.utils import timezone as dj_timezone
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from internal_api.models import ServiceCredential
from internal_api.serializers import ServiceTokenRefreshRequestSerializer, ServiceTokenRequestSerializer

logger = logging.getLogger(__name__)


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
        "access_token": jwt.encode(access_payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256"),
        "refresh_token": jwt.encode(refresh_payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256"),
        "expires_in": settings.INTERNAL_JWT_ACCESS_TTL_SECONDS,
    }


class ServiceTokenView(APIView):
    """POST /api/internal/v1/auth/token/ — emite JWT para un microservicio."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ServiceTokenRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        service_name = serializer.validated_data["service_name"]
        service_secret = serializer.validated_data["service_secret"]

        try:
            credential = ServiceCredential.objects.get(name=service_name)
        except ServiceCredential.DoesNotExist:
            logger.warning("Intento de autenticación con servicio inexistente: %s", service_name)
            return Response({"detail": "Credenciales inválidas."}, status=401)

        if not credential.is_active:
            logger.warning("Intento de autenticación con servicio inactivo: %s", service_name)
            return Response({"detail": "Servicio deshabilitado."}, status=403)

        if not check_password(service_secret, credential.secret_hash):
            logger.warning("Secreto incorrecto para servicio: %s", service_name)
            return Response({"detail": "Credenciales inválidas."}, status=401)

        credential.last_used_at = dj_timezone.now()
        credential.save(update_fields=["last_used_at"])

        logger.info("Token emitido para servicio: %s", service_name)
        return Response(_generate_token_pair(credential), status=200)


class ServiceTokenRefreshView(APIView):
    """POST /api/internal/v1/auth/refresh/ — renueva access token con refresh token."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
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
            credential = ServiceCredential.objects.get(name=payload["sub"], is_active=True)
        except ServiceCredential.DoesNotExist:
            return Response({"detail": "Servicio no encontrado o inactivo."}, status=403)

        return Response(_generate_token_pair(credential), status=200)
```

- [ ] **Step 5: Crear urls.py de internal_api**

```python
# internal_api/urls.py
"""URLs de la API interna. Namespace: internal_api."""
from django.urls import path
from internal_api.views.auth_views import ServiceTokenView, ServiceTokenRefreshView

app_name = "internal_api"

urlpatterns = [
    path("auth/token/", ServiceTokenView.as_view(), name="service_token"),
    path("auth/refresh/", ServiceTokenRefreshView.as_view(), name="service_token_refresh"),
]
```

- [ ] **Step 6: Registrar URLs en TexCore/urls.py**

En `TexCore/urls.py`, dentro de `urlpatterns`, antes del `re_path` de la SPA React:

```python
    path('api/internal/v1/', include('internal_api.urls', namespace='internal_api')),
```

- [ ] **Step 7: Ejecutar tests — deben pasar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_auth_views -v 2
# Expected: Ran 5 tests in X.XXXs — OK
```

---

## Task 6: Django — Endpoint de validación de lote (scanning)

**Files:**
- Create: `internal_api/views/scanning_views.py`
- Modify: `internal_api/urls.py`
- Create: `internal_api/tests/test_scanning_views.py`

- [ ] **Step 1: Escribir tests (TDD)**

```python
# internal_api/tests/test_scanning_views.py
"""Tests para endpoint de validación de lote. EP + BVA."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import (
    Bodega, LoteProduccion, OrdenProduccion, Producto, Sede,
    Maquina, Area, CustomUser,
)
from internal_api.models import ServiceCredential
from inventory.models import StockBodega


def _make_service_token(service="scanning_service", scopes=None):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore", "sub": service,
        "scope": scopes or ["lotes:read"],
        "jti": str(uuid.uuid4()), "iat": now,
        "exp": now + timedelta(seconds=900),
        "type": "service_access",
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class TestValidateLoteView(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token = _make_service_token()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

        self.sede = Sede.objects.create(nombre="Sede Test")
        self.area = Area.objects.create(nombre="Area Test", sede=self.sede)
        self.bodega = Bodega.objects.create(nombre="Bodega Test", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="P-001", descripcion="Hilo Test", tipo="hilo",
            unidad_medida="kg", sede=self.sede,
        )
        self.operario = CustomUser.objects.create_user(
            username="operario_test", password="test123", sede=self.sede
        )
        self.maquina = Maquina.objects.create(
            nombre="Maq-01", capacidad_maxima=100, eficiencia_ideal="0.90", area=self.area
        )
        self.op = OrdenProduccion.objects.create(
            codigo="OP-001", producto=self.producto,
            peso_neto_requerido=100, sede=self.sede,
        )
        self.lote = LoteProduccion.objects.create(
            orden_produccion=self.op,
            codigo_lote="LOT-2026-001",
            peso_neto_producido=95,
            operario=self.operario,
            maquina=self.maquina,
            turno="mañana",
            hora_inicio="2026-05-01T08:00:00Z",
            hora_final="2026-05-01T16:00:00Z",
        )
        self.stock = StockBodega.objects.create(
            bodega=self.bodega, producto=self.producto,
            lote=self.lote, cantidad=95,
        )

    # EP: lote válido con stock → 200 con datos completos
    def test_validate_lote_dado_lote_con_stock_cuando_valida_entonces_retorna_200(self):
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["codigo_lote"], "LOT-2026-001")
        self.assertEqual(resp.data["producto"]["descripcion"], "Hilo Test")
        self.assertIsNotNone(resp.data["peso_kg"])
        self.assertEqual(resp.data["bodega"]["nombre"], "Bodega Test")

    # EP: lote inexistente → 404
    def test_validate_lote_dado_codigo_inexistente_cuando_valida_entonces_retorna_404(self):
        resp = self.client.get("/api/internal/v1/lotes/NO-EXISTE/validate/")
        self.assertEqual(resp.status_code, 404)

    # BVA: lote existe pero stock=0 → 200 con peso_kg=None
    def test_validate_lote_dado_stock_cero_cuando_valida_entonces_retorna_peso_nulo(self):
        self.stock.cantidad = 0
        self.stock.save()
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["peso_kg"])

    # EP: sin token → 403
    def test_validate_lote_dado_sin_token_cuando_valida_entonces_retorna_403(self):
        self.client.credentials()
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 403)

    # EP: scope incorrecto → 403
    def test_validate_lote_dado_scope_incorrecto_cuando_valida_entonces_retorna_403(self):
        token = _make_service_token(scopes=["reports:read"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get("/api/internal/v1/lotes/LOT-2026-001/validate/")
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Step 2: Ejecutar test — debe fallar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_scanning_views -v 2
# Expected: 404 (URL no existe aún)
```

- [ ] **Step 3: Implementar scanning_views.py**

```python
# internal_api/views/scanning_views.py
"""
Endpoint interno para validación de lotes por scanning_service.
SRP: solo expone información de lote+stock para despacho.
DIP: usa Django ORM (abstracción) en lugar de SQL directo.
"""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import LoteProduccion
from internal_api.audit import AuditLogger
from internal_api.authentication import JWTServiceAuthentication
from internal_api.permissions import HasScope, IsInternalService
from inventory.models import StockBodega

logger = logging.getLogger(__name__)


class ValidateLoteView(APIView):
    """GET /api/internal/v1/lotes/{codigo_barras}/validate/"""

    authentication_classes = [JWTServiceAuthentication]
    permission_classes = [IsInternalService, HasScope("lotes:read")]

    def get(self, request, codigo_barras: str):
        AuditLogger.log(
            service=request.user.service_name,
            action="validate_lote",
            resource=codigo_barras[:12],
        )

        try:
            lote = LoteProduccion.objects.select_related(
                "orden_produccion__producto"
            ).get(codigo_lote=codigo_barras)
        except LoteProduccion.DoesNotExist:
            return Response({"detail": "Lote no encontrado."}, status=404)

        op = lote.orden_produccion
        if not op or not op.producto:
            return Response({"detail": "Lote sin orden de producción o producto."}, status=404)

        stock = (
            StockBodega.objects.select_related("bodega")
            .filter(lote=lote, cantidad__gt=0)
            .first()
        )

        return Response({
            "lote_id": lote.id,
            "codigo_lote": lote.codigo_lote,
            "producto": {"id": op.producto.id, "descripcion": op.producto.descripcion},
            "estado": op.estado,
            "orden_produccion_id": op.id,
            "stock_id": stock.id if stock else None,
            "peso_kg": str(stock.cantidad) if stock else None,
            "bodega": {"id": stock.bodega.id, "nombre": stock.bodega.nombre} if stock else None,
        })
```

- [ ] **Step 4: Agregar URL en internal_api/urls.py**

```python
# internal_api/urls.py — reemplazar contenido completo
from django.urls import path
from internal_api.views.auth_views import ServiceTokenView, ServiceTokenRefreshView
from internal_api.views.scanning_views import ValidateLoteView

app_name = "internal_api"

urlpatterns = [
    path("auth/token/", ServiceTokenView.as_view(), name="service_token"),
    path("auth/refresh/", ServiceTokenRefreshView.as_view(), name="service_token_refresh"),
    path("lotes/<str:codigo_barras>/validate/", ValidateLoteView.as_view(), name="validate_lote"),
]
```

- [ ] **Step 5: Ejecutar tests — deben pasar**

```bash
docker exec texcore-backend-1 python manage.py test internal_api.tests.test_scanning_views -v 2
# Expected: Ran 5 tests in X.XXXs — OK
```

---

## Task 7: Django — 18 Endpoints de Reporting

**Files:**
- Create: `internal_api/views/reporting_views.py`
- Modify: `internal_api/urls.py`
- Create: `internal_api/tests/test_reporting_views.py`

- [ ] **Step 1: Escribir tests mínimos (TDD)**

```python
# internal_api/tests/test_reporting_views.py
"""Tests para endpoints de reporting. EP por endpoint representativo."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from gestion.models import Bodega, Producto, Sede, Area


def _make_service_token(scopes=None):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore", "sub": "reporting_excel",
        "scope": scopes or ["reports:read"],
        "jti": str(uuid.uuid4()), "iat": now,
        "exp": now + timedelta(seconds=900),
        "type": "service_access",
    }
    return jwt.encode(payload, settings.INTERNAL_JWT_PRIVATE_KEY, algorithm="RS256")


class TestReportingEndpoints(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {_make_service_token()}")
        self.sede = Sede.objects.create(nombre="Sede R")
        self.bodega = Bodega.objects.create(nombre="Bodega R", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="R-001", descripcion="Prod Report", tipo="hilo",
            unidad_medida="kg", sede=self.sede,
        )

    # EP: productos → 200 retorna lista JSON
    def test_productos_dado_token_valido_cuando_solicita_entonces_retorna_200(self):
        resp = self.client.get("/api/internal/v1/reports/productos/")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)

    # EP: stock-actual requiere bodega_id
    def test_stock_actual_dado_bodega_valida_cuando_solicita_entonces_retorna_200(self):
        resp = self.client.get(f"/api/internal/v1/reports/stock-actual/?bodega_id={self.bodega.id}")
        self.assertEqual(resp.status_code, 200)

    # EP: stock-actual sin bodega_id → 400
    def test_stock_actual_dado_sin_bodega_cuando_solicita_entonces_retorna_400(self):
        resp = self.client.get("/api/internal/v1/reports/stock-actual/")
        self.assertEqual(resp.status_code, 400)

    # EP: scope incorrecto → 403
    def test_productos_dado_scope_incorrecto_cuando_solicita_entonces_retorna_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {_make_service_token(scopes=['lotes:read'])}")
        resp = self.client.get("/api/internal/v1/reports/productos/")
        self.assertEqual(resp.status_code, 403)
```

- [ ] **Step 2: Implementar reporting_views.py**

```python
# internal_api/views/reporting_views.py
"""
18 endpoints de datos para reporting_excel.
SRP: cada view retorna exactamente los datos de un SP.
DIP: Django ORM en lugar de pyodbc directo.
Scope requerido: reports:read
"""
import logging
from datetime import date
from typing import Optional

from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import (
    Bodega, Cliente, CustomUser, LoteProduccion,
    OrdenProduccion, PagoCliente, PedidoVenta, Producto, Sede,
)
from internal_api.audit import AuditLogger
from internal_api.authentication import JWTServiceAuthentication
from internal_api.permissions import HasScope, IsInternalService
from inventory.models import MovimientoInventario, StockBodega

logger = logging.getLogger(__name__)

_AUTH = [JWTServiceAuthentication]
_PERMS = [IsInternalService, HasScope("reports:read")]


def _audit(request, action, resource="reports"):
    AuditLogger.log(service=request.user.service_name, action=action, resource=resource)


# ──────────────────────────────────────────────────────────
# INVENTARIO
# ──────────────────────────────────────────────────────────

class KardexView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_kardex")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        producto_id = request.query_params.get("producto_id")
        lote_codigo = request.query_params.get("lote_codigo")

        qs = MovimientoInventario.objects.select_related(
            "producto", "bodega_origen", "bodega_destino", "lote", "usuario"
        ).filter(bodega_origen_id=bodega_id)

        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)
        if producto_id:
            qs = qs.filter(producto_id=producto_id)
        if lote_codigo:
            qs = qs.filter(lote__codigo_lote=lote_codigo)

        data = list(qs.values(
            "id", "fecha", "tipo_movimiento",
            producto_descripcion=F("producto__descripcion"),
            bodega_origen_nombre=F("bodega_origen__nombre"),
            "cantidad", "saldo_resultante", "documento_ref",
        ))
        return Response(data)


class ProductosView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_productos")
        sede_id = request.query_params.get("sede_id")
        qs = Producto.objects.all()
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(qs.values("id", "codigo", "descripcion", "tipo", "unidad_medida", "precio_base", "stock_minimo"))
        return Response(data)


class UsuariosView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_usuarios")
        sede_id = request.query_params.get("sede_id")
        qs = CustomUser.objects.all()
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(qs.values("id", "username", "first_name", "last_name", "email", sede_nombre=F("sede__nombre")))
        return Response(data)


class StockActualView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_stock_actual")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        producto_id = request.query_params.get("producto_id")
        qs = StockBodega.objects.select_related("producto", "bodega", "lote").filter(bodega_id=bodega_id, cantidad__gt=0)
        if producto_id:
            qs = qs.filter(producto_id=producto_id)
        data = list(qs.values(
            "id", "cantidad",
            producto_descripcion=F("producto__descripcion"),
            producto_codigo=F("producto__codigo"),
            bodega_nombre=F("bodega__nombre"),
            lote_codigo=F("lote__codigo_lote"),
        ))
        return Response(data)


class ValorizacionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_valorizacion")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        qs = StockBodega.objects.select_related("producto").filter(bodega_id=bodega_id, cantidad__gt=0)
        data = list(qs.annotate(
            valor_total=F("cantidad") * F("producto__precio_base")
        ).values(
            "id", "cantidad",
            producto_descripcion=F("producto__descripcion"),
            precio_base=F("producto__precio_base"),
            "valor_total",
        ))
        return Response(data)


class AgingView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_aging")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        from django.utils import timezone
        from datetime import timedelta
        dias = int(request.query_params.get("dias_minimos", 30))
        corte = timezone.now() - timedelta(days=dias)
        productos_con_movimiento_reciente = MovimientoInventario.objects.filter(
            bodega_origen_id=bodega_id, fecha__gte=corte
        ).values_list("producto_id", flat=True)
        qs = StockBodega.objects.select_related("producto").filter(
            bodega_id=bodega_id, cantidad__gt=0
        ).exclude(producto_id__in=productos_con_movimiento_reciente)
        data = list(qs.values("id", "cantidad", producto_descripcion=F("producto__descripcion")))
        return Response(data)


class RotacionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_rotacion")
        bodega_id = request.query_params.get("bodega_id")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        qs = MovimientoInventario.objects.filter(bodega_origen_id=bodega_id)
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)
        data = list(qs.values(producto_descripcion=F("producto__descripcion")).annotate(
            total_salidas=Sum("cantidad")
        ))
        return Response(data)


class StockCeroView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_stock_cero")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        qs = StockBodega.objects.select_related("producto").filter(bodega_id=bodega_id, cantidad=0)
        data = list(qs.values("id", "cantidad", producto_descripcion=F("producto__descripcion")))
        return Response(data)


class ResumenMovimientosView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_resumen_movimientos")
        bodega_id = request.query_params.get("bodega_id")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        qs = MovimientoInventario.objects.filter(bodega_origen_id=bodega_id)
        if fecha_desde:
            qs = qs.filter(fecha__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__date__lte=fecha_hasta)
        data = list(qs.values("tipo_movimiento").annotate(total=Sum("cantidad")))
        return Response(data)


# ──────────────────────────────────────────────────────────
# VENDEDORES
# ──────────────────────────────────────────────────────────

class VentasVendedorView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_ventas_vendedor", f"vendedor/{vendedor_id}")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        qs = PedidoVenta.objects.filter(
            cliente__vendedor_asignado_id=vendedor_id, anulado=False
        ).select_related("cliente")
        if fecha_desde:
            qs = qs.filter(fecha_pedido__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__date__lte=fecha_hasta)
        data = list(qs.values(
            "id", "guia_remision", "fecha_pedido", "estado", "esta_pagado",
            cliente_nombre=F("cliente__nombre_razon_social"),
        ))
        return Response(data)


class TopClientesVendedorView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_top_clientes_vendedor", f"vendedor/{vendedor_id}")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        qs = PedidoVenta.objects.filter(
            cliente__vendedor_asignado_id=vendedor_id, anulado=False
        )
        if fecha_desde:
            qs = qs.filter(fecha_pedido__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__date__lte=fecha_hasta)
        data = list(qs.values(
            cliente_nombre=F("cliente__nombre_razon_social"),
            cliente_id=F("cliente__id"),
        ).annotate(total_pedidos=Sum("id")).order_by("-total_pedidos")[:10])
        return Response(data)


class DeudoresVendedorView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_deudores_vendedor", f"vendedor/{vendedor_id}")
        qs = Cliente.objects.filter(
            vendedor_asignado_id=vendedor_id, is_active=True
        ).annotate(
            total_pagado=Coalesce(Sum("pagos__monto"), Value(0), output_field=DecimalField()),
        )
        data = list(qs.values(
            "id", "nombre_razon_social", "limite_credito", "plazo_credito_dias", "total_pagado",
        ))
        return Response(data)


# ──────────────────────────────────────────────────────────
# GERENCIAL
# ──────────────────────────────────────────────────────────

class VentasGerencialView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_ventas_gerencial")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id = request.query_params.get("sede_id")
        qs = PedidoVenta.objects.filter(anulado=False).select_related("cliente__sede")
        if fecha_desde:
            qs = qs.filter(fecha_pedido__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__date__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(cliente__sede_id=sede_id)
        data = list(qs.values(
            "id", "guia_remision", "fecha_pedido", "estado", "esta_pagado",
            cliente_nombre=F("cliente__nombre_razon_social"),
            sede_nombre=F("cliente__sede__nombre"),
        ))
        return Response(data)


class TopClientesGerencialView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_top_clientes_gerencial")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id = request.query_params.get("sede_id")
        qs = PedidoVenta.objects.filter(anulado=False)
        if fecha_desde:
            qs = qs.filter(fecha_pedido__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__date__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(cliente__sede_id=sede_id)
        data = list(qs.values(
            cliente_nombre=F("cliente__nombre_razon_social"),
            cliente_id=F("cliente__id"),
        ).annotate(total_pedidos=Sum("id")).order_by("-total_pedidos")[:20])
        return Response(data)


class DeudoresGerencialView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_deudores_gerencial")
        sede_id = request.query_params.get("sede_id")
        qs = Cliente.objects.filter(is_active=True).annotate(
            total_pagado=Coalesce(Sum("pagos__monto"), Value(0), output_field=DecimalField()),
        )
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(qs.values("id", "nombre_razon_social", "limite_credito", "total_pagado"))
        return Response(data)


# ──────────────────────────────────────────────────────────
# PRODUCCIÓN
# ──────────────────────────────────────────────────────────

class OrdenesProduccionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_ordenes_produccion")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id = request.query_params.get("sede_id")
        qs = OrdenProduccion.objects.select_related("producto", "sede")
        if fecha_desde:
            qs = qs.filter(fecha_creacion__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_creacion__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(qs.values(
            "id", "codigo", "estado", "prioridad", "fecha_creacion",
            "peso_neto_requerido",
            producto_descripcion=F("producto__descripcion"),
            sede_nombre=F("sede__nombre"),
        ))
        return Response(data)


class LotesProduccionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_lotes_produccion")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id = request.query_params.get("sede_id")
        qs = LoteProduccion.objects.select_related("orden_produccion__producto", "orden_produccion__sede")
        if fecha_desde:
            qs = qs.filter(hora_inicio__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(hora_inicio__date__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(orden_produccion__sede_id=sede_id)
        data = list(qs.values(
            "id", "codigo_lote", "peso_neto_producido", "hora_inicio", "hora_final",
            "clasificacion_calidad",
            producto_descripcion=F("orden_produccion__producto__descripcion"),
            op_codigo=F("orden_produccion__codigo"),
        ))
        return Response(data)


class TendenciaProduccionView(APIView):
    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_tendencia_produccion")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id = request.query_params.get("sede_id")
        from django.db.models.functions import TruncDate
        qs = LoteProduccion.objects.select_related("orden_produccion__sede")
        if fecha_desde:
            qs = qs.filter(hora_inicio__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(hora_inicio__date__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(orden_produccion__sede_id=sede_id)
        data = list(qs.annotate(fecha=TruncDate("hora_inicio")).values("fecha").annotate(
            total_peso=Sum("peso_neto_producido"),
            total_lotes=Sum(Value(1)),
        ).order_by("fecha"))
        return Response(data)
```

- [ ] **Step 3: Actualizar internal_api/urls.py con las 18 rutas**

```python
# internal_api/urls.py — contenido completo final
from django.urls import path
from internal_api.views.auth_views import ServiceTokenView, ServiceTokenRefreshView
from internal_api.views.scanning_views import ValidateLoteView
from internal_api.views.reporting_views import (
    KardexView, ProductosView, UsuariosView, StockActualView,
    ValorizacionView, AgingView, RotacionView, StockCeroView,
    ResumenMovimientosView, VentasVendedorView, TopClientesVendedorView,
    DeudoresVendedorView, VentasGerencialView, TopClientesGerencialView,
    DeudoresGerencialView, OrdenesProduccionView, LotesProduccionView,
    TendenciaProduccionView,
)

app_name = "internal_api"

urlpatterns = [
    # Auth
    path("auth/token/", ServiceTokenView.as_view(), name="service_token"),
    path("auth/refresh/", ServiceTokenRefreshView.as_view(), name="service_token_refresh"),
    # Scanning
    path("lotes/<str:codigo_barras>/validate/", ValidateLoteView.as_view(), name="validate_lote"),
    # Reporting — Inventario
    path("reports/kardex/", KardexView.as_view(), name="reports_kardex"),
    path("reports/productos/", ProductosView.as_view(), name="reports_productos"),
    path("reports/usuarios/", UsuariosView.as_view(), name="reports_usuarios"),
    path("reports/stock-actual/", StockActualView.as_view(), name="reports_stock_actual"),
    path("reports/valorizacion/", ValorizacionView.as_view(), name="reports_valorizacion"),
    path("reports/aging/", AgingView.as_view(), name="reports_aging"),
    path("reports/rotacion/", RotacionView.as_view(), name="reports_rotacion"),
    path("reports/stock-cero/", StockCeroView.as_view(), name="reports_stock_cero"),
    path("reports/resumen-movimientos/", ResumenMovimientosView.as_view(), name="reports_resumen_movimientos"),
    # Reporting — Vendedores
    path("vendedores/<int:vendedor_id>/ventas/", VentasVendedorView.as_view(), name="vendedores_ventas"),
    path("vendedores/<int:vendedor_id>/top-clientes/", TopClientesVendedorView.as_view(), name="vendedores_top_clientes"),
    path("vendedores/<int:vendedor_id>/deudores/", DeudoresVendedorView.as_view(), name="vendedores_deudores"),
    # Reporting — Gerencial
    path("gerencial/ventas/", VentasGerencialView.as_view(), name="gerencial_ventas"),
    path("gerencial/top-clientes/", TopClientesGerencialView.as_view(), name="gerencial_top_clientes"),
    path("gerencial/deudores/", DeudoresGerencialView.as_view(), name="gerencial_deudores"),
    # Reporting — Producción
    path("produccion/ordenes/", OrdenesProduccionView.as_view(), name="produccion_ordenes"),
    path("produccion/lotes/", LotesProduccionView.as_view(), name="produccion_lotes"),
    path("produccion/tendencia/", TendenciaProduccionView.as_view(), name="produccion_tendencia"),
]
```

- [ ] **Step 4: Ejecutar todos los tests Django**

```bash
docker exec texcore-backend-1 python manage.py test internal_api -v 2
# Expected: Ran 12+ tests — OK
```

---

## Task 8: scanning_service — Domain Models + JWTTokenManager

**Files:**
- Create: `scanning_service/src/domain/__init__.py`
- Create: `scanning_service/src/domain/models.py`
- Modify: `scanning_service/src/repositories/base.py`
- Create: `scanning_service/src/infrastructure/__init__.py`
- Create: `scanning_service/src/infrastructure/jwt_token_manager.py`
- Create: `scanning_service/tests/test_jwt_token_manager.py`

- [ ] **Step 1: Crear domain models (dataclasses — sin SQLAlchemy)**

```python
# scanning_service/src/domain/__init__.py
# (vacío)
```

```python
# scanning_service/src/domain/models.py
"""
Domain models: objetos de dominio puros, sin acoplamiento a ORM ni HTTP.
DIP: LoteValidationService depende de estos, no de SQLAlchemy.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Producto:
    id: int
    descripcion: str


@dataclass
class OrdenProduccion:
    id: int
    estado: str
    producto: Producto


@dataclass
class LoteProduccion:
    id: int
    codigo_lote: str
    orden_produccion: OrdenProduccion


@dataclass
class Bodega:
    id: int
    nombre: str


@dataclass
class StockBodega:
    id: int
    cantidad: Decimal
    bodega: Bodega
```

- [ ] **Step 2: Actualizar ILoteRepository para usar domain models**

```python
# scanning_service/src/repositories/base.py
"""
Protocolo ILoteRepository — usa domain models en lugar de SQLAlchemy.
LSP + DIP: SqlAlchemyLoteRepository y DjangoApiClient son intercambiables.
"""
from typing import Optional, Protocol, runtime_checkable
from ..domain.models import LoteProduccion, StockBodega


@runtime_checkable
class ILoteRepository(Protocol):
    def get_lote_by_codigo(self, codigo: str) -> Optional[LoteProduccion]: ...
    def get_stock_activo_por_lote(self, lote_id: int) -> Optional[StockBodega]: ...
```

- [ ] **Step 3: Agregar PyJWT a scanning_service/requirements.txt**

```text
# Reemplazar contenido:
fastapi==0.109.2
uvicorn==0.27.1
pydantic==2.6.2
python-dotenv==1.0.1
requests==2.31.0
httpx>=0.24,<0.29
PyJWT==2.10.1
cryptography==42.0.8
pytest==8.1.1
pytest-cov==5.0.0
pytest-asyncio==0.23.6
respx==0.21.1
```

- [ ] **Step 4: Escribir tests del JWTTokenManager (TDD)**

```python
# scanning_service/tests/test_jwt_token_manager.py
"""Tests para JWTTokenManager. EP + BVA."""
import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt
import pytest

# Claves RSA de prueba — se generan en conftest.py
TEST_PRIVATE_KEY = None  # se sobreescribe en conftest
TEST_PUBLIC_KEY = None


@pytest.fixture(autouse=True)
def rsa_keys(tmp_path):
    """Genera un par RSA temporal para tests."""
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization
    global TEST_PRIVATE_KEY, TEST_PUBLIC_KEY

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    TEST_PRIVATE_KEY = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    TEST_PUBLIC_KEY = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def _make_token(private_key, sub="scanning_service", exp_seconds=900):
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore", "sub": sub,
        "scope": ["lotes:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=exp_seconds),
        "type": "service_access",
    }
    return jwt.encode(payload, private_key, algorithm="RS256")


class TestJWTTokenManager:
    # EP: token fresco → devuelve el mismo sin refrescar
    def test_get_valid_token_dado_token_fresco_cuando_solicita_entonces_no_refresca(self):
        from src.infrastructure.jwt_token_manager import JWTTokenManager
        manager = JWTTokenManager("http://django:8000", "scanning_service", "secret", TEST_PUBLIC_KEY)
        fresh_token = _make_token(TEST_PRIVATE_KEY, exp_seconds=900)
        manager._access_token = fresh_token

        with patch.object(manager, "_fetch_token") as mock_fetch:
            result = manager.get_valid_token()
            mock_fetch.assert_not_called()
        assert result == fresh_token

    # BVA: token expira en 29s (< buffer 30s) → refresca
    def test_get_valid_token_dado_token_por_expirar_cuando_solicita_entonces_refresca(self):
        from src.infrastructure.jwt_token_manager import JWTTokenManager
        manager = JWTTokenManager("http://django:8000", "scanning_service", "secret", TEST_PUBLIC_KEY)
        expiring_token = _make_token(TEST_PRIVATE_KEY, exp_seconds=29)
        manager._access_token = expiring_token

        new_token = _make_token(TEST_PRIVATE_KEY, exp_seconds=900)
        with patch.object(manager, "_fetch_token", return_value=new_token):
            result = manager.get_valid_token()
        assert result == new_token

    # EP: sin token previo → fetch automático
    def test_get_valid_token_dado_sin_token_cuando_solicita_entonces_hace_fetch(self):
        from src.infrastructure.jwt_token_manager import JWTTokenManager
        manager = JWTTokenManager("http://django:8000", "scanning_service", "secret", TEST_PUBLIC_KEY)
        new_token = _make_token(TEST_PRIVATE_KEY, exp_seconds=900)
        with patch.object(manager, "_fetch_token", return_value=new_token):
            result = manager.get_valid_token()
        assert result == new_token
```

- [ ] **Step 5: Implementar JWTTokenManager**

```python
# scanning_service/src/infrastructure/__init__.py
# (vacío)
```

```python
# scanning_service/src/infrastructure/jwt_token_manager.py
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

    def __init__(self, django_url: str, service_name: str, service_secret: str, public_key: str) -> None:
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
                "Renovando token de servicio",
                extra={"sd": {"service": self._service_name}},
            )
            self._access_token = self._fetch_token()
        return self._access_token

    def _fetch_token(self) -> str:
        """Solicita nuevo access token a Django Internal API."""
        response = httpx.post(
            f"{self._django_url}/api/internal/v1/auth/token/",
            json={"service_name": self._service_name, "service_secret": self._service_secret},
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            self._refresh_token = data["refresh_token"]
            logger.info(
                "Token obtenido correctamente",
                extra={"sd": {"service": self._service_name, "severity": 5}},
            )
            return data["access_token"]
        raise RuntimeError(
            f"Error obteniendo token para {self._service_name}: HTTP {response.status_code}"
        )

    def _is_expiring(self, token: str) -> bool:
        """True si el token expira en los próximos REFRESH_BUFFER_SECONDS."""
        try:
            payload = jwt.decode(
                token, self._public_key, algorithms=["RS256"],
                options={"verify_exp": False},
            )
            return payload["exp"] - _REFRESH_BUFFER_SECONDS <= time.time()
        except Exception:
            return True  # Ante cualquier duda, refrescar
```

- [ ] **Step 6: Ejecutar tests**

```bash
docker exec texcore-scanning-1 pytest tests/test_jwt_token_manager.py -v
# Expected: 3 passed
```

---

## Task 9: scanning_service — DjangoApiClient (Adapter)

**Files:**
- Create: `scanning_service/src/infrastructure/django_client.py`
- Create: `scanning_service/tests/test_django_client.py`

- [ ] **Step 1: Escribir tests con mock HTTP (TDD)**

```python
# scanning_service/tests/test_django_client.py
"""Tests para DjangoApiClient. EP + circuit breaker."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import httpx
import pytest
import respx


MOCK_VALIDATE_RESPONSE = {
    "lote_id": 1,
    "codigo_lote": "LOT-001",
    "producto": {"id": 7, "descripcion": "Hilo 40/1"},
    "estado": "finalizada",
    "orden_produccion_id": 3,
    "stock_id": 10,
    "peso_kg": "95.500",
    "bodega": {"id": 2, "nombre": "Bodega Principal"},
}


class TestDjangoApiClient:
    @pytest.fixture
    def mock_token_manager(self):
        mgr = MagicMock()
        mgr.get_valid_token.return_value = "mock-token"
        return mgr

    # EP: API disponible, lote válido → retorna LoteProduccion
    @respx.mock
    def test_get_lote_by_codigo_dado_api_ok_cuando_valida_entonces_retorna_lote(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoApiClient
        respx.get("http://backend:8000/api/internal/v1/lotes/LOT-001/validate/").mock(
            return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE)
        )
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        lote = client.get_lote_by_codigo("LOT-001")

        assert lote is not None
        assert lote.codigo_lote == "LOT-001"
        assert lote.orden_produccion.producto.descripcion == "Hilo 40/1"

    # EP: lote no encontrado → retorna None
    @respx.mock
    def test_get_lote_by_codigo_dado_lote_inexistente_cuando_valida_entonces_retorna_none(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoApiClient
        respx.get("http://backend:8000/api/internal/v1/lotes/NO-EXISTE/validate/").mock(
            return_value=httpx.Response(404, json={"detail": "No encontrado"})
        )
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        result = client.get_lote_by_codigo("NO-EXISTE")
        assert result is None

    # EP: stock disponible retorna StockBodega desde cache
    @respx.mock
    def test_get_stock_activo_dado_cache_poblado_cuando_solicita_entonces_retorna_stock(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoApiClient
        respx.get("http://backend:8000/api/internal/v1/lotes/LOT-001/validate/").mock(
            return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE)
        )
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        lote = client.get_lote_by_codigo("LOT-001")  # puebla el cache
        stock = client.get_stock_activo_por_lote(lote.id)

        assert stock is not None
        assert stock.cantidad == Decimal("95.500")
        assert stock.bodega.nombre == "Bodega Principal"

    # BVA: peso_kg=None en response → get_stock retorna None
    @respx.mock
    def test_get_stock_activo_dado_sin_stock_cuando_solicita_entonces_retorna_none(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoApiClient
        response_sin_stock = {**MOCK_VALIDATE_RESPONSE, "stock_id": None, "peso_kg": None, "bodega": None}
        respx.get("http://backend:8000/api/internal/v1/lotes/LOT-001/validate/").mock(
            return_value=httpx.Response(200, json=response_sin_stock)
        )
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        lote = client.get_lote_by_codigo("LOT-001")
        stock = client.get_stock_activo_por_lote(lote.id)
        assert stock is None
```

- [ ] **Step 2: Implementar DjangoApiClient**

```python
# scanning_service/src/infrastructure/django_client.py
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
_CIRCUIT_RESET_SECONDS = 30


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
            self._error_count = 0  # reset circuit breaker en éxito
        except httpx.TimeoutException:
            self._error_count += 1
            logger.error(
                "Timeout en Django API",
                extra={"sd": {"severity": 3, "url": url, "errors": self._error_count}},
            )
            if self._error_count >= _CIRCUIT_THRESHOLD:
                raise RuntimeError("Django Internal API no responde (circuit breaker activo).")
            raise

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            self._error_count += 1
            logger.error(
                "Error HTTP en Django API",
                extra={"sd": {"severity": 3, "status": response.status_code}},
            )
            raise RuntimeError(f"Django Internal API respondió {response.status_code}")

        data = response.json()
        lote_id = data["lote_id"]

        # Poblar cache de stock para la siguiente llamada
        if data.get("peso_kg") is not None:
            self._stock_cache[lote_id] = StockBodega(
                id=data["stock_id"],
                cantidad=Decimal(str(data["peso_kg"])),
                bodega=Bodega(id=data["bodega"]["id"], nombre=data["bodega"]["nombre"]),
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
```

- [ ] **Step 3: Ejecutar tests**

```bash
docker exec texcore-scanning-1 pytest tests/test_django_client.py -v
# Expected: 4 passed
```

---

## Task 10: scanning_service — Actualizar router + health + eliminar SQL

**Files:**
- Modify: `scanning_service/src/routers/validate.py`
- Modify: `scanning_service/src/routers/health.py`
- Modify: `scanning_service/src/main.py`
- Delete: `scanning_service/src/database.py`
- Delete: `scanning_service/src/models.py`
- Delete: `scanning_service/src/repositories/lote_repository.py`

- [ ] **Step 1: Actualizar config para nuevas env vars**

Al inicio de `scanning_service/src/main.py`, agregar la creación del cliente global:

```python
# scanning_service/src/main.py — REEMPLAZAR CONTENIDO COMPLETO
"""
App factory del scanning_service — versión independiente.
Toda la configuración de BD fue reemplazada por JWT + Django Internal API.
"""
import logging
import logging.handlers
import os
import time

from fastapi import FastAPI, Request

from .logging_rfc5424 import RFC5424Formatter
from .routers import health as health_router
from .routers import validate as validate_router
from .infrastructure.jwt_token_manager import JWTTokenManager
from .infrastructure.django_client import DjangoApiClient


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Variable de entorno requerida no configurada: '{name}'")
    return value


def _setup_logging() -> None:
    formatter = RFC5424Formatter(facility=18, app_name="texcore-scanning")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handlers: list = [handler]
    if os.path.exists("/dev/log"):
        syslog_h = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_h.setFormatter(formatter)
        handlers.append(syslog_h)
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=handlers)


_setup_logging()
logger = logging.getLogger(__name__)

# Fail-Fast: el servicio no arranca sin estas variables
DJANGO_INTERNAL_URL = _get_required_env("DJANGO_INTERNAL_URL")
SERVICE_NAME = _get_required_env("SERVICE_NAME")
SERVICE_SECRET = _get_required_env("SERVICE_SECRET")
INTERNAL_JWT_PUBLIC_KEY = _get_required_env("INTERNAL_JWT_PUBLIC_KEY").replace("\\n", "\n")

# Singleton: token manager y cliente Django
token_manager = JWTTokenManager(
    django_url=DJANGO_INTERNAL_URL,
    service_name=SERVICE_NAME,
    service_secret=SERVICE_SECRET,
    public_key=INTERNAL_JWT_PUBLIC_KEY,
)
django_client = DjangoApiClient(token_manager=token_manager, base_url=DJANGO_INTERNAL_URL)

app = FastAPI(
    title="TexCore Scanning Service",
    description="Microservicio de validación de lotes — independiente de BD",
    version="3.0.0",
)


@app.middleware("http")
async def log_requests_rfc5424(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code if response else 500
        level = logging.ERROR if status_code >= 500 else (
            logging.WARNING if status_code >= 400 else logging.INFO
        )
        logging.getLogger("http-request").log(
            level, f"{request.method} {request.url.path} {status_code}",
            extra={"sd": {"method": request.method, "path": request.url.path,
                          "status_code": status_code, "duration_ms": duration_ms}},
        )


@app.get("/", include_in_schema=False)
def read_root():
    return {"service": "TexCore Scanning Service", "status": "running", "version": "3.0.0"}


app.include_router(health_router.router)
app.include_router(validate_router.router)
```

- [ ] **Step 2: Actualizar routers/validate.py — reemplazar DI**

```python
# scanning_service/src/routers/validate.py
"""
Router HTTP para validación de lotes.
DIP: recibe LoteValidationService con DjangoApiClient inyectado desde main.
"""
from fastapi import APIRouter
from ..main import django_client
from ..services.validation_service import LoteValidationService
from ..schemas.validate import ValidateRequest, ValidateResponse

router = APIRouter(tags=["Validación"])


def get_validation_service() -> LoteValidationService:
    """Usa el DjangoApiClient singleton creado en main.py."""
    return LoteValidationService(django_client)


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validar código de lote escaneado",
)
def validate_lote(request: ValidateRequest) -> ValidateResponse:
    return get_validation_service().validate(request.code)
```

- [ ] **Step 3: Actualizar routers/health.py — verifica Django API en lugar de BD**

```python
# scanning_service/src/routers/health.py
"""Health check: verifica conectividad con Django Internal API."""
import httpx
from fastapi import APIRouter, HTTPException
from ..main import DJANGO_INTERNAL_URL

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check del servicio")
def health_check():
    try:
        resp = httpx.get(f"{DJANGO_INTERNAL_URL}/api/health/", timeout=3.0)
        if resp.status_code == 200:
            return {"status": "healthy", "django_api": "connected"}
        raise HTTPException(status_code=503, detail=f"Django API respondió {resp.status_code}")
    except httpx.RequestError as exc:
        raise HTTPException(status_code=503, detail=f"Django API unreachable: {exc}")
```

- [ ] **Step 4: Eliminar archivos SQL**

```bash
rm scanning_service/src/database.py
rm scanning_service/src/models.py
rm scanning_service/src/repositories/lote_repository.py
```

- [ ] **Step 5: Verificar que no hay imports rotos**

```bash
docker exec texcore-scanning-1 python -c "from src.main import app; print('OK')"
# Expected: OK
```

- [ ] **Step 6: Ejecutar todos los tests del scanning_service**

```bash
docker exec texcore-scanning-1 pytest tests/ -v
# Expected: todos en verde
```

---

## Task 11: reporting_excel — JWTTokenManager + DjangoReportRepository

**Files:**
- Create: `reporting_excel/src/infrastructure/__init__.py`
- Create: `reporting_excel/src/infrastructure/jwt_token_manager.py`
- Create: `reporting_excel/src/infrastructure/django_client.py`
- Create: `reporting_excel/tests/test_django_report_repo.py`

- [ ] **Step 1: Copiar JWTTokenManager (idéntico al de scanning)**

```python
# reporting_excel/src/infrastructure/__init__.py
# (vacío)
```

```python
# reporting_excel/src/infrastructure/jwt_token_manager.py
# Contenido IDÉNTICO al de scanning_service/src/infrastructure/jwt_token_manager.py
# (servicios independientes — no comparten paquete)
import logging
import time
from typing import Optional
import httpx
import jwt

logger = logging.getLogger(__name__)
_REFRESH_BUFFER_SECONDS = 30


class JWTTokenManager:
    """SRP: gestiona ciclo de vida del JWT. ISO 27001 A.10: en memoria."""

    def __init__(self, django_url: str, service_name: str, service_secret: str, public_key: str) -> None:
        self._django_url = django_url
        self._service_name = service_name
        self._service_secret = service_secret
        self._public_key = public_key
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None

    def get_valid_token(self) -> str:
        if self._access_token is None or self._is_expiring(self._access_token):
            self._access_token = self._fetch_token()
        return self._access_token

    def _fetch_token(self) -> str:
        response = httpx.post(
            f"{self._django_url}/api/internal/v1/auth/token/",
            json={"service_name": self._service_name, "service_secret": self._service_secret},
            timeout=10.0,
        )
        if response.status_code == 200:
            data = response.json()
            self._refresh_token = data["refresh_token"]
            return data["access_token"]
        raise RuntimeError(f"Error obteniendo token: HTTP {response.status_code}")

    def _is_expiring(self, token: str) -> bool:
        try:
            payload = jwt.decode(token, self._public_key, algorithms=["RS256"],
                                 options={"verify_exp": False})
            return payload["exp"] - _REFRESH_BUFFER_SECONDS <= time.time()
        except Exception:
            return True
```

- [ ] **Step 2: Escribir tests del DjangoReportRepository (TDD)**

```python
# reporting_excel/tests/test_django_report_repo.py
"""Tests para DjangoReportRepository. EP por endpoint representativo."""
from unittest.mock import MagicMock
import httpx
import pandas as pd
import pytest
import respx


@pytest.fixture
def mock_token_manager():
    mgr = MagicMock()
    mgr.get_valid_token.return_value = "mock-token"
    return mgr


class TestDjangoReportRepository:
    # EP: API disponible → retorna DataFrame con datos
    @respx.mock
    def test_execute_sp_dado_kardex_disponible_cuando_ejecuta_entonces_retorna_dataframe(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoReportRepository
        respx.get("http://backend:8000/api/internal/v1/reports/kardex/").mock(
            return_value=httpx.Response(200, json=[
                {"id": 1, "fecha": "2026-05-01", "tipo_movimiento": "COMPRA",
                 "producto_descripcion": "Hilo", "cantidad": "100.00"}
            ])
        )
        repo = DjangoReportRepository(token_manager=mock_token_manager, base_url="http://backend:8000")
        df = repo.execute_sp("EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?, @FechaInicio=?, @FechaFin=?, @ProveedorID=?, @LoteCodigo=?",
                             (1, None, None, None, None, None))
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "producto_descripcion" in df.columns

    # EP: API retorna lista vacía → DataFrame vacío (no error)
    @respx.mock
    def test_execute_sp_dado_sin_datos_cuando_ejecuta_entonces_retorna_dataframe_vacio(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoReportRepository
        respx.get("http://backend:8000/api/internal/v1/reports/productos/").mock(
            return_value=httpx.Response(200, json=[])
        )
        repo = DjangoReportRepository(token_manager=mock_token_manager, base_url="http://backend:8000")
        df = repo.execute_sp("EXEC sp_GetProductosCatalogo", None)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    # EP: SP no mapeado → ValueError
    def test_execute_sp_dado_sp_desconocido_cuando_ejecuta_entonces_lanza_error(self, mock_token_manager):
        from src.infrastructure.django_client import DjangoReportRepository
        repo = DjangoReportRepository(token_manager=mock_token_manager, base_url="http://backend:8000")
        with pytest.raises(ValueError, match="SP no mapeado"):
            repo.execute_sp("EXEC sp_NoExiste", None)
```

- [ ] **Step 3: Implementar DjangoReportRepository**

```python
# reporting_excel/src/infrastructure/django_client.py
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
_SP_MAPPING: dict[str, tuple[str, list[str]]] = {
    "sp_GetKardexBodega": ("/api/internal/v1/reports/kardex/",
        ["bodega_id", "producto_id", "fecha_desde", "fecha_hasta", "proveedor_id", "lote_codigo"]),
    "sp_GetProductosCatalogo": ("/api/internal/v1/reports/productos/", []),
    "sp_GetUsuariosSistema": ("/api/internal/v1/reports/usuarios/", []),
    "sp_GetStockActualBodega": ("/api/internal/v1/reports/stock-actual/",
        ["bodega_id", "sede_id", "producto_id"]),
    "sp_GetValorizacionInventario": ("/api/internal/v1/reports/valorizacion/",
        ["bodega_id", "sede_id"]),
    "sp_GetInventarioAging": ("/api/internal/v1/reports/aging/",
        ["bodega_id", "sede_id", "dias_minimos"]),
    "sp_GetRotacionInventario": ("/api/internal/v1/reports/rotacion/",
        ["bodega_id", "fecha_desde", "fecha_hasta", "sede_id"]),
    "sp_GetStockCeroBodega": ("/api/internal/v1/reports/stock-cero/",
        ["bodega_id", "sede_id"]),
    "sp_GetResumenMovimientos": ("/api/internal/v1/reports/resumen-movimientos/",
        ["bodega_id", "fecha_desde", "fecha_hasta", "sede_id"]),
    "sp_GetVentasPorVendedor": ("/api/internal/v1/vendedores/{vendedor_id}/ventas/",
        ["vendedor_id", "fecha_desde", "fecha_hasta"]),
    "sp_GetTopClientesPorVendedor": ("/api/internal/v1/vendedores/{vendedor_id}/top-clientes/",
        ["vendedor_id", "fecha_desde", "fecha_hasta"]),
    "sp_GetDeudoresPorVendedor": ("/api/internal/v1/vendedores/{vendedor_id}/deudores/",
        ["vendedor_id"]),
    "sp_GetVentasGerencial": ("/api/internal/v1/gerencial/ventas/",
        ["fecha_desde", "fecha_hasta", "sede_id"]),
    "sp_GetTopClientesGerencial": ("/api/internal/v1/gerencial/top-clientes/",
        ["fecha_desde", "fecha_hasta", "sede_id"]),
    "sp_GetDeudoresGerencial": ("/api/internal/v1/gerencial/deudores/", ["sede_id"]),
    "sp_GetOrdenesProduccionGerencial": ("/api/internal/v1/produccion/ordenes/",
        ["fecha_desde", "fecha_hasta", "sede_id"]),
    "sp_GetLotesProduccionGerencial": ("/api/internal/v1/produccion/lotes/",
        ["fecha_desde", "fecha_hasta", "sede_id"]),
    "sp_GetTendenciaProduccionGerencial": ("/api/internal/v1/produccion/tendencia/",
        ["fecha_desde", "fecha_hasta", "sede_id"]),
}


class DjangoReportRepository:
    """Adapter que implementa IReportRepository via Django Internal API."""

    def __init__(self, token_manager: JWTTokenManager, base_url: str) -> None:
        self._token_manager = token_manager
        self._base_url = base_url.rstrip("/")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token_manager.get_valid_token()}"}

    @staticmethod
    def _extract_sp_name(sp_query: str) -> str:
        """Extrae 'sp_GetKardexBodega' de 'EXEC sp_GetKardexBodega @BodegaID=?, ...'"""
        match = re.search(r"(sp_\w+)", sp_query, re.IGNORECASE)
        if not match:
            raise ValueError(f"No se encontró nombre de SP en: {sp_query[:60]}")
        return match.group(1)

    def execute_sp(self, sp_query: str, params: Optional[Tuple]) -> pd.DataFrame:
        sp_name = self._extract_sp_name(sp_query)
        mapping = _SP_MAPPING.get(sp_name)
        if not mapping:
            raise ValueError(f"SP no mapeado: '{sp_name}'. Agregar a _SP_MAPPING.")

        endpoint_template, param_names = mapping

        # Construir query params y path params
        path_params = {}
        query_params = {}
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
            response = httpx.get(url, params=query_params, headers=self._headers(), timeout=30.0)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP %s en %s: %s", exc.response.status_code, url, exc)
            raise

        data = response.json()
        logger.info(
            "Reporte obtenido",
            extra={"sd": {"severity": 6, "sp": sp_name, "rows": len(data)}},
        )
        return pd.DataFrame(data) if data else pd.DataFrame()
```

- [ ] **Step 4: Agregar PyJWT a reporting_excel/requirements.txt**

```text
fastapi
uvicorn
pandas
openpyxl
xlsxwriter
httpx
PyJWT==2.10.1
cryptography==42.0.8
pydantic-settings
pytest
pytest-cov
respx
python-multipart
```

- [ ] **Step 5: Ejecutar tests**

```bash
docker exec texcore-reporting_excel-1 pytest tests/test_django_report_repo.py -v
# Expected: 3 passed
```

---

## Task 12: reporting_excel — Actualizar factory, auth, health y eliminar SQL

**Files:**
- Modify: `reporting_excel/src/services/report_factory.py`
- Modify: `reporting_excel/src/main.py`
- Delete: `reporting_excel/src/database.py`
- Delete: `reporting_excel/src/repositories/sql_repository.py`

- [ ] **Step 1: Actualizar report_factory.py para usar DjangoReportRepository**

```python
# reporting_excel/src/services/report_factory.py
"""
ReportFactory: crea el ReportService con DjangoReportRepository.
Factory Pattern + OCP: cambiar repositorio no requiere modificar routers.
"""
from ..infrastructure.django_client import DjangoReportRepository
from ..formatters.excel_formatter import ExcelFormatter
from ..formatters.csv_formatter import CsvFormatter
from .report_service import ReportService

# Importar el cliente singleton desde main (se inicializa al arrancar)
def _get_repo() -> DjangoReportRepository:
    from ..main import django_report_repo
    return django_report_repo


class ReportFactory:
    @staticmethod
    def create(format: str) -> ReportService:
        repo = _get_repo()
        formatters = {"xlsx": ExcelFormatter(), "csv": CsvFormatter()}
        formatter = formatters.get(format)
        if formatter is None:
            raise ValueError(f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
        return ReportService(repository=repo, formatter=formatter)
```

- [ ] **Step 2: Reemplazar main.py — JWT Bearer en lugar de X-Internal-Key**

```python
# reporting_excel/src/main.py — REEMPLAZAR CONTENIDO COMPLETO
"""
App factory del reporting_excel — versión independiente.
Autenticación: JWT Bearer RS256 (reemplaza X-Internal-Key).
ISO 27001: sin credenciales de BD, audit trail por cada reporte.
"""
import logging
import logging.handlers
import os
import time

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.logging_rfc5424 import RFC5424Formatter
from src.infrastructure.jwt_token_manager import JWTTokenManager
from src.infrastructure.django_client import DjangoReportRepository


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Variable requerida no configurada: '{name}'")
    return value


def _setup_logging() -> None:
    formatter = RFC5424Formatter(facility=17, app_name="texcore-reporting")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handlers = [handler]
    if os.path.exists("/dev/log"):
        syslog_h = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_h.setFormatter(formatter)
        handlers.append(syslog_h)
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=handlers)


_setup_logging()
logger = logging.getLogger(__name__)

# Fail-Fast
DJANGO_INTERNAL_URL = _get_required_env("DJANGO_INTERNAL_URL")
SERVICE_NAME = _get_required_env("SERVICE_NAME")
SERVICE_SECRET = _get_required_env("SERVICE_SECRET")
INTERNAL_JWT_PUBLIC_KEY = _get_required_env("INTERNAL_JWT_PUBLIC_KEY").replace("\\n", "\n")

_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://backend:8000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# Singletons
token_manager = JWTTokenManager(
    django_url=DJANGO_INTERNAL_URL,
    service_name=SERVICE_NAME,
    service_secret=SERVICE_SECRET,
    public_key=INTERNAL_JWT_PUBLIC_KEY,
)
django_report_repo = DjangoReportRepository(token_manager=token_manager, base_url=DJANGO_INTERNAL_URL)

app = FastAPI(
    title="Reporting Excel Microservice",
    description="Genera reportes Excel/CSV via Django Internal API — sin acceso directo a BD",
    version="2.0.0",
)


@app.middleware("http")
async def log_requests_rfc5424(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code if response else 500
        level = logging.ERROR if status_code >= 500 else (
            logging.WARNING if status_code >= 400 else logging.INFO
        )
        logging.getLogger("http-request").log(
            level, f"{request.method} {request.url.path} {status_code}",
            extra={"sd": {"method": request.method, "path": request.url.path,
                          "status_code": status_code, "duration_ms": duration_ms}},
        )


@app.middleware("http")
async def verify_jwt_service_token(request: Request, call_next):
    """Reemplaza X-Internal-Key por JWT Bearer RS256."""
    if request.url.path == "/health":
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"detail": "Authorization header Bearer requerido."})

    token = auth_header.split(" ", 1)[1].strip()
    try:
        jwt.decode(token, INTERNAL_JWT_PUBLIC_KEY, algorithms=["RS256"],
                   options={"verify_exp": True})
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expirado."})
    except jwt.InvalidTokenError as exc:
        return JSONResponse(status_code=401, content={"detail": f"Token inválido: {exc}"})

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Authorization"],
)


@app.get("/health")
def health_check():
    try:
        resp = httpx.get(f"{DJANGO_INTERNAL_URL}/api/health/", timeout=3.0)
        if resp.status_code == 200:
            return {"status": "healthy", "django_api": "connected"}
        return {"status": "degraded", "django_api": f"HTTP {resp.status_code}"}
    except httpx.RequestError:
        return {"status": "degraded", "django_api": "unreachable"}


from src.routers import exports, vendedores, gerencial, produccion
app.include_router(exports.router, prefix="/export", tags=["Exports"])
app.include_router(vendedores.router, prefix="/vendedores", tags=["Vendedores"])
app.include_router(gerencial.router, prefix="/gerencial", tags=["Gerencial"])
app.include_router(produccion.router, prefix="/produccion", tags=["Produccion"])
```

- [ ] **Step 3: Eliminar archivos SQL**

```bash
rm reporting_excel/src/database.py
rm reporting_excel/src/repositories/sql_repository.py
```

- [ ] **Step 4: Verificar imports**

```bash
docker exec texcore-reporting_excel-1 python -c "from src.main import app; print('OK')"
# Expected: OK
```

---

## Task 13: Docker Compose — Actualizar env vars y dependencias

**Files:**
- Modify: `docker-compose.yml`

- [ ] **Step 1: Actualizar docker-compose.yml — sección scanning**

Reemplazar el bloque `scanning:` con:
```yaml
  scanning:
    build:
      context: ./scanning_service
      dockerfile: Dockerfile
    environment:
      - DJANGO_INTERNAL_URL=http://backend:8000
      - SERVICE_NAME=scanning_service
      - SERVICE_SECRET=${SCANNING_SERVICE_SECRET}
      - INTERNAL_JWT_PUBLIC_KEY=${INTERNAL_JWT_PUBLIC_KEY}
    expose:
      - "8000"
    depends_on:
      backend:
        condition: service_healthy
```

- [ ] **Step 2: Actualizar docker-compose.yml — sección reporting_excel**

Reemplazar el bloque `reporting_excel:` con:
```yaml
  reporting_excel:
    build:
      context: ./reporting_excel
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    volumes:
      - ./reporting_excel/src:/app/src
    environment:
      - DJANGO_INTERNAL_URL=http://backend:8000
      - SERVICE_NAME=reporting_excel
      - SERVICE_SECRET=${REPORTING_SERVICE_SECRET}
      - INTERNAL_JWT_PUBLIC_KEY=${INTERNAL_JWT_PUBLIC_KEY}
      - CORS_ALLOWED_ORIGINS=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
```

- [ ] **Step 3: Agregar al backend las nuevas env vars**

En el bloque `backend:` de docker-compose.yml, agregar junto a las env vars existentes:
```yaml
      - INTERNAL_JWT_PRIVATE_KEY=${INTERNAL_JWT_PRIVATE_KEY}
      - INTERNAL_JWT_PUBLIC_KEY=${INTERNAL_JWT_PUBLIC_KEY}
```

- [ ] **Step 4: Crear ServiceCredentials en Django para ambos servicios**

Crear management command `internal_api/management/commands/seed_service_credentials.py`:

```python
# internal_api/management/__init__.py  (vacío)
# internal_api/management/commands/__init__.py  (vacío)
```

```python
# internal_api/management/commands/seed_service_credentials.py
"""Crea ServiceCredentials para los microservicios si no existen."""
import os
from django.core.management.base import BaseCommand
from internal_api.models import ServiceCredential


class Command(BaseCommand):
    help = "Crea credenciales de servicio para scanning_service y reporting_excel"

    def handle(self, *args, **options):
        services = [
            ("scanning_service", os.environ.get("SCANNING_SERVICE_SECRET", ""), ["lotes:read"]),
            ("reporting_excel", os.environ.get("REPORTING_SERVICE_SECRET", ""), ["reports:read"]),
        ]
        for name, secret, scopes in services:
            if not secret:
                self.stdout.write(self.style.WARNING(f"Sin secret para {name} — saltando"))
                continue
            obj, created = ServiceCredential.objects.get_or_create(
                name=name,
                defaults={
                    "secret_hash": ServiceCredential.hash_secret(secret),
                    "allowed_scopes": scopes,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Creado: {name}"))
            else:
                self.stdout.write(f"Ya existe: {name}")
```

- [ ] **Step 5: Agregar seed_service_credentials al entrypoint**

En `entrypoint.sh` (o equivalente), después de `migrate`:
```bash
python manage.py seed_service_credentials
```

- [ ] **Step 6: Rebuild y smoke test**

```bash
docker compose down
docker compose build --no-cache scanning reporting_excel backend
docker compose up -d

# Esperar que backend esté healthy, luego:
docker exec texcore-backend-1 python manage.py test internal_api -v 2

# Test end-to-end scanning:
curl -s http://localhost/api/scanning/validate \
  -X POST -H "Content-Type: application/json" \
  -d '{"code": "LOT-TEST-001"}' | jq .

# Health check microservicios:
curl http://localhost:8002/health | jq .
```

---

## Resumen de archivos a crear/modificar

| Acción | Archivo |
|--------|---------|
| CREATE | `internal_api/__init__.py` |
| CREATE | `internal_api/apps.py` |
| CREATE | `internal_api/models.py` |
| CREATE | `internal_api/authentication.py` |
| CREATE | `internal_api/permissions.py` |
| CREATE | `internal_api/audit.py` |
| CREATE | `internal_api/serializers.py` |
| CREATE | `internal_api/urls.py` |
| CREATE | `internal_api/views/__init__.py` |
| CREATE | `internal_api/views/auth_views.py` |
| CREATE | `internal_api/views/scanning_views.py` |
| CREATE | `internal_api/views/reporting_views.py` |
| CREATE | `internal_api/management/commands/seed_service_credentials.py` |
| CREATE | `internal_api/tests/` (4 archivos de test) |
| MODIFY | `TexCore/settings.py` (INSTALLED_APPS + INTERNAL_JWT_*) |
| MODIFY | `TexCore/urls.py` (registrar internal_api) |
| MODIFY | `requirements.txt` (agregar cryptography) |
| CREATE | `scanning_service/src/domain/models.py` |
| MODIFY | `scanning_service/src/repositories/base.py` |
| CREATE | `scanning_service/src/infrastructure/jwt_token_manager.py` |
| CREATE | `scanning_service/src/infrastructure/django_client.py` |
| MODIFY | `scanning_service/src/main.py` |
| MODIFY | `scanning_service/src/routers/validate.py` |
| MODIFY | `scanning_service/src/routers/health.py` |
| MODIFY | `scanning_service/requirements.txt` |
| DELETE | `scanning_service/src/database.py` |
| DELETE | `scanning_service/src/models.py` |
| DELETE | `scanning_service/src/repositories/lote_repository.py` |
| CREATE | `reporting_excel/src/infrastructure/jwt_token_manager.py` |
| CREATE | `reporting_excel/src/infrastructure/django_client.py` |
| MODIFY | `reporting_excel/src/services/report_factory.py` |
| MODIFY | `reporting_excel/src/main.py` |
| MODIFY | `reporting_excel/requirements.txt` |
| DELETE | `reporting_excel/src/database.py` |
| DELETE | `reporting_excel/src/repositories/sql_repository.py` |
| MODIFY | `docker-compose.yml` |
