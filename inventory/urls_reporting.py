from django.urls import path, re_path

from .reportes_async import DescargaReporteAsyncView, EstadoReporteAsyncView
from .reporting_proxy import ReportingProxyView

urlpatterns = [
    # Exportaciones encoladas en Celery (?async=true): antes del comodín del proxy.
    path("tareas/<str:token>/", EstadoReporteAsyncView.as_view(), name="reporte-async-estado"),
    path("tareas/<str:token>/descarga/", DescargaReporteAsyncView.as_view(), name="reporte-async-descarga"),
    # Capturar todo lo que venga después de /api/reporting/ y enviarlo al proxy
    re_path(r"^(?P<report_path>.*)$", ReportingProxyView.as_view(), name="reporting-proxy"),
]
