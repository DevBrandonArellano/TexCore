"""
Permisos para la API interna.
ISP: una clase por responsabilidad de permiso.
COBIT DSS06: control de acceso basado en scopes.
"""
import logging

from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class IsInternalService(BasePermission):
    """Permite acceso solo si el request fue autenticado como ServicePrincipal."""

    message = "Acceso restringido a servicios internos autenticados."

    def has_permission(self, request, view) -> bool:
        from internal_api.authentication import ServicePrincipal
        return isinstance(getattr(request, "user", None), ServicePrincipal)


class _ScopePermission(BasePermission):
    """Base de los permisos por scope: verifica que el ServicePrincipal tenga `required_scope`."""

    required_scope: str = ""

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "user", None)
        scopes = getattr(principal, "scopes", [])
        allowed = self.required_scope in scopes
        if not allowed:
            logger.warning(
                "Scope insuficiente para %s",
                getattr(principal, "service_name", "unknown"),
                extra={
                    "sd": {
                        "severity": 4,
                        "service": getattr(principal, "service_name", "unknown"),
                        "required_scope": self.required_scope,
                        "has_scopes": str(scopes),
                    }
                },
            )
        return allowed


def HasScope(required_scope: str) -> type[_ScopePermission]:
    """
    Crea la clase de permiso que exige `required_scope` al ServicePrincipal.
    Uso: permission_classes = [IsInternalService, HasScope('lotes:read')]

    Devuelve una CLASE, que es lo que DRF espera en permission_classes (las instancia
    en cada request) y lo que admiten los operadores `&`, `|` y `~`.
    """
    return type(
        f"HasScope[{required_scope}]",
        (_ScopePermission,),
        {"required_scope": required_scope, "__module__": __name__},
    )
