"""Helpers y mixins compartidos por los módulos de vistas de gestion/."""

# El parseo de parámetros vive en `gestion/params.py`, que no depende de las vistas: así lo
# pueden usar también los servicios sin cerrar un círculo de imports. Se reexporta aquí para
# que los módulos de vistas lo sigan importando de un solo sitio.
from gestion.params import parse_date_param, parse_int_param, parse_rango_fechas

__all__ = ["parse_date_param", "parse_int_param", "parse_rango_fechas"]


class SedeAutoAssignMixin:
    """
    Auto-asigna sede=user.sede en perform_create si el serializer no la trae
    explícitamente. DRY (barrido de higiene Fase 5.3) — antes duplicado byte a
    byte en ChemicalViewSet, ProductoViewSet, ProveedorViewSet, BodegaViewSet,
    ClienteViewSet y (con kwargs extra) FormulaColorViewSet.

    Subclases con kwargs adicionales al guardar (p. ej. creado_por en
    FormulaColorViewSet, vendedor_asignado condicional en ClienteViewSet)
    sobreescriben get_perform_create_extra_kwargs() en vez de perform_create().
    """

    def get_perform_create_extra_kwargs(self, serializer):
        return {}

    def perform_create(self, serializer):
        user = self.request.user
        save_kwargs = self.get_perform_create_extra_kwargs(serializer)
        if not serializer.validated_data.get("sede") and hasattr(user, "sede") and user.sede:
            save_kwargs["sede"] = user.sede
        serializer.save(**save_kwargs)


class AuditedDestroyMixin:
    """
    perform_destroy con justificación de auditoría (query param, header o
    body — en ese orden), con motivo genérico de fallback. DRY (barrido de
    higiene Fase 5.3) — antes duplicado byte a byte (o funcionalmente
    idéntico, con la misma cadena `or` reescrita en 2 pasos) en
    ProductoViewSet, ProveedorViewSet, BodegaViewSet, ClienteViewSet y
    FormulaColorViewSet.
    """

    def perform_destroy(self, instance):
        from gestion.middleware import clear_cascade_justification, set_cascade_justification

        justificacion = (
            self.request.query_params.get("_justificacion_auditoria")
            or self.request.headers.get("X-Justificacion-Auditoria")
            or self.request.data.get("_justificacion_auditoria")
        )
        if not justificacion:
            justificacion = "Eliminación desde panel de administración"
        instance._justificacion_auditoria = justificacion
        set_cascade_justification(justificacion)
        try:
            instance.delete()
        finally:
            clear_cascade_justification()
