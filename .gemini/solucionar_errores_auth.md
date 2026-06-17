# Solucionar Errores de Autenticación (401/403)

## Errores Reportados

```
❌ 401 Unauthorized - GET /profile/
   "No active session found"

❌ 403 Forbidden - POST /ordenes-produccion/
   "Permission denied"
```

---

## Causas Posibles

### Error 401 (No Autenticado)
1. **Token JWT expirado**
2. **Token no se está enviando correctamente**
3. **Cookie de sesión perdida**
4. **Usuario no está logeado**

### Error 403 (Sin Permisos)
1. **Usuario no tiene el grupo correcto** (no es jefe_planta, jefe_area, etc.)
2. **Permisos incorrectos en el ViewSet**
3. **Usuario activo pero sin grupo asignado**

---

## Soluciones

### Solución 1: Verificar Login y Token

**Paso 1**: Abre la consola del navegador (F12)

**Paso 2**: Verifica si hay token almacenado:
```javascript
// En la consola del navegador
localStorage.getItem('access_token')
localStorage.getItem('refresh_token')
```

**Esperado**: Deberías ver un token JWT largo
**Si está vacío**: El usuario no está autenticado

**Solución**:
```javascript
// Limpiar y reloguear
localStorage.clear()
sessionStorage.clear()
// Recarga la página y loguéate de nuevo
```

---

### Solución 2: Verificar Grupos del Usuario

**Como Admin de la Aplicación**:

**Backend (Django)**:
```bash
python manage.py shell

# Verificar usuario
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='tu_usuario')
print(user.groups.all())  # Debería mostrar ['jefe_planta'] o similar
```

**Frontend**:
1. Loguéate
2. Abre DevTools (F12)
3. Ve a la pestaña Network
4. Busca la petición `/profile/`
5. Haz click en ella
6. Ve a "Response"
7. Busca el campo `role` - debe mostrar tu rol

```json
{
  "user": {...},
  "role": "jefe_planta"  // ← Debe estar aquí
}
```

---

### Solución 3: Asignar Grupo al Usuario

**Si el usuario no tiene grupo**:

**Backend (Django Admin o Shell)**:
```bash
python manage.py shell

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()
user = User.objects.get(username='tu_usuario')

# Obtener el grupo Jefe de Planta
jefe_planta_group = Group.objects.get(name='jefe_planta')

# Asignar al usuario
user.groups.add(jefe_planta_group)

print(f"Grupos del usuario: {user.groups.all()}")
```

**O vía Django Admin**:
1. Ve a http://localhost/admin/
2. Busca "Users" (Usuarios)
3. Abre el usuario
4. En "Groups" (Grupos), agrega "jefe_planta"
5. Guarda

---

### Solución 4: Verificar Permisos en Backend

**Se acaba de actualizar**:
```python
# ANTES (restrictivo)
if self.action == 'create':
    return [IsAuthenticated(), IsAdminSistemasOrSede()]

# AHORA (permite jefe_planta)
if self.action == 'create':
    return [IsAuthenticated(), IsJefeAreaOrAdmin()]
```

✅ Los cambios ya están aplicados. Ahora permite:
- `admin_sistemas`
- `admin_sede`
- `jefe_area`
- `jefe_planta`

---

## Checklist de Diagnóstico

Ejecuta esto en orden:

### 1️⃣ Verificar autenticación
```javascript
// Consola del navegador
fetch('http://localhost/api/profile/', {
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
  }
})
.then(r => r.json())
.then(data => console.log(data))
.catch(e => console.error(e))
```

Esperado: Ver objeto con user y role

### 2️⃣ Verificar si token es válido
```bash
# Backend
python manage.py shell

from rest_framework_simplejwt.tokens import AccessToken
token_string = "tu_token_aqui"  # Copia del localStorage
token = AccessToken(token_string)
print(token.payload)  # Debe mostrar user_id, etc.
```

### 3️⃣ Verificar grupos en backend
```bash
python manage.py shell
from django.contrib.auth import get_user_model
User = get_user_model()
for user in User.objects.all():
    print(f"{user.username}: {list(user.groups.values_list('name', flat=True))}")
```

### 4️⃣ Verificar si sede y area están asignadas
```bash
python manage.py shell
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(username='tu_usuario')
print(f"Sede: {user.sede}")
print(f"Área: {user.area}")
```

---

## Pasos Recomendados (En Orden)

### 1. Limpiar tokens
```javascript
// Consola del navegador
localStorage.clear()
sessionStorage.clear()
// Recarga
location.reload()
```

### 2. Loguéate de nuevo
- Ingresa credenciales correctas
- Verifica que aparezca el mensaje de éxito

### 3. Verifica el token se guarde
```javascript
// Consola
localStorage.getItem('access_token')  // Debería tener contenido
```

### 4. Intenta crear orden
- Abre Gestión de Órdenes
- Click "Nueva Orden"
- Completa: Código, Peso, Área
- Click "Crear"

### 5. Si sigue fallando
Ejecuta el checklist de diagnóstico arriba

---

## Errores Comunes y Soluciones

### ❌ "No active session found"
**Causa**: Token expirado o no existe
**Solución**: Limpiar cache y volver a loguear

```javascript
localStorage.clear()
```

### ❌ "Permission denied" (403)
**Causa**: Usuario sin grupo "jefe_planta"
**Solución**: Asignar grupo via Django Admin o shell

```bash
# Shell
user.groups.add(Group.objects.get(name='jefe_planta'))
```

### ❌ "Unauthorized" (401) después de loguear
**Causa**: Token JWT no se está enviando
**Solución**: Verificar header Authorization en Network tab

En DevTools → Network → POST /api/login/
Ver headers → Authorization debe estar presente

### ❌ "CORS error"
**Causa**: Frontend y backend en puertos diferentes
**Solución**: Verificar CORS_ALLOWED_ORIGINS en settings.py

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    # ... tu puerto
]
```

---

## Verificación Final

Una vez resuelto, verifica que:

✅ Puedas loguear
✅ Token aparezca en localStorage
✅ GET /profile/ devuelva tu usuario y rol
✅ Puedas ver "Nueva Orden"
✅ Puedas crear orden con código, peso, área
✅ No veas campos bodega/producto al crear

---

## Contacto / Próximos Pasos

Si después de esto sigue fallando:

1. **Reporta en logs**: Copia el error completo
2. **Verifica base de datos**: ¿Existe el usuario? ¿Tiene grupo?
3. **Reinicia servicios**: A veces el cache causa problemas

```bash
# Reiniciar backend
python manage.py runserver

# Limpiar cache del navegador
Ctrl+Shift+Delete → Borrar todo
```
