# Microservicio de Impresión y Reportes (Printing Service)

Se ha incorporado un nuevo microservicio dedicado para la generación de documentos PDF (Notas de Venta) y etiquetas ZPL (Código de Barras), desacoplando esta lógica pesada del núcleo principal de Django.

## Arquitectura

*   **Tecnología**: Python + FastAPI
*   **Motor PDF**: `WeasyPrint` + `Jinja2` (HTML Templates)
*   **Motor ZPL**: Plantillas nativas ZPL dinámicas
*   **Puerto Interno**: `8001`
*   **Comunicación**: REST API (HTTP POST) desde el Backend Django.

## Endpoints

### 1. Generar Nota de Venta (PDF)
*   **URL**: `/pdf/nota-venta`
*   **Método**: `POST`
*   **Payload**: Datos del pedido, cliente y detalles.
*   **Retorno**: Archivo binario PDF.

### 2. Generar Etiqueta de Producto (ZPL)
*   **URL**: `/zpl/etiqueta`
*   **Método**: `POST`
*   **Payload**: Datos del lote, producto y peso.
*   **Retorno**: Cadena de texto ZPL cruda.

## Integración con Django

El backend (`gestion`) se comunica con este servicio a través de la clase utilitaria `PrintingService` ubicada en `gestion/utils.py`.

```python
# Ejemplo de uso
pdf_content = PrintingService.generate_nota_venta_pdf(data_dict)
```

## Reconciliación Automática de Pagos

Junto con las mejoras de impresión, se implementó un sistema de **Reconciliación FIFO** para los pagos de clientes:

1.  Cada vez que se registra un **Pago** o se crea un **Pedido**, el sistema recalcula el estado de la deuda.
2.  Los pagos se aplican a los pedidos más antiguos primero (First In, First Out).
3.  El estado `esta_pagado` de los pedidos se actualiza automáticamente en base al saldo disponible del cliente.
