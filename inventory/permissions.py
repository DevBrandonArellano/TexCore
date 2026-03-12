from rest_framework import permissions

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
