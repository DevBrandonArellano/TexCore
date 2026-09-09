"""
Bloque compartido por settings_test.py (CI, SQL Server) y settings_test_local.py
(local, SQLite) — DRY: ambos necesitaban exactamente los mismos overrides de
performance y logging para correr la suite de tests.

Uso: `from TexCore.settings_test_common import *` después de definir DATABASES
(este módulo no toca DATABASES, cada settings_test* define el suyo).
"""

# ---------------------------------------------------------------------------
# Rendimiento — MD5 es órdenes de magnitud más rápido que bcrypt en tests
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# ---------------------------------------------------------------------------
# Celery — ejecutar tareas de forma síncrona; no se necesita broker en tests
# ---------------------------------------------------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# ---------------------------------------------------------------------------
# Logging — silenciar todo para mantener la salida de tests limpia
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {"null": {"class": "logging.NullHandler"}},
    "root": {"handlers": ["null"], "level": "CRITICAL"},
}
