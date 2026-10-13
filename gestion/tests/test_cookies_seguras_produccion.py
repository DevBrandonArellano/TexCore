"""
RNF-01 — cookies de Django con ``Secure`` en producción.

Las cookies JWT ya salían con ``Secure`` cuando ``DEBUG=0``, pero las de sesión
y CSRF (las del admin de Django) no. El navegador las envía en la primera
petición por ``http://``, antes del 301 de nginx, y viajarían sin cifrar.

``DEBUG`` se evalúa al importar ``settings.py``, así que cada caso importa los
settings en un proceso aparte con el ``DEBUG`` deseado.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): producción (``DEBUG=0``) / desarrollo (``DEBUG=1``).
"""
import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase

_LEER_SETTINGS = (
    "import json, TexCore.settings as s; "
    "print(json.dumps({'session': getattr(s, 'SESSION_COOKIE_SECURE', False), "
    "'csrf': getattr(s, 'CSRF_COOKIE_SECURE', False), "
    "'jwt': s.SIMPLE_JWT['AUTH_COOKIE_SECURE']}))"
)


def _cookies_secure(debug: str) -> dict:
    entorno = {**os.environ, "DEBUG": debug}
    entorno.pop("DJANGO_SETTINGS_MODULE", None)
    salida = subprocess.run(  # noqa: S603 — intérprete y argumentos propios, sin entrada externa
        [sys.executable, "-c", _LEER_SETTINGS],
        cwd=settings.BASE_DIR, env=entorno, capture_output=True, text=True, check=False,
    )
    if salida.returncode:
        raise AssertionError(salida.stderr[-2000:])
    return json.loads(salida.stdout.strip().splitlines()[-1])


class CookiesSegurasProduccionTestCase(SimpleTestCase):
    def test_cookies_dado_debug_0_cuando_carga_settings_entonces_sesion_csrf_y_jwt_son_secure(self):
        self.assertEqual(_cookies_secure("0"), {"session": True, "csrf": True, "jwt": True})

    def test_cookies_dado_debug_1_cuando_carga_settings_entonces_no_exigen_https(self):
        self.assertEqual(_cookies_secure("1"), {"session": False, "csrf": False, "jwt": False})
