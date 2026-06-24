"""
Django settings para ejecutar la suite de tests EN LOCAL (sin SQL Server).

Usa SQLite en memoria para permitir el ciclo TDD (red-green-refactor) en la
máquina del desarrollador. CI sigue usando ``settings_test`` con SQL Server.

Uso:
    set DJANGO_SETTINGS_MODULE=TexCore.settings_test_local   (PowerShell: $env:...)
    pytest gestion/tests -p no:cacheprovider

Las variables de entorno obligatorias de ``settings.py`` se inyectan aquí con
valores ficticios deterministas — nunca se usan contra recursos reales.
"""
import os

# --- Variables de entorno obligatorias (Fail Fast en settings.py) -----------
os.environ.setdefault("SECRET_KEY", "test-secret-key-local-only")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

from TexCore.settings import *  # noqa: E402, F401, F403

# ---------------------------------------------------------------------------
# Base de datos — SQLite en memoria (rápida, sin dependencias externas)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# ---------------------------------------------------------------------------
# Rendimiento — MD5 es mucho más rápido que bcrypt en tests
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# ---------------------------------------------------------------------------
# Celery — síncrono; sin broker en tests
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Logging — silenciar para mantener limpia la salida de tests
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
