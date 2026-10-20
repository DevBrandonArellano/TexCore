"""
RS-19 — Cifrado en reposo de los datos personales (LOPDP 2021, ISO/IEC 27001).

Cifra `Cliente.ruc_cedula` y `CustomUser.date_of_birth`, y añade el índice ciego
`Cliente.ruc_cedula_hash` para conservar la búsqueda por igualdad y la unicidad
(RUC + sede), que ya no pueden ir sobre la columna cifrada: Fernet usa un IV
aleatorio, así que un mismo RUC produce un texto distinto en cada escritura.

Estrategia, por campo: columna nueva → copia cifrada de los datos → se borra la
columna en claro → se renombra la nueva con el nombre original. Se hace así, y no con
un `AlterField` sobre la columna existente, porque el `ALTER COLUMN` dejaría el texto
en claro dentro de la columna nueva y la conversión de `date` a texto en SQL Server
depende del estilo de `CONVERT`. Leyendo con el ORM antes de borrar la columna, el
valor llega como `str`/`date` de Python y el formato es explícito.

Requiere `FIELD_ENCRYPTION_KEYS` y `BLIND_INDEX_KEY` en el entorno. Tómese el respaldo
previo de costumbre: el paso que borra las columnas en claro no se puede revertir con
`migrate gestion 0003_squashed_0009_paromaquina_origen` (ver
docs/arquitectura/CIFRADO_DATOS_PERSONALES.md).
"""

from django.db import migrations

import gestion.model_fields
from gestion.crypto import indice_ciego

LOTE = 500


def _en_lotes(queryset, campos, transformar):
    """Recorre el queryset en lotes y escribe `campos` con `bulk_update`."""
    pendientes = []
    for obj in queryset.iterator(chunk_size=LOTE):
        transformar(obj)
        pendientes.append(obj)
        if len(pendientes) >= LOTE:
            queryset.model.objects.bulk_update(pendientes, campos)
            pendientes = []
    if pendientes:
        queryset.model.objects.bulk_update(pendientes, campos)


def cifrar_clientes(apps, schema_editor):
    """Copia `ruc_cedula` (en claro) a la columna cifrada y calcula el índice ciego."""
    Cliente = apps.get_model("gestion", "Cliente")

    def transformar(cliente):
        valor = (cliente.ruc_cedula or "").strip()
        # La asignación guarda el valor en claro en memoria; el cifrado lo hace
        # `EncryptedCharField.get_db_prep_value()` al escribir en la base.
        cliente.ruc_cedula_cifrado = valor
        cliente.ruc_cedula_hash = indice_ciego(valor) if valor else ""

    _en_lotes(
        Cliente.objects.all().only("id", "ruc_cedula"),
        ["ruc_cedula_cifrado", "ruc_cedula_hash"],
        transformar,
    )


def descifrar_clientes(apps, schema_editor):
    """Inversa de `cifrar_clientes`: devuelve el valor en claro a la columna original."""
    Cliente = apps.get_model("gestion", "Cliente")

    def transformar(cliente):
        cliente.ruc_cedula = cliente.ruc_cedula_cifrado or ""

    _en_lotes(Cliente.objects.all(), ["ruc_cedula"], transformar)


def cifrar_fechas_nacimiento(apps, schema_editor):
    CustomUser = apps.get_model("gestion", "CustomUser")

    def transformar(usuario):
        usuario.date_of_birth_cifrado = usuario.date_of_birth

    _en_lotes(
        CustomUser.objects.exclude(date_of_birth__isnull=True).only("id", "date_of_birth"),
        ["date_of_birth_cifrado"],
        transformar,
    )


def descifrar_fechas_nacimiento(apps, schema_editor):
    CustomUser = apps.get_model("gestion", "CustomUser")

    def transformar(usuario):
        usuario.date_of_birth = usuario.date_of_birth_cifrado

    # `isnull` explícito: es el único lookup que `EncryptedDateField` admite.
    _en_lotes(
        CustomUser.objects.exclude(date_of_birth_cifrado__isnull=True),
        ["date_of_birth"],
        transformar,
    )


class Migration(migrations.Migration):
    dependencies = [("gestion", "0003_squashed_0009_paromaquina_origen")]

    operations = [
        # ── Cliente.ruc_cedula ────────────────────────────────────────────────
        migrations.AddField(
            model_name="cliente",
            name="ruc_cedula_cifrado",
            field=gestion.model_fields.EncryptedCharField(max_length=20, null=True, verbose_name="RUC o cédula"),
        ),
        migrations.AddField(
            model_name="cliente",
            name="ruc_cedula_hash",
            field=gestion.model_fields.BlindIndexField(
                db_index=True,
                editable=False,
                max_length=64,
                null=True,
                source_field="ruc_cedula",
                verbose_name="índice de la identificación",
            ),
        ),
        # La unicidad vieja apunta a la columna que se va a borrar: se retira primero.
        migrations.AlterUniqueTogether(name="cliente", unique_together=set()),
        migrations.RunPython(cifrar_clientes, descifrar_clientes),
        migrations.RemoveField(model_name="cliente", name="ruc_cedula"),
        migrations.RenameField(model_name="cliente", old_name="ruc_cedula_cifrado", new_name="ruc_cedula"),
        migrations.AlterField(
            model_name="cliente",
            name="ruc_cedula",
            field=gestion.model_fields.EncryptedCharField(max_length=20, verbose_name="RUC o cédula"),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="ruc_cedula_hash",
            field=gestion.model_fields.BlindIndexField(
                db_index=True,
                editable=False,
                max_length=64,
                source_field="ruc_cedula",
                verbose_name="índice de la identificación",
            ),
        ),
        migrations.AlterUniqueTogether(name="cliente", unique_together={("ruc_cedula_hash", "sede")}),
        # ── CustomUser.date_of_birth ──────────────────────────────────────────
        migrations.AddField(
            model_name="customuser",
            name="date_of_birth_cifrado",
            field=gestion.model_fields.EncryptedDateField(blank=True, null=True),
        ),
        migrations.RunPython(cifrar_fechas_nacimiento, descifrar_fechas_nacimiento),
        migrations.RemoveField(model_name="customuser", name="date_of_birth"),
        migrations.RenameField(
            model_name="customuser", old_name="date_of_birth_cifrado", new_name="date_of_birth"
        ),
    ]
