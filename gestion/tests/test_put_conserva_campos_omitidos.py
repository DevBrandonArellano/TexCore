"""
DRF 3.16 da `default=None` a los campos anulables que forman parte de un unique_together
(p. ej. `sede`, `area`). En un PUT que los omite, ese default los dejaba en NULL: el registro
salía del filtro multi-tenant de su sede (bug hallado en FormulaColorWriteSerializer, CHANGELOG
24-sep-2026). ConservarOmitidosEnPutMixin restaura la semántica previa: lo omitido se conserva.

Técnicas ISTQB: partición de equivalencia (EP) — campo omitido / enviado con valor / enviado
como null; PUT frente a PATCH.
"""
from django.test import RequestFactory, TestCase

from gestion.serializers.catalog_serializers import ProductoSerializer, ProveedorSerializer
from gestion.serializers.production_serializers import MaquinaSerializer, OrdenProduccionSerializer
from gestion.serializers.sales_serializers import ClienteSerializer
from gestion.tests.factories import (
    AreaFactory, ClienteFactory, CustomUserFactory, MaquinaFactory, OrdenProduccionFactory, ProductoFactory,
    ProveedorFactory,
    SedeFactory,
)

# (serializer, factory, campo anulable del unique_together)
CASOS = [
    (ProductoSerializer, ProductoFactory, 'sede'),
    (ProveedorSerializer, ProveedorFactory, 'sede'),
    (ClienteSerializer, ClienteFactory, 'sede'),
    (OrdenProduccionSerializer, OrdenProduccionFactory, 'sede'),
    (MaquinaSerializer, MaquinaFactory, 'area'),
]


class PutConservaCamposOmitidosTestCase(TestCase):

    def setUp(self):
        self.request = RequestFactory().put('/')
        self.request.user = CustomUserFactory(groups=['admin_sistemas'])

    def _put(self, serializer_cls, instancia, cambios=None, quitar=None, partial=False):
        datos = dict(serializer_cls(instancia).data)
        if quitar:
            datos.pop(quitar)
        # Cliente es registro crítico: modificarlo exige justificación (los demás la ignoran)
        datos['_justificacion_auditoria'] = 'Prueba de PUT sin el campo de sede'
        datos.update(cambios or {})
        s = serializer_cls(instancia, data=datos, partial=partial, context={'request': self.request})
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        instancia.refresh_from_db()
        return instancia

    def test_put_dado_campo_omitido_cuando_guarda_entonces_conserva_el_valor_actual(self):
        for serializer_cls, factory, campo in CASOS:
            with self.subTest(serializer=serializer_cls.__name__):
                instancia = factory()
                original = getattr(instancia, f'{campo}_id')
                self.assertIsNotNone(original)
                instancia = self._put(serializer_cls, instancia, quitar=campo)
                self.assertEqual(getattr(instancia, f'{campo}_id'), original)

    def test_put_dado_campo_enviado_con_otro_valor_cuando_guarda_entonces_lo_cambia(self):
        instancia = ProductoFactory()
        otra_sede = SedeFactory()
        instancia = self._put(ProductoSerializer, instancia, cambios={'sede': otra_sede.id})
        self.assertEqual(instancia.sede, otra_sede)

    def test_put_dado_campo_enviado_como_null_cuando_guarda_entonces_lo_anula(self):
        # Enviar null explícito sigue siendo una decisión del cliente
        instancia = MaquinaFactory()
        instancia = self._put(MaquinaSerializer, instancia, cambios={'area': None})
        self.assertIsNone(instancia.area)

    def test_patch_dado_campo_omitido_cuando_guarda_entonces_conserva_el_valor_actual(self):
        instancia = MaquinaFactory(area=AreaFactory())
        area = instancia.area_id
        s = MaquinaSerializer(instancia, data={'nombre': 'Renombrada'}, partial=True)
        self.assertTrue(s.is_valid(), s.errors)
        s.save()
        instancia.refresh_from_db()
        self.assertEqual((instancia.nombre, instancia.area_id), ('Renombrada', area))
