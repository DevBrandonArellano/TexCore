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
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from inventory.reporting_proxy import ReportingProxyView
from gestion.custom_jwt_views import (
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    LogoutView
)

urlpatterns = [
    # 1. Rutas de API y Admin
    path('admin/', admin.site.urls),
    re_path(r'^api/reporting/(?P<report_path>.*)$', ReportingProxyView.as_view(), name='reporting-proxy-direct'),
    path('api/scanning/', include('inventory.urls_scanning')),
    path('api/inventory/', include('inventory.urls')),
    path('api/', include('gestion.urls')),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/logout/', LogoutView.as_view(), name='token_logout'),
    # 2. Documentación OpenAPI (solo admins — ver SPECTACULAR_SETTINGS)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # 3. SPA React — captura todo lo demás
    re_path(r'^.*', TemplateView.as_view(template_name='index.html'), name='react_app_root'),
]