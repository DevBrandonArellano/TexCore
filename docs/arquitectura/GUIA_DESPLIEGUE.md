# Guía de despliegue y operación en producción — TexCore

Única guía para instalar TexCore en un servidor nuevo, actualizarlo y operarlo. Reemplaza a las antiguas `GUIA_SERVIDOR_UBUNTU.md`, `PLAN_DESPLIEGUE_PRODUCCION_TEXCORE.md` y `COMANDOS_OPERACION.md`.

**Fuente de verdad:** `infrastructure/docker/docker-compose.prod.yml`, `.env.prod.example` y `scripts/deploy_production.sh` / `.ps1`. La prueba `gestion/tests/test_despliegue_produccion.py` verifica que los tres coincidan.

---

## 1. Qué se despliega

Seis contenedores, en el proyecto de Compose `texcore-prod`:

| Servicio | Imagen | Función | Expuesto |
|---|---|---|---|
| `nginx` | `nginx/Dockerfile` (incluye el frontend compilado) | Única entrada. El 80 redirige con 301 a HTTPS; el 443 sirve React y enruta `/api/` | 80 y 443 |
| `backend` | `infrastructure/docker/Dockerfile.prod` | Django + DRF con Gunicorn | No |
| `db` | `database/Dockerfile` | SQL Server 2022 | No |
| `scanning` | `scanning_service/` | Validación de escaneo de lotes (FastAPI) | No (vía nginx) |
| `printing` | `printing_service/` | PDF y etiquetas ZPL (FastAPI) | No |
| `reporting_excel` | `reporting_excel/` | Formato de reportes en Excel (FastAPI) | No |

**Redes:**
- `dmz_net`: nginx, backend y scanning.
- `internal_net` (sin salida a internet): db, printing, reporting_excel y backend, que hace de puente.

Cada imagen tiene su `HEALTHCHECK`. El compose de producción **no** incluye Redis ni Celery: la exportación asíncrona de reportes queda deshabilitada y los reportes se generan al momento.

---

## 2. Requisitos del servidor

Dimensionamiento medido con 3 años de operación simulada (`REQUISITOS_INFRAESTRUCTURA.md`):

| Usuarios concurrentes | vCPU | RAM | Disco |
|---|---|---|---|
| Hasta 100 | 8 | 10 GB | 80 GB |
| Hasta 250 | 12–14 | 14–16 GB | 80 GB |

- **SO:** Ubuntu Server 22.04 o 24.04 LTS (en la organización, VM de Hyper-V) con IP estática.
- **Software:** Docker Engine 24+ con el plugin Compose 2.21+ (necesario para `up --wait-timeout`) y Git.
- **Puertos:** 80 y 443 hacia los usuarios; 22 solo para administración.

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER        # cerrar sesión y volver a entrar
docker compose version               # 2.21 o superior
sudo apt install -y git
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp && sudo ufw enable
```

---

## 3. Instalación

### 3.1 Código

```bash
sudo mkdir -p /opt/texcore && sudo chown $USER /opt/texcore
git clone https://github.com/<organización>/TexCore.git /opt/texcore
cd /opt/texcore
git checkout master        # o la etiqueta de la versión a desplegar
```

### 3.2 Secretos y `.env.prod`

```bash
cp .env.prod.example .env.prod
chmod 600 .env.prod
```

Completa cada valor del archivo. Cada variable está comentada en el propio ejemplo.

| Valor | Cómo generarlo |
|---|---|
| `SECRET_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `FIELD_ENCRYPTION_KEYS` | `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — **guárdala también fuera del servidor: sin ella los datos personales cifrados no se recuperan** |
| `BLIND_INDEX_KEY` | `python3 -c "import secrets; print(secrets.token_urlsafe(32))"` — estable; cambiarla obliga a `manage.py cifrar_datos_personales --recalcular-indices` |
| `INTERNAL_JWT_PRIVATE_KEY` / `INTERNAL_JWT_PUBLIC_KEY` | `docker run --rm -v "$PWD":/app -w /app python:3.12-slim sh -c "pip install -q cryptography && python scripts/generate_rsa_keys.py"` |
| `SCANNING_SERVICE_SECRET` / `REPORTING_SERVICE_SECRET` | `python3 -c "import secrets; print(secrets.token_urlsafe(40))"`, uno distinto para cada servicio |
| `DB_PASSWORD` | Contraseña fuerte para la cuenta `sa` de SQL Server |
| `MSSQL_PID` | Edición licenciada por la organización (`Standard` o `Enterprise`) |
| `REDIS_PASSWORD` | `openssl rand -hex 24` — solo hexadecimal, porque va dentro de la URL del broker de Celery |

Además:
- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS` y `TRAZABILIDAD_BASE_URL` usan el dominio o la IP real del servidor, con `https://`. El primer valor de `ALLOWED_HOSTS` es el que usa el `HEALTHCHECK` del backend.
- Los recursos (`DB_CPUS`, `BACKEND_WORKERS`, `CELERY_*`…) vienen con los valores medidos para el uso previsto: 50 personas conectadas y unas 10 trabajando a la vez, validado con 20. Para más usuarios, ver `REQUISITOS_INFRAESTRUCTURA.md` §3.2.

