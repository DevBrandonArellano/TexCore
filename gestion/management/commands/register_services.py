"""
Registra las credenciales de los microservicios en la BD (ServiceCredential).
Debe ejecutarse una sola vez tras el primer despliegue, o al rotar secrets.

Uso:
    python manage.py register_services

Los secrets se leen de las variables de entorno:
    SCANNING_SERVICE_SECRET
    REPORTING_SERVICE_SECRET
"""
import os

from django.core.management.base import BaseCommand, CommandError

from internal_api.models import ServiceCredential


SERVICES = [
    {
        "name": "scanning_service",
        "env_var": "SCANNING_SERVICE_SECRET",
        "scopes": ["lotes:read"],
    },
    {
        "name": "reporting_excel",
        "env_var": "REPORTING_SERVICE_SECRET",
        "scopes": ["reports:read"],
    },
]


class Command(BaseCommand):
    help = "Registra o actualiza las credenciales de los microservicios en la BD"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Actualiza el secret aunque el servicio ya exista",
        )

    def handle(self, *args, **options):
        force = options["force"]
        errors = []

        for svc in SERVICES:
            secret = os.environ.get(svc["env_var"])
            if not secret:
                errors.append(f"Variable de entorno '{svc['env_var']}' no definida")
                continue

            credential, created = ServiceCredential.objects.get_or_create(
                name=svc["name"],
                defaults={
                    "secret_hash": ServiceCredential.hash_secret(secret),
                    "allowed_scopes": svc["scopes"],
                    "is_active": True,
                },
            )

            if not created and force:
                credential.secret_hash = ServiceCredential.hash_secret(secret)
                credential.allowed_scopes = svc["scopes"]
                credential.is_active = True
                credential.save()
                self.stdout.write(self.style.WARNING(f"  Actualizado: {svc['name']}"))
            elif not created:
                self.stdout.write(f"  Ya existe (sin cambios): {svc['name']} — usa --force para actualizar")
            else:
                self.stdout.write(self.style.SUCCESS(f"  Creado: {svc['name']} con scopes {svc['scopes']}"))

        if errors:
            raise CommandError("\n".join(errors))

        self.stdout.write(self.style.SUCCESS("\nRegistro de servicios completado."))
