from rest_framework import permissions

from gestion.permissions import GRUPOS_TODAS_LAS_SEDES, validar_misma_sede, validar_visible


def bodegas_visibles(user):
    """Bodegas que el usuario puede consultar u operar; None = todas.

    admin_sistemas/ejecutivo (y superuser) ven todas las sedes; admin_sede, las
    bodegas de su sede; el resto, solo sus bodegas asignadas.
    """
    from gestion.models import Bodega

    grupos = set(user.groups.values_list('name', flat=True))  # una sola consulta
    if user.is_superuser or grupos & set(GRUPOS_TODAS_LAS_SEDES):
        return None
    if 'admin_sede' in grupos:
        return Bodega.objects.filter(sede_id=user.sede_id) if user.sede_id else Bodega.objects.none()
    return user.bodegas_asignadas.all()


def validar_bodega_operable(user, bodega, campo):
    """OWASP A01 en escrituras de stock: la bodega donde sale o entra el stock
    es una que el usuario opera. Una ajena responde igual que una inexistente."""
    visibles = bodegas_visibles(user)
    if bodega is not None and visibles is not None:
        validar_visible(visibles, bodega, campo)


def validar_traslado(user, origen, destino, campo_destino):
    """Transferencias y transformaciones: el origen es operable por el usuario y
    el destino es de la sede del origen (no necesita estar asignado)."""
    validar_bodega_operable(user, origen, 'bodega_origen')
    validar_misma_sede(origen.sede_id, **{campo_destino: destino})


class IsDespachoReader(permissions.BasePermission):
    """
    Permiso para VER el historial de despachos.
    Permitidos: admin_sistemas, admin_sede, despacho, ejecutivo.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        allowed_groups = ['admin_sistemas', 'admin_sede', 'despacho', 'ejecutivo']
        return request.user.groups.filter(name__in=allowed_groups).exists()


class IsDespachoWriter(permissions.BasePermission):
    """
    Permiso para PROCESAR despachos (escritura).
    Permitidos: admin_sistemas, admin_sede, despacho.
    (Ejecutivo NO está permitido para procesar).
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        allowed_groups = ['admin_sistemas', 'admin_sede', 'despacho']
        return request.user.groups.filter(name__in=allowed_groups).exists()


class IsInventoryWriterOrAdmin(permissions.BasePermission):
    """
    Permiso para ESCRIBIR movimientos de inventario (crear/editar/eliminar).
    Permitidos: bodeguero, jefe_area, jefe_planta, admin_sede, admin_sistemas.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        allowed_groups = ['bodeguero', 'jefe_area', 'jefe_planta', 'admin_sede', 'admin_sistemas']
        return request.user.groups.filter(name__in=allowed_groups).exists()


class IsInventoryStaffOrAdmin(permissions.BasePermission):
    """
    Permiso para ver stock y movimientos generales.
    Excluye operarios de planta rasos del acceso a KPIs de inventario global.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        # Denegamos explícitamente a operarios rasos si no tienen otros roles
        groups = request.user.groups.values_list('name', flat=True)
        if 'operario' in groups and len(groups) == 1:
            return False

        return True
