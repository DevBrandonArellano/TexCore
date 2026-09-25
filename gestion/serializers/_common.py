import re

from rest_framework.fields import empty

ALPHANUMERIC_ACCENTS_REGEX = re.compile(r'^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$')


class ConservarOmitidosEnPutMixin:
    """DRF 3.16 da `default=None` a los campos anulables de un unique_together (p. ej. `sede`,
    `area`): en un PUT que los omite, el default los dejaba en NULL y el registro salía del
    filtro multi-tenant de su sede. Aquí un campo omitido conserva su valor actual, como antes
    de DRF 3.16; enviarlo con valor (o null explícito) sigue cambiándolo. Se resuelve en
    to_internal_value para que el UniqueTogetherValidator valide contra el valor real."""

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        if self.instance is None or self.partial:
            return attrs
        for nombre, campo in self.fields.items():
            if (campo.read_only or nombre in data or campo.source not in attrs
                    or getattr(campo, 'default', empty) is not None):
                continue
            attrs[campo.source] = getattr(self.instance, campo.source)
        return attrs
