# Implementación del Módulo de Despacho con Servicios Satélite

---

## 🎯 Objetivo

Implementar un sistema completo de gestión de despachos con arquitectura de monolito Django y servicios satélite, permitiendo el escaneo de códigos de barras/QR, validación en tiempo real, y trazabilidad completa de los despachos realizados.

---

## ✅ Funcionalidades Implementadas

### 1. Servicio Satélite de Escaneo (`scanning_service`)

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
- ✅ Enrutamiento transparente al servicio satélite
- ✅ Facilita la adición de nuevos servicios satélite en el futuro

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

1. ✅ **API de Consulta de Historial** — `GET /api/inventory/historial-despachos/` (filtros por fecha)
2. ✅ **Vista de Historial en Frontend** — `HistorialDespachos.tsx`, con filtros por fecha e impresión
   (ver actualización 2026-08-25 abajo)
3. ✅ **Funcionalidad de Devoluciones** — implementada como reversión de despacho, ver
   [REVERSION_DESPACHO.md](REVERSION_DESPACHO.md)
4. **Tests automatizados E2E** del flujo completo — pendiente

---

## 🔧 Comandos de Despliegue

### Construir y levantar servicios:
```bash
docker compose -f infrastructure/docker/docker-compose.prod.yml up -d --build
```

### Ver logs del servicio satélite:
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

---

## Actualización 2026-08-25 — Despacho parcial, Guía de Remisión e Historial imprimible

### Despacho parcial robusto (ya no todo-o-nada)

Bug reportado: despachar solo parte de un pedido lo marcaba como `despachado` completo, y un segundo
despacho para completar lo que faltaba volvía a pedir el 100% original en vez de solo lo restante.

- Nuevo estado `despachado_parcial` en `PedidoVenta.ESTADO_CHOICES`.
- Nueva FK `DetalleHistorialDespacho.pedido` — cada lote escaneado se asigna al pedido correcto
  (asignación FIFO por producto, en el orden de los pedidos recibido) incluso cuando un despacho
  cubre varios pedidos a la vez. Esto también corrigió que
  `DetalleHistorialDespachoPedido.cantidad_despachada` (documentado arriba como parte del modelo)
  quedaba siempre hardcodeado en `0` — ahora refleja el peso real asignado a cada pedido.
- `inventory/services/despacho_estado.py::DespachoEstadoService` (nuevo, compartido con la
  reversión — ver [REVERSION_DESPACHO.md](REVERSION_DESPACHO.md)) decide el estado real del pedido
  comparando lo despachado (no revertido) contra lo requerido.
- `_calcular_incompletos` resta lo ya despachado en intentos previos no revertidos.
- El filtro `?estado=` de `PedidoVentaViewSet` acepta ahora múltiples valores separados por coma —
  Despacho pide `?estado=pendiente,despachado_parcial` para que los pedidos parciales sigan en cola.

### Guía de Remisión (documento informativo, no autorizado por el SRI)

A pedido del rol Despacho, y tras investigar los requisitos del SRI (Ecuador) para el traslado de
mercadería. Como `gestion/tests/test_anticipos_pagos_parciales_p1.py` ya documentaba que "la
facturación SRI la maneja software externo; TexCore solo registra pagos", se implementó como
documento **informativo** (mismo patrón que la nota de venta: PDF generado por `printing_service`,
sin clave de acceso ni firma digital) — no un comprobante electrónico autorizado.

- `HistorialDespachoViewSet.guia_remision` (`POST /historial-despachos/{id}/guia-remision/`) — valida
  datos de transporte que el sistema no capturaba (motivo del traslado, punto de partida, fechas de
  transporte, placa, transportista) y arma destinatarios/mercadería desde los datos reales del
  despacho. Nuevo setting `EMPRESA_RUC` (opcional, solo para mostrar en la guía).
- Frontend: `GuiaRemisionModal.tsx`, botón por fila en `HistorialDespachos.tsx`.

### Historial de Despachos imprimible

- `HistorialDespachoViewSet.imprimir` (`GET /historial-despachos/imprimir/?fecha_desde=&fecha_hasta=`)
  — PDF del listado con los mismos filtros de fecha que ya tenía `list()`.
- `PedidoVentaViewSet.download_pdf` acepta `?historial_id=` — la nota de venta impresa justo después
  de un despacho ahora lista solo lo realmente despachado en ese evento, no el pedido completo.
- Botón "Imprimir Historial" en `HistorialDespachos.tsx` (respeta los filtros de fecha activos).

### Tests nuevos

```
inventory/tests/test_process_despacho.py        # 5 tests: completo/parcial/multi-pedido/reversión E2E
inventory/tests/test_despacho_documentos.py     # 8 tests: imprimir historial + guía de remisión
gestion/tests/test_sales_views_extra.py         # +3: filtro multi-estado, nota de venta por historial_id
printing_service/tests/unit/test_printing_endpoints.py  # +5: historial-despachos.html, guia_remision.html
```
- El campo `pedidos_ids` de `HistorialDespacho` almacena IDs separados por coma — candidato a normalizar en una tabla M2M en una iteración futura
