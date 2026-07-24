# Guía de Despliegue en Producción — TexCore

Guía paso a paso para desplegar TexCore en un servidor nuevo **sin depender del pipeline CI/CD**. Aplica tanto para el primer despliegue como para actualizaciones manuales.

---

## Requisitos del Servidor

| Requisito | Mínimo recomendado |
|---|---|
| SO | Ubuntu 22.04 LTS / Debian 12 |
| RAM | 4 GB |
| Disco | 40 GB |
| CPU | 2 núcleos |
| Puertos abiertos | 80 (HTTP), 443 (HTTPS), 22 (SSH admin) |

**Software a instalar en el servidor:**

```bash
# Docker Engine
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # cierra sesión y vuelve a entrar

# Docker Compose plugin (incluido en Docker Engine >= 23)
docker compose version

# Git
sudo apt install -y git

# Dependencias para generar claves RSA (en tu máquina local, no en el servidor)
pip install cryptography
```

---

## Paso 1 — Clonar el Repositorio

```bash
# En el servidor
git clone https://github.com/TU_USUARIO/TexCore.git /opt/texcore
cd /opt/texcore
```

---

## Paso 2 — Generar el Par de Claves RSA (una sola vez)

Las claves RSA permiten la autenticación JWT entre servicios satélite. Ejecuta esto **en tu máquina local**:

```bash
pip install cryptography
python scripts/generate_rsa_keys.py
```

La salida tendrá este formato (los valores reales serán mucho más largos):

```
INTERNAL_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n"
INTERNAL_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\nMIIB...\n-----END PUBLIC KEY-----\n"
```

Guarda estos valores en un gestor de secretos (Bitwarden, 1Password, etc.). **Nunca los commitees al repositorio.**

---

## Paso 3 — Generar el Django SECRET_KEY

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Paso 4 — Generar Secrets para los Servicios Satélite

```bash
# Secret del scanning_service (mínimo 32 caracteres)
python -c "import secrets; print(secrets.token_urlsafe(40))"

# Secret del reporting_excel (ejecutar de nuevo para obtener uno diferente)
python -c "import secrets; print(secrets.token_urlsafe(40))"
```

---

## Paso 5 — Crear el Archivo `.env` en el Servidor

En el servidor (`/opt/texcore/.env`):

```bash
# Para despliegue manual sin CI/CD, define imagen y tag locales
CI_REGISTRY_IMAGE=texcore
TAG=local

# ── Base de Datos ─────────────────────────────────────────────
DB_PASSWORD=UnaContraseñaMuySegura2024!
DB_NAME=texcore_db
DB_USER=sa
DB_HOST=db
DB_PORT=1433
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_ENGINE=mssql

# ── Django ────────────────────────────────────────────────────
SECRET_KEY=TU_SECRET_KEY_GENERADA_EN_PASO_3
DEBUG=0
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CORS_ALLOWED_ORIGINS=https://tudominio.com,https://www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com
STATIC_ROOT=/home/appuser/app/staticfiles

# ── JWT de Servicio (RS256) ───────────────────────────────────
INTERNAL_JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...TU CLAVE PRIVADA...\n-----END RSA PRIVATE KEY-----\n"
INTERNAL_JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...TU CLAVE PÚBLICA...\n-----END PUBLIC KEY-----\n"

# ── Secrets de Servicios Satélite ─────────────────────────────
SCANNING_SERVICE_SECRET=TU_SECRET_SCANNING_PASO_4
REPORTING_SERVICE_SECRET=TU_SECRET_REPORTING_PASO_4
```

Protege el archivo:

```bash
chmod 600 /opt/texcore/.env
```

---

## Paso 6 — Certificado SSL

### Opción A — Let's Encrypt (dominio real, recomendado)

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d tudominio.com -d www.tudominio.com

# Los certificados quedan en:
#   /etc/letsencrypt/live/tudominio.com/fullchain.pem
#   /etc/letsencrypt/live/tudominio.com/privkey.pem

