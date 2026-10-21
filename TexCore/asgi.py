"""
Configuración ASGI del proyecto TexCore.

Expone el invocable ASGI como variable a nivel de módulo llamada ``application``.

Para más información sobre este archivo, consulta
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TexCore.settings")

application = get_asgi_application()
