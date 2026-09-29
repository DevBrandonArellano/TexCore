"""
Permisos de acceso para TexCore.

Usa make_group_permission() para eliminar la duplicación de código
que existía en 6 clases casi idénticas (principio DRY).
"""
from django.db.models import Q
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
IsSystemAdmin = make_group_permission('admin_sistemas')
IsTintorero = make_group_permission('tintorero')
IsTintoreroOrAdmin = make_group_permission('tintorero', 'admin_sistemas')
IsJefeArea = make_group_permission('jefe_area')
IsJefeAreaOrAdmin = make_group_permission('jefe_area', 'admin_sistemas', 'jefe_planta')
IsAdminSistemasOrSede = make_group_permission('admin_sistemas', 'admin_sede')
# Gestión de catálogos operativos: administradores y bodegueros pueden mantener
# productos, insumos y químicos usados por inventario.
IsCatalogManager = make_group_permission('bodeguero', 'admin_sistemas', 'admin_sede')
# Gestión de pagos de clientes (P0-017, ISO 27001 A.9.4): solo roles del
# dominio comercial — el filtrado por cliente asignado se aplica en get_queryset
IsVendedorOrEjecutivoOrAdmin = make_group_permission('vendedor', 'ejecutivo', 'admin_sistemas', 'admin_sede')
# Recepción de materia prima (F0-001): bodegueros y administradores
IsBodegueroOrAdmin = make_group_permission('bodeguero', 'admin_sistemas', 'admin_sede')
# Transferencias interárea: solo Jefe de Planta y administradores las crean
IsJefePlantaOrAdmin = make_group_permission('jefe_planta', 'admin_sistemas', 'admin_sede')
# Operarios: operan máquinas y registran transformaciones de su área
IsOperario = make_group_permission('operario')
# Registro de transformaciones máquina a máquina: Jefe de Área, Operario y admins.
# El Bodeguero queda EXCLUIDO: solo gestiona movimientos de bodega, no transforma.
IsJefeAreaOrOperarioOrAdmin = make_group_permission(
    'jefe_area', 'operario', 'jefe_planta', 'admin_sistemas', 'admin_sede'
)
# Registro de lotes (OperarioDashboard, ManageOrdenesProduccion, EmpaquetadoDashboard).
# El alcance por área/sede de cada rol se valida en la vista.
IsRegistroLoteRole = make_group_permission(
    'operario', 'jefe_area', 'jefe_planta', 'empaquetado', 'admin_sistemas', 'admin_sede'
)

# Trazabilidad lote → materias primas: expone proveedores y costos de compra.
IsTrazabilidadCostosRole = make_group_permission(
    'bodeguero', 'jefe_planta', 'ejecutivo', 'admin_sistemas', 'admin_sede'
)

GRUPOS_TODAS_LAS_SEDES = ('admin_sistemas', 'ejecutivo')


def ve_todas_las_sedes(user) -> bool:
    """Multi-tenancy (OWASP A01): superuser, admin_sistemas y ejecutivo ven todas las sedes."""
    return user.is_superuser or user.groups.filter(name__in=GRUPOS_TODAS_LAS_SEDES).exists()


def filtrar_por_sede(qs, user, campo='sede'):
    """Acota `qs` a la sede del usuario salvo que vea todas. Sin sede no ve nada
    (filtrar por sede=None traería justamente los registros sin sede)."""
    if ve_todas_las_sedes(user):
        return qs
    if not user.sede_id:
        return qs.none()
    return qs.filter(**{f'{campo}_id': user.sede_id})


def filtrar_lotes_por_sede(qs, user):
    """La sede de un lote es la de su orden o, sin orden (corridas MES), la de su
    producto — misma regla que LoteProduccion.save()."""
    if ve_todas_las_sedes(user):
        return qs
    if not user.sede_id:
        return qs.none()
    return qs.filter(
        Q(orden_produccion__sede_id=user.sede_id)
        | Q(orden_produccion__isnull=True, producto__sede_id=user.sede_id)
    )
