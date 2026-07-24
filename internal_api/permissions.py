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


class HasScope(BasePermission):
    """
    Verifica que el ServicePrincipal tiene el scope requerido.
    Uso: permission_classes = [IsInternalService, HasScope('lotes:read')]
    """

    def __init__(self, required_scope: str) -> None:
        self.required_scope = required_scope

    def __call__(self):
        return self

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
