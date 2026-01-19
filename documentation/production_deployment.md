# Guía de Deployment en Producción - TexCore
## Ubuntu Server + XFCE en Hyper-V

Esta guía proporciona instrucciones completas para desplegar TexCore en un entorno de producción sobre Ubuntu Server con XFCE en una máquina virtual Hyper-V.

---

## 📋 Requisitos Previos del Sistema

### Especificaciones Mínimas Recomendadas

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 2 cores | 4 cores |
| RAM | 4 GB | 8 GB |
| Disco | 40 GB | 80 GB |
| Red | Adaptador de red configurado | IP estática |

### Sistema Operativo
- ✅ Ubuntu Server 20.04 LTS o superior
- ✅ XFCE Desktop Environment
- ✅ Conexión a internet activa
- ✅ Usuario con permisos sudo

---

## 🔧 Paso 1: Instalación de Dependencias Base

### 1.1 Actualizar el Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Instalar Docker Engine

```bash
# Remover versiones antiguas si existen
sudo apt remove docker docker-engine docker.io containerd runc

# Instalar dependencias
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Agregar la clave GPG oficial de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Configurar el repositorio
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verificar instalación
sudo docker --version
sudo docker compose version
```

### 1.3 Configurar Permisos de Docker

```bash
# Agregar tu usuario al grupo docker (evita usar sudo)
sudo usermod -aG docker $USER

# Aplicar cambios (requiere logout/login o ejecutar)
newgrp docker

# Verificar que funciona sin sudo
docker ps
```

### 1.4 Instalar Git (si no está instalado)

```bash
sudo apt install -y git
git --version
```

---

## 📦 Paso 2: Preparar el Proyecto

### 2.1 Navegar al Directorio del Proyecto

```bash
cd /home/barellano/Documents/Desarrollo/TexCore
```

### 2.2 Verificar la Estructura del Proyecto

```bash
ls -la
# Deberías ver: docker-compose.prod.yml, Dockerfile.prod, nginx/, etc.
```

---

## ⚙️ Paso 3: Configuración de Variables de Entorno

### 3.1 Crear el Archivo `.env`

```bash
# Copiar el ejemplo
cp .env.example .env

# Editar con tu editor preferido
nano .env
```

### 3.2 Configurar Variables Críticas

Edita el archivo `.env` con los siguientes valores:

```bash
# Base de Datos
DB_PASSWORD=TuPasswordSeguro123!@#
DB_NAME=texcore_db
DB_USER=sa
DB_HOST=db
DB_PORT=1433

# Django
SECRET_KEY=genera-una-clave-secreta-muy-larga-y-aleatoria-aqui
DEBUG=0
ALLOWED_HOSTS=localhost,127.0.0.1,tu-ip-del-servidor

# Ejemplo si tu VM tiene IP 192.168.1.100:
# ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.100
```

> [!IMPORTANT]
> **Generar SECRET_KEY seguro:**
> ```bash
> python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
> ```

### 3.3 Descripción de Variables de Entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DB_PASSWORD` | Contraseña del usuario SA de SQL Server | `MySecureP@ssw0rd!` |
| `DB_NAME` | Nombre de la base de datos | `texcore_db` |
| `SECRET_KEY` | Clave secreta de Django (generada) | `django-insecure-xyz...` |
| `DEBUG` | Modo debug (0 en producción) | `0` |
| `ALLOWED_HOSTS` | Hosts permitidos (separados por coma) | `localhost,192.168.1.100` |

---

## 🔐 Paso 4: Configurar Certificados SSL

### 4.1 Generar Certificados Auto-firmados (Para Testing)

```bash
cd nginx/certs

# Generar certificado auto-firmado
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx-selfsigned.key \
  -out nginx-selfsigned.crt \
  -subj "/C=CO/ST=State/L=City/O=TexCore/CN=localhost"

# Ajustar permisos
sudo chmod 644 nginx-selfsigned.crt
sudo chmod 600 nginx-selfsigned.key
```

> [!WARNING]
> **Para producción real:** Usa certificados válidos de Let's Encrypt o una CA confiable. Los certificados auto-firmados son solo para desarrollo y testing.

### 4.2 Usar Certificados de Let's Encrypt (Producción Recomendada)

