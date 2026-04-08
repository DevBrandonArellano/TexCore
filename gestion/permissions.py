"""
Permisos de acceso para TexCore.

Usa make_group_permission() para eliminar la duplicación de código
que existía en 6 clases casi idénticas (principio DRY).
"""
from rest_framework import permissions


def make_group_permission(*group_names: str) -> type:
    """
    Factory para crear clases de permiso basadas en grupos de Django.

    Otorga acceso si el usuario:
    - Está autenticado, Y
    - Es superuser/staff, O pertenece a uno de los grupos especificados

    Uso:
        IsSystemAdmin = make_group_permission('admin_sistemas')
        IsTintoreroOrAdmin = make_group_permission('tintorero', 'admin_sistemas')
    """
    class GroupPermission(permissions.BasePermission):
        _groups = group_names

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            if request.user.is_superuser or request.user.is_staff:
                return True
            return request.user.groups.filter(name__in=self._groups).exists()

        def __repr__(self):
            return f"GroupPermission({', '.join(self._groups)})"

    GroupPermission.__name__ = f"GroupPermission({'_'.join(group_names)})"
    GroupPermission.__qualname__ = GroupPermission.__name__
    return GroupPermission


# Permisos del proyecto — definidos una sola vez
IsSystemAdmin         = make_group_permission('admin_sistemas')
IsTintorero           = make_group_permission('tintorero')
IsTintoreroOrAdmin    = make_group_permission('tintorero', 'admin_sistemas')
IsJefeArea            = make_group_permission('jefe_area')
IsJefeAreaOrAdmin     = make_group_permission('jefe_area', 'admin_sistemas', 'jefe_planta')
IsAdminSistemasOrSede = make_group_permission('admin_sistemas', 'admin_sede')
