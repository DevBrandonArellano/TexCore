# Señales para auditoría y lógica de negocio
import datetime
import logging
import threading
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .middleware import get_current_ip, get_current_user
from .models import (
    Area,
    AuditLog,
    Bodega,
    CustomUser,
    DetallePedido,
    FaseReceta,
    LoteProduccion,
    Maquina,
    PagoCliente,
    ProcessStep,
    Proveedor,
    Sede,
    _get_object_sede_id,
)

logger = logging.getLogger("gestion.signals")


@receiver(post_save, sender=AuditLog)
def audit_log_saved(sender, instance, created, **kwargs):
    logger.info(
        "Evento de auditoría registrado",
        extra={
            "sd": {
                "entity": instance.__class__.__name__,
                "action": getattr(instance, "accion", "unknown"),
                "object_id": str(getattr(instance, "object_id", "")),
                "user": str(getattr(instance, "usuario", "")),
            }
        },
    )


# Usuarios recién creados en esta petición; evitar log UPDATE del segundo save() del serializer
_pending_skip_update = threading.local()


def _get_pending_skip():
    return getattr(_pending_skip_update, "user_ids", set())


def _mark_created_and_skip_next_update(pk):
    s = _get_pending_skip()
    s.add(pk)
    _pending_skip_update.user_ids = s


def _should_skip_update(pk):
    s = _get_pending_skip()
    if pk in s:
        s.discard(pk)
        _pending_skip_update.user_ids = s
        return True
    return False


CAMPOS_AUDITABLES_USER = [
    "username",
    "first_name",
    "last_name",
    "email",
    "is_active",
    "is_staff",
    "sede_id",
    "area_id",
    "date_of_birth",
]

# RS-19: datos personales que se auditan sin guardar su valor. `AuditLog` es
# inmutable y no está cifrado, así que escribir la fecha de nacimiento en claro ahí
# anularía el cifrado del campo. Se guarda su HMAC: cambia cuando el dato cambia
# —que es lo que la auditoría necesita demostrar— y no revela la fecha.
CAMPOS_USER_SIN_VALOR_EN_AUDITORIA = frozenset({"date_of_birth"})


def _valor_redactado(val):
    """HMAC truncado del valor, para auditar el cambio sin registrar el dato."""
    from gestion.crypto import indice_ciego

    if val is None:
        return None
    return f"hmac:{indice_ciego(str(val))[:16]}"


def _get_user_audit_data(instance):
    """Extrae datos auditables del usuario (solo PKs para FKs)."""
    data = {}
    for field in CAMPOS_AUDITABLES_USER:
        try:
            val = getattr(instance, field, None)
            if field in CAMPOS_USER_SIN_VALOR_EN_AUDITORIA:
                data[field] = _valor_redactado(val)
            elif val is not None and hasattr(val, "pk"):
                data[field] = val.pk
            elif hasattr(val, "isoformat"):  # date/datetime
                data[field] = str(val)
            else:
                data[field] = val
        except Exception:
            logger.warning(
                "No se pudo extraer campo '%s' para auditoría de usuario (pk=%s)",
                field,
                getattr(instance, "pk", "?"),
                exc_info=True,
            )
    return data


@receiver(post_save, sender=CustomUser)
def audit_user_save(sender, instance, created, **kwargs):
    """Registra creación y actualización de usuarios en auditoría."""
    if kwargs.get("raw"):  # Skip en loaddata / fixtures
        return
    user = get_current_user()
    user_inst = user if user and getattr(user, "is_authenticated", False) else None
    ip = get_current_ip()
    ct = ContentType.objects.get_for_model(CustomUser)
    data = _get_user_audit_data(instance)

    object_sede_id = _get_object_sede_id(instance)
    if created:
        _mark_created_and_skip_next_update(instance.pk)
        AuditLog.objects.create(
            usuario=user_inst,
            ip_address=ip,
            content_type=ct,
            object_id=instance.pk,
            object_sede_id=object_sede_id,
            accion="CREATE",
            valor_anterior=None,
            valor_nuevo=data,
            justificacion="",
        )
    else:
        if _should_skip_update(instance.pk):
            return
        AuditLog.objects.create(
            usuario=user_inst,
            ip_address=ip,
            content_type=ct,
            object_id=instance.pk,
            object_sede_id=object_sede_id,
            accion="UPDATE",
            valor_anterior={},  # No disponible en post_save
            valor_nuevo=data,
            justificacion="",
        )


