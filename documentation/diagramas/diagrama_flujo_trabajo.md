# Diagrama de Flujo de Trabajo (Producción y Venta)

```mermaid
flowchart TD
    Start((Inicio)) --> Venta[Pedido de Venta Recibido]
    Venta --> CheckStock{¿Hay Stock Disponible?}
    
    %% Flujo si hay stock
    CheckStock -- Sí --> Despacho[Generar Orden de Despacho]
    Despacho --> SalidaInv[Registrar Salida de Inventario]
    SalidaInv --> Facturacion[Facturar y Entregar]
    Facturacion --> Fin((Fin))

    %% Flujo si NO hay stock (Producción)
    CheckStock -- No --> Planificacion[Planificar Producción]
    Planificacion --> OrdenProd[Crear Orden de Producción]
    OrdenProd --> CheckMat{¿Hay Materia Prima?}
    
    CheckMat -- No --> Compra[Generar Orden de Compra/Requisición]
    Compra --> Recepcion[Recepción de Material (Batch)]
    Recepcion --> CheckMat
    
    CheckMat -- Sí --> ProdProceso[Producción en Proceso]
    ProdProceso --> ConsumoMat[Consumo de Materia Prima]
    ConsumoMat --> RegistroLote[Registrar Lote Producido]
    RegistroLote --> Calidad{¿Control de Calidad OK?}
    
    Calidad -- No --> Reproceso[Reproceso / Descarte]
    Reproceso --> ProdProceso
    
    Calidad -- Sí --> IngresoInv[Ingreso a Bodega Producto Terminado]
    IngresoInv --> CheckPendientes{¿Atiende Pedido Pendiente?}
    
    CheckPendientes -- Sí --> Despacho
    CheckPendientes -- No --> StockAlmacen[Almacenar en Stock]
    StockAlmacen --> Fin
```
