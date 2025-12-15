from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['groups'] = list(user.groups.values_list('id', flat=True))
        token['sede'] = user.sede.id if user.sede else None
        token['area'] = user.area.id if user.area else None
        
        # You can add permissions here if needed
        # token['permissions'] = list(user.get_all_permissions())

        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
