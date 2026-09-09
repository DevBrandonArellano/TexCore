from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
import logging
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


@method_decorator(csrf_exempt, name='dispatch')
class FrontendLogView(APIView):
    """
    Relay para logs del frontend. Recibe LogEntry (LogEntry.ts) via navigator.sendBeacon
    o fetch POST y los re-emite mediante el logger del backend en formato RFC 5424.
    """
    authentication_classes = []  # Permitir incluso sin sesión
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            entry = request.data
            if not isinstance(entry, dict):
                return Response(status=status.HTTP_400_BAD_REQUEST)

            severity = entry.get('severity', 6)
            msgid = entry.get('msgid', 'frontend').replace('.', '-')
            message = entry.get('message', '')
            sd = entry.get('sd', {})

            # Datos adicionales de contexto
            sd['source'] = 'browser'
            sd['ip'] = request.META.get('REMOTE_ADDR', 'unknown')

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

            f_logger.log(level, message, extra={'sd': sd})
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            # Fallo silencioso para el cliente, pero registrado en el backend.
            logger.warning("Error procesando log de frontend", exc_info=True)
            return Response(status=status.HTTP_400_BAD_REQUEST)
