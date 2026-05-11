import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TexCore.settings')
django.setup()

from django.urls import resolve, Resolver404

try:
    print('Match:', resolve('/api/reporting/gerencial/ventas'))
except Resolver404 as e:
    print('404:', e)

try:
    print('Match with slash:', resolve('/api/reporting/gerencial/ventas/'))
except Resolver404 as e:
    print('404 slash:', e)