Guarda las claves y contraseñas en el gestor de secretos de la organización. `.env.prod` está en `.gitignore`: nunca se versiona.

### 3.3 Certificado TLS

nginx lee `nginx/certs/nginx-selfsigned.crt` y `nginx/certs/nginx-selfsigned.key`. Acepta TLS 1.2 y 1.3, con HSTS.

**Dominio real (Let's Encrypt):**

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d texcore.tudominio.com
sudo cp /etc/letsencrypt/live/texcore.tudominio.com/fullchain.pem nginx/certs/nginx-selfsigned.crt
sudo cp /etc/letsencrypt/live/texcore.tudominio.com/privkey.pem   nginx/certs/nginx-selfsigned.key
sudo chown $USER nginx/certs/* && chmod 600 nginx/certs/nginx-selfsigned.key
```

**Red interna o IP** (el navegador pedirá aceptar el certificado):

```bash
openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
  -keyout nginx/certs/nginx-selfsigned.key -out nginx/certs/nginx-selfsigned.crt \
  -subj "/CN=192.168.1.10" -addext "subjectAltName=IP:192.168.1.10"
chmod 600 nginx/certs/nginx-selfsigned.key
```

### 3.4 Despliegue

```bash
bash scripts/deploy_production.sh          # Windows: scripts\deploy_production.ps1
```

El script:
1. construye las imágenes;
2. levanta los seis servicios y espera, con `up --wait`, a que todos pasen su `HEALTHCHECK`;
3. ejecuta `seed_production_masters`: crea los 11 grupos RBAC con sus permisos y la cuenta `admin`, con una contraseña aleatoria que **imprime una sola vez**. Anótala y cámbiala en el primer ingreso.

En **cada arranque**, el backend ejecuta `infrastructure/docker/entrypoint.sh`:
1. `scripts/create_db.py`: crea `texcore_db` si no existe;
2. `migrate`;
3. `apply_sql_optimizations`, que aplica:
   - `database/V2`: RCSI, CHECK constraints, índices filtrados y columnstore;
   - `V4` y `V5`: índices de reportes y MES;
   - `V6`: elimina los stored procedures obsoletos;
4. `register_services`: credenciales de `scanning_service` y `reporting_excel`.

Todo es idempotente. Los archivos estáticos se recolectan al construir la imagen.

> **Al actualizar una base que ya tiene datos:** la migración `gestion/0010` cifra los
> datos personales en reposo (RS-19). Exige `FIELD_ENCRYPTION_KEYS` y `BLIND_INDEX_KEY`
> en el entorno —sin ellas el backend no arranca— y **borra las columnas en claro**, así
> que la marcha atrás requiere restaurar el respaldo. Tómalo antes
> (`scripts/respaldar_bd.sh`) y comprueba el resultado después con
> `tc exec backend python manage.py cifrar_datos_personales`, que no escribe nada y falla
> si quedó algo sin cifrar. Detalle en `CIFRADO_DATOS_PERSONALES.md` §5.

Las sedes y las áreas **no se precargan**: el Administrador de Sistemas las crea en su primer ingreso. Después, cada Administrador de Sede registra las equivalencias de empaque de su sede.

### 3.5 Verificación

```bash
alias tc='docker compose -p texcore-prod -f infrastructure/docker/docker-compose.prod.yml --env-file .env.prod'
tc ps                                             # los 6 en "healthy"
curl -sI http://<host>/ | head -3                 # 301 hacia https://
curl -sk https://<host>/api/health/               # {"status": "ok"}
curl -sk https://<host>/api/scanning/health       # scanning_service a través de nginx
```

Después, en el navegador:
1. ingresar como `admin`;
2. crear la primera sede y sus áreas;
3. crear los usuarios por rol.

La ficha de trazabilidad (`/trazabilidad/<código>`, la que abre el QR) solo responde desde la red interna. nginx la limita a `192.168.1.0/24`; si la red de la planta es otra, ajusta las reglas `allow` de `location /trazabilidad` en `nginx/nginx.conf`.

---

## 4. Operación

Los comandos usan el alias `tc` de la sección 3.5, ejecutados desde `/opt/texcore`.

| Tarea | Comando |
|---|---|
| Estado | `tc ps` |
| Logs (todos / uno) | `tc logs -f --tail=100` · `tc logs -f backend` |
| Reiniciar un servicio | `tc restart backend` |
| Consola de Django | `tc exec backend python manage.py shell` |
| Detener (conserva los datos) | `tc down` |
| Uso de recursos | `docker stats` |
| Limpiar imágenes viejas | `docker image prune -f --filter "until=168h"` |

`tc down -v` **borra los volúmenes**, incluida la base de datos: no se usa en producción.

### 4.1 Actualizar a una versión nueva

1. Respalda la base (sección 4.3).
2. Actualiza el código:

   ```bash
   git fetch --tags && git checkout <nueva-versión>
   tc build --pull && tc up -d --wait --wait-timeout 900
   ```

Las migraciones se aplican solas al arrancar el backend. Si la versión trae migraciones que cambian columnas existentes (consulta el CHANGELOG), pruébalas antes sobre una copia restaurada del respaldo y mide su duración para planificar la ventana. Así se hizo con la `gestion/0005`, que tardó 37 s sobre ~1 M de auditorías.

### 4.2 Arranque automático

```ini
# /etc/systemd/system/texcore.service
[Unit]
Description=TexCore
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/texcore
ExecStart=/usr/bin/docker compose -p texcore-prod -f infrastructure/docker/docker-compose.prod.yml --env-file .env.prod up -d
ExecStop=/usr/bin/docker compose -p texcore-prod -f infrastructure/docker/docker-compose.prod.yml --env-file .env.prod down

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now texcore.service
```

Además, cada contenedor tiene `restart: always`.

### 4.3 Respaldos

El respaldo se hace dentro del contenedor `db` con su propia variable `MSSQL_SA_PASSWORD`, así que no hace falta leer `.env.prod`:

```bash
#!/bin/bash
# /opt/texcore/scripts-locales/respaldo.sh — programar en cron: 0 2 * * * (diario 2 a. m.)
set -euo pipefail
cd /opt/texcore
FECHA=$(date +%Y%m%d_%H%M)
COMPOSE="docker compose -p texcore-prod -f infrastructure/docker/docker-compose.prod.yml --env-file .env.prod"
$COMPOSE exec -T db bash -c "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -N \
  -Q \"BACKUP DATABASE [texcore_db] TO DISK=N'/var/opt/mssql/backup/texcore_${FECHA}.bak' WITH COMPRESSION, INIT\""
mkdir -p /var/backups/texcore
$COMPOSE cp db:/var/opt/mssql/backup/texcore_${FECHA}.bak /var/backups/texcore/
$COMPOSE exec -T db rm -f /var/opt/mssql/backup/texcore_${FECHA}.bak
find /var/backups/texcore -name 'texcore_*.bak' -mtime +7 -delete
```

Copia `/var/backups/texcore` fuera del servidor (otro equipo o almacenamiento de la organización).

**Restauración:**

```bash
tc stop backend scanning
tc cp /var/backups/texcore/texcore_<fecha>.bak db:/var/opt/mssql/backup/restaurar.bak
tc exec -T -u 0 db chown mssql:mssql /var/opt/mssql/backup/restaurar.bak   # docker cp lo deja ilegible para SQL Server
tc exec -T db bash -c "/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P \"\$MSSQL_SA_PASSWORD\" -C -N \
  -Q \"ALTER DATABASE [texcore_db] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; \
RESTORE DATABASE [texcore_db] FROM DISK=N'/var/opt/mssql/backup/restaurar.bak' WITH REPLACE; \
ALTER DATABASE [texcore_db] SET MULTI_USER\""
tc up -d --wait
```

### 4.4 Rotación de secretos

- **Secretos de servicio:** se cambian `SCANNING_SERVICE_SECRET` y/o `REPORTING_SERVICE_SECRET` en `.env.prod`, luego `tc exec backend python manage.py register_services --force` y `tc up -d --force-recreate scanning reporting_excel`.
- **Par RSA:** se cambian las dos claves y se recrean todos los servicios (`tc up -d --force-recreate`).

### 4.5 Renovación del certificado (Let's Encrypt)

```cron
0 3 * * 1 certbot renew --quiet && cp /etc/letsencrypt/live/texcore.tudominio.com/fullchain.pem /opt/texcore/nginx/certs/nginx-selfsigned.crt && cp /etc/letsencrypt/live/texcore.tudominio.com/privkey.pem /opt/texcore/nginx/certs/nginx-selfsigned.key && cd /opt/texcore && docker compose -p texcore-prod -f infrastructure/docker/docker-compose.prod.yml --env-file .env.prod restart nginx
```

---

## 5. Rollback

- **Con CI/CD:** el job manual `rollback:produccion` de `.gitlab-ci.yml` vuelve a la versión anterior con un clic. Al lanzarlo se indica `ROLLBACK_SHA` (vacío usa las imágenes `:backup`; con un SHA se verifica la firma) y `ROLLBACK_MOTIVO`, que queda registrado. Detalle en `GUIA_GITLAB.md` §9.
- **Manual:**
  1. `git checkout <versión-anterior>`, `tc build` y `tc up -d --wait`.
  2. Si la versión que se revierte aplicó migraciones, restaura el respaldo tomado antes de actualizar (sección 4.3): las migraciones de datos no siempre son reversibles.

---

## 6. Solución de problemas

| Síntoma | Causa probable y solución |
|---|---|
| `backend` queda `unhealthy` | Revisa `tc logs backend`. El primer arranque sobre una base grande puede tardar varios minutos aplicando migraciones (el `HEALTHCHECK` concede 600 s). Si responde 400, el primer valor de `ALLOWED_HOSTS` no es el host del servidor. |
| 403 CSRF al entrar al admin de Django | `CSRF_TRUSTED_ORIGINS` debe incluir el origen con `https://`. |
| 502 Bad Gateway | El backend está caído o reiniciando: `tc ps` y `tc logs backend`. |
| 429 Too Many Requests al iniciar sesión | Límite de nginx: 5 intentos por minuto por IP en `/api/token/`. Esperar un minuto. |
| El QR no abre la ficha | La trazabilidad solo responde desde la red interna (`location /trazabilidad` en `nginx/nginx.conf`). |
| PDF o etiquetas con 503 | `printing` no está sano o no tiene la clave pública: `tc logs printing`. |
| Advertencia de certificado | Certificado autofirmado: es lo esperado en red interna; usa Let's Encrypt con un dominio real. |
| `db` sin memoria | `DB_MEMORY_LIMIT_MB` debe coincidir con la RAM asignada (el compose fija también `MSSQL_MEMORY_LIMIT_MB`). |

---

## 7. Lista de verificación

- [ ] Servidor dimensionado según la sección 2, con IP estática y firewall (22, 80, 443).
- [ ] `.env.prod` completo con `chmod 600`; secretos guardados en el gestor de la organización.
- [ ] Certificado en `nginx/certs/`.
- [ ] `scripts/deploy_production.sh` terminado sin errores y los 8 contenedores en `healthy` (los 6 de la aplicación más `redis` y `celery_worker`).
- [ ] Contraseña inicial de `admin` anotada y cambiada.
- [ ] `http://` responde 301 y `https://<host>/api/health/` responde `ok`.
- [ ] Primera sede, sus áreas y equivalencias de empaque creadas; usuarios por rol creados.
- [ ] Respaldo diario programado y probado con una restauración.
- [ ] Arranque automático (systemd) habilitado.
