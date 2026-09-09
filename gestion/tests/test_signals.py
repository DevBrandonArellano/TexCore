"""
Tests de gestion/signals.py — helpers puros de extracción de datos de auditoría.

Bajo: _get_user_audit_data y _get_model_audit_data descartaban en silencio
cualquier campo cuya extracción reventara (except Exception: pass, sin log),
así que un registro de auditoría podía quedar incompleto sin que nadie lo notara.

No requieren BD: son funciones puras sobre un objeto con la forma esperada
(no hace falta un modelo Django real ni factories).
"""
from django.test import TestCase

from gestion.signals import _get_model_audit_data, _get_user_audit_data


class _FakeUsuarioConCampoRoto:
    """Objeto con la forma de CustomUser, cuyo 'sede_id' revienta al leerlo."""
    pk = 1
    username = 'user1'
    first_name = 'Ana'
    last_name = 'Perez'
    email = 'ana@test.com'
    is_active = True
    is_staff = False
    area_id = 2
    date_of_birth = None

    @property
    def sede_id(self):
        raise RuntimeError('boom')


class GetUserAuditDataTestCase(TestCase):

    def test_dado_campo_que_revienta_cuando_extrae_entonces_lo_omite_y_loguea(self):
        with self.assertLogs('gestion.signals', level='WARNING') as cm:
            data = _get_user_audit_data(_FakeUsuarioConCampoRoto())
        self.assertNotIn('sede_id', data)
        self.assertEqual(data['username'], 'user1')
        self.assertTrue(any('sede_id' in msg for msg in cm.output))

    def test_dado_instancia_sin_campos_rotos_cuando_extrae_entonces_incluye_todos_los_campos(self):
        class _UsuarioOk(_FakeUsuarioConCampoRoto):
            sede_id = 5

        data = _get_user_audit_data(_UsuarioOk())
        self.assertEqual(data['sede_id'], 5)
        self.assertEqual(data['username'], 'user1')


class _FakeField:
    def __init__(self, name):
        self.name = name


class _FakeMeta:
    fields = [_FakeField('id'), _FakeField('nombre'), _FakeField('codigo')]


class _FakeModeloConCampoRoto:
    """Objeto con la forma de una instancia de modelo Django, 'codigo' revienta."""
    _meta = _FakeMeta()
    pk = 7
    id = 7
    nombre = 'Bodega Test'

    @property
    def codigo(self):
        raise RuntimeError('boom')


class GetModelAuditDataTestCase(TestCase):

    def test_dado_campo_que_revienta_cuando_extrae_entonces_lo_omite_y_loguea(self):
        with self.assertLogs('gestion.signals', level='WARNING') as cm:
            data = _get_model_audit_data(_FakeModeloConCampoRoto())
        self.assertNotIn('codigo', data)
        self.assertEqual(data['nombre'], 'Bodega Test')
        self.assertTrue(any('codigo' in msg for msg in cm.output))
