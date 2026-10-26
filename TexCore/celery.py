import logging
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TexCore.settings")

app = Celery("TexCore")

# - namespace='CELERY' indica que todas las claves de configuración de celery
# deben tener el prefijo `CELERY_`.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Carga los módulos de tareas de todas las apps Django registradas.
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.info("Request: %r", self.request)
