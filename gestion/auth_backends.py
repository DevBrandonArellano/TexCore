from django.conf import settings
from rest_framework.authentication import CSRFCheck
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """
    Backend de autenticación que lee el JWT desde una cookie httponly
    en lugar del header Authorization.
    """

    def authenticate(self, request):
        cookie_name = getattr(settings, "SIMPLE_JWT", {}).get("AUTH_COOKIE", "access_token")
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
        except (InvalidToken, TokenError):
            # Token inválido, expirado o en blacklist — el usuario no está autenticado
            return None
        # El navegador envía la cookie sola en cualquier petición a la API, también desde
        # otra página: una escritura exige además el token CSRF en `X-CSRFToken` (Zero
        # Trust, OWASP A01). Los métodos seguros (GET, HEAD, OPTIONS) no lo piden.
        self.enforce_csrf(request)
        return user, validated_token

    @staticmethod
    def enforce_csrf(request):
        """La misma comprobación que `SessionAuthentication.enforce_csrf` de DRF."""

        def dummy_get_response(request):  # pragma: no cover — CsrfViewMiddleware la exige
            return None

        # CSRFCheck de DRF devuelve el motivo en texto en vez de una respuesta HTML.
        check = CSRFCheck(dummy_get_response)
        check.process_request(request)
        reason = check.process_view(request, None, (), {})
        if reason:
            raise PermissionDenied(f"CSRF Failed: {reason}")
