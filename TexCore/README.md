# TexCore (Configuración Global)

Este directorio contiene la configuración central del proyecto Django.

## Contenido
- `settings.py`: Configuración principal (Base de datos, Middleware, Apps instaladas).
- `urls.py`: Enrutamiento raíz que distribuye a `gestion`, `inventory`, etc.
- `celery.py`: Configuración de la cola de tareas asíncronas.
- `logging_rfc5424.py`: Formateador de logs para cumplimiento de estándares.
- `wsgi.py` / `asgi.py`: Interfaces de servidor para despliegue.
