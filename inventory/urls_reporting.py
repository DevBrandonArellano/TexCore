from django.urls import path, re_path
from .reporting_proxy import ReportingProxyView

urlpatterns = [
    # Capturar todo lo que venga después de /api/reporting/ y enviarlo al proxy
    re_path(r'^(?P<report_path>.*)$', ReportingProxyView.as_view(), name='reporting-proxy'),
]
