"""
ServiceCredential: identidad de un microservicio autorizado.
ISO 27001 A.9.2 — Gestión de información de autenticación secreta.
SRP: única responsabilidad — almacenar y verificar credenciales de servicio.
"""
from django.contrib.auth.hashers import make_password
from django.db import models


class ServiceCredential(models.Model):
    """Representa la identidad de un microservicio que consume la API interna."""

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre único del servicio (ej: scanning_service)",
    )
    secret_hash = models.CharField(
        max_length=255,
        help_text="Hash bcrypt del secret del servicio",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Si False, el servicio no puede autenticarse",
    )
    allowed_scopes = models.JSONField(
        default=list,
        help_text='Ej: ["lotes:read", "reports:read"]',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "internal_service_credential"
        verbose_name = "Service Credential"
        verbose_name_plural = "Service Credentials"

    def __str__(self) -> str:
        status = "activo" if self.is_active else "inactivo"
        return f"{self.name} ({status})"

    @staticmethod
    def hash_secret(plain_secret: str) -> str:
        """Genera hash seguro del secret usando el hasher de Django (PBKDF2/bcrypt)."""
        return make_password(plain_secret)
