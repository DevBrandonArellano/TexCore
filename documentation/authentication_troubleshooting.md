# Solución de Problemas de Autenticación y CORS

Este documento detalla los problemas de autenticación y CORS que se encontraron durante la configuración inicial del entorno de desarrollo y las soluciones implementadas para resolverlos.

---

## 1. Problema de la Política CORS (`Access-Control-Allow-Credentials`)

### Descripción
El frontend (ejecutándose en `http://localhost:3000`) intentaba enviar credenciales (como tokens de autenticación o cookies) al backend (ejecutándose en `http://127.0.0.1:8000`). Sin embargo, las políticas de seguridad del navegador (CORS) bloqueaban estas solicitudes porque la respuesta del backend no incluía la cabecera `Access-Control-Allow-Credentials: true`, que es obligatoria cuando se envían credenciales en peticiones cross-origin.

### Solución
Se añadió la configuración `CORS_ALLOW_CREDENTIALS = True` al archivo `TexCore/settings.py`. Esto instruye al backend a incluir la cabecera necesaria en sus respuestas, permitiendo que el navegador procese las peticiones con credenciales desde orígenes permitidos.

**Cambio en `TexCore/settings.py`:**
```python
# ...
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_CREDENTIALS = True # <-- Línea añadida
# ...
```

---

## 2. `IndentationError` en `gestion/custom_jwt_views.py`

### Descripción
Después de aplicar los cambios para la configuración de cookies en las vistas JWT personalizadas, el servidor de backend no podía iniciarse debido a un error de sintaxis: `IndentationError: unexpected indent` en el archivo `gestion/custom_jwt_views.py`. Este error fue introducido inadvertidamente durante la edición del método `post` en `CustomTokenObtainPairView`.

### Solución
Se corrigió la indentación incorrecta en el método `post` de `CustomTokenObtainPairView` en `gestion/custom_jwt_views.py`, asegurando que el bloque de código de manejo de la respuesta se encontrara correctamente anidado dentro de la condición `if response.status_code == 200:`.

---

## 3. Desfase de Autenticación (Frontend basado en Cookies vs. Backend por Defecto)

### Descripción
El frontend estaba diseñado para usar autenticación JWT basada en cookies `HttpOnly`, esperando que el backend gestionara automáticamente el almacenamiento y envío de tokens mediante cookies. Sin embargo, el backend (`djangorestframework-simplejwt`) por defecto no utiliza cookies, sino que devuelve los tokens en el cuerpo de la respuesta JSON. Esto causó varios problemas:
*   El frontend recibía una respuesta vacía en el login, impidiendo establecer el perfil de usuario.
*   Las peticiones subsecuentes (ej. a `/api/profile/` o `/api/token/refresh/`) fallaban con `401 Unauthorized` porque el backend no leía el token de las cookies.
*   Los nombres de las cookies estaban parcialmente hardcodeados en las vistas, lo que generaba inconsistencias y errores como "No refresh token found in cookies."

### Soluciones

#### 3.1. Creación de un Backend de Autenticación Personalizado
Se creó un nuevo archivo `gestion/auth_backends.py` para extender la funcionalidad de autenticación de Django REST Framework. Esta clase personalizada, `CookieJWTAuthentication`, permite al backend leer el token de acceso directamente desde la cookie `access_token` en las peticiones entrantes.

**Archivo `gestion/auth_backends.py`:**
```python
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

class CookieJWTAuthentication(JWTAuthentication):
    """
    An authentication backend that authenticates users with a JWT provided
    in a cookie.
    """
    def authenticate(self, request):
        cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except Exception: # Se puede refinar para InvalidToken
            return None
```

#### 3.2. Configuración de `settings.py` para JWT y Cookies
Se actualizó `TexCore/settings.py` para:
*   Registrar la nueva clase `CookieJWTAuthentication` como la clase de autenticación por defecto en `REST_FRAMEWORK`.
*   Añadir el diccionario `SIMPLE_JWT` para centralizar la configuración de los tokens y las cookies, incluyendo la duración de los tokens, los nombres de las cookies y otras opciones de seguridad.

**Cambio en `TexCore/settings.py`:**
```python
# ...
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'gestion.auth_backends.CookieJWTAuthentication', # <-- Nueva clase
        'rest_framework.authentication.SessionAuthentication',
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,

    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',

    # Custom settings for cookie-based auth
    'AUTH_COOKIE': 'access_token',
    'AUTH_COOKIE_REFRESH': 'refresh_token',
    'AUTH_COOKIE_DOMAIN': None,
    'AUTH_COOKIE_SECURE': False, # Set to True in production
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_PATH': '/',
    'AUTH_COOKIE_SAMESITE': 'Lax',
}
# ...
```

#### 3.3. Mejora de las Vistas JWT Personalizadas
Se modificaron las vistas `CustomTokenObtainPairView`, `CustomTokenRefreshView` y `LogoutView` en `gestion/custom_jwt_views.py` para:
*   **`CustomTokenObtainPairView` (Login):** Después de generar los tokens y establecer las cookies `HttpOnly`, la vista ahora serializa el perfil del usuario (usando `CustomUserSerializer`) y lo devuelve en el cuerpo de la respuesta. Esto satisface la expectativa del frontend de recibir la información del usuario en el login. Se extraen los nombres de las cookies y la configuración de seguridad (`secure_cookie`, `samesite`) de `settings.SIMPLE_JWT`.
*   **`CustomTokenRefreshView` (Refresh):** Se modificó para leer el token de refresco de la cookie `refresh_token` (cuyo nombre se obtiene de `settings.SIMPLE_JWT`), y establecer el nuevo token de acceso en una cookie `access_token`.
*   **`LogoutView` (Logout):** Se actualizó para eliminar las cookies de `access_token` y `refresh_token` utilizando los nombres definidos en `settings.SIMPLE_JWT`.

---

Estos cambios en conjunto establecen un flujo de autenticación JWT robusto y seguro basado en cookies `HttpOnly`, resolviendo los problemas de comunicación entre el frontend de React y el backend de Django.