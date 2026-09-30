"""
Pruebas de la configuración global de permisos de la API (TEX-07 CA-3, RNF-02).

La auditoría del backlog (24-sep-2026, hallazgo C-1) encontró que `/api/groups/`
quedaba pública porque DRF, sin DEFAULT_PERMISSION_CLASSES, aplica AllowAny:
la configuración fallaba en abierto. Estas pruebas fijan dos defensas:
1. El permiso por defecto exige autenticación (una vista nueva sin permisos
   queda cerrada, no abierta).
2. Toda vista del proyecto declara sus permisos explícitamente.

Técnicas ISTQB aplicadas:
- Caja blanca: recorrido de todas las rutas registradas en el resolver.
- Partición de equivalencia (EP): petición anónima a una ruta sin permisos propios.
"""
from django.test import TestCase
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.settings import api_settings
from rest_framework.test import APIClient
from rest_framework.views import APIView

APPS_DEL_PROYECTO = ('gestion.', 'inventory.', 'internal_api.')


def _recorrer_rutas(patrones, prefijo=''):
    for patron in patrones:
        if isinstance(patron, URLResolver):
            yield from _recorrer_rutas(patron.url_patterns, prefijo + str(patron.pattern))
        elif isinstance(patron, URLPattern):
            yield prefijo + str(patron.pattern), patron.callback


def _declara_permisos(clase_vista):
    for clase in clase_vista.__mro__:
        if clase is APIView:
            return False
        if 'permission_classes' in clase.__dict__ or 'get_permissions' in clase.__dict__:
            return True
    return False


class PermisosPorDefectoTestCase(TestCase):

    def test_api_dado_configuracion_global_cuando_se_inspecciona_entonces_exige_autenticacion(self):
        self.assertIn(IsAuthenticated, api_settings.DEFAULT_PERMISSION_CLASSES)

    def test_vistas_dado_codigo_del_proyecto_cuando_se_recorren_las_rutas_entonces_todas_declaran_permisos(self):
        sin_permisos = set()
        for ruta, callback in _recorrer_rutas(get_resolver().url_patterns):
            clase = getattr(callback, 'cls', None) or getattr(callback, 'view_class', None)
            if clase is None or not issubclass(clase, APIView):
                continue
            if clase.__module__.startswith(APPS_DEL_PROYECTO) and not _declara_permisos(clase):
                sin_permisos.add(f'{clase.__module__}.{clase.__name__} ({ruta})')
        self.assertEqual(sin_permisos, set(), 'Vistas sin permission_classes ni get_permissions')

    def test_raiz_api_dado_anonimo_cuando_get_entonces_rechaza(self):
        # La raíz del router no declara permisos: debe quedar cubierta por el valor por defecto.
        resp = APIClient().get('/api/inventory/')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
