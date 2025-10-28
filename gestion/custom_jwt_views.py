from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Add custom claims
        data['username'] = self.user.username
        data['email'] = self.user.email

        # Add user's groups
        data['groups'] = [group.name for group in self.user.groups.all()]

        # Add user's permissions (codenames)
        data['permissions'] = [str(p) for p in self.user.get_all_permissions()]

        return data

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer