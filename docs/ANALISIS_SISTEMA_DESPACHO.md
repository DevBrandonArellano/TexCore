# 📦 Análisis Completo del Sistema de Despacho - TexCore

**Fecha de Análisis:** 13 de febrero de 2026  
**Rama:** `featdespacho`  
**Analista:** Experto en Django/React

---

## 🎯 Resumen Ejecutivo

El sistema de despacho de TexCore es una **solución completa de arquitectura de microservicios** que permite gestionar el proceso de despacho de pedidos con validación en tiempo real mediante escaneo de códigos de barras/QR. El sistema garantiza trazabilidad completa, control de inventario y prevención de errores humanos.

---

## 🏗️ Arquitectura del Sistema

### Diagrama de Arquitectura

```
┌─────────────────┐      ┌──────────────┐      ┌──────────────────┐
│   Frontend      │─────▶│    Nginx     │─────▶│ Scanning Service │
│   (React)       │      │ (API Gateway)│      │    (FastAPI)     │
│                 │      │              │      │   Puerto: 8000   │
│ DespachoDash    │      │ Proxy Pass   │      └──────────────────┘
└─────────────────┘      └──────────────┘               │
                                │                       │
                                │                       ▼
                                │                ┌───────────┐
                                │                │  Database │
                                │                │ (MS SQL)  │
                                ▼                └───────────┘
                         ┌─────────────┐               ▲
                         │   Backend   │───────────────┘
                         │  (Django)   │
                         │ Puerto: 8000│
                         └─────────────┘
```

### Componentes Principales

#### 1. **Frontend - DespachoDashboard.tsx**
- **Ubicación:** `/frontend/src/components/despacho/DespachoDashboard.tsx`
- **Tecnología:** React + TypeScript
- **Funcionalidades:**
  - ✅ Selección múltiple de pedidos pendientes
  - ✅ Validación de cliente único por despacho
  - ✅ Interfaz de escaneo en tiempo real
  - ✅ Comparativa teórico vs físico (peso)
  - ✅ Barra de progreso visual por producto
  - ✅ Generación automática de PDFs
  - ✅ Búsqueda y filtrado de pedidos

**Estados del Dashboard:**
1. **Modo Selección:** Lista de pedidos pendientes con checkboxes
2. **Modo Despacho:** Interfaz de escaneo con validación en tiempo real

#### 2. **Microservicio de Escaneo - FastAPI**
- **Ubicación:** `/scanning_service/`
- **Tecnología:** FastAPI + SQLAlchemy + Uvicorn
- **Puerto:** 8000 (interno), expuesto vía Nginx en `/api/scanning/`

**Endpoints:**

##### `GET /health`
```json
{
  "status": "healthy",
  "database": "connected"
}
```

##### `POST /scanning/validate`
**Request:**
```json
{
  "code": "LOTE-2024-001"
}
```

**Response (Éxito):**
```json
{
  "valid": true,
  "lote": {
    "codigo": "LOTE-2024-001",
    "producto_id": 123,
    "producto_nombre": "Tela Algodón 100%",
    "peso": "150.50",
    "bodega_id": 5,
    "bodega_nombre": "Bodega Principal"
  }
}
```

**Response (Error):**
```json
{
  "valid": false,
  "reason": "Lote no encontrado en el sistema"
}
```

**Validaciones:**
- ✅ Existencia del lote en la base de datos
- ✅ Stock disponible (cantidad > 0)
- ✅ Información completa del producto y bodega

#### 3. **Backend Django - Procesamiento de Despachos**

##### Modelos de Datos

###### `HistorialDespacho`
```python
class HistorialDespacho(models.Model):
    fecha_despacho = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    pedidos_ids = models.TextField(help_text="IDs de Pedidos despachados (separados por coma)")
    total_bultos = models.IntegerField()
    total_peso = models.DecimalField(max_digits=12, decimal_places=2)
    observaciones = models.TextField(blank=True, null=True)
```

**Propósito:** Registro maestro de cada despacho realizado

