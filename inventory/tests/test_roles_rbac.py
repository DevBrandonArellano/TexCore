from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient
from rest_framework import status
from gestion.models import Sede, Area, Bodega

User = get_user_model()


class RBACMatrixTestCase(TestCase):
    """
    Suite de pruebas para verificar el Control de Acceso basado en Roles (RBAC).
    Verifica que cada grupo tenga acceso solo a los recursos permitidos.
    """

    def setUp(self):
        # Configuración de Sede y Áreas base
        self.sede = Sede.objects.create(nombre="Sede Norte", location="Quito")
        self.area_inv = Area.objects.create(nombre="Inventario", sede=self.sede)
        self.bodega = Bodega.objects.create(nombre="Bodega Principal", sede=self.sede)

        # Definición de Roles
        self.roles = [
            'admin_sistemas', 'admin_sede', 'jefe_planta', 'jefe_area',
            'ejecutivo', 'vendedor', 'bodeguero', 'operario',
            'empaquetado', 'despacho', 'tintorero'
        ]

        # Crear grupos y usuarios para cada rol
        self.users = {}
        for role in self.roles:
            group, _ = Group.objects.get_or_create(name=role)
            user = User.objects.create_user(
                username=f'user_{role}',
                password='password123',
                email=f'{role}@texcore.com'
            )
            user.groups.add(group)
            if role == 'admin_sistemas':
                user.is_superuser = True
                user.is_staff = True
            user.save()
            self.users[role] = user

        self.client = APIClient()

    def test_historial_despachos_access(self):
        """
        Matrix test para /api/inventory/historial-despachos/
        Permitidos: admin_sistemas, admin_sede, despacho, ejecutivo
        Denegados: Resto
        """
        allowed_roles = ['admin_sistemas', 'admin_sede', 'despacho', 'ejecutivo']
        url = '/api/inventory/historial-despachos/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            response = self.client.get(url)

            if role in allowed_roles:
                # 200 OK
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK,
                    f"Rol '{role}' DEBERÍA tener acceso a historial despachos pero recibió {response.status_code}"
                )
            else:
                # 403 Forbidden
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener acceso a historial despachos pero recibió {response.status_code}"
                )

    def test_stock_inventory_access(self):
        """
        Matrix test para /api/inventory/stock/
        Permitidos: Casi todos excepto operario raso (depende de implementación)
        Asumimos: Todos menos operario
        """
        denied_roles = ['operario']
        url = '/api/inventory/stock/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            response = self.client.get(url)

            if role in denied_roles:
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener acceso a stock"
                )
            else:
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK,
                    f"Rol '{role}' DEBERÍA tener acceso a stock"
                )

    def test_process_despacho_post_access(self):
        """
        Matrix test para /api/inventory/process-despacho/ (Endpoint crítico de escritura)
        Solo rol DESPACHO y ADMINS
        """
        allowed_roles = ['admin_sistemas', 'admin_sede', 'despacho']
        url = '/api/inventory/process-despacho/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            # Intentamos un POST (aunque falle por falta de data, el status code de permiso importa)
            response = self.client.post(url, {})

            if role in allowed_roles:
                # Esperamos 400 (Bad Request) o similar, pero NO 403
                self.assertNotEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' DEBERÍA tener permiso de ejecución en despacho"
                )
            else:
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener permiso de ejecución en despacho"
                )

    def test_unauthenticated_access(self):
        """Verifica que sin login no haya acceso a nada"""
        self.client.force_authenticate(user=None)
        endpoints = [
            '/api/inventory/historial-despachos/',
            '/api/inventory/stock/',
            '/api/inventory/process-despacho/',
            '/api/inventory/movimientos/',
            '/api/inventory/transferencias/',
            f'/api/inventory/bodegas/{self.bodega.id}/kardex/',
        ]
        for url in endpoints:
            response = self.client.get(url) if 'process' not in url and 'transferencias' not in url \
                else self.client.post(url)
            self.assertEqual(
                response.status_code, status.HTTP_401_UNAUTHORIZED,
                f"'{url}' debería exigir autenticación pero recibió {response.status_code}"
            )

    def test_movimientos_list_access(self):
        """
        Matrix test para GET /api/inventory/movimientos/
        Denegados: solo operario raso (IsInventoryStaffOrAdmin, misma política que /stock/)
        """
        denied_roles = ['operario']
        url = '/api/inventory/movimientos/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            response = self.client.get(url)

            if role in denied_roles:
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener acceso a movimientos"
                )
            else:
                self.assertEqual(
                    response.status_code, status.HTTP_200_OK,
                    f"Rol '{role}' DEBERÍA tener acceso a movimientos"
                )

    def test_movimientos_create_access(self):
        """
        Matrix test para POST /api/inventory/movimientos/ (escritura)
        Permitidos: bodeguero, jefe_area, jefe_planta, admin_sede, admin_sistemas
        """
        allowed_roles = ['admin_sistemas', 'admin_sede', 'jefe_planta', 'jefe_area', 'bodeguero']
        url = '/api/inventory/movimientos/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            response = self.client.post(url, {})

            if role in allowed_roles:
                self.assertNotEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' DEBERÍA tener permiso de escritura en movimientos"
                )
            else:
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener permiso de escritura en movimientos"
                )

    def test_transferencias_post_access(self):
        """
        Matrix test para POST /api/inventory/transferencias/ (escritura de stock)
        Mismo conjunto permitido que la escritura de movimientos.
        """
        allowed_roles = ['admin_sistemas', 'admin_sede', 'jefe_planta', 'jefe_area', 'bodeguero']
        url = '/api/inventory/transferencias/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            response = self.client.post(url, {})

            if role in allowed_roles:
                self.assertNotEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' DEBERÍA tener permiso de escritura en transferencias"
                )
            else:
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener permiso de escritura en transferencias"
                )

    def test_kardex_get_access(self):
        """
        Matrix test para GET /api/inventory/bodegas/{id}/kardex/ (lectura)
        Denegados: solo operario raso (misma política que /stock/ y /movimientos/).
        """
        denied_roles = ['operario']
        url = f'/api/inventory/bodegas/{self.bodega.id}/kardex/'

        for role in self.roles:
            self.client.force_authenticate(user=self.users[role])
            response = self.client.get(url)

            if role in denied_roles:
                self.assertEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' NO debería tener acceso al kardex"
                )
            else:
                self.assertNotEqual(
                    response.status_code, status.HTTP_403_FORBIDDEN,
                    f"Rol '{role}' DEBERÍA tener acceso al kardex"
                )
