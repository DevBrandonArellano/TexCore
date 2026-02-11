from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import CustomUserSerializer

def get_user_role(user):
    if user.is_superuser:
        return 'admin_sistemas' # Superusers are treated as system admins
    
    # Prioritize roles
    groups = user.groups.values_list('name', flat=True)
    if 'admin_sistemas' in groups:
        return 'admin_sistemas'
    if 'admin_sede' in groups:
        return 'admin_sede'
    if 'jefe_planta' in groups:
        return 'jefe_planta'
    if 'jefe_area' in groups:
        return 'jefe_area'
    if 'ejecutivo' in groups:
        return 'ejecutivo'
    if 'bodeguero' in groups:
        return 'bodeguero'
    if 'vendedor' in groups:
        return 'vendedor'
    if 'operario' in groups:
        return 'operario'
    if 'empaquetado' in groups:
        return 'empaquetado'
    if 'despacho' in groups:
        return 'despacho'
    
    return None

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = get_user_role(user)
        
        serializer = CustomUserSerializer(user)
        
        profile_data = {
            'user': serializer.data,
            'role': role
        }
        
        return Response(profile_data)