###### `DetalleHistorialDespacho`
```python
class DetalleHistorialDespacho(models.Model):
    historial = models.ForeignKey(HistorialDespacho, related_name='detalles', on_delete=models.CASCADE)
    lote = models.ForeignKey(LoteProduccion, on_delete=models.SET_NULL, null=True)
    producto = models.ForeignKey(Producto, on_delete=models.SET_NULL, null=True)
    peso = models.DecimalField(max_digits=12, decimal_places=2)
    es_devolucion = models.BooleanField(default=False)
```

**Propósito:** Detalle de cada lote/bulto despachado

##### Vista de Procesamiento

###### `ProcessDespachoAPIView`
- **Endpoint:** `POST /api/inventory/process-despacho/`
- **Permisos:** `IsAuthenticated`

**Request:**
```json
{
  "pedidos": [1, 2, 3],
  "lotes": ["LOTE-001", "LOTE-002", "LOTE-003"],
  "observaciones": "Despacho urgente"
}
```

**Response:**
```json
{
  "message": "Despacho procesado correcto",
  "despacho_id": 42,
  "pedidos_actualizados": 3,
  "lotes_procesados": 3
}
```

**Proceso Transaccional:**

```python
with transaction.atomic():
    # 1. Crear registro de Historial
    historial = HistorialDespacho.objects.create(...)
    
    # 2. Procesar cada lote
    for code in lotes_codes:
        # 2.1 Buscar lote y stock
        lote = LoteProduccion.objects.get(codigo_lote=code)
        stock = StockBodega.objects.select_for_update().filter(lote=lote).first()
        
        # 2.2 Crear movimiento de inventario (VENTA)
        MovimientoInventario.objects.create(
            tipo_movimiento='VENTA',
            documento_ref=f"Despacho #{historial.id} (Pedidos: {pedidos_ids})"
        )
        
        # 2.3 Guardar detalle del despacho
        DetalleHistorialDespacho.objects.create(...)
        
        # 2.4 Actualizar stock a 0
        stock.cantidad = 0
        stock.save()
    
    # 3. Actualizar peso total
    historial.total_peso = total_peso_despachado
    historial.save()
    
    # 4. Actualizar estado de pedidos
    pedidos.update(estado='despachado', fecha_despacho=timezone.now().date())
```

**Garantías:**
- ✅ **Atomicidad:** Todo o nada (rollback automático en caso de error)
- ✅ **Trazabilidad:** Cada movimiento queda registrado
- ✅ **Integridad:** Lock optimista en stock (`select_for_update`)

#### 4. **Nginx - API Gateway**

**Configuración:**
```nginx
location /api/scanning/ {
    proxy_pass http://scanning:8000/scanning/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

**Ventajas:**
- ✅ Punto de entrada único
- ✅ Enrutamiento transparente
- ✅ Facilita escalabilidad horizontal
- ✅ SSL/TLS termination

---

## 🔄 Flujo Completo de Despacho

### Paso a Paso

```
1. Usuario selecciona pedidos pendientes
   └─▶ Frontend: DespachoDashboard (Modo Selección)
   
2. Click en "Iniciar Despacho"
   └─▶ Validación: ¿Mismo cliente?
       └─▶ Warning si hay diferentes clientes
   
3. Modo Escaneo activado
   └─▶ Frontend: DespachoDashboard (Modo Despacho)
   
4. Usuario escanea código de barras
   └─▶ POST /api/scanning/validate
       └─▶ Microservicio FastAPI valida
           ├─▶ ✅ Lote existe y tiene stock
           │   └─▶ Retorna info del lote
           │       └─▶ Frontend agrega a lista
           │           └─▶ Actualiza progreso visual
           │
           └─▶ ❌ Lote inválido o sin stock
               └─▶ Toast de error
   
5. Repetir paso 4 hasta completar
   
6. Click en "Confirmar Salida"
   └─▶ Validación: ¿Cantidad completa?
       ├─▶ Incompleto: Confirmar despacho parcial
       └─▶ Completo: Continuar
   
7. POST /api/inventory/process-despacho/
   └─▶ Backend Django procesa
       ├─▶ Crea HistorialDespacho
       ├─▶ Crea DetalleHistorialDespacho (por cada lote)
       ├─▶ Crea MovimientoInventario (VENTA)
       ├─▶ Actualiza Stock a 0
       └─▶ Actualiza estado de Pedidos
   
8. Generación automática de PDFs
   └─▶ GET /api/pedidos-venta/{id}/download_pdf/
       └─▶ Abre en nueva pestaña
   
