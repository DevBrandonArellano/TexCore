# Módulo de Inventario

El módulo de **Inventory** gestiona el control de existencias, movimientos entre bodegas y la integración con servicios externos de escaneo y reportes.

## Responsabilidades
- **Stock en Bodega**: Control de saldos por producto, bodega y lote.
- **Movimientos de Inventario**: Registro de entradas, salidas, transferencias y ajustes.
- **Despachos**: Gestión de entrega de insumos a producción.
- **Integración de Escaneo**: Endpoints optimizados para el servicio satélite `scanning_service`.
- **Reportes de Inventario**: Lógica para la generación de reportes de saldos y trazabilidad.

## Integraciones
- **Scanning Service**: Recibe datos de escaneo de códigos de barras para procesar movimientos en tiempo real.
- **Reporting Excel**: Provee los datos crudos para la generación de libros de inventario en Excel.

## Estructura Principal
- `models.py`: `StockBodega` y `MovimientoInventario`.
- `services/`: Lógica de validación de stock y cálculos de saldos.
- `urls_scanning.py`: Rutas dedicadas para la API de escaneo.