Si tienes un dominio público, puedes usar Let's Encrypt:

```bash
# Instalar certbot
sudo apt install -y certbot

# Generar certificados (requiere dominio apuntando a tu servidor)
sudo certbot certonly --standalone -d tudominio.com

# Copiar certificados a la carpeta de nginx
sudo cp /etc/letsencrypt/live/tudominio.com/fullchain.pem nginx/certs/nginx-selfsigned.crt
sudo cp /etc/letsencrypt/live/tudominio.com/privkey.pem nginx/certs/nginx-selfsigned.key
```

### 4.3 Verificar Certificados

```bash
ls -lh nginx/certs/
# Deberías ver: nginx-selfsigned.crt y nginx-selfsigned.key
```

---

## 🚀 Paso 5: Construir y Levantar los Contenedores

### 5.1 Construir las Imágenes

```bash
cd /home/barellano/Documents/Desarrollo/TexCore

# Construir todas las imágenes de producción
docker compose -f docker-compose.prod.yml build
```

Este proceso puede tomar **5-15 minutos** dependiendo de tu conexión a internet y recursos del sistema.

### 5.2 Levantar los Servicios

```bash
# Levantar en modo detached (segundo plano)
docker compose -f docker-compose.prod.yml up -d

# Ver los logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f
```

### 5.3 Verificar que los Contenedores Estén Corriendo

```bash
docker compose -f docker-compose.prod.yml ps
```

Deberías ver 3 servicios con estado `Up`:
- `texcore-db-1` (SQL Server)
- `texcore-backend-1` (Django + Gunicorn)
- `texcore-nginx-1` (Nginx)

---

## 🗄️ Paso 6: Inicializar la Base de Datos

### 6.1 Esperar a que SQL Server Esté Listo

```bash
# Verificar logs de la base de datos
docker compose -f docker-compose.prod.yml logs db | grep "SQL Server is now ready"

# O esperar aproximadamente 30-60 segundos después del inicio
```

### 6.2 Aplicar Migraciones

```bash
# Ejecutar migraciones dentro del contenedor backend
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### 6.3 Crear Superusuario

```bash
# Crear usuario administrador
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

Sigue las instrucciones interactivas:
- Username: `admin` (o el que prefieras)
- Email: tu correo
- Password: contraseña segura

### 6.4 Poblar con Datos de Prueba (Opcional)

```bash
# Si existe el comando seed_data
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_data
```

Esto creará usuarios de prueba con diferentes roles:
- `user_operario` / `password123`
- `user_jefe_area` / `password123`
- `user_admin_sistemas` / `password123`

---

## 🌐 Paso 7: Acceder a la Aplicación

### 7.1 Desde la Misma VM

Abre un navegador en XFCE:

```bash
firefox https://localhost &
```

O:

```bash
chromium-browser https://localhost &
```

### 7.2 Desde Otra Máquina en la Red

#### 7.2.1 Obtener la IP de tu VM

```bash
ip addr show | grep inet
# O más específico:
hostname -I
```

#### 7.2.2 Configurar Firewall (si está activo)

```bash
# Verificar estado del firewall
sudo ufw status

# Si está activo, permitir tráfico HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Verificar reglas
sudo ufw status numbered
```

#### 7.2.3 Acceder desde navegador

Desde cualquier máquina en la red:

```
https://IP-DE-TU-VM
```

Por ejemplo: `https://192.168.1.100`

> [!NOTE]
> Si usas certificados auto-firmados, el navegador mostrará una advertencia de seguridad. Acepta el riesgo para continuar (solo en entornos de desarrollo/testing).

---

## ✅ Paso 8: Verificación del Deployment

### 8.1 Checklist de Verificación

- [ ] Los 3 contenedores están corriendo (`docker compose -f docker-compose.prod.yml ps`)
- [ ] Nginx responde en puerto 80 y redirige a 443
- [ ] HTTPS funciona correctamente
- [ ] La API responde en `https://localhost/api/`
- [ ] El frontend carga correctamente
- [ ] Puedes hacer login con las credenciales
- [ ] El panel de admin funciona: `https://localhost/admin/`
- [ ] Los archivos estáticos cargan correctamente

