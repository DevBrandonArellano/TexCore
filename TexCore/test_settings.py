from .settings import *
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'test_db.sqlite3',
    }
}

# Saltar migraciones en tests para evitar errores con RunSQL de SQL Server en SQLite
MIGRATION_MODULES = {
    'gestion': None,
    'inventory': None,
}
