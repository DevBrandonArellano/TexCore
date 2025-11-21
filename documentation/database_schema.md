# Esquema de la Base de Datos

Este documento detalla la estructura de la base de datos y las relaciones entre las tablas principales.

## Diagrama Entidad-Relación (ERD)

```mermaid
erDiagram
    CustomUser {
        int id PK
        string username
        string email
        string role
    }

    Sede {
        int id PK
        string name
        string location
        string status
    }

    Area {
        int id PK
        string name
        int sede_id FK
    }

    Bodega {
        int id PK
        string name
        int area_id FK
    }

    Producto {
        int id PK
        string name
        string description
        float stock_minimo
    }

    FormulaColor {
        int id PK
        string name
        int producto_id FK
    }

    OrdenProduccion {
        int id PK
        int formula_id FK
        int bodega_id FK
        float cantidad
        string status
        bool inventario_descontado
    }

    Cliente {
        int id PK
        string name
        string contact_info
    }

    PedidoVenta {
        int id PK
        int cliente_id FK
        string status
        datetime created_at
    }

    StockBodega {
        int id PK
        int producto_id FK
        int bodega_id FK
        float cantidad
    }

    MovimientoInventario {
        int id PK
        int producto_id FK
        int bodega_id FK
        string tipo_movimiento
        float cantidad
        datetime timestamp
    }

    Sede ||--|{ Area : "contiene"
    Area ||--|{ Bodega : "contiene"
    Sede ||--o{ CustomUser : "emplea"

    Producto ||--o{ FormulaColor : "es base de"
    FormulaColor ||--o{ OrdenProduccion : "se produce en"
    Bodega ||--o{ OrdenProduccion : "se asigna a"

    Cliente ||--o{ PedidoVenta : "realiza"

    Producto ||--o{ StockBodega : "tiene stock en"
    Bodega ||--o{ StockBodega : "almacena"

    Producto ||--o{ MovimientoInventario : "registra movimiento de"
    Bodega ||--o{ MovimientoInventario : "ocurre en"
```

## Descripción de Tablas Clave

-   **`gestion` (App Principal):**
    -   `CustomUser`: Almacena los usuarios y sus roles.
    -   `Sede`, `Area`, `Bodega`: Definen la estructura organizativa física.
    -   `Producto`: Catálogo de productos.
    -   `OrdenProduccion`: Órdenes para producir un producto a partir de una fórmula en una bodega específica.
    -   `PedidoVenta`: Pedidos de venta realizados por clientes.

-   **`inventory` (App de Inventario):**
    -   `StockBodega`: Tabla de resumen que muestra la cantidad actual (`stock`) de cada producto en cada bodega. Se actualiza con cada movimiento.
    -   `MovimientoInventario`: Actúa como un "Kardex", registrando cada entrada, salida, transferencia o ajuste de inventario. Proporciona un historial completo y trazabilidad.

## Relaciones Importantes

-   `StockBodega` y `MovimientoInventario` son el núcleo del sistema de inventario, conectando `Producto` y `Bodega` para dar una visión completa del stock.
-   `OrdenProduccion` conecta la producción (`FormulaColor`) con la logística (`Bodega`).
-   Las relaciones de `ForeignKey` en todo el esquema garantizan la integridad de los datos.