### 8.2 Comandos de Diagnóstico

```bash
# Ver logs de todos los servicios
docker compose -f docker-compose.prod.yml logs

# Ver logs de un servicio específico
docker compose -f docker-compose.prod.yml logs backend
docker compose -f docker-compose.prod.yml logs nginx
docker compose -f docker-compose.prod.yml logs db

# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f

# Ver uso de recursos
docker stats

# Verificar conectividad a la API
curl -k https://localhost/api/

# Verificar que Nginx está escuchando
sudo netstat -tulpn | grep -E ':(80|443)'
```

### 8.3 Pruebas Funcionales

1. **Login:** Accede a `https://localhost` e inicia sesión
2. **Admin Panel:** Accede a `https://localhost/admin/`
3. **API Endpoints:** Verifica que la API responde correctamente
4. **Navegación:** Prueba las diferentes secciones de la aplicación

---

## 🔄 Paso 9: Gestión del Deployment

### 9.1 Comandos Útiles de Docker Compose

```bash
# Detener todos los servicios
docker compose -f docker-compose.prod.yml down

# Detener y eliminar volúmenes (¡CUIDADO! Borra la BD)
docker compose -f docker-compose.prod.yml down -v

# Reiniciar todos los servicios
docker compose -f docker-compose.prod.yml restart

# Reiniciar un servicio específico
docker compose -f docker-compose.prod.yml restart backend

# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f backend

# Ejecutar comandos dentro del contenedor
docker compose -f docker-compose.prod.yml exec backend python manage.py shell

# Ver estado de los servicios
docker compose -f docker-compose.prod.yml ps

# Ver uso de recursos
docker stats
```

### 9.2 Actualizar la Aplicación

Cuando necesites actualizar el código:

```bash
# 1. Obtener últimos cambios del repositorio
git pull origin main

# 2. Reconstruir imágenes
docker compose -f docker-compose.prod.yml build

# 3. Aplicar cambios (recrear contenedores)
docker compose -f docker-compose.prod.yml up -d

# 4. Aplicar migraciones si hay cambios en modelos
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 5. Recolectar archivos estáticos si hay cambios en frontend
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --no-input
```

### 9.3 Ver Logs de la Aplicación

```bash
# Logs del backend (Django/Gunicorn)
docker compose -f docker-compose.prod.yml logs -f backend

# Logs de Nginx (acceso y errores)
docker compose -f docker-compose.prod.yml logs -f nginx

# Logs de SQL Server
docker compose -f docker-compose.prod.yml logs -f db

# Todos los logs combinados
docker compose -f docker-compose.prod.yml logs -f
```

---

## 🛡️ Paso 10: Configuración de Seguridad Adicional

### 10.1 Configurar Auto-inicio con Systemd

Crear un servicio systemd para que Docker Compose inicie automáticamente al arrancar el servidor:

```bash
sudo nano /etc/systemd/system/texcore.service
```

Contenido del archivo:

```ini
[Unit]
Description=TexCore Production Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/barellano/Documents/Desarrollo/TexCore
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
User=barellano

[Install]
WantedBy=multi-user.target
```

Activar y probar el servicio:

```bash
# Recargar configuración de systemd
sudo systemctl daemon-reload

# Habilitar inicio automático
sudo systemctl enable texcore.service

# Iniciar el servicio
sudo systemctl start texcore.service

# Verificar estado
sudo systemctl status texcore.service

# Ver logs del servicio
sudo journalctl -u texcore.service -f
```

### 10.2 Configurar Backups Automáticos

#### 10.2.1 Crear Script de Backup

```bash
# Crear directorio para backups
mkdir -p ~/backups

# Crear script de backup
nano ~/backup-texcore.sh
```

Contenido del script:

```bash
#!/bin/bash
BACKUP_DIR=~/backups
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR=/home/barellano/Documents/Desarrollo/TexCore

cd $PROJECT_DIR

# Cargar variables de entorno
source .env

# Backup de la base de datos
docker compose -f docker-compose.prod.yml exec -T db /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "${DB_PASSWORD}" -C -N \
  -Q "BACKUP DATABASE texcore_db TO DISK='/var/opt/mssql/backup/texcore_${DATE}.bak'"

# Copiar backup al host
docker cp texcore-db-1:/var/opt/mssql/backup/texcore_${DATE}.bak ${BACKUP_DIR}/

# Mantener solo últimos 7 días
find ${BACKUP_DIR} -name "texcore_*.bak" -mtime +7 -delete

echo "Backup completado: ${BACKUP_DIR}/texcore_${DATE}.bak"
```

