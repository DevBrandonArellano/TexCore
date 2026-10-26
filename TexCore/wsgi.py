"""
Configuración WSGI del proyecto TexCore.

Expone el invocable WSGI como variable a nivel de módulo llamada ``application``.

Para más información sobre este archivo, consulta
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "TexCore.settings")

application = get_wsgi_application()
