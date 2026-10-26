from django.middleware.csrf import get_token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.permissions import ve_todas_las_sedes
from gestion.serializers import CustomUserSerializer


def get_user_role(user):
    if user.is_superuser:
        return "admin_sistemas"  # Los superusuarios se tratan como administradores del sistema

    # Prioriza los roles
    groups = user.groups.values_list("name", flat=True)
    if "admin_sistemas" in groups:
        return "admin_sistemas"
    if "admin_sede" in groups:
        return "admin_sede"
    if "jefe_planta" in groups:
        return "jefe_planta"
    if "jefe_area" in groups:
        return "jefe_area"
    if "tintorero" in groups:
        return "tintorero"
    if "ejecutivo" in groups:
        return "ejecutivo"
    if "bodeguero" in groups:
        return "bodeguero"
    if "vendedor" in groups:
        return "vendedor"
    if "operario" in groups:
        return "operario"
    if "empaquetado" in groups:
        return "empaquetado"
    if "despacho" in groups:
        return "despacho"

    return None


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = get_user_role(user)

        serializer = CustomUserSerializer(user)

        profile_data = {"user": serializer.data, "role": role}

        # El front pide el perfil al arrancar: aquí recibe la cookie `csrftoken` que
        # axios reenvía en `X-CSRFToken` con cada escritura (CookieJWTAuthentication).
        get_token(request)
        return Response(profile_data)


class VerificarSesionView(APIView):
    """
    Verificación de sesión para el `auth_request` de nginx (OWASP API2).

    El scanning_service no autentica usuarios: nginx consulta esta vista con la cookie
    del navegador antes de pasarle la petición. Sin sesión válida responde 401 y nginx
    corta ahí. Con sesión, 204 y la sede del usuario en cabeceras, que nginx reenvía al
    servicio para acotar la consulta del lote (OWASP API1).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        resp = Response(status=204)
        resp["X-Texcore-Sede-Id"] = str(user.sede_id or "")
        resp["X-Texcore-Ve-Todas"] = "1" if ve_todas_las_sedes(user) else "0"
        return resp
