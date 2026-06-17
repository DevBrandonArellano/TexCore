"""
Migration inicial: crea la tabla internal_service_credential.
ISO 27001 A.9.2 — registro de identidades de microservicios.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ServiceCredential",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Nombre único del servicio (ej: scanning_service)",
                        max_length=100,
                        unique=True,
                    ),
                ),
                (
                    "secret_hash",
                    models.CharField(
                        help_text="Hash bcrypt del secret del servicio",
                        max_length=255,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Si False, el servicio no puede autenticarse",
                    ),
                ),
                (
                    "allowed_scopes",
                    models.JSONField(
                        default=list,
                        help_text='Ej: ["lotes:read", "reports:read"]',
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Service Credential",
                "verbose_name_plural": "Service Credentials",
                "db_table": "internal_service_credential",
            },
        ),
    ]
