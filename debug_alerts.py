import os
import django

# Load .env manually since python-dotenv might not be installed
try:
    with open('.env') as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    print(".env file not found")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TexCore.settings')
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status
from django.contrib.auth.models import Group
from gestion.models import CustomUser, Bodega
from inventory.views import AlertasStockAPIView

def run():
    factory = APIRequestFactory()
    view = AlertasStockAPIView.as_view()

    # Create or get a bodeguero user
    try:
        bodeguero_group, _ = Group.objects.get_or_create(name='bodeguero')
        user, created = CustomUser.objects.get_or_create(username='test_bodeguero', defaults={'email': 'test@example.com'})
        user.set_password('password')
        user.groups.add(bodeguero_group)
        user.save()
        
        # Ensure user has assigned bodegas
        bodega = Bodega.objects.first()
        if bodega:
            user.bodegas_asignadas.add(bodega)
            print(f"Assigned bodega: {bodega}")
        else:
            print("No bodegas found to assign")
            
    except Exception as e:
        print(f"Error setting up user: {e}")
        return

    request = factory.get('/api/inventory/alertas-stock/')
    force_authenticate(request, user=user)

    try:
        response = view(request)
        print(f"Status Code: {response.status_code}")
        print(f"Data: {response.data}")
        print(f"Type of Data: {type(response.data)}")
    except Exception as e:
        print(f"View execution error: {e}")

if __name__ == '__main__':
    run()
