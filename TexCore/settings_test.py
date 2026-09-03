"""
Django settings para CI/GitHub Actions.

Extiende settings.py apuntando a un servicio SQL Server en el runner.
Todas las variables requeridas son inyectadas por el job backend-test en ci.yml.
"""
import os
from TexCore.settings import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Base de datos — SQL Server levantado como service container en CI
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": os.environ.get("DB_NAME", "texcore_ci"),
        "USER": os.environ.get("DB_USER", "sa"),
        "PASSWORD": os.environ.get("DB_PASSWORD"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "1433"),
        "OPTIONS": {
            "driver": "ODBC Driver 18 for SQL Server",
            "extra_params": "Encrypt=yes;TrustServerCertificate=yes",
        },
    }
}

from TexCore.settings_test_common import *  # noqa: E402, F401, F403
