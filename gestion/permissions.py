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
