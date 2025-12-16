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

        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        token['groups'] = list(user.groups.values_list('id', flat=True))
        token['sede'] = user.sede.id if user.sede else None
        token['area'] = user.area.id if user.area else None
        
        return token

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            access_token = response.data.pop('access')
            refresh_token = response.data.pop('refresh')

            secure_cookie = getattr(settings, 'SECURE_SSL_REDIRECT', False)

            response.set_cookie(
                'access_token',
                access_token,
                max_age=timedelta(minutes=5).total_seconds(),
                httponly=True,
                samesite='Lax',
                secure=secure_cookie,
                path='/'
            )
            response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=timedelta(days=1).total_seconds(),
                httponly=True,
                samesite='Lax',
                secure=secure_cookie,
                path='/'
            )
        
        return response

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        
        if not refresh_token:
            raise InvalidToken("No refresh token found in cookies.")

        # Django's request.data is immutable, so we work on a mutable copy
        mutable_data = request.data.copy()
        mutable_data['refresh'] = refresh_token
        
        # Temporarily replace request.data
        original_data = request.data
        request._data = mutable_data

        try:
            response = super().post(request, *args, **kwargs)
        except InvalidToken as e:
            response = Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
            response.delete_cookie('access_token')
            response.delete_cookie('refresh_token')
            return response
        finally:
            # Restore original request data
            request._data = original_data

        if response.status_code == 200:
            access_token = response.data['access']
            
            secure_cookie = getattr(settings, 'SECURE_SSL_REDIRECT', False)

            response.set_cookie(
                'access_token',
                access_token,
                max_age=timedelta(minutes=5).total_seconds(),
                httponly=True,
                samesite='Lax',
                secure=secure_cookie,
                path='/'
            )
            del response.data['access']

        return response

class LogoutView(APIView):
    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/')
        return response