from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta
from django.conf import settings
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['groups'] = list(user.groups.values_list('name', flat=True))
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # --- Start of modification ---

            # Get user from serializer
            user = self.serializer.user
            
            # Serialize user data
            from .serializers import CustomUserSerializer
            user_serializer = CustomUserSerializer(user)
            
            # Get user's primary role
            role = user.groups.first().name if user.groups.exists() else None

            # Original tokens are in response.data, let's grab them
            access_token = response.data['access']
            refresh_token = response.data['refresh']

            # Now, overwrite response.data with the profile info
            response.data = {
                'user': user_serializer.data,
                'role': role
            }

            # Set cookies using the tokens we grabbed
            access_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
            refresh_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_REFRESH', 'refresh_token')
            secure_cookie = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_SECURE', False)
            samesite = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_SAMESITE', 'Lax')
            
            response.set_cookie(
                access_cookie_name,
                access_token,
                expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                httponly=True,
                samesite=samesite,
                secure=secure_cookie,
                path='/'
            )
            response.set_cookie(
                refresh_cookie_name,
                refresh_token,
                expires=settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'],
                httponly=True,
                samesite=samesite,
                secure=secure_cookie,
                path='/'
            )
            # --- End of modification ---
        
        return response

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_REFRESH', 'refresh_token')
        refresh_token = request.COOKIES.get(refresh_cookie_name)
        
        if not refresh_token:
            raise InvalidToken("No refresh token found in cookies.")

        request.data['refresh'] = refresh_token

        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken as e:
            response = Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
            access_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
            response.delete_cookie(access_cookie_name, path='/')
            response.delete_cookie(refresh_cookie_name, path='/')
            return response

        if response.status_code == 200:
            access_token = response.data['access']
            access_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
            secure_cookie = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_SECURE', False)
            samesite = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_SAMESITE', 'Lax')

            response.set_cookie(
                access_cookie_name,
                access_token,
                expires=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'],
                httponly=True,
                samesite=samesite,
                secure=secure_cookie,
                path='/'
            )
            # The new refresh token (if rotated) is already handled by the cookie middleware
            # if it's being used, or by the super().post() response.
            # For clarity, we can remove the access token from the response body.
            if 'access' in response.data:
                del response.data['access']

        return response

class LogoutView(APIView):
    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        access_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
        refresh_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_REFRESH', 'refresh_token')
        
        response.delete_cookie(access_cookie_name, path='/')
        response.delete_cookie(refresh_cookie_name, path='/')
        return response