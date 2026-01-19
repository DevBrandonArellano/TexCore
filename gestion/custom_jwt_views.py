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
        # We process the serializer ourselves to have access to the user object
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except InvalidToken as e:
            raise InvalidToken(e.args[0])

        # At this point, serializer.validated_data contains 'access' and 'refresh'
        # and serializer.user is populated.
        
        user = serializer.user
        
        # Serialize user data
        from .serializers import CustomUserSerializer
        from .profile_views import get_user_role
        user_serializer = CustomUserSerializer(user)
        
        # Get user's primary role
        role = get_user_role(user)

        # Get tokens from validated data
        access_token = serializer.validated_data['access']
        refresh_token = serializer.validated_data['refresh']

        # Construct the response
        response_data = {
            'user': user_serializer.data,
            'role': role
        }
        
        # Depending on settings, you might want to include tokens in the body or not.
        # The previous code implied we want to overwrite response.data completely.
        # But usually you want them in cookies AND maybe body if you weren't using cookies only.
        # Given the previous code, we overwrite response.data entirely.
        
        response = Response(response_data, status=status.HTTP_200_OK)

        # Set cookies
        access_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
        refresh_cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_REFRESH', 'refresh_token')
        secure_cookie = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_SECURE', False)
        samesite = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE_SAMESITE', 'Lax')
        
        response.set_cookie(
            access_cookie_name,
            access_token,
            max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            samesite=samesite,
            secure=secure_cookie,
            path='/'
        )
        response.set_cookie(
            refresh_cookie_name,
            refresh_token,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            httponly=True,
            samesite=samesite,
            secure=secure_cookie,
            path='/'
        )

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
                max_age=int(settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()),
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