Hacer ejecutable:

```bash
chmod +x ~/backup-texcore.sh
```

#### 10.2.2 Programar Backups con Cron

```bash
# Editar crontab
crontab -e

# Agregar línea para backup diario a las 2 AM
0 2 * * * /home/barellano/backup-texcore.sh >> /home/barellano/backup.log 2>&1
```

#### 10.2.3 Probar el Backup Manualmente

```bash
# Ejecutar script de backup
~/backup-texcore.sh

# Verificar que se creó el backup
ls -lh ~/backups/
```

### 10.3 Restaurar desde Backup

```bash
# Copiar backup al contenedor
docker cp ~/backups/texcore_YYYYMMDD_HHMMSS.bak texcore-db-1:/var/opt/mssql/backup/

# Restaurar la base de datos
docker compose -f docker-compose.prod.yml exec db /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "${DB_PASSWORD}" -C -N \
  -Q "RESTORE DATABASE texcore_db FROM DISK='/var/opt/mssql/backup/texcore_YYYYMMDD_HHMMSS.bak' WITH REPLACE"
```

---

## 🐛 Troubleshooting

### Problema: Contenedores no inician

**Síntomas:** Los contenedores se detienen inmediatamente después de iniciar.

**Diagnóstico:**

```bash
# Ver logs detallados
docker compose -f docker-compose.prod.yml logs

# Verificar que no haya conflictos de puertos
sudo netstat -tulpn | grep -E ':(80|443|1433|8000)'

# Verificar espacio en disco
df -h

# Verificar memoria disponible
free -h
```

**Soluciones:**

- Si hay conflictos de puertos, detén los servicios que los estén usando
- Si falta espacio en disco, limpia con `docker system prune -a`
- Revisa los logs para identificar errores específicos

### Problema: Error de conexión a la base de datos

**Síntomas:** Backend no puede conectarse a SQL Server.

**Diagnóstico:**

```bash
# Verificar que SQL Server esté listo
docker compose -f docker-compose.prod.yml exec db /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "${DB_PASSWORD}" -C -N -Q "SELECT @@VERSION"

# Ver logs de la base de datos
docker compose -f docker-compose.prod.yml logs db
```

**Soluciones:**

```bash
# Reiniciar servicio de backend
docker compose -f docker-compose.prod.yml restart backend

# Si persiste, reiniciar todos los servicios
docker compose -f docker-compose.prod.yml restart
```

### Problema: Nginx muestra 502 Bad Gateway

**Síntomas:** Al acceder a la aplicación, aparece error 502.

**Diagnóstico:**

```bash
# Verificar que backend esté corriendo
docker compose -f docker-compose.prod.yml ps backend

# Ver logs de Nginx
docker compose -f docker-compose.prod.yml logs nginx

# Ver logs del backend
docker compose -f docker-compose.prod.yml logs backend

# Verificar conectividad interna
docker compose -f docker-compose.prod.yml exec nginx ping backend
```

**Soluciones:**

```bash
# Reiniciar backend
docker compose -f docker-compose.prod.yml restart backend

# Si persiste, reconstruir y reiniciar
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend
```

### Problema: Archivos estáticos no cargan

**Síntomas:** La aplicación carga pero sin estilos CSS o JavaScript.

**Diagnóstico:**

```bash
# Verificar volumen de archivos estáticos
docker volume inspect texcore_prod_django_static

# Ver logs de Nginx
docker compose -f docker-compose.prod.yml logs nginx
```

**Soluciones:**

```bash
# Recolectar archivos estáticos nuevamente
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --no-input

# Reiniciar Nginx
docker compose -f docker-compose.prod.yml restart nginx
```

### Problema: Certificado SSL inválido

**Síntomas:** El navegador muestra advertencias de certificado.

**Soluciones:**

