"""
Management command: crea ServiceCredentials para los microservicios si no existen.
Ejecutar en entrypoint.sh después de migrate.
ISO 27001 A.9.2: gestión de identidades de servicios.
"""
import os

from django.core.management.base import BaseCommand

from internal_api.models import ServiceCredential


class Command(BaseCommand):
    help = "Crea credenciales de servicio para scanning_service y reporting_excel"

    def handle(self, *args, **options):
        services = [
            (
                "scanning_service",
                os.environ.get("SCANNING_SERVICE_SECRET", ""),
                ["lotes:read"],
            ),
            (
                "reporting_excel",
                os.environ.get("REPORTING_SERVICE_SECRET", ""),
                ["reports:read"],
            ),
        ]
        for name, secret, scopes in services:
            if not secret:
                self.stdout.write(
                    self.style.WARNING(
                        f"Sin secret configurado para '{name}' — saltando. "
                        f"Revisar {name.upper().replace('_', '_')}_SERVICE_SECRET en .env"
                    )
                )
                continue

            obj, created = ServiceCredential.objects.get_or_create(
                name=name,
                defaults={
                    "secret_hash": ServiceCredential.hash_secret(secret),
                    "allowed_scopes": scopes,
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Credencial creada: {name} (scopes: {scopes})")
                )
            else:
                self.stdout.write(f"  Ya existe: {name} (sin cambios)")