@receiver(pre_delete, sender=CustomUser)
def audit_user_delete(sender, instance, **kwargs):
    """Registra eliminación de usuarios en auditoría."""
    user = get_current_user()
    user_inst = user if user and getattr(user, "is_authenticated", False) else None
    ip = get_current_ip()
    ct = ContentType.objects.get_for_model(CustomUser)
    pk = instance.pk
    data = _get_user_audit_data(instance)
    object_sede_id = _get_object_sede_id(instance)

    AuditLog.objects.create(
        usuario=user_inst,
        ip_address=ip,
        content_type=ct,
        object_id=pk,
        object_sede_id=object_sede_id,
        accion="DELETE",
        valor_anterior=data,
        valor_nuevo=None,
        justificacion="",
    )
    logger.warning(
        "Objeto eliminado del sistema", extra={"sd": {"entity": sender.__name__, "object_id": str(instance.pk)}}
    )


def _get_model_audit_data(instance, exclude_fields=("id", "fecha_creacion", "fecha_modificacion")):
    """Extrae datos auditables de cualquier modelo (solo campos normales, no M2M)."""
    data = {}
    for f in instance._meta.fields:
        if f.name in exclude_fields:
            continue
        try:
            val = getattr(instance, f.name, None)
            if isinstance(val, models.Model):
                data[f.name] = val.pk
            elif isinstance(val, (Decimal, datetime.datetime, datetime.date)):
                data[f.name] = str(val)
            else:
                data[f.name] = val
        except Exception:
            logger.warning(
                "No se pudo extraer campo '%s' para auditoría de %s (pk=%s)",
                f.name,
                type(instance).__name__,
                getattr(instance, "pk", "?"),
                exc_info=True,
            )
    return data


def _create_audit_for_model(sender, instance, created, raw=False, **kwargs):
    """Handler genérico post_save para modelos de Gestión."""
    if raw:
        return
    user = get_current_user()
    user_inst = user if user and getattr(user, "is_authenticated", False) else None
    ip = get_current_ip()
    ct = ContentType.objects.get_for_model(sender)
    data = _get_model_audit_data(instance)
    object_sede_id = _get_object_sede_id(instance)
    AuditLog.objects.create(
        usuario=user_inst,
        ip_address=ip,
        content_type=ct,
        object_id=instance.pk,
        object_sede_id=object_sede_id,
        accion="CREATE" if created else "UPDATE",
        valor_anterior=None if created else {},
        valor_nuevo=data,
        justificacion="",
    )


def _delete_audit_for_model(sender, instance, **kwargs):
    """Handler genérico pre_delete para modelos de Gestión."""
    user = get_current_user()
    user_inst = user if user and getattr(user, "is_authenticated", False) else None
    ip = get_current_ip()
    ct = ContentType.objects.get_for_model(sender)
    pk = instance.pk
    data = _get_model_audit_data(instance)
    object_sede_id = _get_object_sede_id(instance)
    AuditLog.objects.create(
        usuario=user_inst,
        ip_address=ip,
        content_type=ct,
        object_id=pk,
        object_sede_id=object_sede_id,
        accion="DELETE",
        valor_anterior=data,
        valor_nuevo=None,
        justificacion="",
    )
    logger.warning(
        "Objeto eliminado del sistema", extra={"sd": {"entity": sender.__name__, "object_id": str(instance.pk)}}
    )


# Registrar señales para modelos de Gestión
_MODELOS_AUDITABLES_GESTION = [
    Sede,
    Area,
    Proveedor,
    Bodega,
    Maquina,
    ProcessStep,
    FaseReceta,
    PagoCliente,
    LoteProduccion,
    DetallePedido,
]
for _model in _MODELOS_AUDITABLES_GESTION:
    post_save.connect(_create_audit_for_model, sender=_model)
    pre_delete.connect(_delete_audit_for_model, sender=_model)

# Registrar señales para modelos de Inventario


def _register_inventory_signals():
    from inventory.models import HistorialDespacho, MRPEjecucion

    # Del MRP se audita cada ejecución (quién, cuándo, resultado), no cada requerimiento o
    # sugerencia: son datos calculados que la ejecución siguiente reemplaza (ADR-012).
    for _model in [HistorialDespacho, MRPEjecucion]:
        post_save.connect(_create_audit_for_model, sender=_model)
        pre_delete.connect(_delete_audit_for_model, sender=_model)


_register_inventory_signals()