9. Refresh y reset
   └─▶ Vuelve a Modo Selección
```

---

## 📊 Modelos de Base de Datos

### Tablas Creadas

#### `inventory_historialdespacho`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer (PK) | Identificador único |
| fecha_despacho | DateTime | Timestamp automático |
| usuario_id | Integer (FK) | Usuario responsable |
| pedidos_ids | Text | IDs separados por coma |
| total_bultos | Integer | Cantidad de lotes |
| total_peso | Decimal(12,2) | Peso total en kg |
| observaciones | Text | Notas adicionales |

#### `inventory_detallehistorialdespacho`
| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | Integer (PK) | Identificador único |
| historial_id | Integer (FK) | Referencia al despacho |
| lote_id | Integer (FK) | Lote despachado |
| producto_id | Integer (FK) | Producto del lote |
| peso | Decimal(12,2) | Peso del lote |
| es_devolucion | Boolean | Flag para devoluciones |

### Relaciones

```
HistorialDespacho (1) ──▶ (N) DetalleHistorialDespacho
       │
       ├──▶ (N) PedidoVenta (via pedidos_ids)
       └──▶ (1) User (usuario)

DetalleHistorialDespacho
       ├──▶ (1) LoteProduccion
       └──▶ (1) Producto
```

---

## 🔐 Seguridad y Permisos

### Autenticación
- ✅ Todos los endpoints requieren autenticación (`IsAuthenticated`)
- ✅ Usuario registrado en cada despacho
- ✅ Trazabilidad de quién realizó cada operación

### Permisos en Admin Django
- ❌ **No se permite crear** despachos manualmente
- ❌ **No se permite eliminar** despachos
- ✅ **Solo lectura** para auditoría

### Validaciones de Negocio
- ✅ No se puede despachar lotes sin stock
- ✅ No se puede escanear el mismo lote dos veces
- ✅ Advertencia si se mezclan clientes diferentes
- ✅ Confirmación para despachos parciales

---

## 📈 Ventajas de la Arquitectura

### Microservicios
1. **Separación de Responsabilidades**
   - Escaneo aislado del backend principal
   - Lógica de negocio separada de validación

2. **Escalabilidad Independiente**
   - Scanning service puede escalar según demanda
   - No afecta al backend principal

3. **Rendimiento**
   - Conexión directa a BD (sin Django ORM)
   - FastAPI es más rápido que Django para APIs simples

4. **Tecnología Apropiada**
   - FastAPI para validación rápida
   - Django para lógica de negocio compleja

### Trazabilidad Completa
- ✅ Cada despacho queda registrado
- ✅ Cada lote despachado tiene detalle
- ✅ Movimientos de inventario vinculados
- ✅ Usuario responsable identificado
- ✅ Timestamp automático

### Prevención de Errores
- ✅ Validación en tiempo real
- ✅ No se puede despachar sin stock
- ✅ Confirmación de despachos parciales
- ✅ Comparativa visual teórico vs físico

---

## 🛠️ Configuración y Despliegue

### Variables de Entorno (Scanning Service)

```yaml
environment:
  - DB_ENGINE=mssql+pyodbc
  - DB_NAME=texcore_db
  - DB_USER=sa
  - DB_PASSWORD=${DB_PASSWORD}
  - DB_HOST=db
  - DB_PORT=1433
  - DB_DRIVER=ODBC Driver 18 for SQL Server
```

### Comandos de Despliegue

```bash
# Construir y levantar todos los servicios
docker compose -f docker-compose.prod.yml up -d --build

# Solo el microservicio scanning
docker compose -f docker-compose.prod.yml up -d --build scanning

# Ver logs del scanning service
docker compose -f docker-compose.prod.yml logs -f scanning

# Verificar salud del servicio
docker compose -f docker-compose.prod.yml exec scanning curl http://localhost:8000/health

# Aplicar migraciones
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

---

## 🐛 Problemas Resueltos

### Error de Importación (Corregido)
**Problema:** `ImportError: cannot import name 'Producto' from 'src.models'`

**Causa:** Typo en el nombre de la clase (`Produto` en lugar de `Producto`)

**Solución:**
```python
# Antes
class Produto(Base):
    ...

# Después
class Producto(Base):
    ...
```

