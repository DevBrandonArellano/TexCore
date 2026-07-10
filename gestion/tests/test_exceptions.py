"""
Pruebas de gestion/exceptions.py — texcore_exception_handler y _extract_message.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): ProtectedError (409), excepción no
  manejada por DRF (500), error de validación con campos (400).
- Caja blanca: rama DEBUG=True agrega 'detail' completo en errores >=500;
  _extract_message con string / lista / dict con 'detail' / dict con
  'non_field_errors' / dict con campo arbitrario.
"""
from unittest.mock import MagicMock

from django.db.models import ProtectedError
from django.test import TestCase, override_settings
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import APIView

from gestion.exceptions import _extract_message, texcore_exception_handler


class ExtractMessageTestCase(TestCase):
    def test_extract_message_dado_string_cuando_extrae_entonces_retorna_igual(self):
        self.assertEqual(_extract_message('mensaje simple'), 'mensaje simple')

    def test_extract_message_dado_lista_de_strings_cuando_extrae_entonces_primer_elemento(self):
        self.assertEqual(_extract_message(['primer error', 'segundo error']), 'primer error')

    def test_extract_message_dado_lista_vacia_cuando_extrae_entonces_string_generico(self):
        self.assertEqual(_extract_message([]), 'Error en la solicitud')

    def test_extract_message_dado_dict_con_detail_cuando_extrae_entonces_usa_detail(self):
        self.assertEqual(_extract_message({'detail': 'no encontrado'}), 'no encontrado')

    def test_extract_message_dado_dict_con_non_field_errors_cuando_extrae_entonces_los_usa(self):
        self.assertEqual(
            _extract_message({'non_field_errors': ['las contraseñas no coinciden']}),
            'las contraseñas no coinciden',
        )

    def test_extract_message_dado_dict_con_campo_arbitrario_cuando_extrae_entonces_incluye_nombre_campo(self):
        self.assertEqual(_extract_message({'nombre': ['este campo es requerido']}), 'nombre: este campo es requerido')

    def test_extract_message_dado_lista_de_dicts_cuando_extrae_entonces_recursivo(self):
        self.assertEqual(_extract_message([{'detail': 'error anidado'}]), 'error anidado')

    def test_extract_message_dado_tipo_no_reconocido_cuando_extrae_entonces_string_generico(self):
        self.assertEqual(_extract_message(42), 'Error en la solicitud')


class TexcoreExceptionHandlerTestCase(TestCase):
    def _context(self):
        view = MagicMock(spec=APIView)
        view.__class__.__name__ = 'FakeView'
        request = MagicMock()
        request.method = 'DELETE'
        request.path = '/api/fake/1/'
        return {'view': view, 'request': request}

    def test_handler_dado_protected_error_cuando_maneja_entonces_409(self):
        resp = texcore_exception_handler(ProtectedError('no se puede borrar', []), self._context())
        self.assertEqual(resp.status_code, 409)
        self.assertFalse(resp.data['success'])
        self.assertEqual(resp.data['error']['code'], 409)

    def test_handler_dado_excepcion_no_manejada_por_drf_cuando_maneja_entonces_500(self):
        resp = texcore_exception_handler(RuntimeError('fallo inesperado'), self._context())
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.data['error']['message'], 'Error interno del servidor')

    def test_handler_dado_validation_error_con_campos_cuando_maneja_entonces_400_con_fields(self):
        exc = ValidationError({'nombre': ['este campo es requerido']})
        resp = texcore_exception_handler(exc, self._context())
        self.assertEqual(resp.status_code, 400)
        self.assertIn('fields', resp.data['error'])
        self.assertIn('nombre', resp.data['error']['fields'])

    @override_settings(DEBUG=True)
    def test_handler_dado_debug_activo_y_apiexception_500_cuando_maneja_entonces_incluye_detalle(self):
        # Para llegar a la rama DEBUG hace falta una excepción que DRF SÍ
        # reconozca (response is not None) y cuyo status_code sea >= 500 —
        # una excepción genérica (RuntimeError) no es reconocida por DRF y
        # devuelve el 500 "hardcodeado" antes de llegar a este bloque.
        class FalloServicioExterno(APIException):
            status_code = 500
            default_detail = 'Servicio externo no disponible'

        resp = texcore_exception_handler(FalloServicioExterno(), self._context())
        self.assertEqual(resp.status_code, 500)
        self.assertIn('detail', resp.data['error'])

    def test_handler_dado_debug_inactivo_y_apiexception_500_cuando_maneja_entonces_no_incluye_detalle(self):
        class FalloServicioExterno(APIException):
            status_code = 500
            default_detail = 'Servicio externo no disponible'

        resp = texcore_exception_handler(FalloServicioExterno(), self._context())
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detail', resp.data['error'])
