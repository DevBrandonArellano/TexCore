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
from pathlib import Path

# --- Variables de entorno obligatorias (Fail Fast en settings.py) -----------
os.environ.setdefault("SECRET_KEY", "test-secret-key-local-only")
os.environ.setdefault("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
os.environ.setdefault("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

# DATABASES también es Fail Fast en settings.py (barrido de higiene Fase 5.7) —
# aunque este módulo sobreescribe DATABASES a SQLite justo debajo, la ejecución
# de settings.py completa primero vía `from TexCore.settings import *`, así que
# necesita valores (ficticios, nunca se usan) para no abortar antes de llegar ahí.
os.environ.setdefault("DB_ENGINE", "django.db.backends.sqlite3")
os.environ.setdefault("DB_NAME", ":memory:")
os.environ.setdefault("DB_USER", "unused")
os.environ.setdefault("DB_PASSWORD", "unused")
os.environ.setdefault("DB_HOST", "unused")
os.environ.setdefault("DB_PORT", "0")
os.environ.setdefault("DB_DRIVER", "unused")

# --- Claves JWT internas (reporting_proxy / internal_api) ------------------
# manage.py carga .env/.env.test vía python-dotenv, pero pytest no pasa por
# manage.py::main() — sin esto, INTERNAL_JWT_PRIVATE_KEY/PUBLIC_KEY quedan
# vacías y jwt.encode(RS256) falla con InvalidKeyError. CI ya inyecta estas
# mismas claves de prueba (.env.test) a mano antes de correr los tests;
# replicamos eso aquí para el harness local.
try:
    from dotenv import load_dotenv
    _env_test = Path(__file__).resolve().parent.parent / ".env.test"
    if _env_test.exists():
        load_dotenv(_env_test, override=False)
except ImportError:
    pass

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

from TexCore.settings_test_common import *  # noqa: E402, F401, F403