# Copia al directorio del proyecto
mkdir -p /opt/texcore/nginx/certs
cp /etc/letsencrypt/live/tudominio.com/fullchain.pem /opt/texcore/nginx/certs/nginx-selfsigned.crt
cp /etc/letsencrypt/live/tudominio.com/privkey.pem   /opt/texcore/nginx/certs/nginx-selfsigned.key
chmod 600 /opt/texcore/nginx/certs/nginx-selfsigned.key
```

### Opción B — Certificado Self-Signed (IP interna / staging)

```bash
mkdir -p /opt/texcore/nginx/certs
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /opt/texcore/nginx/certs/nginx-selfsigned.key \
  -out    /opt/texcore/nginx/certs/nginx-selfsigned.crt \
  -subj "/CN=tudominio.com"
chmod 600 /opt/texcore/nginx/certs/nginx-selfsigned.key
```

---

## Paso 7 — Construir y Levantar los Servicios

```bash
cd /opt/texcore

# Construye las imágenes localmente y levanta todos los servicios
docker compose -f docker-compose.prod.yml up -d --build

# Verifica que todos arranquen
docker compose -f docker-compose.prod.yml ps
```

Espera hasta que todos los servicios muestren `healthy` o `Up`. La BD tarda ~60-90 segundos en inicializar la primera vez.

---

## Paso 8 — Migraciones y Configuración Inicial

```bash
# Ejecutar migraciones de Django
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate

# Recolectar archivos estáticos
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py collectstatic --no-input

# Cargar datos: superusuario + permisos de roles + simulación integral + MRP
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py seed_data
```

`seed_data` es un comando **orquestador**: en una sola ejecución crea el superusuario
`sistemas`, corre `setup_permissions`, puebla los datos maestros (sedes, áreas, bodegas,
productos, máquinas, procesos), y siembra una **simulación integral end-to-end** que
recorre el flujo completo por rol — recepción de materia prima, creación de OP, fórmula
de tintorería, avance de subprocesos, transformación, costeo, transferencia interárea,
empaque, despacho por escaneo, ventas y cobranza — dejando **~38 de 39 modelos** del
dominio con datos coherentes (stock cuadra con el Kardex, trazabilidad, auditoría). Al
final ejecuta el motor **MRP** (requerimientos + órdenes de compra sugeridas).

Es **idempotente**: volver a ejecutarlo no duplica datos ni falla si ya corrió antes.

**Flags disponibles:**

| Flag | Efecto |
|---|---|
| `--no-superuser` | No crea/asegura el superusuario `sistemas` (usar si ya existe o se gestiona aparte). |
| `--no-permissions` | No ejecuta `setup_permissions` (usar si los permisos ya fueron configurados y no deben resetearse). |
| `--sin-mrp` | No ejecuta el motor MRP al final. |
| `--sin-credenciales` | No crea los `ServiceCredential` de desarrollo para `scanning_service`/`reporting_excel` (en producción real, usa siempre `register_services` con secrets reales — ver Paso 9). |

> **Importante — datos de demostración vs. producción real:** la simulación que siembra
> `seed_data` incluye clientes, pedidos, pagos y órdenes **ficticios** (prefijo `SIM-` en
> lotes, `RUC-00x` en clientes, `OP-SIM-00x` en órdenes) pensados para poblar un entorno
> de **demo/staging** o para la puesta en marcha inicial de un ambiente vacío. Si el
> despliegue es sobre una base con datos reales de clientes/producción, **no ejecutes
> `seed_data`** — usa únicamente `python manage.py setup_permissions` (y `create_admin`
> si hace falta un superusuario) para no introducir registros de prueba.

Los comandos individuales `create_admin` y `setup_permissions` se conservan y pueden
seguir usándose por separado si no se desea la simulación completa.

---

## Paso 9 — Registrar los Servicios Satélite en la BD

Este paso es **crítico**: sin él, `scanning_service` y `reporting_excel` no podrán autenticarse con el backend Django.

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py register_services
```

Salida esperada:
```
  Creado: scanning_service con scopes ['lotes:read']
  Creado: reporting_excel con scopes ['reports:read']

Registro de servicios completado.
```

---

## Paso 10 — Verificación de Salud

