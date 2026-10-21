# Garantiza que la app se importe al iniciar Django para que shared_task la use
from .celery import app as celery_app

__all__ = ("celery_app",)