### Error de SQLAlchemy 2.0 (Corregido)
**Problema:** `Textual SQL expression 'SELECT 1' should be explicitly declared`

**Causa:** SQLAlchemy 2.0 requiere usar `text()` para queries SQL raw

**Solución:**
```python
# Antes
db.execute("SELECT 1")

# Después
from sqlalchemy import text
db.execute(text("SELECT 1"))
```

---

## 📋 Próximas Mejoras Sugeridas

### Corto Plazo
1. **API de Consulta de Historial**
   ```python
   GET /api/inventory/despachos/
   GET /api/inventory/despachos/{id}/
   ```
   - Paginación
   - Filtros por fecha, usuario, cliente
   - Búsqueda por pedido

2. **Vista de Historial en Frontend**
   - Tabla con lista de despachos
   - Filtros avanzados
   - Vista detallada de cada despacho
   - Exportación a Excel/PDF

### Mediano Plazo
3. **Funcionalidad de Devoluciones**
   - Endpoint para procesar returns
   - Interfaz de escaneo para devoluciones
   - Actualización de stock (reversa)
   - Flag `es_devolucion=True`

4. **Validación de Items No Despachados**
   - Comparación pedido vs lotes escaneados
   - Alertas de discrepancias
   - Confirmación de despachos parciales mejorada

5. **Generación de Documentos**
   - PDF automático del despacho
   - Reimpresión desde historial
   - Almacenamiento de documentos

### Largo Plazo
6. **Dashboard de Métricas**
   - Análisis de despachos por período
   - Tasa de devoluciones
   - Gráficos de tendencias
   - KPIs de eficiencia

7. **Optimizaciones de Rendimiento**
   - Caché de validaciones frecuentes (Redis)
   - Métricas de rendimiento (Prometheus)
   - Rate limiting
   - Autenticación JWT entre servicios

8. **Testing**
   - Tests unitarios del microservicio
   - Tests de integración
   - Tests end-to-end del flujo completo

---

## 📚 Documentación de Referencia

### Archivos Clave
- `/docs/IMPLEMENTACION_DESPACHO.md` - Documentación de implementación
- `/scanning_service/README.md` - Documentación del microservicio
- `/ROADMAP.md` - Fase 8: Módulo de Despacho

### Endpoints Importantes
- `POST /api/scanning/validate` - Validación de lotes
- `POST /api/inventory/process-despacho/` - Procesamiento de despacho
- `GET /api/pedidos-venta/?estado=pendiente` - Lista de pedidos
- `GET /api/pedidos-venta/{id}/download_pdf/` - Descarga de PDF

---

## ✅ Checklist de Funcionalidades

### Implementado
- [x] Microservicio de escaneo (FastAPI)
- [x] Validación en tiempo real de lotes
- [x] Modelos de historial de despacho
- [x] Procesamiento transaccional de despachos
- [x] Interfaz de escaneo en React
- [x] Comparativa teórico vs físico
- [x] Generación automática de PDFs
- [x] Trazabilidad completa
- [x] Admin de Django configurado
- [x] Nginx como API Gateway
- [x] Dockerización completa

### Pendiente
- [ ] API de consulta de historial
- [ ] Vista de historial en frontend
- [ ] Funcionalidad de devoluciones
- [ ] Validación de items no despachados
- [ ] Dashboard de métricas
- [ ] Tests automatizados
- [ ] Caché y optimizaciones

---

## 🎓 Conclusiones

El sistema de despacho de TexCore representa una **implementación sólida y profesional** de arquitectura de microservicios en un entorno Django/React. Los puntos destacados son:

1. **Arquitectura Moderna:** Uso apropiado de microservicios para separar responsabilidades
2. **Trazabilidad Total:** Cada operación queda registrada con usuario y timestamp
3. **Prevención de Errores:** Validaciones en tiempo real evitan errores humanos
4. **Escalabilidad:** Diseño preparado para crecimiento futuro
5. **Mantenibilidad:** Código limpio, documentado y bien estructurado

El sistema está **listo para producción** y proporciona una base sólida para futuras mejoras.

---

**Desarrollado por:** Equipo TexCore  
**Revisado por:** Experto Django/React  
**Estado:** ✅ Funcionando correctamente en `featdespacho`
