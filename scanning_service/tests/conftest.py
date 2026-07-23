"""
conftest.py del scanning_service.

Configura variables de entorno dummy ANTES de que pytest importe src.main.
src/main.py llama _get_required_env() a nivel de módulo, lo que lanza RuntimeError
si las variables no existen. setdefault no sobreescribe valores ya definidos en el
entorno (ej: CI con variables reales o test_validate_endpoint.py que importa src.main).
"""
import os

os.environ.setdefault("DJANGO_INTERNAL_URL", "http://mock-django:8000")
os.environ.setdefault("SERVICE_NAME", "scanning_ci")
os.environ.setdefault("SERVICE_SECRET", "ci-test-secret-not-for-production")
os.environ.setdefault("INTERNAL_JWT_PUBLIC_KEY", "ci-test-placeholder")
