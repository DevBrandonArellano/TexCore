import logging
from datetime import datetime, time, timedelta

from django.apps import apps
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from gestion.models import AuditableModelMixin, AuditLog
from gestion.views._common import parse_int_param, parse_rango_fechas
from inventory.serializers import AuditLogSerializer, nombre_de_tabla

logger = logging.getLogger("inventory.views")


class AuditLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AuditLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    # Solo listado: el detalle no tiene consumidor (Fase B, B6).
    queryset = AuditLog.objects.select_related("usuario", "content_type").all().order_by("-fecha_hora")
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        user = self.request.user
        qs = self.queryset
        grupos = set(user.groups.values_list("name", flat=True))

        # Solo admins pueden ver auditoría
        if not self._puede_ver_auditoria(user):
            return qs.none()

        # TEX-52 CA-1: rango de fechas y tipo de operación. Sin `fecha_desde` se muestran
        # los cambios del último mes (en BD se guardan todos).
        qs = self._filtrar_por_fecha_y_accion(qs, self.request.query_params)

        # Scope por rol:
        # - admin_sede: siempre restringido a su sede asignada.
        # - admin_sistemas/superuser: puede filtrar por sede_id opcional.
        # Ambas condiciones son columnas de gestion_auditlog con su índice: unir con el
        # usuario para leer su sede hacía del COUNT el 75 % de la CPU de SQL Server con
        # ~1 M de registros (prueba de carga 2026-10-06).
        if "admin_sede" in grupos and not (user.is_superuser or "admin_sistemas" in grupos):
            sede_id = getattr(user, "sede_id", None)
            if not sede_id:
                return qs.none()
        else:
            sede_id = parse_int_param(self.request.query_params.get("sede_id"), "sede_id")
        if sede_id:
            qs = qs.filter(Q(usuario_sede_id=sede_id) | Q(object_sede_id=sede_id))

        # Búsqueda de AuditLogViewer: usuario, tabla afectada o id del registro; no
        # recorre los JSON de valores.
        texto = (self.request.query_params.get("search") or "").strip()
        if texto:
            condicion = Q(usuario__username__icontains=texto) | Q(content_type__model__icontains=texto)
            if texto.isdigit():
                condicion |= Q(object_id=int(texto))
            qs = qs.filter(condicion)

        return qs

    @staticmethod
    def _filtrar_por_fecha_y_accion(qs, params):
        fecha_desde, fecha_hasta = parse_rango_fechas(params)
        # Rangos sobre fecha_hora (no `__date`) para que SQL Server use el índice
        # compuesto (sede, -fecha_hora); cada día completo en la zona horaria local.
        if fecha_desde:
            qs = qs.filter(fecha_hora__gte=timezone.make_aware(datetime.combine(fecha_desde, time.min)))
        elif not fecha_hasta:
            qs = qs.filter(fecha_hora__gte=timezone.now() - timedelta(days=30))
        if fecha_hasta:
            siguiente = timezone.make_aware(datetime.combine(fecha_hasta + timedelta(days=1), time.min))
            qs = qs.filter(fecha_hora__lt=siguiente)

        # Filtro por módulo: el nombre de la tabla afectada (ContentType.model).
        tabla = (params.get("tabla") or "").strip().lower()
        if tabla:
            qs = qs.filter(content_type__model=tabla)

        accion = (params.get("accion") or "").strip().upper()
        if accion:
            if accion not in dict(AuditLog.ACCION_CHOICES):
                raise ValidationError({"accion": "Use CREATE, UPDATE o DELETE."})
            qs = qs.filter(accion=accion)
        return qs

    @staticmethod
    def _puede_ver_auditoria(user):
        return user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "admin_sede"]).exists()

    @action(detail=False, methods=["get"], url_path="modulos", pagination_class=None)
    def modulos(self, request):
        """GET /inventory/audit-logs/modulos/ — módulos que se auditan, para el filtro por
        módulo del visor. Sale de los modelos auditados, sin recorrer la tabla de logs."""
        if not self._puede_ver_auditoria(request.user):
            raise PermissionDenied("Solo los administradores ven la auditoría.")
        modelos = {m._meta.model_name for m in _modelos_auditados()}
        datos = [{"valor": m, "etiqueta": nombre_de_tabla(m)} for m in modelos]
        return Response(sorted(datos, key=lambda d: d["etiqueta"]))


def _modelos_auditados():
    """Modelos con AuditableModelMixin y los que se auditan por señal (gestion.signals)."""
    from gestion.signals import modelos_auditados_por_senal

    propios = [m for m in apps.get_models() if issubclass(m, AuditableModelMixin)]
    return [*propios, *modelos_auditados_por_senal()]
