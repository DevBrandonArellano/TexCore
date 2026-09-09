# Guía de Comandos para Operaciones en Producción

Este documento resume los comandos esenciales para desplegar, gestionar y mantener la aplicación TexCore en un entorno de producción.

## 🚀 Despliegue e Inicio

Recomendamos usar los scripts automatizados que detectan tu sistema operativo y configuran el entorno correctamente.

### Iniciar / Actualizar Servicios
Este comando levanta los contenedores. Si hay cambios en el código o configuración, reconstruirá las imágenes automáticamente.

**En Windows (PowerShell):**
```powershell
./deploy.ps1
```

**En Linux / macOS (Bash):**
```bash
./deploy.sh
```

---

## 🛑 Detener Servicios

Para detener todos los contenedores de la aplicación de forma segura.

**Universal (si tienes Docker instalado y estás en la raíz):**
```bash
docker compose -f docker-compose.prod.yml down
```
*(Nota: Si usas Windows Server nativo, usa `docker-compose.windows.yml`)*

---

## 🔄 Recrear Imágenes (Forzar Rebuild)

Si has hecho cambios en las dependencias (`requirements.txt` o `package.json`) y necesitas forzar una reconstrucción completa desde cero:

```bash
docker compose -f docker-compose.prod.yml up -d --build --force-recreate
```

---

## 📋 Ver Logs (Monitoreo)

Para ver qué está pasando dentro de los servicios en tiempo real.

**Ver logs de todos los servicios:**
```bash
docker compose -f docker-compose.prod.yml logs -f
```

**Ver logs solo del Backend:**
```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

**Ver logs solo del Proxy (Nginx):**
```bash
docker compose -f docker-compose.prod.yml logs -f nginx
```

---

## 🛠 Tareas de Mantenimiento

### Entrar a la consola del contenedor (Backend)
Útil para ejecutar scripts de Python o migrar manualmente.

```bash
docker compose -f docker-compose.prod.yml exec backend /bin/bash
```

### Ejecutar Migraciones Manualmente
Aunque el script de inicio lo hace automático, si necesitas forzarlo:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Crear un Superusuario
```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```
> **Nota:** Los Roles de usuario (`operario`, `admin_sistemas`, etc.) NO se crean automáticamente —
> hay que ejecutar explícitamente `python manage.py setup_permissions` o
> `python manage.py seed_production_masters` (crea los grupos/permisos RBAC y la cuenta `admin`
> inicial, sin pre-crear Sedes/Areas falsas; ver `CLAUDE.md`).

### Resetear la Base de Datos (CUIDADO: Borra datos)
Si necesitas reiniciar todo (solo para pruebas o reinicio total):

```bash
docker compose -f docker-compose.prod.yml down -v
```
*(El flag `-v` elimina los volúmenes persistentes de la base de datos)*
