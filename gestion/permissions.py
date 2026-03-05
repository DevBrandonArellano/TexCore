from rest_framework import permissions

class IsSystemAdmin(permissions.BasePermission):
    """
    Custom permission to only allow users who are staff
    or belong to the 'admin_sistemas' group.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # User is a superuser or staff
        if request.user.is_superuser or request.user.is_staff:
            return True
        
        # User belongs to the 'admin_sistemas' group
        return request.user.groups.filter(name='admin_sistemas').exists()


class IsTintorero(permissions.BasePermission):
    """
    Permiso que verifica si el usuario pertenece al grupo 'tintorero'.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name='tintorero').exists()


class IsTintoreroOrAdmin(permissions.BasePermission):
    """
    Permiso que otorga acceso a usuarios del grupo 'tintorero' o
    'admin_sistemas', asi como a superusuarios y staff.
    Utilizar en los ViewSets del modulo de formulas quimicas.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.is_superuser or request.user.is_staff:
            return True

        return request.user.groups.filter(
            name__in=['tintorero', 'admin_sistemas']
        ).exists()