- Si usas certificados auto-firmados, esto es normal en desarrollo
- Para producción, usa certificados de Let's Encrypt o una CA confiable
- Verifica que los archivos de certificado existan en `nginx/certs/`

### Problema: Alto uso de recursos

**Diagnóstico:**

```bash
# Ver uso de recursos por contenedor
docker stats

# Ver procesos dentro del contenedor
docker compose -f docker-compose.prod.yml exec backend top
```

**Soluciones:**

- Ajusta el número de workers de Gunicorn en `Dockerfile.prod`
- Aumenta recursos de la VM si es necesario
- Implementa caché para reducir carga en la base de datos

---

## 📊 Monitoreo y Mantenimiento

### 10.1 Verificar Salud del Sistema

```bash
# Uso de disco
df -h

# Uso de memoria
free -h

# Recursos de Docker
docker system df

# Estado de los contenedores
docker compose -f docker-compose.prod.yml ps

# Logs recientes
docker compose -f docker-compose.prod.yml logs --tail=100
```

### 10.2 Limpieza de Recursos

```bash
# Limpiar imágenes no usadas
docker image prune -a

# Limpiar volúmenes no usados
docker volume prune

# Limpieza completa (¡CUIDADO!)
docker system prune -a --volumes
```

### 10.3 Logs Centralizados

```bash
# Ver todos los logs
docker compose -f docker-compose.prod.yml logs --tail=100 -f

# Exportar logs a archivo
docker compose -f docker-compose.prod.yml logs > ~/texcore-logs-$(date +%Y%m%d).log

# Ver logs de un período específico
docker compose -f docker-compose.prod.yml logs --since 1h
```

### 10.4 Monitoreo de Rendimiento

```bash
# Ver estadísticas en tiempo real
docker stats

# Ver uso de red
docker network inspect texcore_default

# Ver procesos dentro de un contenedor
docker compose -f docker-compose.prod.yml exec backend ps aux
```

---

## 🎯 Resumen de Comandos Esenciales

| Acción | Comando |
|--------|---------|
| Iniciar servicios | `docker compose -f docker-compose.prod.yml up -d` |
| Detener servicios | `docker compose -f docker-compose.prod.yml down` |
| Ver estado | `docker compose -f docker-compose.prod.yml ps` |
| Ver logs | `docker compose -f docker-compose.prod.yml logs -f` |
| Reiniciar | `docker compose -f docker-compose.prod.yml restart` |
| Reconstruir | `docker compose -f docker-compose.prod.yml build` |
| Ejecutar comando | `docker compose -f docker-compose.prod.yml exec backend <comando>` |
| Aplicar migraciones | `docker compose -f docker-compose.prod.yml exec backend python manage.py migrate` |
| Crear superusuario | `docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser` |
| Recolectar estáticos | `docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --no-input` |

---

## 📞 Próximos Pasos

Una vez que tengas el sistema corriendo en producción:

1. **Configurar certificados SSL válidos** (Let's Encrypt para dominios públicos)
2. **Implementar CI/CD** con GitLab para automatizar deployments
3. **Configurar monitoreo** (Prometheus + Grafana) para métricas en tiempo real
4. **Realizar pruebas de carga** para validar el objetivo de 50 usuarios simultáneos
5. **Documentar procedimientos operativos** específicos de tu organización
6. **Configurar alertas** para notificaciones de errores o problemas
7. **Implementar estrategia de alta disponibilidad** si es necesario

---

## 📚 Referencias

- [Documentación de Docker](https://docs.docker.com/)
- [Documentación de Django](https://docs.djangoproject.com/)
- [Documentación de Nginx](https://nginx.org/en/docs/)
- [Documentación de Gunicorn](https://docs.gunicorn.org/)
- [Documentación de SQL Server en Linux](https://docs.microsoft.com/en-us/sql/linux/)

---

> [!TIP]
> **Recomendaciones finales:**
> - Crea snapshots de tu VM en Hyper-V antes de hacer cambios importantes
> - Mantén backups regulares de la base de datos
> - Documenta cualquier cambio en la configuración
> - Revisa los logs regularmente para detectar problemas temprano
> - Mantén el sistema actualizado con parches de seguridad
