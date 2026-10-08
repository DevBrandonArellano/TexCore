"""Helpers y mixins compartidos por los módulos de vistas de gestion/."""
from django.utils.dateparse import parse_date
from rest_framework.exceptions import ValidationError


def parse_int_param(value, field_name):
    """
    Valida un query param usado como ID entero positivo (OWASP A03).

    Retorna int, o None si el valor viene vacío/ausente. Lanza
    ValidationError (→ HTTP 400 controlado) si el valor no es un entero
    válido, evitando un 500 no controlado al pasar '?area=abc' a un
    queryset `.filter(id=...)`.
    """
    if value in (None, ''):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValidationError({field_name: f"'{value}' no es un identificador válido."}) from None
    if parsed <= 0:
        raise ValidationError({field_name: "El identificador debe ser un entero positivo."})
    return parsed


def parse_date_param(params, nombre):
    """Query param de fecha `YYYY-MM-DD` (OWASP A03): None si viene vacío; 400 si no es
    una fecha válida (formato incorrecto o día inexistente, p. ej. 2026-02-30)."""
    crudo = params.get(nombre)
    if not crudo:
        return None
    try:
        fecha = parse_date(crudo)
    except ValueError:
        fecha = None
    if not fecha:
        raise ValidationError({nombre: 'Formato de fecha inválido (usar YYYY-MM-DD).'})
    return fecha


def parse_rango_fechas(params, desde='fecha_desde', hasta='fecha_hasta'):
    """Par (desde, hasta) validado: cada fecha con parse_date_param y el orden del rango."""
    fecha_desde = parse_date_param(params, desde)
    fecha_hasta = parse_date_param(params, hasta)
    if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
        raise ValidationError({desde: f'{desde} no puede ser posterior a {hasta}.'})
    return fecha_desde, fecha_hasta


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
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            save_kwargs['sede'] = user.sede
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
        justificacion = self.request.query_params.get('_justificacion_auditoria') or \
            self.request.headers.get('X-Justificacion-Auditoria') or \
            self.request.data.get('_justificacion_auditoria')
        if not justificacion:
            justificacion = "Eliminación desde panel de administración"
        instance._justificacion_auditoria = justificacion
        set_cascade_justification(justificacion)
        try:
            instance.delete()
        finally:
            clear_cascade_justification()
