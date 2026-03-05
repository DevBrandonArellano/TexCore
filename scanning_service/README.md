# Microservicio de Escaneo - TexCore

## Descripción

Microservicio independiente desarrollado en **FastAPI** para la validación de códigos de barras/QR de lotes de producción durante el proceso de despacho. Este servicio se comunica directamente con la base de datos para verificar la existencia y disponibilidad de stock de los lotes escaneados.

## Arquitectura

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

## Características

- ✅ **Validación en tiempo real** de códigos de lotes
- ✅ **Verificación de stock** disponible en bodegas
- ✅ **Respuestas rápidas** con conexión directa a la base de datos
- ✅ **Arquitectura desacoplada** del backend principal
- ✅ **Escalabilidad independiente** del resto de servicios
- ✅ **Dockerizado** para fácil despliegue

## Endpoints

### `POST /scanning/validate`

Valida un código de lote escaneado y retorna información del producto y stock disponible.

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

**Response (Error - Lote no encontrado):**
```json
{
  "valid": false,
  "reason": "Lote no encontrado en el sistema"
}
```

**Response (Error - Sin stock):**
```json
{
  "valid": false,
  "reason": "Lote existe pero no tiene stock disponible (0 kg)"
}
```

## Tecnologías

- **FastAPI** - Framework web moderno y de alto rendimiento
- **SQLAlchemy** - ORM para interacción con la base de datos
- **Uvicorn** - Servidor ASGI de alto rendimiento
- **pyodbc** - Driver ODBC para MS SQL Server
- **Pydantic** - Validación de datos y serialización

## Estructura del Proyecto

```
scanning_service/
├── Dockerfile              # Configuración de contenedor Docker
├── requirements.txt        # Dependencias Python
└── src/
    ├── main.py            # Aplicación FastAPI principal
    ├── database.py        # Configuración de conexión a BD
    └── models.py          # Modelos SQLAlchemy
```

## Configuración

El servicio se configura mediante variables de entorno definidas en `docker-compose.prod.yml`:

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

## Despliegue

El servicio se despliega automáticamente como parte del stack de Docker Compose:

```bash
docker-compose -f docker-compose.prod.yml up -d scanning
```

## Integración con Nginx

Nginx actúa como API Gateway, enrutando las peticiones al microservicio:

```nginx
location /api/scanning/ {
    proxy_pass http://scanning:8001/scanning/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## Modelos de Datos

El servicio accede a las siguientes tablas (solo lectura):

- **`gestion_producto`** - Información de productos
- **`gestion_bodega`** - Información de bodegas
- **`gestion_loteproduccion`** - Lotes de producción
- **`inventory_stockbodega`** - Stock disponible por bodega

## Ventajas de la Arquitectura de Microservicios

1. **Separación de Responsabilidades**: La lógica de escaneo está aislada del backend principal
2. **Escalabilidad**: Se puede escalar independientemente según la demanda de escaneos
3. **Rendimiento**: Conexión directa a la BD sin pasar por Django ORM
4. **Mantenibilidad**: Código más simple y enfocado en una única responsabilidad
5. **Tecnología Apropiada**: FastAPI es ideal para APIs de alto rendimiento

## Monitoreo

El servicio expone logs estándar que pueden ser monitoreados:

```bash
docker-compose -f docker-compose.prod.yml logs -f scanning
```

## Desarrollo Local

Para desarrollo local, el servicio puede ejecutarse directamente:

```bash
cd scanning_service
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8001
```

## Próximas Mejoras

- [ ] Implementar caché de validaciones frecuentes
- [ ] Añadir métricas de rendimiento (Prometheus)
- [ ] Implementar rate limiting
- [ ] Añadir autenticación JWT
- [ ] Crear tests unitarios y de integración

## Seguridad

- ✅ Acceso de solo lectura a la base de datos
- ✅ Validación de entrada con Pydantic
- ✅ Comunicación interna a través de red Docker
- ⚠️ Pendiente: Implementar autenticación entre servicios

## Contacto y Soporte

Para reportar problemas o sugerencias relacionadas con el microservicio de escaneo, contactar al equipo de desarrollo de TexCore.
