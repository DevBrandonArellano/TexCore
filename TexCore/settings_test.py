from .settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Desactivar logs pesados en tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
}

# Simplificar seguridad para tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]
