"""
Pruebas de gestion/serializers/inventory_serializers.py — BodegaSerializer.

Serializer ejercitado unitariamente (sin cliente HTTP): sin dependencias
externas, solo ORM. Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): create/update con y sin justificación de
  auditoría, con y sin usuarios asignados.
"""
from django.test import TestCase

from gestion.serializers.inventory_serializers import BodegaSerializer
from gestion.tests.factories import BodegaFactory, CustomUserFactory, SedeFactory


class BodegaSerializerCreateTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()

    def test_create_dado_justificacion_auditoria_cuando_guarda_entonces_la_asigna_a_la_instancia(self):
        serializer = BodegaSerializer(data={
            'nombre': 'Bodega Central', 'sede': self.sede.id,
            '_justificacion_auditoria': 'Alta inicial de bodega',
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertEqual(bodega._justificacion_auditoria, 'Alta inicial de bodega')

    def test_create_dado_usuarios_asignados_cuando_guarda_entonces_los_setea(self):
        u1 = CustomUserFactory(sede=self.sede)
        u2 = CustomUserFactory(sede=self.sede)
        serializer = BodegaSerializer(data={
            'nombre': 'Bodega con usuarios', 'sede': self.sede.id,
            'usuarios_asignados': [u1.id, u2.id],
        })
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertCountEqual(
            bodega.usuarios_asignados.values_list('id', flat=True), [u1.id, u2.id],
        )

    def test_create_dado_sin_justificacion_ni_usuarios_cuando_guarda_entonces_crea_bodega_simple(self):
        serializer = BodegaSerializer(data={'nombre': 'Bodega Simple', 'sede': self.sede.id})
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertEqual(bodega.nombre, 'Bodega Simple')
        self.assertEqual(bodega.usuarios_asignados.count(), 0)


class BodegaSerializerUpdateTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede, nombre='Original')

    def test_update_dado_nuevo_nombre_cuando_guarda_entonces_lo_persiste(self):
        serializer = BodegaSerializer(
            self.bodega, data={'nombre': 'Renombrada', 'sede': self.sede.id}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertEqual(bodega.nombre, 'Renombrada')

    def test_update_dado_justificacion_auditoria_cuando_guarda_entonces_la_asigna_a_la_instancia(self):
        serializer = BodegaSerializer(
            self.bodega,
            data={'nombre': 'Original', '_justificacion_auditoria': 'Cambio de nombre autorizado'},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertEqual(bodega._justificacion_auditoria, 'Cambio de nombre autorizado')

    def test_update_dado_usuarios_asignados_cuando_guarda_entonces_reemplaza_el_conjunto(self):
        u1 = CustomUserFactory(sede=self.sede)
        self.bodega.usuarios_asignados.set([CustomUserFactory(sede=self.sede)])
        serializer = BodegaSerializer(
            self.bodega, data={'usuarios_asignados': [u1.id]}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertCountEqual(
            bodega.usuarios_asignados.values_list('id', flat=True), [u1.id],
        )

    def test_update_dado_usuarios_asignados_ausente_cuando_guarda_entonces_no_toca_el_conjunto(self):
        u1 = CustomUserFactory(sede=self.sede)
        self.bodega.usuarios_asignados.set([u1])
        serializer = BodegaSerializer(
            self.bodega, data={'nombre': 'Otro nombre'}, partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        bodega = serializer.save()
        self.assertCountEqual(
            bodega.usuarios_asignados.values_list('id', flat=True), [u1.id],
        )
