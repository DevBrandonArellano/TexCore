# Guía: Merge de staging → Fix-ejecutivo

## Situación actual
- **Rama actual:** Fix-ejecutivo (con cambios locales sin commitear)
- **Rama a integrar:** origin/staging
- **Archivos con posible conflicto:** ~20 archivos modificados en ambas ramas

---

## Opción A: Commit primero (recomendada si quieres guardar tu trabajo)

### Paso 1: Guardar tus cambios
```powershell
cd c:\Users\Sistemas\Desktop\Texcore\TexCore

# Ver qué cambiarías
git status

# Añadir todos tus cambios
git add -A

# Commit con mensaje descriptivo
git commit -m "Fix-ejecutivo: dashboard ejecutivo, stress_test_data, flush_test_data"
```

### Paso 2: Traer staging y hacer merge
```powershell
# Asegurarte de tener staging actualizado (ya hiciste fetch)
git merge origin/staging
```

### Paso 3: Resolver conflictos (si aparecen)
- Git listará los archivos en conflicto
- Abre cada archivo y busca marcadores `<<<<<<<`, `=======`, `>>>>>>>`
- Edita para quedarte con el código correcto (tuyo + staging)
- Luego:
```powershell
git add <archivo_resuelto>
git commit -m "Merge staging: resolución de conflictos"
```

---

## Opción B: Stash primero (si prefieres probar el merge sin commitear)

### Paso 1: Guardar cambios temporalmente
```powershell
cd c:\Users\Sistemas\Desktop\Texcore\TexCore

git stash push -u -m "Fix-ejecutivo: cambios locales antes de merge staging"
```
El `-u` incluye archivos sin trackear (ej. `flush_test_data.py`).

### Paso 2: Hacer merge
```powershell
git merge origin/staging
```

### Paso 3: Recuperar tus cambios
```powershell
git stash pop
```

### Paso 4: Resolver conflictos
- Si `stash pop` genera conflictos, resuélvelos igual que en la Opción A
- Luego: `git add .` y `git stash drop` (si todo quedó bien)

---

## Comandos útiles durante el merge

| Acción | Comando |
|--------|---------|
| Ver conflictos pendientes | `git status` |
| Cancelar merge en curso | `git merge --abort` |
| Ver diferencias en un archivo | `git diff <archivo>` |
| Aceptar versión de staging | `git checkout --theirs <archivo>` |
| Aceptar tu versión | `git checkout --ours <archivo>` |

---

## Archivos a revisar con más cuidado

1. **gestion/models.py** – staging tiene muchos cambios (223 líneas)
2. **gestion/views.py** – 405 líneas afectadas
3. **gestion/serializers.py** – 201 líneas
4. **frontend/** – varios dashboards y configuración
5. **inventory/** – URLs, vistas, modelos

---

## Después del merge

```powershell
# Verificar que todo compila
# Backend
docker-compose -f docker-compose.prod.yml build --no-cache backend

# Frontend (si tocaste código React)
cd frontend && npm run build
```
