"""
URL configuration for TexCore project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.http import JsonResponse
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from gestion.custom_jwt_views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LogoutView
)


def health_check(request):
    """Endpoint de salud para CI/CD y load balancers (sin autenticación)."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    # 0. Health check — usado por CI/CD y Nginx
    path('api/health/', health_check, name='health_check'),
    # 1. Rutas de API y Admin
    path('admin/', admin.site.urls),
    path('api/inventory/', include('inventory.urls')),
    path('api/reporting/', include('inventory.urls_reporting')),
    path('api/scanning/', include('inventory.urls_scanning')),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', LogoutView.as_view(), name='token_logout'),
    path('api/', include('gestion.urls')),
    # 2. Internal API — comunicación servicio-a-servicio (JWT RS256)
    path('api/internal/v1/', include('internal_api.urls', namespace='internal_api')),
    # 3. Documentación OpenAPI (solo admins — ver SPECTACULAR_SETTINGS)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # 3. SPA React — captura todo lo demás. Excluye 'api/' a propósito: nginx
    # ya sirve index.html vía try_files para las rutas del SPA (Django no
    # tiene ese template en este setup, solo lo builda Vite); sin la
    # exclusión, cualquier request a 'api/...' que no matcheara ningún patrón
    # (ej. un código escaneado con caracteres inválidos) caía aquí e
    # intentaba renderizar 'index.html' -> TemplateDoesNotExist -> 500 en vez
    # de un 404 limpio.
    re_path(r'^(?!api/).*', TemplateView.as_view(template_name='index.html'), name='react_app_root'),
]
