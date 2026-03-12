import threading

_local = threading.local()

class AuditMiddleware:
    """
    Middleware para capturar la IP y el usuario de la petición actual,
    guardándolos en un thread local para su uso en los modelos durante
    la auditoría (AuditLog).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR')
        if ip:
            ip = ip.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        _local.user = getattr(request, 'user', None)
        _local.ip_address = ip

        response = self.get_response(request)

        # Cleanup
        if hasattr(_local, 'user'):
            del _local.user
        if hasattr(_local, 'ip_address'):
            del _local.ip_address

        return response

def get_current_user():
    return getattr(_local, 'user', None)

def get_current_ip():
    return getattr(_local, 'ip_address', None)