```bash
# Health check del backend Django
curl -sf https://tudominio.com/api/health/ | python3 -m json.tool

# Esperado: {"status": "ok", ...}

# Health check del scanning_service (a través de Nginx)
curl -sf https://tudominio.com/api/scanning/health | python3 -m json.tool

# Logs en tiempo real de todos los servicios
docker compose -f docker-compose.prod.yml logs -f --tail=50
```

---

## Actualizaciones (Despliegue de Nueva Versión)

```bash
cd /opt/texcore

# 1. Obtener el último código
git pull origin master

# 2. Reconstruir solo los servicios que cambiaron (ejemplo: backend + nginx)
docker compose -f docker-compose.prod.yml up -d --build backend nginx

# 3. Ejecutar migraciones si hubo cambios de modelos
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 4. Verificar salud
curl -sf https://tudominio.com/api/health/
```

Para rotar los secrets de servicios satélite:

```bash
# 1. Actualizar SCANNING_SERVICE_SECRET y/o REPORTING_SERVICE_SECRET en .env
# 2. Re-registrar con --force
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py register_services --force

# 3. Reiniciar los servicios satélite para que lean el nuevo secret
docker compose -f docker-compose.prod.yml restart scanning reporting_excel
```

---

## Rollback

```bash
cd /opt/texcore

# Volver al commit anterior
git log --oneline -5          # identifica el commit anterior
git checkout <commit-anterior>

# Reconstruir y levantar
docker compose -f docker-compose.prod.yml up -d --build

# Si hay migraciones que revertir (raro, pero posible)
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate gestion <numero_migracion_anterior>
```

---

## Comandos de Mantenimiento Frecuentes

```bash
# Ver logs de un servicio específico
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f scanning

# Reiniciar un servicio sin reconstruir
docker compose -f docker-compose.prod.yml restart backend

# Detener todo (mantiene los volúmenes de datos)
docker compose -f docker-compose.prod.yml down

# Backup manual de la BD
docker compose -f docker-compose.prod.yml exec db \
  /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${DB_PASSWORD}" -C -N \
  -Q "BACKUP DATABASE [texcore_db] TO DISK='/var/opt/mssql/backup/texcore_$(date +%Y%m%d).bak'"

# Ver uso de disco de los volúmenes Docker
docker system df -v

# Limpiar imágenes no usadas (con precaución)
docker image prune -f --filter "until=72h"
```

---

## Renovación Automática de Certificados (Let's Encrypt)

```bash
# Agregar al crontab del servidor (cron de root)
sudo crontab -e

# Añadir esta línea:
0 3 * * 1 certbot renew --quiet && \
  cp /etc/letsencrypt/live/tudominio.com/fullchain.pem /opt/texcore/nginx/certs/nginx-selfsigned.crt && \
  cp /etc/letsencrypt/live/tudominio.com/privkey.pem /opt/texcore/nginx/certs/nginx-selfsigned.key && \
  docker compose -f /opt/texcore/docker-compose.prod.yml restart nginx
```

---

## Checklist de Despliegue

- [ ] Claves RSA generadas y guardadas en gestor de secretos
- [ ] Archivo `.env` creado con `chmod 600`
- [ ] `CI_REGISTRY_IMAGE=texcore` y `TAG=local` en `.env` (despliegue manual)
- [ ] Certificado SSL en `nginx/certs/`
- [ ] `docker compose -f docker-compose.prod.yml up -d --build` exitoso
- [ ] Todos los servicios en estado `Up` o `healthy`
- [ ] Migraciones ejecutadas sin errores
- [ ] `register_services` ejecutado y confirmado
- [ ] `setup_permissions` ejecutado (directo o vía `seed_data`)
- [ ] Decidido si corresponde `seed_data` (entorno demo/staging vacío) o solo
      `create_admin` + `setup_permissions` (base con datos reales de producción)
- [ ] `curl https://tudominio.com/api/health/` retorna `{"status": "ok"}`
- [ ] Login de usuario administrador funcional en el navegador
- [ ] Escaneo de lote de prueba funcional (si hay hardware disponible)
