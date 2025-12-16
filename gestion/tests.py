from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from .models import Sede, Producto, Area, CustomUser # Import CustomUser
from django.contrib.auth.models import Group # Import Group
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, NotFound, AuthenticationFailed # Import AuthenticationFailed
from django.http import Http404


# Original tests (re-added)
class SedeAPITestCase(APITestCase):
    def setUp(self):
        self.sede1 = Sede.objects.create(nombre='Sede Principal', location='Ubicacion 1', status='activo')
        self.sede2 = Sede.objects.create(nombre='Sede Secundaria', location='Ubicacion 2', status='activo')

    def test_list_sedes(self):
        """Ensure we can list all sedes."""
        url = reverse('sede-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_retrieve_sede(self):
        """Ensure we can retrieve a single sede."""
        url = reverse('sede-detail', args=[self.sede1.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre'], self.sede1.nombre)

    def test_create_sede(self):
        """Ensure we can create a new sede."""
        url = reverse('sede-list')
        data = {'nombre': 'Sede Nueva', 'location': 'Ubicacion Nueva', 'status': 'activo'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Sede.objects.count(), 3)
        self.assertEqual(Sede.objects.get(id=response.data['id']).nombre, 'Sede Nueva')

    def test_update_sede(self):
        """Ensure we can update an existing sede."""
        url = reverse('sede-detail', args=[self.sede1.id])
        data = {'nombre': 'Sede Principal Actualizada'}
        response = self.client.patch(url, data, format='json') # Use patch for partial update
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.sede1.refresh_from_db()
        self.assertEqual(self.sede1.nombre, 'Sede Principal Actualizada')

    def test_delete_sede(self):
        """Ensure we can delete a sede."""
        url = reverse('sede-detail', args=[self.sede1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Sede.objects.count(), 1)


class ProductoAPITestCase(APITestCase):
    def setUp(self):
        self.producto1 = Producto.objects.create(
            codigo='P001',
            descripcion='Hilo de Algodon',
            tipo='hilo',
            unidad_medida='kg'
        )

    def test_list_productos(self):
        """Ensure we can list all productos."""
        url = reverse('producto-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_producto(self):
        """Ensure we can create a new producto."""
        url = reverse('producto-list')
        data = {
            'codigo': 'P002',
            'descripcion': 'Tela de Poliester',
            'tipo': 'tela',
            'unidad_medida': 'metros'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Producto.objects.count(), 2)
        self.assertEqual(Producto.objects.get(id=response.data['id']).codigo, 'P002')


class AreaAPITestCase(APITestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede de Pruebas', location='Ubicacion', status='activo')
        self.area1 = Area.objects.create(nombre='Area 1', sede=self.sede)

    def test_list_areas(self):
        """Ensure we can list all areas."""
        url = reverse('area-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_area(self):
        """Ensure we can create a new area linked to a sede."""
        url = reverse('area-list')
        data = {'nombre': 'Area 2', 'sede': self.sede.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Area.objects.count(), 2)
        self.assertEqual(response.data['nombre'], 'Area 2')
        self.assertEqual(response.data['sede'], self.sede.id)


class UserAuthenticationTestCase(APITestCase):
    def setUp(self):
        self.sede = Sede.objects.create(nombre='Sede Central', location='Ubicacion Central', status='activo')
        self.group_admin_sistemas = Group.objects.create(name='admin_sistemas')
        self.group_jefe_planta = Group.objects.create(name='jefe_planta')
        
        self.user_admin = CustomUser.objects.create_user(
            username='adminuser', 
            password='adminpassword', 
            sede=self.sede
        )
        self.user_admin.groups.add(self.group_admin_sistemas)
        self.user_admin.save()

        self.user_jefe = CustomUser.objects.create_user(
            username='jefeuser', 
            password='jefepassword', 
            sede=self.sede
        )
        self.user_jefe.groups.add(self.group_jefe_planta)
        self.user_jefe.save()

        self.login_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')
        self.logout_url = reverse('token_logout')
        self.profile_url = reverse('user-profile') # An authenticated endpoint

    def _get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def test_user_creation(self):
        """Ensure we can create a custom user."""
        users_before = CustomUser.objects.count()
        response = self.client.post(reverse('user-list'), {
            'username': 'newuser',
            'password': 'newpassword',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'new@example.com',
            'sede': self.sede.id,
            'groups': [self.group_jefe_planta.id]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomUser.objects.count(), users_before + 1)
        new_user = CustomUser.objects.get(username='newuser')
        self.assertTrue(new_user.check_password('newpassword'))
        self.assertIn(self.group_jefe_planta, new_user.groups.all())

    def test_login_success_and_cookie_setting(self):
        """Ensure user can log in and receive HttpOnly cookies."""
        response = self.client.post(self.login_url, {
            'username': 'adminuser',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])
        self.assertNotIn('access', response.data) # Tokens should not be in body
        self.assertNotIn('refresh', response.data) # Tokens should not be in body

        # Check if the profile data is returned in the body
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'adminuser')
    
    def test_login_failure(self):
        """Ensure login fails with incorrect credentials."""
        response = self.client.post(self.login_url, {
            'username': 'adminuser',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data) # Check standardized error
        self.assertNotIn('access_token', response.cookies)
        self.assertNotIn('refresh_token', response.cookies)

    def test_authenticated_access_with_cookies(self):
        """Ensure authenticated user can access protected endpoint using cookies."""
        # First, log in to get cookies
        login_response = self.client.post(self.login_url, {
            'username': 'adminuser',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Then, access a protected endpoint (e.g., user profile)
        profile_response = self.client.get(self.profile_url)
        self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
        self.assertEqual(profile_response.data['username'], 'adminuser')

    def test_unauthenticated_access_to_protected_endpoint(self):
        """Ensure unauthenticated user cannot access protected endpoint."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data) # Check standardized error

    def test_token_refresh_with_cookies(self):
        """Ensure tokens can be refreshed using the refresh_token cookie."""
        # Log in to get initial tokens
        login_response = self.client.post(self.login_url, {
            'username': 'adminuser',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        initial_access_token = login_response.cookies['access_token'].value

        # Request token refresh
        refresh_response = self.client.post(self.refresh_url, format='json') # Body not needed, token from cookie
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', refresh_response.cookies)
        self.assertIn('refresh_token', refresh_response.cookies) # Refresh token should also be re-issued
        self.assertTrue(refresh_response.cookies['access_token']['httponly'])
        self.assertTrue(refresh_response.cookies['refresh_token']['httponly'])
        self.assertNotIn('access', refresh_response.data)
        self.assertNotIn('refresh', refresh_response.data)
        # Ensure new access token is different
        self.assertNotEqual(initial_access_token, refresh_response.cookies['access_token'].value)

    def test_logout_deletes_cookies(self):
        """Ensure logging out deletes the authentication cookies."""
        # Log in first
        login_response = self.client.post(self.login_url, {
            'username': 'adminuser',
            'password': 'adminpassword'
        }, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        # Then, log out
        logout_response = self.client.post(self.logout_url)
        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn('access_token', logout_response.cookies)
        self.assertIn('refresh_token', logout_response.cookies)
        self.assertEqual(logout_response.cookies['access_token']['max_age'], 0) # Should be expired
        self.assertEqual(logout_response.cookies['refresh_token']['max_age'], 0) # Should be expired


class CustomExceptionHandlerTestCase(APITestCase):
    def test_validation_error_format(self):
        """Ensure ValidationError returns standardized format."""
        url = reverse('test-error', args=['validation'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Validation Error')
        self.assertIn('errors', response.data)
        self.assertIn('field_name', response.data['errors'])
        self.assertIn('non_field_errors', response.data['errors'])

    def test_404_error_format(self):
        """Ensure Http404 returns standardized format."""
        url = reverse('test-error', args=['404'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Not Found')
    
    def test_500_error_format(self):
        """Ensure unhandled Exception (500) returns standardized format."""
        url = reverse('test-error', args=['500'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('detail', response.data)
        self.assertIn('Internal server error', response.data['detail'])

    def test_401_error_format(self):
        """Ensure AuthenticationFailed (401) returns standardized format."""
        url = reverse('test-error', args=['401'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')