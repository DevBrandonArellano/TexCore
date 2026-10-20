import logging
import re

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from gestion.middleware import _extract_client_ip

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger("gestion.views")

# Límites del relay público de logs (RNF-02 / OWASP API4).
MSGID_VALIDO = re.compile(r"[A-Za-z0-9_-]{1,40}")
LARGO_MENSAJE = 2000
CLAVES_SD = 20
LARGO_CLAVE_SD = 40
LARGO_VALOR_SD = 200


def _una_linea(texto, largo):
    """Texto en una sola línea y recortado: un salto de línea falsificaría otra entrada del log."""
    return re.sub(r"[\r\n\x00-\x1f\x7f]+", " ", str(texto))[:largo]


class FrontendLogThrottle(SimpleRateThrottle):
    """Límite por IP del cliente real (la misma regla anti-spoofing del AuditMiddleware)."""

    scope = "frontend_logs"
    rate = "120/min"

    def get_rate(self):
        return self.rate

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": _extract_client_ip(request) or "unknown"}


@method_decorator(csrf_exempt, name="dispatch")
class FrontendLogView(APIView):
    """
    Relay para logs del frontend. Recibe LogEntry (LogEntry.ts) via navigator.sendBeacon
    o fetch POST y los re-emite mediante el logger del backend en formato RFC 5424.

    Es pública porque el frontend también registra errores antes de iniciar sesión, así que
    acota lo que acepta: `msgid` con caracteres y largo fijos (cada valor distinto crea un
    logger que Python no libera), mensaje y `sd` en una línea y recortados, y límite por IP.
    """

    authentication_classes = []  # Permitir incluso sin sesión
    permission_classes = [AllowAny]
    throttle_classes = [FrontendLogThrottle]

    def post(self, request):
        try:
            entry = request.data
            if not isinstance(entry, dict):
                return Response(status=status.HTTP_400_BAD_REQUEST)

            try:
                severity = int(entry.get("severity", 6))
            except (TypeError, ValueError):
                severity = 6
            msgid = str(entry.get("msgid", "frontend")).replace(".", "-")
            if not MSGID_VALIDO.fullmatch(msgid):
                msgid = "frontend"
            message = _una_linea(entry.get("message", ""), LARGO_MENSAJE)
            sd_cliente = entry.get("sd", {})
            if not isinstance(sd_cliente, dict):
                logger.warning("Log de frontend rechazado: 'sd' no es un objeto")
                return Response(status=status.HTTP_400_BAD_REQUEST)
            sd = {
                _una_linea(k, LARGO_CLAVE_SD): _una_linea(v, LARGO_VALOR_SD)
                for k, v in list(sd_cliente.items())[:CLAVES_SD]
            }

            # Datos adicionales de contexto
            sd["source"] = "browser"
            # IP real detrás de Nginx, con la misma regla anti-spoofing del AuditMiddleware.
            sd["ip"] = _extract_client_ip(request) or "unknown"

            f_logger = logging.getLogger(f"frontend.{msgid}")

            # Mapeo RFC 5424 -> Python levels
            if severity <= 2:
                level = logging.CRITICAL
            elif severity == 3:
                level = logging.ERROR
            elif severity == 4:
                level = logging.WARNING
            elif severity >= 5:
                level = logging.INFO
            else:
                level = logging.DEBUG

            f_logger.log(level, message, extra={"sd": sd})
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            # Fallo silencioso para el cliente, pero registrado en el backend.
            logger.warning("Error procesando log de frontend", exc_info=True)
            return Response(status=status.HTTP_400_BAD_REQUEST)
