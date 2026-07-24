# Implementación del Módulo de Despacho con Microservicios

---

## 🎯 Objetivo

Implementar un sistema completo de gestión de despachos con arquitectura de microservicios, permitiendo el escaneo de códigos de barras/QR, validación en tiempo real, y trazabilidad completa de los despachos realizados.

---

## ✅ Funcionalidades Implementadas

### 1. Microservicio de Escaneo (`scanning_service`)

**Tecnología:** FastAPI + SQLAlchemy + Uvicorn · Puerto interno: 8000

**Estructura de capas (Sprint 7 — SOLID):**
```
scanning_service/src/
  schemas/validate.py          ← DTOs Pydantic (ValidateRequest, ValidateResponse)
  repositories/base.py         ← ILoteRepository Protocol (DIP)
  repositories/lote_repository.py ← SqlAlchemy implementation
  services/validation_service.py  ← LoteValidationService (3 reglas de negocio)
  routers/validate.py          ← POST /scanning/validate
  routers/health.py            ← GET /health (verifica BD real)
  main.py                      ← App factory
```

**Características:**
- Endpoint `POST /scanning/validate` con validación: existencia, stock > 0, info completa
- Endpoint `GET /health` verifica conexión real a SQL Server
- Tests unitarios (`tests/unit/`) sin `sys.modules` hacks — inyección via Protocol

---

### 2. Configuración de Nginx como API Gateway

**Archivo modificado:**
- `nginx/nginx.conf`

**Cambios:**
```nginx
location /api/scanning/ {
    proxy_pass http://scanning:8001/scanning/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**Beneficios:**
- ✅ Punto de entrada único para todos los servicios
- ✅ Enrutamiento transparente al microservicio
- ✅ Facilita la adición de nuevos microservicios en el futuro

---

### 3. Modelos de Historial de Despacho

**Archivo modificado:**
- `inventory/models.py`

**Modelos creados:**

#### `HistorialDespacho`
Registro maestro de cada despacho con:
- `fecha_despacho` - Timestamp automático
- `usuario` - Usuario responsable del despacho
- `pedidos_ids` - IDs de pedidos despachados (separados por coma)
- `total_bultos` - Cantidad total de bultos/lotes
- `total_peso` - Peso total despachado (kg)
- `observaciones` - Notas adicionales

#### `DetalleHistorialDespacho`
Detalle de cada lote despachado:
- `historial` - Referencia al despacho maestro
- `lote` - Lote despachado
- `producto` - Producto del lote
- `peso` - Peso del lote despachado
- `es_devolucion` - Flag para marcar devoluciones (preparado para futuro)

**Migración:**
- `inventory/migrations/0006_add_historial_despacho.py` - Creada y aplicada exitosamente

---

### 4. Actualización del Proceso de Despacho

**Archivo modificado:**
- `inventory/views.py` - `ProcessDespachoAPIView`

**Mejoras implementadas:**
1. **Registro automático de historial:**
   - Se crea `HistorialDespacho` al inicio de cada transacción
   - Cada lote se registra en `DetalleHistorialDespacho`
   
2. **Trazabilidad completa:**
   - `MovimientoInventario.documento_ref` ahora incluye el ID del despacho
   - Formato: `"Despacho #{id} (Pedidos: 1,2,3)"`
   
3. **Cálculo automático:**
   - Peso total se calcula sumando todos los lotes
   - Se actualiza en el registro maestro

4. **Atomicidad garantizada:**
   - Todo el proceso ocurre en una transacción
   - Si algo falla, se revierte completamente

---

### 5. Integración del Frontend

**Archivo modificado:**
- `frontend/src/components/despacho/DespachoDashboard.tsx`

**Cambios:**
- ✅ Endpoint de validación cambiado de `/inventory/validate-lote/` a `/scanning/validate`
- ✅ Mantenimiento de funcionalidad multi-orden
- ✅ Validación de cliente único por despacho
- ✅ Interfaz de escaneo en tiempo real

---

### 6. Orquestación con Docker Compose

**Archivo modificado:**
- `infrastructure/docker/docker-compose.prod.yml`

**Servicio añadido:**
```yaml
scanning:
  build:
    context: ./scanning_service
    dockerfile: Dockerfile
  environment:
    - DB_ENGINE=mssql+pyodbc
    - DB_NAME=texcore_db
    - DB_USER=sa
    - DB_PASSWORD=${DB_PASSWORD}
    - DB_HOST=db
    - DB_PORT=1433
    - DB_DRIVER=ODBC Driver 18 for SQL Server
  depends_on:
    - db
  networks:
    - texcore-network
```

---

### 7. Documentación

Ver [Análisis del Sistema de Despacho](ANALISIS_SISTEMA_DESPACHO.md) para la arquitectura completa, flujo paso a paso y modelo de datos.

---

## 📊 Arquitectura Resultante

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────┐
│   Frontend  │─────▶│    Nginx    │─────▶│ Scanning Service │
│   (React)   │      │ (API Gateway)│      │    (FastAPI)     │
└─────────────┘      └─────────────┘      └──────────────────┘
                            │                       │
                            │                       │
                            ▼                       ▼
                     ┌─────────────┐         ┌───────────┐
                     │   Backend   │         │  Database │
                     │  (Django)   │◀────────│ (MS SQL)  │
                     └─────────────┘         └───────────┘
```

---

## 📋 Próximos Pasos (Documentados en ROADMAP.md)

1. **API de Consulta de Historial** — `GET /api/inventory/despachos/` con paginación y filtros
2. **Vista de Historial en Frontend** — tabla con filtros por fecha, usuario, cliente
3. **Funcionalidad de Devoluciones** — endpoint + interfaz de escaneo + reversión de stock
4. **Tests automatizados E2E** del flujo completo

---

## 🔧 Comandos de Despliegue

### Construir y levantar servicios:
```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d --build
```

### Ver logs del microservicio:
```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml logs -f scanning
```

### Aplicar migraciones:
```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml exec backend python manage.py migrate
```

---

## Notas Técnicas

- Tablas `inventory_historialdespacho` y `inventory_detallehistorialdespacho` aplicadas en producción
- `scanning_service` accede a la BD directamente (SQLAlchemy); no pasa por Django ORM
- El campo `pedidos_ids` de `HistorialDespacho` almacena IDs separados por coma — candidato a normalizar en una tabla M2M en una iteración futura
