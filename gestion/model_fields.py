"""
Campos de modelo con cifrado en reposo (RS-19).

`EncryptedCharField` y `EncryptedDateField` guardan el valor cifrado y lo entregan
descifrado: el resto del proyecto (serializers, vistas, plantillas de impresión) los
usa como el campo normal del que heredan, sin saber que están cifrados.

`BlindIndexField` guarda el índice ciego de otro campo del mismo modelo, para poder
buscar por igualdad y declarar unicidad en la base. Ver `gestion/crypto.py`.
"""

import logging

from django.core.exceptions import FieldError
from django.db import models

from gestion.crypto import ErrorDeCifrado, cifrar, descifrar, indice_ciego

logger = logging.getLogger(__name__)

__all__ = ["BlindIndexField", "EncryptedCharField", "EncryptedDateField"]


class _CampoCifradoMixin:
    """
    Parte común de los campos cifrados.

    La columna es `nvarchar(max)` (`get_internal_type` devuelve `TextField`) porque un
    token Fernet de un texto corto ya ocupa ~120 caracteres, pero el campo sigue siendo
    un `CharField`/`DateField` para Django, DRF y el admin: las validaciones de
    `max_length` y de formato de fecha se aplican sobre el valor **en claro**, antes de
    cifrar, igual que antes de este cambio.
    """

    # Los demás lookups no pueden funcionar: el texto cifrado de un mismo valor es
    # distinto en cada escritura (Fernet usa IV aleatorio), así que un `exact`,
    # `startswith` o `gt` devolvería siempre vacío en silencio.
    LOOKUPS_PERMITIDOS = frozenset({"isnull"})

    def get_internal_type(self):
        return "TextField"

    def _a_texto(self, value) -> str:
        raise NotImplementedError

    def from_db_value(self, value, expression, connection):
        if value is None:
            return None
        try:
            return self.to_python(descifrar(value))
        except ErrorDeCifrado:
            # Django no pasa la clave primaria a `from_db_value`: aquí solo hay modelo y
            # campo; la fila exacta la localiza `manage.py cifrar_datos_personales`.
            logger.exception("No se pudo leer %s.%s: dato cifrado ilegible.", self.model.__name__, self.name)
            raise

    def get_db_prep_value(self, value, connection, prepared=False):
        if value is None:
            return None
        return cifrar(self._a_texto(value))

    def get_lookup(self, lookup_name):
        if lookup_name not in self.LOOKUPS_PERMITIDOS:
            raise FieldError(
                f"'{self.model.__name__}.{self.name}' está cifrado en reposo: no admite el "
                f"lookup '{lookup_name}'. Para buscar por igualdad usa el índice ciego "
                f"(p. ej. `Cliente.objects.por_identificacion(valor)`); para filtrar por "
                f"rango, hazlo en Python sobre el conjunto ya acotado por otro campo."
            )
        return super().get_lookup(lookup_name)


class EncryptedCharField(_CampoCifradoMixin, models.CharField):
    """Texto corto cifrado en reposo. `max_length` valida el valor en claro."""

    def _a_texto(self, value) -> str:
        return str(value)


class EncryptedDateField(_CampoCifradoMixin, models.DateField):
    """Fecha cifrada en reposo. Se guarda como el ISO-8601 del día, cifrado."""

    def _a_texto(self, value) -> str:
        fecha = self.to_python(value)
        return fecha.isoformat()


class BlindIndexField(models.CharField):
    """
    Índice ciego (HMAC-SHA256) de otro campo del modelo.

    Se recalcula en `pre_save`, que es el único punto por el que pasan **todas** las
    escrituras de Django, `bulk_create` incluido; si se calculara solo en `save()` o en
    `clean()`, los comandos de carga masiva dejarían el índice vacío y romperían la
    unicidad. Un `queryset.update()` del campo de origen sí lo dejaría obsoleto: para
    eso está `manage.py cifrar_datos_personales --recalcular-indices`.
    """

    def __init__(self, *args, source_field: str = "", **kwargs):
        self.source_field = source_field
        kwargs.setdefault("max_length", 64)  # SHA-256 en hexadecimal
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["source_field"] = self.source_field
        return name, path, args, kwargs

    def calcular(self, model_instance) -> str:
        valor = getattr(model_instance, self.source_field, None)
        if valor is None or valor == "":
            return ""
        return indice_ciego(str(valor))

    def pre_save(self, model_instance, add):
        indice = self.calcular(model_instance)
        setattr(model_instance, self.attname, indice)
        return indice
