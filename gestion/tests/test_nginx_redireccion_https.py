"""RNF-01: en producción el puerto 80 redirige a HTTPS (nginx).

La imagen de nginx es la misma en desarrollo y en producción: la redirección
se activa con NGINX_REDIRIGIR_HTTP=1, que solo declara el compose de producción.
Las pruebas leen los archivos de configuración; el comportamiento en el stack
se verifica con curl en el equipo con Docker.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): servicio nginx / server del puerto 80 / variables de nginx / healthcheck /
  envsubst.
"""

import re
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
# Plantilla de envsubst: el Dockerfile la copia a /etc/nginx/templates/.
PLANTILLA = BASE / "nginx" / "nginx.conf"
DOCKERFILE = BASE / "nginx" / "Dockerfile"
COMPOSE_PROD = BASE / "infrastructure" / "docker" / "docker-compose.prod.yml"
COMPOSE_DEV = BASE / "infrastructure" / "docker" / "docker-compose.yml"


def _entorno_nginx(ruta_compose):
    servicio = yaml.safe_load(ruta_compose.read_text(encoding="utf-8"))["services"]["nginx"]
    entorno = servicio.get("environment") or {}
    if isinstance(entorno, list):
        entorno = dict(item.split("=", 1) for item in entorno)
    return entorno


def _server_del_puerto_80(plantilla):
    inicio = plantilla.index("listen 80;")
    fin = plantilla.index("listen 443 ssl;")
    return plantilla[inicio:fin]


class RedireccionHttpComposeTest(SimpleTestCase):
    def test_compose_prod_dado_servicio_nginx_cuando_se_lee_entonces_activa_la_redireccion_http(self):
        self.assertEqual(str(_entorno_nginx(COMPOSE_PROD).get("NGINX_REDIRIGIR_HTTP")), "1")

    def test_compose_dev_dado_servicio_nginx_cuando_se_lee_entonces_no_activa_la_redireccion(self):
        self.assertNotEqual(str(_entorno_nginx(COMPOSE_DEV).get("NGINX_REDIRIGIR_HTTP", "0")), "1")


class RedireccionHttpPlantillaTest(SimpleTestCase):
    def test_plantilla_dado_server_del_puerto_80_cuando_bandera_vale_1_entonces_redirige_con_301_a_https(self):
        server_80 = _server_del_puerto_80(PLANTILLA.read_text(encoding="utf-8"))
        self.assertIn('set $redirigir_http "${NGINX_REDIRIGIR_HTTP}";', server_80)
        self.assertRegex(
            server_80,
            r'if \(\$redirigir_http = "1"\)\s*\{\s*return 301 https://\$host\$request_uri;\s*\}',
        )

    def test_plantilla_dado_variables_de_nginx_cuando_se_lee_entonces_solo_sustituye_las_que_empiezan_por_nginx(self):
        variables_de_entorno = set(re.findall(r"\$\{(\w+)\}", PLANTILLA.read_text(encoding="utf-8")))
        self.assertEqual(variables_de_entorno, {"NGINX_REDIRIGIR_HTTP"})


class RedireccionHttpDockerfileTest(SimpleTestCase):
    def setUp(self):
        self.dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    def test_dockerfile_nginx_dado_healthcheck_cuando_se_lee_entonces_sondea_por_https(self):
        self.assertIn("--no-check-certificate", self.dockerfile)
        self.assertIn("https://127.0.0.1/", self.dockerfile)
        self.assertNotIn("http://127.0.0.1/", self.dockerfile)

    def test_dockerfile_nginx_dado_envsubst_cuando_se_lee_entonces_filtra_solo_variables_nginx(self):
        self.assertIn("NGINX_ENVSUBST_FILTER=^NGINX_", self.dockerfile)
        self.assertIn("NGINX_REDIRIGIR_HTTP=0", self.dockerfile)
        self.assertIn("COPY nginx/nginx.conf /etc/nginx/templates/texcore.conf.template", self.dockerfile)
