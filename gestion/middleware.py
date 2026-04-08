import ipaddress
import logging
import threading

_local = threading.local()
logger = logging.getLogger(__name__)

# Redes de proxy de confianza — solo se confía en X-Forwarded-For
# si el request llega desde una de estas redes (Nginx interno de Docker).
# Ajustar según la configuración real de red de Docker Compose.
_TRUSTED_PROXY_NETWORKS = [
    ipaddress.ip_network('172.16.0.0/12'),   # Red bridge de Docker (172.16-31.x.x)
    ipaddress.ip_network('10.0.0.0/8'),       # Red privada clase A
    ipaddress.ip_network('192.168.0.0/16'),   # Red privada clase C
    ipaddress.ip_network('127.0.0.1/32'),     # Loopback
]


def _is_trusted_proxy(ip_str: str) -> bool:
    """Verifica si una IP pertenece a una red de proxy de confianza."""
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return any(ip in network for network in _TRUSTED_PROXY_NETWORKS)
    except ValueError:
        return False


def _extract_client_ip(request) -> str:
    """
    Extrae la IP real del cliente de forma segura.
    Solo confía en X-Forwarded-For si el request proviene de un proxy conocido.
    Previene IP spoofing desde clientes externos.
    """
    remote_addr = request.META.get('REMOTE_ADDR', '')
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()

    if forwarded_for and _is_trusted_proxy(remote_addr):
        # Tomar la primera IP de la cadena (la del cliente original)
        client_ip = forwarded_for.split(',')[0].strip()
        # Validar que sea una IP válida antes de usarla
        try:
            ipaddress.ip_address(client_ip)
            return client_ip
        except ValueError:
            logger.warning(
                "X-Forwarded-For contiene IP inválida: '%s' desde proxy %s",
                client_ip, remote_addr
            )

    return remote_addr


class AuditMiddleware:
    """
    Middleware para capturar la IP y el usuario de la petición actual,
    guardándolos en un thread local para su uso en los modelos durante
    la auditoría (AuditLog).

    Nota: usa threading.local() — compatible con WSGI (Gunicorn).
    Para ASGI (async) se requiere una implementación diferente.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.user = getattr(request, 'user', None)
        _local.ip_address = _extract_client_ip(request)

        try:
            response = self.get_response(request)
        finally:
            # Limpiar siempre, incluso si ocurre una excepción en la vista
            _local.__dict__.pop('user', None)
            _local.__dict__.pop('ip_address', None)

        return response


def get_current_user():
    return getattr(_local, 'user', None)


def get_current_ip():
    return getattr(_local, 'ip_address', None)


def set_cascade_justification(val):
    """Justificación para borrados en cascada (ej. DetalleFormula al borrar FormulaColor)."""
    _local.justificacion_cascade = val


def get_cascade_justification():
    return getattr(_local, 'justificacion_cascade', None)


def clear_cascade_justification():
    _local.__dict__.pop('justificacion_cascade', None)
