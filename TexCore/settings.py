"""
Configuración de Django para el proyecto TexCore.

Generado por 'django-admin startproject' con Django 5.2.7.

Para más información sobre este archivo, consulta
https://docs.djangoproject.com/en/5.2/topics/settings/

Para la lista completa de ajustes y sus valores, consulta
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured

from TexCore.logging_rfc5424 import RFC5424Formatter as _RFC5424Formatter


def get_env_variable(var_name):
    """Obtiene la variable de entorno o lanza una excepción (Fail Fast)."""
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = f"Falta la variable de entorno obligatoria: {var_name}"
        raise ImproperlyConfigured(error_msg) from None


BASE_DIR = Path(__file__).resolve().parent.parent


# Ajustes de desarrollo rápido — no aptos para producción
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

SECRET_KEY = get_env_variable("SECRET_KEY")

# ---------------------------------------------------------------------------
# RS-19 — Cifrado de datos personales en reposo (LOPDP 2021, ISO/IEC 27001)
# ---------------------------------------------------------------------------
# Fail-fast, igual que SECRET_KEY: sin estas claves el sistema no puede leer los
# datos personales ya guardados, y arrancar «a medias» los dejaría ilegibles sin
# avisar. Ver gestion/crypto.py y docs/arquitectura/CIFRADO_DATOS_PERSONALES.md.
#
# FIELD_ENCRYPTION_KEYS: lista separada por comas. La primera cifra; todas descifran,
# lo que permite rotar la clave sin parar el sistema (MultiFernet).
FIELD_ENCRYPTION_KEYS = [
    clave.strip() for clave in get_env_variable("FIELD_ENCRYPTION_KEYS").split(",") if clave.strip()
]
# BLIND_INDEX_KEY: estable. Si cambia, hay que recalcular los índices ciegos con
# `manage.py cifrar_datos_personales --recalcular-indices`.
BLIND_INDEX_KEY = get_env_variable("BLIND_INDEX_KEY")

# Acepta: 1, true, yes (sin distinguir mayúsculas). Cualquier otro valor = False.
DEBUG = os.environ.get("DEBUG", "0").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")


# Definición de aplicaciones

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps de terceros
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",  # Lista negra de JWT (requiere migrate)
    "corsheaders",
    "drf_spectacular",  # Documentación OpenAPI 3.1 en /api/docs/
    # Local Apps (GestionConfig carga las señales de auditoría en ready())
    "gestion.apps.GestionConfig",
    "inventory.apps.InventoryConfig",
    "internal_api.apps.InternalApiConfig",
]

# Seguridad y middleware
APPEND_SLASH = False

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # Añadido para CORS
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "gestion.middleware.AuditMiddleware",
]

# Configuración de CORS — estricta
CORS_ALLOWED_ORIGINS_ENV = get_env_variable("CORS_ALLOWED_ORIGINS")
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS_ENV.split(",")]

CORS_ALLOW_CREDENTIALS = True

# Orígenes de confianza para CSRF — estricto
CSRF_TRUSTED_ORIGINS_ENV = get_env_variable("CSRF_TRUSTED_ORIGINS")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_ENV.split(",")]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# RNF-01: las cookies de sesión y CSRF (admin de Django) solo viajan por HTTPS en
# producción, igual que las JWT (AUTH_COOKIE_SECURE).
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG


ROOT_URLCONF = "TexCore.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "TexCore.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": get_env_variable("DB_ENGINE"),
        "NAME": get_env_variable("DB_NAME"),
        "USER": get_env_variable("DB_USER"),
        "PASSWORD": get_env_variable("DB_PASSWORD"),
        "HOST": get_env_variable("DB_HOST"),
        "PORT": get_env_variable("DB_PORT"),
        "OPTIONS": {"driver": get_env_variable("DB_DRIVER"), "extra_params": "Encrypt=yes;TrustServerCertificate=yes"},
    }
}


# Validación de contraseñas
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"
# Hora de la planta para los mensajes que el backend arma en texto (p. ej., «despachado a
# las 13:23»): TIME_ZONE sigue en UTC y el frontend convierte las fechas por su cuenta.
ZONA_HORARIA_PLANTA = os.environ.get("ZONA_HORARIA_PLANTA", "America/Guayaquil")

USE_I18N = True

USE_TZ = True


# Archivos estáticos (CSS, JavaScript, imágenes)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

STATICFILES_DIRS = [
    d
    for d in [
        BASE_DIR / "frontend" / "dist",
    ]
    if Path(d).exists()
]

STATIC_ROOT = os.environ.get("STATIC_ROOT", str(BASE_DIR / "staticfiles"))


# Tipo de campo de clave primaria por defecto
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("gestion.auth_backends.CookieJWTAuthentication",),
    # Seguro por defecto: una vista que omita permission_classes queda cerrada,
    # no pública (DRF usa AllowAny si no se define). Ver test_permisos_por_defecto.py.
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "gestion.exceptions.texcore_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "TexCore API",
    "DESCRIPTION": "Sistema Integral de Gestión Textil — API REST",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # Solo exponer docs en DEBUG — en producción requiere autenticación
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}


SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    # Ajustes personalizados para autenticación con cookies
    "AUTH_COOKIE": "access_token",
    "AUTH_COOKIE_REFRESH": "refresh_token",
    "AUTH_COOKIE_DOMAIN": None,
    "AUTH_COOKIE_SECURE": not DEBUG,  # True en producción (cuando DEBUG=False)
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/",
    "AUTH_COOKIE_SAMESITE": "Lax",
}

# Modelo de usuario personalizado
AUTH_USER_MODEL = "gestion.CustomUser"

# ---------------------------------------------------------------------------
# Logging — RFC 5424 (protocolo Syslog de la IETF)
# Facility 16 (local0) reservado para el backend Django principal.
# Todos los loggers del proyecto emiten mensajes con el formato:
#   <PRI>1 TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD-ELEMENT] MSG
# ---------------------------------------------------------------------------


# Directorio de logs — se crea en arranque si no existe
_LOGS_DIR = BASE_DIR / "logs"
_LOGS_DIR.mkdir(exist_ok=True, parents=True)

LOGGING: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # Formatter principal — RFC 5424 Syslog
        "rfc5424": {
            "()": _RFC5424Formatter,
            "facility": 16,  # local0 — backend Django
            "app_name": "texcore-backend",
        },
        # Fallback legible para desarrollo local (DEBUG=True)
        "verbose": {
            "format": "{levelname} {asctime} [{name}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        # stdout → recogido por Docker / systemd journal en producción
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "rfc5424" if not DEBUG else "verbose",
        },
        # Archivo rotante — RFC 5424 en producción, verbose en dev
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(_LOGS_DIR / "backend.log"),
            "maxBytes": 1024 * 1024 * 5,  # 5 MB por archivo
            "backupCount": 5,
            "formatter": "rfc5424",
            "encoding": "utf-8",
        },
        # SysLogHandler — solo activo si /dev/log existe (Linux / Docker)
        **(
            {
                "syslog": {
                    "level": "WARNING",
                    "class": "logging.handlers.SysLogHandler",
                    "address": "/dev/log",
                    "facility": "local0",
                    "formatter": "rfc5424",
                }
            }
            if Path("/dev/log").exists()
            else {}
        ),
    },
    "loggers": {
        # App de gestión — todos los niveles a archivo + consola
        "gestion": {
            "handlers": ["console", "file"] + (["syslog"] if Path("/dev/log").exists() else []),
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        # App de inventario / MRP
        "inventory": {
            "handlers": ["console", "file"] + (["syslog"] if Path("/dev/log").exists() else []),
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
        # Django core — solo WARNING y superior
        "django": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
        # Errores HTTP — siempre a archivo y syslog
        "django.request": {
            "handlers": ["console", "file"] + (["syslog"] if Path("/dev/log").exists() else []),
            "level": "ERROR",
            "propagate": False,
        },
        # ORM queries — solo en modo DEBUG para evitar flood
        "django.db.backends": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "WARNING",
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------------------------
# Internal API — JWT Service Tokens (RS256 asimétrico)
# ISO 27001 A.10: clave privada solo en Django, pública distribuida a servicios
# ---------------------------------------------------------------------------


def _load_rsa_key(env_var: str) -> str:
    """Carga clave RSA desde env var (Fail Fast), reemplazando \\n literales por saltos reales."""
    raw = get_env_variable(env_var)
    return raw.replace("\\n", "\n")


INTERNAL_JWT_PRIVATE_KEY: str = _load_rsa_key("INTERNAL_JWT_PRIVATE_KEY")
INTERNAL_JWT_PUBLIC_KEY: str = _load_rsa_key("INTERNAL_JWT_PUBLIC_KEY")
INTERNAL_JWT_ACCESS_TTL_SECONDS: int = int(os.environ.get("INTERNAL_JWT_ACCESS_TTL_SECONDS", 900))  # 15 min
INTERNAL_JWT_REFRESH_TTL_SECONDS: int = int(os.environ.get("INTERNAL_JWT_REFRESH_TTL_SECONDS", 86400))  # 24h

# Agregar logger para internal_api al bloque de loggers existente
LOGGING["loggers"]["internal_api"] = {
    "handlers": ["console", "file"] + (["syslog"] if Path("/dev/log").exists() else []),
    "level": "DEBUG" if DEBUG else "INFO",
    "propagate": False,
}
LOGGING["loggers"]["internal_api.audit"] = {
    "handlers": ["console", "file"] + (["syslog"] if Path("/dev/log").exists() else []),
    "level": "INFO",
    "propagate": False,
}

# ---------------------------------------------------------------------------
# Trazabilidad de etiquetas — URL pública embebida en el QR de cada lote
# (gestion/views/production_lote_views.py:_build_zpl_payload). Configurable por
# entorno para que dev/staging no impriman etiquetas apuntando al dominio
# de producción.
# ---------------------------------------------------------------------------
TRAZABILIDAD_BASE_URL = os.environ.get("TRAZABILIDAD_BASE_URL", "https://app.texcore.com/trazabilidad")

# ---------------------------------------------------------------------------
# RUC de la empresa — usado únicamente para mostrarlo en documentos
# informativos (ej. Guía de Remisión, gestion/views/despacho_documentos_views.py).
# La facturación electrónica oficial (SRI) la maneja software externo; este
# valor NO participa de ningún flujo de autorización electrónica.
# ---------------------------------------------------------------------------
EMPRESA_RUC = os.environ.get("EMPRESA_RUC", "")

# ---------------------------------------------------------------------------
# Microservicio de impresión — usado por gestion/utils.py (ZPL/PDF de
# etiquetas, nota de venta) e internal_api/views/pdf_produccion_views.py
# (reportes de producción). Único punto de verdad: antes había 3 defaults
# distintos repartidos en 2 archivos (uno de ellos apuntando al hostname
# 'printing_service', que no existe en docker-compose — el servicio real se
# llama 'printing'), y ningún docker-compose seteaba la env var, así que
# siempre se usaba el default equivocado.
# ---------------------------------------------------------------------------
PRINTING_SERVICE_URL = os.environ.get("PRINTING_SERVICE_URL", "http://printing:8001")
# Timeout en segundos para la llamada al printing_service — WeasyPrint puede
# tardar para documentos grandes (internal_api/views/pdf_produccion_views.py).
PRINTING_PDF_TIMEOUT = float(os.environ.get("PRINTING_PDF_TIMEOUT", "60.0"))

# Configuración de Celery
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Con el broker caído, kombu reintenta publicar durante 20-70 s y bloquea un worker
# síncrono de gunicorn: se acota a un reintento y conexiones de pocos segundos para
# que el proxy responda 503 enseguida (inventory/reporting_proxy.py).
CELERY_BROKER_CONNECTION_TIMEOUT = 3
CELERY_BROKER_TRANSPORT_OPTIONS = {"socket_connect_timeout": 3, "socket_timeout": 5}
CELERY_REDIS_SOCKET_CONNECT_TIMEOUT = 3
CELERY_REDIS_SOCKET_TIMEOUT = 5
CELERY_TASK_PUBLISH_RETRY_POLICY = {"max_retries": 1, "interval_start": 0, "interval_step": 0.5, "interval_max": 1}
# El result backend de Redis trae su propia política (20 reintentos de ~1 s): sin esto,
# encolar con Redis caído tardaba 25 s aunque el broker ya estuviera acotado.
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {"retry_policy": CELERY_TASK_PUBLISH_RETRY_POLICY}
# Exportación asíncrona de reportes (?async=true → Celery). Apagada por defecto:
# solo la activan los entornos que levantan Redis y celery_worker (los dos composes).
REPORTES_ASYNC_HABILITADO = os.environ.get("REPORTES_ASYNC_HABILITADO", "false").lower() in ("1", "true", "yes")
# Directorio compartido entre backend y celery_worker donde la tarea deja el archivo
# generado; en producción es el volumen prod_reportes_async.
REPORTES_ASYNC_DIR = os.environ.get("REPORTES_ASYNC_DIR", str(BASE_DIR / "reportes_async"))
# Vida del archivo, del resultado en Redis y del token de descarga (24 h).
REPORTES_ASYNC_TTL_SEGUNDOS = int(os.environ.get("REPORTES_ASYNC_TTL_SEGUNDOS", "86400"))
CELERY_RESULT_EXPIRES = REPORTES_ASYNC_TTL_SEGUNDOS
