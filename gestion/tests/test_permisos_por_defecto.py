"""
Regresión del hallazgo crítico C-1 (auditoría backlog vs. código, 2026-09-24):
`/api/groups/` quedaba expuesto sin autenticación porque `GroupViewSet` no
declaraba permisos y `REST_FRAMEWORK` no definía `DEFAULT_PERMISSION_CLASSES`
(DRF aplica `AllowAny` por defecto).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): anónimo / autenticado sin rol administrativo /
  admin_sistemas, sobre lectura y escritura.
- Caja blanca (CB-D): configuración por defecto de DRF y recorrido de todas las
  rutas del proyecto para comprobar que cada vista declara sus permisos.
"""
from django.conf import settings
from django.test import TestCase
from django.urls import get_resolver, reverse
from django.urls.resolvers import URLPattern, URLResolver
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.views import APIView

from gestion.tests.factories import CustomUserFactory

APPS_PROPIAS = ('gestion', 'inventory', 'internal_api', 'TexCore')


def _iterar_patrones(patrones):
    for p in patrones:
        if isinstance(p, URLResolver):
            yield from _iterar_patrones(p.url_patterns)
        elif isinstance(p, URLPattern):
            yield p


def _es_vista_de_funcion(cls):
    """True si la clase la generó @api_view para una vista de función.

    DRF crea la clase con type('WrappedAPIView', ...) y luego reasigna
    `__name__` y `__module__` a los de la función, pero `__qualname__` queda
    como 'WrappedAPIView'. No sirve mirar `__module__`: ya apunta al módulo
    propio de la vista.
    """
    return cls.__qualname__.endswith('WrappedAPIView')


def _declara_permisos(cls):
    """True si la vista declara permission_classes o get_permissions propios."""
    if _es_vista_de_funcion(cls):
        # @api_view siempre escribe permission_classes en el __dict__ de la
        # clase generada (sin @permission_classes copia el objeto por defecto
        # de APIView), así que el recorrido del MRO daría un falso negativo.
        # Solo cuenta como declarado si @permission_classes lo sustituyó.
        return cls.permission_classes is not APIView.permission_classes
    for k in cls.__mro__:
        if not k.__module__.startswith(APPS_PROPIAS):
            continue
        if 'get_permissions' in k.__dict__:
            return True
        if 'permission_classes' in k.__dict__:
            return True
    return False


class GroupViewSetPermisosTestCase(TestCase):
    """Seis pruebas: anónimo o sin rol administrativo no consulta ni modifica grupos."""

    def setUp(self):
        self.client = APIClient()
        self.url_list = reverse('group-list')

    def test_list_dado_anonimo_cuando_get_entonces_rechazado(self):
        resp = self.client.get(self.url_list)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_create_dado_anonimo_cuando_post_entonces_rechazado_sin_crear(self):
        from django.contrib.auth.models import Group
        antes = Group.objects.count()
        resp = self.client.post(self.url_list, {'name': 'intruso'}, format='json')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertEqual(Group.objects.count(), antes)

    def test_delete_dado_anonimo_cuando_delete_entonces_rechazado_sin_borrar(self):
        from django.contrib.auth.models import Group
        grupo = Group.objects.create(name='grupo_protegido')
        resp = self.client.delete(reverse('group-detail', args=[grupo.id]))
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        self.assertTrue(Group.objects.filter(id=grupo.id).exists())

    def test_list_dado_rol_no_administrativo_cuando_get_entonces_403(self):
        self.client.force_authenticate(user=CustomUserFactory(groups=['vendedor']))
        resp = self.client.get(self.url_list)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dado_rol_no_administrativo_cuando_post_entonces_403(self):
        self.client.force_authenticate(user=CustomUserFactory(groups=['jefe_planta']))
        resp = self.client.post(self.url_list, {'name': 'escalada'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_dado_admin_sede_cuando_patch_entonces_403_sin_modificar(self):
        from django.contrib.auth.models import Group
        grupo = Group.objects.create(name='grupo_original')
        self.client.force_authenticate(user=CustomUserFactory(groups=['admin_sede']))
        resp = self.client.patch(reverse('group-detail', args=[grupo.id]), {'name': 'alterado'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        grupo.refresh_from_db()
        self.assertEqual(grupo.name, 'grupo_original')


class PermisoPorDefectoTestCase(TestCase):
    """Cuatro pruebas: configuración segura por defecto, raíz del router y recorrido de rutas."""

    def test_configuracion_dado_settings_cuando_se_lee_entonces_exige_autenticacion(self):
        defaults = settings.REST_FRAMEWORK.get('DEFAULT_PERMISSION_CLASSES', ())
        self.assertIn('rest_framework.permissions.IsAuthenticated', defaults)

    def test_vista_sin_permisos_dado_anonimo_cuando_get_entonces_rechazado(self):
        from rest_framework.response import Response
        from rest_framework.test import APIRequestFactory

        class VistaSinPermisos(APIView):
            def get(self, request):
                return Response({'ok': True})

        request = APIRequestFactory().get('/vista-sin-permisos/')
        resp = VistaSinPermisos.as_view()(request)
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_rutas_dado_todas_las_vistas_del_proyecto_cuando_se_recorren_entonces_declaran_permisos(self):
        sin_permisos = set()
        for patron in _iterar_patrones(get_resolver().url_patterns):
            cls = getattr(patron.callback, 'cls', None) or getattr(patron.callback, 'view_class', None)
            if cls is None or not issubclass(cls, APIView):
                continue
            # Las vistas @api_view heredan el __module__ de la función, así que
            # este filtro también las cubre.
            if not cls.__module__.startswith(APPS_PROPIAS):
                continue
            if not _declara_permisos(cls):
                sin_permisos.add(f'{cls.__module__}.{cls.__name__} ({patron.pattern})')
        self.assertEqual(sorted(sin_permisos), [], 'Vistas sin permisos declarados')

    def test_raiz_api_dado_anonimo_cuando_get_entonces_rechazado(self):
        # La raíz del router no declara permisos: debe quedar cubierta por el valor por defecto.
        resp = APIClient().get('/api/inventory/')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
